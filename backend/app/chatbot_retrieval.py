"""Bounded, provider-independent, read-only retrieval for chatbot grounding."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
import json
import math
from pathlib import Path
import re
import sqlite3
from time import monotonic
from typing import TypeAlias

from .saved_hotel_data import SIMULATED_DATA_NOTICE


MAX_QUESTION_CHARACTERS = 500
MAX_SQL_CHARACTERS = 4_000
MAX_SQL_TOKENS = 512
MAX_BOUND_PARAMETERS = 24
MAX_PARAMETER_CHARACTERS = 500
MAX_PARAMETER_PAYLOAD_BYTES = 4_096
MAX_RETURNED_ROWS = 20
MAX_RETURNED_COLUMNS = 12
MAX_COLUMN_NAME_CHARACTERS = 64
MAX_CELL_CHARACTERS = 1_024
MAX_TOTAL_PAYLOAD_BYTES = 32 * 1_024
MAX_STAY_NIGHTS = 20
DEFAULT_EXECUTION_TIMEOUT_SECONDS = 0.25
PROGRESS_HANDLER_STEPS = 1_000

ALLOWED_TABLE_COLUMNS: dict[str, frozenset[str]] = {
    "saved_hotels": frozenset(
        {"hotel_id", "name", "address", "latitude", "longitude"}
    ),
    "saved_hotel_zip_associations": frozenset({"hotel_id", "postcode"}),
    "saved_search_contexts": frozenset(
        {"postcode", "country_code", "locality", "latitude", "longitude"}
    ),
    "demo_hotel_nights": frozenset(
        {
            "hotel_id",
            "stay_date",
            "nightly_rate_cents",
            "rooms_available",
        }
    ),
}
ALLOWED_FUNCTIONS = frozenset(
    {"coalesce", "count", "max", "min", "round", "sum"}
)

_PROHIBITED_KEYWORDS = frozenset(
    {
        "alter",
        "analyze",
        "attach",
        "begin",
        "commit",
        "create",
        "delete",
        "detach",
        "drop",
        "explain",
        "insert",
        "load_extension",
        "pragma",
        "recursive",
        "reindex",
        "release",
        "replace",
        "returning",
        "rollback",
        "savepoint",
        "transaction",
        "update",
        "vacuum",
    }
)
_INTEGER_TOKEN = re.compile(r"[0-9]+\Z")

ParameterValue: TypeAlias = str | int | float | None
CellValue: TypeAlias = str | int | float | None


@dataclass(frozen=True, slots=True)
class BoundParameter:
    """One positional SQLite parameter supplied separately from SQL text."""

    value: ParameterValue = field(repr=False)


@dataclass(frozen=True, slots=True)
class ProposedSqlStatement:
    """An untrusted model proposal containing SQL and positional bindings."""

    sql: str
    parameters: tuple[BoundParameter, ...] = ()


@dataclass(frozen=True, slots=True)
class RetrievedRecords:
    """A bounded, normalized table returned by an allowed query."""

    columns: tuple[str, ...]
    rows: tuple[tuple[CellValue, ...], ...]


@dataclass(frozen=True, slots=True)
class SafeRetrievalResult:
    """Successful evidence safe to use in a later grounding request."""

    proposed_sql: str
    records: RetrievedRecords
    simulated_data_notice: str = SIMULATED_DATA_NOTICE


@dataclass(frozen=True, slots=True)
class RejectedQuery:
    """A proposal rejected before safe evidence could be returned."""

    code: str
    message: str


@dataclass(frozen=True, slots=True)
class RetrievalExecutionFailure:
    """A safe execution failure that never exposes raw SQLite details."""

    code: str
    message: str


@dataclass(frozen=True, slots=True)
class SimulatedStaySummary:
    """Deterministic checkout-exclusive coverage and totals for one hotel."""

    hotel_id: str
    check_in: str
    check_out: str
    requested_nights: tuple[str, ...]
    missing_nights: tuple[str, ...]
    total_nightly_rate_cents: int | None
    minimum_rooms_available: int | None
    is_available: bool
    status: str
    simulated_data_notice: str = SIMULATED_DATA_NOTICE


RetrievalOutcome: TypeAlias = (
    SafeRetrievalResult | RejectedQuery | RetrievalExecutionFailure
)
StaySummaryOutcome: TypeAlias = (
    SimulatedStaySummary | RejectedQuery | RetrievalExecutionFailure
)


@dataclass(frozen=True, slots=True)
class _SqlToken:
    kind: str
    value: str
    depth: int
    parameter_index: int | None = None


@dataclass(slots=True)
class _AuthorizationState:
    denied: bool = False
    allowed_reads: int = 0


class _ProposalRejected(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.outcome = RejectedQuery(code=code, message=message)


def execute_read_only_retrieval(
    question: str,
    proposal: ProposedSqlStatement,
    database_path: Path,
    *,
    execution_timeout_seconds: float = DEFAULT_EXECUTION_TIMEOUT_SECONDS,
) -> RetrievalOutcome:
    """Validate and execute one bounded query against an existing database."""

    try:
        tokens = _validate_proposal(question, proposal)
        timeout_seconds = _validate_execution_timeout(
            execution_timeout_seconds
        )
    except _ProposalRejected as exc:
        return exc.outcome

    path = Path(database_path).resolve()
    if not path.is_file():
        return RetrievalExecutionFailure(
            code="database_unavailable",
            message="The local hotel database is unavailable.",
        )

    authorization = _AuthorizationState()
    deadline_reached = False
    connection: sqlite3.Connection | None = None

    def authorize(
        action_code: int,
        argument_one: str | None,
        argument_two: str | None,
        database_name: str | None,
        _trigger_or_view: str | None,
    ) -> int:
        if action_code == sqlite3.SQLITE_SELECT:
            return sqlite3.SQLITE_OK
        if action_code == sqlite3.SQLITE_READ:
            table_name = (argument_one or "").casefold()
            column_name = (argument_two or "").casefold()
            allowed_columns = ALLOWED_TABLE_COLUMNS.get(table_name)
            if (
                database_name == "main"
                and allowed_columns is not None
                and (column_name in allowed_columns or column_name == "")
            ):
                authorization.allowed_reads += 1
                return sqlite3.SQLITE_OK
        if action_code == sqlite3.SQLITE_FUNCTION:
            function_name = (argument_two or argument_one or "").casefold()
            if function_name in ALLOWED_FUNCTIONS:
                return sqlite3.SQLITE_OK
        authorization.denied = True
        return sqlite3.SQLITE_DENY

    deadline = monotonic() + timeout_seconds

    def stop_excessive_work() -> int:
        nonlocal deadline_reached
        if monotonic() >= deadline:
            deadline_reached = True
            return 1
        return 0

    try:
        connection = sqlite3.connect(
            f"{path.as_uri()}?mode=ro",
            uri=True,
            timeout=1.0,
        )
        connection.execute("PRAGMA query_only = ON")
        connection.execute("PRAGMA trusted_schema = OFF")
        connection.enable_load_extension(False)
        connection.set_authorizer(authorize)
        connection.set_progress_handler(
            stop_excessive_work,
            PROGRESS_HANDLER_STEPS,
        )
        values = tuple(parameter.value for parameter in proposal.parameters)
        cursor = connection.execute(proposal.sql, values)
        if authorization.allowed_reads == 0:
            return RejectedQuery(
                code="no_allowed_table_read",
                message="The query must read an approved local hotel table.",
            )
        records = _normalize_records(cursor)
        return SafeRetrievalResult(
            proposed_sql=proposal.sql,
            records=records,
        )
    except _ProposalRejected as exc:
        return exc.outcome
    except sqlite3.Error:
        if authorization.denied:
            return RejectedQuery(
                code="unauthorized_query",
                message="The query attempted an unauthorized database action.",
            )
        if deadline_reached:
            return RetrievalExecutionFailure(
                code="execution_timeout",
                message="The read-only query exceeded its execution limit.",
            )
        return RetrievalExecutionFailure(
            code="query_execution_failed",
            message="The read-only query could not be executed.",
        )
    except (OSError, TypeError, ValueError):
        return RetrievalExecutionFailure(
            code="query_execution_failed",
            message="The read-only query could not be executed.",
        )
    finally:
        if connection is not None:
            connection.set_progress_handler(None, 0)
            connection.set_authorizer(None)
            connection.close()


def summarize_simulated_stay(
    hotel_id: str,
    check_in: str,
    check_out: str,
    database_path: Path,
) -> StaySummaryOutcome:
    """Return checkout-exclusive coverage and totals from simulated nights."""

    try:
        requested_nights = _requested_nights(check_in, check_out)
        if not isinstance(hotel_id, str) or not hotel_id:
            _reject("invalid_stay", "A saved hotel identifier is required.")
        if len(hotel_id) > MAX_PARAMETER_CHARACTERS:
            _reject("invalid_stay", "The saved hotel identifier is too long.")
    except _ProposalRejected as exc:
        return exc.outcome

    proposal = ProposedSqlStatement(
        sql=(
            "SELECT stay_date, nightly_rate_cents, rooms_available "
            "FROM demo_hotel_nights "
            "WHERE hotel_id = ? AND stay_date >= ? AND stay_date < ? "
            "ORDER BY stay_date LIMIT 20"
        ),
        parameters=(
            BoundParameter(hotel_id),
            BoundParameter(check_in),
            BoundParameter(check_out),
        ),
    )
    outcome = execute_read_only_retrieval(
        "Evaluate checkout-exclusive simulated hotel nights.",
        proposal,
        database_path,
    )
    if not isinstance(outcome, SafeRetrievalResult):
        return outcome

    records_by_date: dict[str, tuple[int, int]] = {}
    try:
        for stay_date, nightly_rate_cents, rooms_available in (
            outcome.records.rows
        ):
            if (
                not isinstance(stay_date, str)
                or isinstance(nightly_rate_cents, bool)
                or not isinstance(nightly_rate_cents, int)
                or nightly_rate_cents < 0
                or isinstance(rooms_available, bool)
                or not isinstance(rooms_available, int)
                or rooms_available < 0
            ):
                raise ValueError
            records_by_date[stay_date] = (
                nightly_rate_cents,
                rooms_available,
            )
    except (TypeError, ValueError):
        return RetrievalExecutionFailure(
            code="invalid_retrieved_data",
            message="The retrieved simulated-night data is invalid.",
        )

    missing_nights = tuple(
        stay_date
        for stay_date in requested_nights
        if stay_date not in records_by_date
    )
    if missing_nights:
        return SimulatedStaySummary(
            hotel_id=hotel_id,
            check_in=check_in,
            check_out=check_out,
            requested_nights=requested_nights,
            missing_nights=missing_nights,
            total_nightly_rate_cents=None,
            minimum_rooms_available=None,
            is_available=False,
            status="missing_nights",
        )

    included_records = [
        records_by_date[stay_date] for stay_date in requested_nights
    ]
    total_nightly_rate_cents = sum(
        nightly_rate_cents
        for nightly_rate_cents, _rooms_available in included_records
    )
    minimum_rooms_available = min(
        rooms_available
        for _nightly_rate_cents, rooms_available in included_records
    )
    is_available = minimum_rooms_available > 0
    return SimulatedStaySummary(
        hotel_id=hotel_id,
        check_in=check_in,
        check_out=check_out,
        requested_nights=requested_nights,
        missing_nights=(),
        total_nightly_rate_cents=total_nightly_rate_cents,
        minimum_rooms_available=minimum_rooms_available,
        is_available=is_available,
        status="available" if is_available else "unavailable_rooms",
    )


def _validate_proposal(
    question: str,
    proposal: ProposedSqlStatement,
) -> tuple[_SqlToken, ...]:
    if not isinstance(question, str) or not question.strip():
        _reject("invalid_question", "A non-empty question is required.")
    if len(question) > MAX_QUESTION_CHARACTERS:
        _reject("invalid_question", "The question exceeds the allowed length.")
    if not isinstance(proposal, ProposedSqlStatement):
        _reject("invalid_proposal", "A typed SQL proposal is required.")
    if not isinstance(proposal.sql, str) or not proposal.sql.strip():
        _reject("invalid_sql", "A non-empty SQL statement is required.")
    if len(proposal.sql) > MAX_SQL_CHARACTERS:
        _reject("invalid_sql", "The SQL statement exceeds the allowed length.")
    if not isinstance(proposal.parameters, tuple):
        _reject("invalid_parameters", "Bound parameters must be a tuple.")
    if len(proposal.parameters) > MAX_BOUND_PARAMETERS:
        _reject(
            "parameter_limit_exceeded",
            "The query contains too many bound parameters.",
        )

    parameter_values: list[ParameterValue] = []
    for parameter in proposal.parameters:
        if not isinstance(parameter, BoundParameter):
            _reject(
                "invalid_parameters",
                "Every parameter must use the bound-parameter structure.",
            )
        _validate_parameter_value(parameter.value)
        parameter_values.append(parameter.value)
    parameter_payload = json.dumps(
        parameter_values,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    if len(parameter_payload) > MAX_PARAMETER_PAYLOAD_BYTES:
        _reject(
            "parameter_limit_exceeded",
            "The bound-parameter payload is too large.",
        )

    tokens = _scan_sql(proposal.sql)
    words = [token.value.casefold() for token in tokens if token.kind == "word"]
    if not words or words[0] not in {"select", "with"}:
        _reject(
            "non_select_statement",
            "Only one read-only SELECT statement is allowed.",
        )
    prohibited = _PROHIBITED_KEYWORDS.intersection(words)
    if prohibited:
        _reject(
            "prohibited_sql",
            "The SQL statement contains a prohibited operation.",
        )
    if words[0] == "with" and not any(
        token.depth == 0
        and token.kind == "word"
        and token.value.casefold() == "select"
        for token in tokens[1:]
    ):
        _reject(
            "non_select_statement",
            "A common-table expression must end in a read-only SELECT.",
        )

    placeholders = [token for token in tokens if token.kind == "parameter"]
    if len(placeholders) != len(proposal.parameters):
        _reject(
            "parameter_mismatch",
            "SQL placeholders and bound parameters do not match.",
        )
    _validate_bound_values(tokens)
    _validate_top_level_limit(tokens, proposal.parameters)
    return tokens


def _scan_sql(sql: str) -> tuple[_SqlToken, ...]:
    tokens: list[_SqlToken] = []
    position = 0
    depth = 0
    parameter_index = 0

    while position < len(sql):
        character = sql[position]
        next_two = sql[position : position + 2]
        if character.isspace():
            position += 1
            continue
        if next_two in {"--", "/*", "*/"}:
            _reject("comments_not_allowed", "SQL comments are not allowed.")
        if character == ";":
            _reject(
                "multiple_statements",
                "Statement separators are not allowed.",
            )
        if character in {"'", '"', "`", "[", "]"}:
            _reject(
                "literal_values_not_allowed",
                "Quoted SQL values and identifiers are not allowed; bind values.",
            )
        if character == "?":
            if position + 1 < len(sql) and sql[position + 1].isdigit():
                _reject(
                    "invalid_parameters",
                    "Only unnumbered positional placeholders are allowed.",
                )
            tokens.append(
                _SqlToken(
                    kind="parameter",
                    value=character,
                    depth=depth,
                    parameter_index=parameter_index,
                )
            )
            parameter_index += 1
            position += 1
            continue
        if character.isascii() and (character.isalpha() or character == "_"):
            end = position + 1
            while end < len(sql) and sql[end].isascii() and (
                sql[end].isalnum() or sql[end] == "_"
            ):
                end += 1
            tokens.append(_SqlToken("word", sql[position:end], depth))
            position = end
            continue
        if character.isdigit():
            end = position + 1
            while end < len(sql) and sql[end].isdigit():
                end += 1
            if (
                end < len(sql)
                and sql[end] == "."
                and end + 1 < len(sql)
                and sql[end + 1].isdigit()
            ):
                end += 2
                while end < len(sql) and sql[end].isdigit():
                    end += 1
            tokens.append(_SqlToken("number", sql[position:end], depth))
            position = end
            continue
        if character == "(":
            tokens.append(_SqlToken("punctuation", character, depth))
            depth += 1
            position += 1
            continue
        if character == ")":
            depth -= 1
            if depth < 0:
                _reject("invalid_sql", "The SQL parentheses are unbalanced.")
            tokens.append(_SqlToken("punctuation", character, depth))
            position += 1
            continue
        if character in {",", ".", "*", "+", "-", "/", "%", "=", "<", ">", "!", "|", "&", "~"}:
            if next_two in {"<=", ">=", "!=", "<>", "||", "=="}:
                tokens.append(_SqlToken("operator", next_two, depth))
                position += 2
            else:
                tokens.append(_SqlToken("operator", character, depth))
                position += 1
            continue
        _reject(
            "unsupported_sql_syntax",
            "The SQL statement contains unsupported syntax.",
        )

    if depth != 0:
        _reject("invalid_sql", "The SQL parentheses are unbalanced.")
    if not tokens or len(tokens) > MAX_SQL_TOKENS:
        _reject("invalid_sql", "The SQL statement is too complex.")
    return tuple(tokens)


def _validate_top_level_limit(
    tokens: tuple[_SqlToken, ...],
    parameters: tuple[BoundParameter, ...],
) -> None:
    limit_indexes = [
        index
        for index, token in enumerate(tokens)
        if token.depth == 0
        and token.kind == "word"
        and token.value.casefold() == "limit"
    ]
    if len(limit_indexes) != 1:
        _reject(
            "invalid_row_limit",
            "The query must end with one top-level row limit.",
        )
    limit_index = limit_indexes[0]
    value_index = limit_index + 1
    if value_index >= len(tokens):
        _reject("invalid_row_limit", "The row limit is missing.")
    value_token = tokens[value_index]
    if value_token.depth != 0:
        _reject("invalid_row_limit", "The row limit is invalid.")
    if value_token.kind == "number" and _INTEGER_TOKEN.fullmatch(
        value_token.value
    ):
        row_limit = int(value_token.value)
    elif (
        value_token.kind == "parameter"
        and value_token.parameter_index is not None
    ):
        parameter_value = parameters[value_token.parameter_index].value
        if isinstance(parameter_value, bool) or not isinstance(
            parameter_value, int
        ):
            _reject(
                "invalid_row_limit",
                "A bound row limit must be an integer.",
            )
        row_limit = parameter_value
    else:
        _reject(
            "invalid_row_limit",
            "The row limit must be a literal or bound integer.",
        )
    if row_limit < 1 or row_limit > MAX_RETURNED_ROWS:
        _reject(
            "row_limit_exceeded",
            f"The row limit must be between 1 and {MAX_RETURNED_ROWS}.",
        )
    if any(token.depth == 0 for token in tokens[value_index + 1 :]):
        _reject(
            "invalid_row_limit",
            "The top-level row limit must end the statement.",
        )


def _validate_bound_values(tokens: tuple[_SqlToken, ...]) -> None:
    for index, token in enumerate(tokens):
        if token.kind != "number":
            continue
        previous_token = tokens[index - 1] if index > 0 else None
        if not (
            previous_token is not None
            and previous_token.kind == "word"
            and previous_token.value.casefold() == "limit"
            and previous_token.depth == token.depth
        ):
            _reject(
                "literal_values_not_allowed",
                "Query values must use bound parameters.",
            )


def _validate_parameter_value(value: ParameterValue) -> None:
    if value is None:
        return
    if isinstance(value, bool):
        _reject("invalid_parameters", "Boolean parameters are not allowed.")
    if isinstance(value, str):
        if len(value) > MAX_PARAMETER_CHARACTERS:
            _reject(
                "parameter_limit_exceeded",
                "A bound text parameter is too long.",
            )
        return
    if isinstance(value, int):
        if not -(2**63) <= value <= 2**63 - 1:
            _reject(
                "invalid_parameters",
                "An integer parameter is outside SQLite's supported range.",
            )
        return
    if isinstance(value, float) and math.isfinite(value):
        return
    _reject(
        "invalid_parameters",
        "A bound parameter has an unsupported type.",
    )


def _validate_execution_timeout(value: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        _reject("invalid_execution_limit", "The execution limit is invalid.")
    timeout = float(value)
    if not math.isfinite(timeout) or timeout < 0 or timeout > 1.0:
        _reject("invalid_execution_limit", "The execution limit is invalid.")
    return timeout


def _normalize_records(cursor: sqlite3.Cursor) -> RetrievedRecords:
    description = cursor.description or ()
    columns = tuple(str(column[0]) for column in description)
    if not columns or len(columns) > MAX_RETURNED_COLUMNS:
        _reject(
            "column_limit_exceeded",
            "The retrieved column count is outside the allowed limit.",
        )
    if len({column.casefold() for column in columns}) != len(columns):
        _reject(
            "ambiguous_columns",
            "Retrieved column names must be unique.",
        )
    if any(
        not column or len(column) > MAX_COLUMN_NAME_CHARACTERS
        for column in columns
    ):
        _reject(
            "column_limit_exceeded",
            "A retrieved column name exceeds the allowed limit.",
        )

    fetched_rows = cursor.fetchmany(MAX_RETURNED_ROWS + 1)
    if len(fetched_rows) > MAX_RETURNED_ROWS:
        _reject(
            "row_limit_exceeded",
            "The query returned too many records.",
        )

    rows: list[tuple[CellValue, ...]] = []
    for fetched_row in fetched_rows:
        row: list[CellValue] = []
        for value in fetched_row:
            if value is None:
                row.append(None)
            elif isinstance(value, bool):
                row.append(int(value))
            elif isinstance(value, int):
                row.append(value)
            elif isinstance(value, float) and math.isfinite(value):
                row.append(value)
            elif isinstance(value, str):
                if len(value) > MAX_CELL_CHARACTERS:
                    _reject(
                        "cell_limit_exceeded",
                        "A retrieved value exceeds the allowed size.",
                    )
                row.append(value)
            else:
                _reject(
                    "unsupported_result_type",
                    "The query returned an unsupported value type.",
                )
        rows.append(tuple(row))

    payload = json.dumps(
        {"columns": columns, "rows": rows},
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    if len(payload) > MAX_TOTAL_PAYLOAD_BYTES:
        _reject(
            "payload_limit_exceeded",
            "The retrieved record payload exceeds the allowed size.",
        )
    return RetrievedRecords(columns=columns, rows=tuple(rows))


def _requested_nights(check_in: str, check_out: str) -> tuple[str, ...]:
    if not isinstance(check_in, str) or not isinstance(check_out, str):
        _reject("invalid_stay", "Stay dates must use YYYY-MM-DD.")
    try:
        arrival = date.fromisoformat(check_in)
        departure = date.fromisoformat(check_out)
    except ValueError:
        _reject("invalid_stay", "Stay dates must use YYYY-MM-DD.")
    if arrival.isoformat() != check_in or departure.isoformat() != check_out:
        _reject("invalid_stay", "Stay dates must use YYYY-MM-DD.")
    night_count = (departure - arrival).days
    if night_count < 1 or night_count > MAX_STAY_NIGHTS:
        _reject(
            "invalid_stay",
            f"A stay must include between 1 and {MAX_STAY_NIGHTS} nights.",
        )
    return tuple(
        (arrival + timedelta(days=offset)).isoformat()
        for offset in range(night_count)
    )


def _reject(code: str, message: str) -> None:
    raise _ProposalRejected(code, message)

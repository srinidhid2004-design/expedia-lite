"""Two-request, provider-independent orchestration for grounded answers."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import json
import math
from pathlib import Path
import httpx

from .chatbot_retrieval import (
    ALLOWED_FUNCTIONS,
    ALLOWED_TABLE_COLUMNS,
    MAX_BOUND_PARAMETERS,
    MAX_PARAMETER_CHARACTERS,
    MAX_PARAMETER_PAYLOAD_BYTES,
    MAX_QUESTION_CHARACTERS,
    MAX_RETURNED_ROWS,
    MAX_SQL_CHARACTERS,
    BoundParameter,
    CellValue,
    ProposedSqlStatement,
    RejectedQuery,
    RetrievalExecutionFailure,
    RetrievedRecords,
    SafeRetrievalResult,
    execute_read_only_retrieval,
)
from .config import GEMINI_MODEL_ID, get_gemini_api_key
from .gemini_client import (
    MAX_ANSWER_COMPLETION_TOKENS,
    MAX_SQL_COMPLETION_TOKENS,
    GeminiAuthenticationError,
    GeminiClientError,
    GeminiConfigurationError,
    GeminiEmptyResponseError,
    GeminiInvalidRequestError,
    GeminiMalformedResponseError,
    GeminiPermissionError,
    GeminiProviderError,
    GeminiQuotaError,
    GeminiRateLimitError,
    GeminiSafetyBlockedError,
    GeminiTimeoutError,
    request_structured_json,
)
from .saved_hotel_data import SIMULATED_DATA_NOTICE


MAX_INTENT_CHARACTERS = 300
MAX_ANSWER_CHARACTERS = 1_200
MAX_EXPLANATION_CHARACTERS = 600
MAX_LIMITATION_CHARACTERS = 400
DEFAULT_PROPOSAL_INTENT = "No model-provided intent was supplied."
_MISSING = object()


class RagOutcome(str, Enum):
    INVALID_QUESTION = "invalid_question"
    MISSING_CONFIGURATION = "missing_configuration"
    AUTHENTICATION_FAILURE = "authentication_failure"
    PERMISSION_FAILURE = "permission_failure"
    QUOTA_FAILURE = "quota_failure"
    RATE_LIMIT_FAILURE = "rate_limit_failure"
    TIMEOUT_FAILURE = "timeout_failure"
    INVALID_PROVIDER_REQUEST = "invalid_provider_request"
    PROVIDER_FAILURE = "provider_failure"
    SAFETY_BLOCKED = "safety_blocked"
    EMPTY_RESPONSE = "empty_response"
    MALFORMED_RESPONSE = "malformed_response"
    REJECTED_QUERY = "rejected_query"
    DATABASE_FAILURE = "database_failure"
    NO_MATCH = "no_match"
    GROUNDING_FAILURE = "grounding_failure"
    SUCCESS = "success"


class ProposalDiagnostic(str, Enum):
    """Non-sensitive structural classifications for proposal failures."""

    INVALID_RESPONSE_ENVELOPE = "invalid_response_envelope"
    MISSING_SQL = "missing_sql"
    MISSING_PARAMETERS = "missing_parameters"
    UNKNOWN_FIELDS = "unknown_fields"
    INVALID_SQL_FIELD = "invalid_sql_field"
    SQL_FIELD_TOO_LARGE = "sql_field_too_large"
    PARAMETERS_INVALID_SHAPE = "parameters_invalid_shape"
    TOO_MANY_PARAMETERS = "too_many_parameters"
    INVALID_PARAMETER_TYPE = "invalid_parameter_type"
    PARAMETER_VALUE_TOO_LARGE = "parameter_value_too_large"
    PARAMETER_PAYLOAD_TOO_LARGE = "parameter_payload_too_large"
    INVALID_INTENT = "invalid_intent"
    INTENT_TOO_LARGE = "intent_too_large"


@dataclass(frozen=True, slots=True)
class SafeParameterDisplay:
    position: int
    value: CellValue


@dataclass(frozen=True, slots=True)
class SqlProposal:
    statement: ProposedSqlStatement
    intent: str


@dataclass(frozen=True, slots=True)
class GroundedAnswer:
    answer: str
    referenced_row_numbers: tuple[int, ...]
    explanation: str
    limitation: str | None


@dataclass(frozen=True, slots=True)
class RagServiceResult:
    outcome: RagOutcome
    question: str
    model_identifier: str = GEMINI_MODEL_ID
    provider_request_count: int = 0
    proposed_sql: str | None = None
    parameters: tuple[SafeParameterDisplay, ...] = ()
    proposal_intent: str | None = None
    records: RetrievedRecords | None = None
    answer: str | None = None
    explanation: str | None = None
    referenced_row_numbers: tuple[int, ...] = ()
    limitation: str | None = None
    safe_message: str | None = None
    diagnostic_code: str | None = None


class _StructuredOutputError(ValueError):
    """Internal signal for malformed or unsafe structured output."""

    def __init__(self, diagnostic: ProposalDiagnostic) -> None:
        super().__init__(diagnostic.value)
        self.diagnostic = diagnostic


def answer_saved_hotel_question(
    question: str,
    database_path: Path,
    *,
    api_key: str | None = None,
    client: httpx.Client | None = None,
) -> RagServiceResult:
    """Run the fixed two-request flow without exposing SQLite to the model."""

    normalized_question = question.strip() if isinstance(question, str) else ""
    if (
        not normalized_question
        or len(normalized_question) > MAX_QUESTION_CHARACTERS
    ):
        return RagServiceResult(
            outcome=RagOutcome.INVALID_QUESTION,
            question=normalized_question,
            safe_message=(
                "Enter a question of no more than "
                f"{MAX_QUESTION_CHARACTERS} characters."
            ),
        )

    provider_key = get_gemini_api_key() if api_key is None else api_key
    if not isinstance(provider_key, str) or not provider_key.strip():
        return RagServiceResult(
            outcome=RagOutcome.MISSING_CONFIGURATION,
            question=normalized_question,
            safe_message="The language-model provider is not configured.",
        )

    if client is not None:
        return _run_two_request_flow(
            normalized_question,
            database_path,
            provider_key,
            client,
        )

    transport = httpx.HTTPTransport(retries=0)
    with httpx.Client(transport=transport) as owned_client:
        return _run_two_request_flow(
            normalized_question,
            database_path,
            provider_key,
            owned_client,
        )


def _run_two_request_flow(
    question: str,
    database_path: Path,
    api_key: str,
    client: httpx.Client,
) -> RagServiceResult:
    request_count = 0
    try:
        proposal_system, proposal_content = _sql_request_parts(question)
        proposal_payload = request_structured_json(
            api_key=api_key,
            system_instruction=proposal_system,
            user_content=proposal_content,
            response_schema=_sql_response_schema(),
            max_output_tokens=MAX_SQL_COMPLETION_TOKENS,
            client=client,
        )
        request_count += 1
    except GeminiClientError as exc:
        return _provider_failure_result(question, request_count + 1, exc)

    try:
        proposal = _parse_sql_proposal(proposal_payload)
    except _StructuredOutputError as exc:
        return RagServiceResult(
            outcome=RagOutcome.MALFORMED_RESPONSE,
            question=question,
            provider_request_count=request_count,
            safe_message="The model returned an invalid SQL proposal.",
            diagnostic_code=exc.diagnostic.value,
        )

    displayed_parameters = _safe_parameter_displays(
        proposal.statement.parameters
    )
    retrieval = execute_read_only_retrieval(
        question,
        proposal.statement,
        database_path,
    )
    trace = {
        "question": question,
        "provider_request_count": request_count,
        "proposed_sql": proposal.statement.sql,
        "parameters": displayed_parameters,
        "proposal_intent": proposal.intent,
    }
    if isinstance(retrieval, RejectedQuery):
        return RagServiceResult(
            outcome=RagOutcome.REJECTED_QUERY,
            safe_message=retrieval.message,
            **trace,
        )
    if isinstance(retrieval, RetrievalExecutionFailure):
        return RagServiceResult(
            outcome=RagOutcome.DATABASE_FAILURE,
            safe_message=retrieval.message,
            **trace,
        )
    if not isinstance(retrieval, SafeRetrievalResult):
        return RagServiceResult(
            outcome=RagOutcome.DATABASE_FAILURE,
            safe_message="The local hotel records could not be retrieved.",
            **trace,
        )
    if not retrieval.records.rows:
        return RagServiceResult(
            outcome=RagOutcome.NO_MATCH,
            records=retrieval.records,
            safe_message=(
                "No saved local hotel records matched the question. "
                "No generated answer was requested."
            ),
            **trace,
        )

    try:
        answer_system, answer_content = _answer_request_parts(
            question,
            retrieval.records,
        )
        answer_payload = request_structured_json(
            api_key=api_key,
            system_instruction=answer_system,
            user_content=answer_content,
            response_schema=_answer_response_schema(),
            max_output_tokens=MAX_ANSWER_COMPLETION_TOKENS,
            client=client,
        )
        request_count += 1
    except GeminiClientError as exc:
        return _provider_failure_result(
            question,
            request_count + 1,
            exc,
            proposed_sql=proposal.statement.sql,
            parameters=displayed_parameters,
            proposal_intent=proposal.intent,
            records=retrieval.records,
        )

    try:
        answer = _parse_grounded_answer(
            answer_payload,
            len(retrieval.records.rows),
        )
    except _StructuredOutputError as exc:
        return RagServiceResult(
            outcome=RagOutcome.GROUNDING_FAILURE,
            question=question,
            provider_request_count=request_count,
            proposed_sql=proposal.statement.sql,
            parameters=displayed_parameters,
            proposal_intent=proposal.intent,
            records=retrieval.records,
            safe_message=(
                "The model answer did not reference the retrieved records "
                "safely."
            ),
            diagnostic_code=exc.diagnostic.value,
        )

    return RagServiceResult(
        outcome=RagOutcome.SUCCESS,
        question=question,
        provider_request_count=request_count,
        proposed_sql=proposal.statement.sql,
        parameters=displayed_parameters,
        proposal_intent=proposal.intent,
        records=retrieval.records,
        answer=answer.answer,
        explanation=answer.explanation,
        referenced_row_numbers=answer.referenced_row_numbers,
        limitation=answer.limitation,
    )


def _sql_request_parts(question: str) -> tuple[str, str]:
    table_lines = [
        f"- {table}: {', '.join(sorted(columns))}"
        for table, columns in ALLOWED_TABLE_COLUMNS.items()
    ]
    system_message = "\n".join(
        (
            "Propose retrieval SQL for the local Expedia Lite classroom data.",
            "Use only this allowlisted schema:",
            *table_lines,
            f"Allowed SQL functions: {', '.join(sorted(ALLOWED_FUNCTIONS))}.",
            "Return exactly one SELECT or read-only WITH ... SELECT statement.",
            "Every text, date, postcode, status, threshold, price, room count, night count, zero, positive number, negative number, and comparison value must use an unnumbered ? placeholder.",
            "Numeric constants in WHERE, HAVING, CASE, and expressions must be bound parameters.",
            "The only permitted value literal is the final top-level LIMIT integer between 1 and 20.",
            "Parameters must appear in exact left-to-right placeholder order.",
            "For a two-night availability query, both the positive-availability threshold and required-night count must be parameters.",
            "Do not use comments, multiple statements, metadata, pragmas, mutations, schema operations, attachments, transactions, extensions, or recursive CTEs.",
            "Checkout is excluded. Every requested night must exist and have rooms_available greater than zero. Missing nights are unavailable.",
            "Multi-night total cost is the sum of nightly_rate_cents for included nights.",
            "Rates and room counts are simulated classroom data, not live inventory.",
            "Return only the schema-constrained JSON object requested by the API.",
            "Use the exact keys sql and parameters; intent is optional. Do not use aliases, prose, Markdown fences, multiple objects, or extra keys.",
            "Safe formatting example only; do not hard-code or bypass model generation:",
            "SQL:",
            "SELECT h.hotel_id, h.name,",
            "       SUM(n.nightly_rate_cents) AS total_cost_cents",
            "FROM saved_hotels AS h",
            "JOIN demo_hotel_nights AS n ON h.hotel_id = n.hotel_id",
            "WHERE n.stay_date IN (?, ?)",
            "  AND n.rooms_available > ?",
            "GROUP BY h.hotel_id, h.name",
            "HAVING COUNT(DISTINCT n.stay_date) = ?",
            "LIMIT 20",
            "Parameters:",
            '["2026-10-10", "2026-10-11", 0, 2]',
            "October 12 is checkout and therefore is not one of the occupied dates or parameters for this example.",
        )
    )
    return system_message, question


def _answer_request_parts(
    question: str,
    records: RetrievedRecords,
) -> tuple[str, str]:
    system_message = "\n".join(
        (
            "Answer only from the bounded records supplied by the backend.",
            "Do not identify a hotel that is not in those records.",
            "Use one-based row numbers to identify every record supporting the answer.",
            "Do not invent names, addresses, dates, rates, rooms, availability, or bookability.",
            f"Required data label: {SIMULATED_DATA_NOTICE}",
            "Checkout is excluded; missing nights must not be treated as available.",
            "State genuine limitations or insufficient fields plainly.",
            "Return only the schema-constrained JSON object requested by the API.",
            "Use the exact keys answer, referenced_row_numbers, and explanation; limitation is optional. Do not use aliases, prose, Markdown fences, multiple objects, or extra keys.",
            "Exact JSON example: {\"answer\":\"The returned hotel has a two-night simulated total of $200.00.\",\"referenced_row_numbers\":[1,2],\"explanation\":\"Rows 1 and 2 are the included nights; checkout is excluded.\",\"limitation\":\"Rates and room counts are simulated classroom data.\"}",
        )
    )
    evidence = json.dumps(
        {
            "question": question,
            "retrieved_records": {
                "columns": records.columns,
                "rows": records.rows,
            },
        },
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    )
    return system_message, evidence


def _sql_response_schema() -> dict[str, object]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["sql", "parameters"],
        "properties": {
            "sql": {
                "type": "string",
                "description": (
                    "One bounded read-only SELECT or WITH ... SELECT statement "
                    "using unnumbered ? bindings and a final LIMIT up to 20."
                ),
            },
            "parameters": {
                "type": "array",
                "maxItems": MAX_BOUND_PARAMETERS,
                "items": {
                    "type": ["string", "number", "integer", "null"]
                },
            },
            "intent": {
                "type": "string",
                "description": "Optional short description of the retrieval intent.",
            },
        },
    }


def _answer_response_schema() -> dict[str, object]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "answer",
            "referenced_row_numbers",
            "explanation",
        ],
        "properties": {
            "answer": {
                "type": "string",
                "description": "Grounded answer supported only by retrieved rows.",
            },
            "referenced_row_numbers": {
                "type": "array",
                "minItems": 1,
                "maxItems": MAX_RETURNED_ROWS,
                "items": {"type": "integer", "minimum": 1},
            },
            "explanation": {
                "type": "string",
                "description": "Explanation grounded only in referenced rows.",
            },
            "limitation": {
                "type": ["string", "null"],
                "description": "Optional genuine limitation of the bounded answer.",
            },
        },
    }


def _parse_sql_proposal(payload: dict[str, object]) -> SqlProposal:
    return _parse_sql_arguments(payload)


def _parse_sql_arguments(
    arguments: dict[str, object],
) -> SqlProposal:
    allowed_fields = {"sql", "parameters", "intent"}
    if set(arguments) - allowed_fields:
        raise _StructuredOutputError(ProposalDiagnostic.UNKNOWN_FIELDS)
    if "sql" not in arguments:
        raise _StructuredOutputError(ProposalDiagnostic.MISSING_SQL)
    if "parameters" not in arguments:
        raise _StructuredOutputError(ProposalDiagnostic.MISSING_PARAMETERS)
    sql = arguments["sql"]
    parameters = arguments["parameters"]
    intent = arguments.get("intent", _MISSING)
    if not isinstance(sql, str) or not sql.strip():
        raise _StructuredOutputError(ProposalDiagnostic.INVALID_SQL_FIELD)
    if len(sql) > MAX_SQL_CHARACTERS:
        raise _StructuredOutputError(ProposalDiagnostic.SQL_FIELD_TOO_LARGE)
    if not isinstance(parameters, list):
        raise _StructuredOutputError(
            ProposalDiagnostic.PARAMETERS_INVALID_SHAPE
        )
    if len(parameters) > MAX_BOUND_PARAMETERS:
        raise _StructuredOutputError(ProposalDiagnostic.TOO_MANY_PARAMETERS)
    if intent is _MISSING or (
        isinstance(intent, str) and not intent.strip()
    ):
        normalized_intent = DEFAULT_PROPOSAL_INTENT
    elif not isinstance(intent, str):
        raise _StructuredOutputError(ProposalDiagnostic.INVALID_INTENT)
    elif len(intent) > MAX_INTENT_CHARACTERS:
        raise _StructuredOutputError(ProposalDiagnostic.INTENT_TOO_LARGE)
    else:
        normalized_intent = intent.strip()

    parameter_values: list[CellValue] = []
    for value in parameters:
        if value is None:
            parameter_values.append(None)
        elif isinstance(value, bool):
            raise _StructuredOutputError(
                ProposalDiagnostic.INVALID_PARAMETER_TYPE
            )
        elif isinstance(value, str):
            if len(value) > MAX_PARAMETER_CHARACTERS:
                raise _StructuredOutputError(
                    ProposalDiagnostic.PARAMETER_VALUE_TOO_LARGE
                )
            parameter_values.append(value)
        elif isinstance(value, int):
            if not -(2**63) <= value <= 2**63 - 1:
                raise _StructuredOutputError(
                    ProposalDiagnostic.INVALID_PARAMETER_TYPE
                )
            parameter_values.append(value)
        elif isinstance(value, float) and math.isfinite(value):
            parameter_values.append(value)
        else:
            raise _StructuredOutputError(
                ProposalDiagnostic.INVALID_PARAMETER_TYPE
            )
    encoded_parameters = json.dumps(
        parameter_values,
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    if len(encoded_parameters) > MAX_PARAMETER_PAYLOAD_BYTES:
        raise _StructuredOutputError(
            ProposalDiagnostic.PARAMETER_PAYLOAD_TOO_LARGE
        )

    return SqlProposal(
        statement=ProposedSqlStatement(
            sql=sql,
            parameters=tuple(
                BoundParameter(value) for value in parameter_values
            ),
        ),
        intent=normalized_intent,
    )


def _parse_grounded_answer(
    payload: dict[str, object],
    row_count: int,
) -> GroundedAnswer:
    return _parse_grounded_answer_arguments(payload, row_count)


def _parse_grounded_answer_arguments(
    arguments: dict[str, object],
    row_count: int,
) -> GroundedAnswer:
    allowed_fields = {
        "answer",
        "referenced_row_numbers",
        "explanation",
        "limitation",
    }
    required_fields = {
        "answer",
        "referenced_row_numbers",
        "explanation",
    }
    if set(arguments) - allowed_fields or not required_fields <= set(arguments):
        raise _StructuredOutputError(
            ProposalDiagnostic.INVALID_RESPONSE_ENVELOPE
        )
    answer = arguments["answer"]
    row_numbers = arguments["referenced_row_numbers"]
    explanation = arguments["explanation"]
    limitation = arguments.get("limitation")
    if (
        not isinstance(answer, str)
        or not answer.strip()
        or len(answer) > MAX_ANSWER_CHARACTERS
        or not isinstance(explanation, str)
        or not explanation.strip()
        or len(explanation) > MAX_EXPLANATION_CHARACTERS
        or not isinstance(row_numbers, list)
        or not row_numbers
        or len(row_numbers) > MAX_RETURNED_ROWS
        or limitation is not None
        and (
            not isinstance(limitation, str)
            or len(limitation) > MAX_LIMITATION_CHARACTERS
        )
    ):
        raise _StructuredOutputError(
            ProposalDiagnostic.INVALID_RESPONSE_ENVELOPE
        )
    if any(
        isinstance(row_number, bool)
        or not isinstance(row_number, int)
        or row_number < 1
        or row_number > row_count
        for row_number in row_numbers
    ):
        raise _StructuredOutputError(
            ProposalDiagnostic.INVALID_RESPONSE_ENVELOPE
        )
    if len(set(row_numbers)) != len(row_numbers):
        raise _StructuredOutputError(
            ProposalDiagnostic.INVALID_RESPONSE_ENVELOPE
        )
    return GroundedAnswer(
        answer=answer.strip(),
        referenced_row_numbers=tuple(row_numbers),
        explanation=explanation.strip(),
        limitation=(
            limitation.strip()
            if isinstance(limitation, str) and limitation.strip()
            else None
        ),
    )


def _safe_parameter_displays(
    parameters: tuple[BoundParameter, ...],
) -> tuple[SafeParameterDisplay, ...]:
    return tuple(
        SafeParameterDisplay(position=index, value=parameter.value)
        for index, parameter in enumerate(parameters, start=1)
    )


def _provider_failure_result(
    question: str,
    request_count: int,
    error: GeminiClientError,
    *,
    proposed_sql: str | None = None,
    parameters: tuple[SafeParameterDisplay, ...] = (),
    proposal_intent: str | None = None,
    records: RetrievedRecords | None = None,
) -> RagServiceResult:
    mapping: tuple[
        tuple[type[GeminiClientError], RagOutcome, str], ...
    ] = (
        (
            GeminiConfigurationError,
            RagOutcome.MISSING_CONFIGURATION,
            "The language-model provider is not configured.",
        ),
        (
            GeminiAuthenticationError,
            RagOutcome.AUTHENTICATION_FAILURE,
            "The language-model provider rejected authentication.",
        ),
        (
            GeminiPermissionError,
            RagOutcome.PERMISSION_FAILURE,
            "The language-model provider denied access.",
        ),
        (
            GeminiQuotaError,
            RagOutcome.QUOTA_FAILURE,
            "The language-model provider quota is unavailable.",
        ),
        (
            GeminiRateLimitError,
            RagOutcome.RATE_LIMIT_FAILURE,
            "The language-model provider rate limit was reached.",
        ),
        (
            GeminiTimeoutError,
            RagOutcome.TIMEOUT_FAILURE,
            "The language-model provider request timed out.",
        ),
        (
            GeminiInvalidRequestError,
            RagOutcome.INVALID_PROVIDER_REQUEST,
            "The language-model provider rejected the bounded request.",
        ),
        (
            GeminiSafetyBlockedError,
            RagOutcome.SAFETY_BLOCKED,
            "The language-model provider blocked the request or response.",
        ),
        (
            GeminiEmptyResponseError,
            RagOutcome.EMPTY_RESPONSE,
            "The language-model provider returned no usable candidate.",
        ),
        (
            GeminiMalformedResponseError,
            RagOutcome.MALFORMED_RESPONSE,
            "The language-model provider returned an invalid response.",
        ),
        (
            GeminiProviderError,
            RagOutcome.PROVIDER_FAILURE,
            "The language-model provider request failed.",
        ),
    )
    outcome = RagOutcome.PROVIDER_FAILURE
    safe_message = "The language-model provider request failed."
    for error_type, candidate_outcome, candidate_message in mapping:
        if isinstance(error, error_type):
            outcome = candidate_outcome
            safe_message = candidate_message
            break
    return RagServiceResult(
        outcome=outcome,
        question=question,
        provider_request_count=request_count,
        proposed_sql=proposed_sql,
        parameters=parameters,
        proposal_intent=proposal_intent,
        records=records,
        safe_message=safe_message,
    )

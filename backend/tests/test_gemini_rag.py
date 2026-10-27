import hashlib
import json
from pathlib import Path
import sqlite3

import httpx
import pytest

from app.chatbot_retrieval import (
    MAX_BOUND_PARAMETERS,
    MAX_PARAMETER_CHARACTERS,
    MAX_PARAMETER_PAYLOAD_BYTES,
    MAX_SQL_CHARACTERS,
)
from app.config import GEMINI_GENERATE_CONTENT_URL, GEMINI_MODEL_ID
from app.gemini_client import (
    GEMINI_CONNECT_TIMEOUT_SECONDS,
    GEMINI_POOL_TIMEOUT_SECONDS,
    GEMINI_READ_TIMEOUT_SECONDS,
    GEMINI_WRITE_TIMEOUT_SECONDS,
    MAX_PROVIDER_REQUEST_BYTES,
    MAX_PROVIDER_RESPONSE_BYTES,
    GeminiInvalidRequestError,
    GeminiMalformedResponseError,
    request_structured_json,
)
from app.rag_service import (
    ProposalDiagnostic,
    RagOutcome,
    _sql_request_parts,
    answer_saved_hotel_question,
)


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "gemini_rag_scenarios.json"
FAKE_KEY = "fixture-gemini-key-not-a-real-credential"
QUESTION = (
    "Can hotel-a accommodate October 10 through checkout October 12, "
    "and what is the simulated total?"
)
LIVE_QUESTION = (
    "Among my saved hotels, which are available for both October 10 and "
    "October 11, 2026, and what is each hotel's total simulated cost for "
    "those two nights? Checkout is October 12, 2026."
)
SUPPORTED_PROVIDER_SCHEMA_KEYWORDS = {
    "type",
    "properties",
    "required",
    "additionalProperties",
    "items",
    "minItems",
    "maxItems",
    "minimum",
    "maximum",
    "anyOf",
    "oneOf",
    "title",
    "description",
}
UNSUPPORTED_PROVIDER_SCHEMA_KEYWORDS = {
    "minLength",
    "maxLength",
    "uniqueItems",
    "pattern",
}


@pytest.fixture
def scenarios() -> dict[str, object]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


@pytest.fixture
def rag_database(tmp_path: Path) -> Path:
    database_path = tmp_path / "gemini-rag.sqlite3"
    with sqlite3.connect(database_path) as connection:
        connection.executescript(
            """
            CREATE TABLE saved_hotels (
                hotel_id TEXT PRIMARY KEY,
                name TEXT,
                address TEXT,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL
            );
            CREATE TABLE saved_search_contexts (
                postcode TEXT PRIMARY KEY,
                country_code TEXT NOT NULL,
                locality TEXT,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL
            );
            CREATE TABLE saved_hotel_zip_associations (
                hotel_id TEXT NOT NULL,
                postcode TEXT NOT NULL,
                PRIMARY KEY (hotel_id, postcode)
            );
            CREATE TABLE demo_hotel_nights (
                hotel_id TEXT NOT NULL,
                stay_date TEXT NOT NULL,
                nightly_rate_cents INTEGER NOT NULL,
                rooms_available INTEGER NOT NULL,
                PRIMARY KEY (hotel_id, stay_date)
            );
            CREATE TABLE users (
                user_id TEXT PRIMARY KEY,
                full_name TEXT NOT NULL
            );
            """
        )
        connection.execute(
            """
            INSERT INTO saved_hotels
                (hotel_id, name, address, latitude, longitude)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                "hotel-a",
                "Scholar Hotel State College",
                "205 East Beaver Avenue",
                40.7946313,
                -77.8590467,
            ),
        )
        connection.execute(
            """
            INSERT INTO saved_search_contexts
                (postcode, country_code, locality, latitude, longitude)
            VALUES (?, ?, ?, ?, ?)
            """,
            ("16802", "US", "State College", 40.803167822, -77.861384958),
        )
        connection.execute(
            """
            INSERT INTO saved_hotel_zip_associations (hotel_id, postcode)
            VALUES (?, ?)
            """,
            ("hotel-a", "16802"),
        )
        connection.executemany(
            """
            INSERT INTO demo_hotel_nights
                (hotel_id, stay_date, nightly_rate_cents, rooms_available)
            VALUES (?, ?, ?, ?)
            """,
            (
                ("hotel-a", "2026-10-10", 10_000, 2),
                ("hotel-a", "2026-10-11", 12_000, 3),
                ("hotel-a", "2026-10-12", 15_000, 0),
            ),
        )
        connection.execute(
            "INSERT INTO users (user_id, full_name) VALUES (?, ?)",
            ("U001", "Unrelated classroom record"),
        )
    return database_path


def _snapshot(database_path: Path) -> tuple[str, tuple[int, ...]]:
    digest = hashlib.sha256(database_path.read_bytes()).hexdigest()
    with sqlite3.connect(database_path) as connection:
        counts = tuple(
            connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in (
                "saved_hotels",
                "saved_search_contexts",
                "saved_hotel_zip_associations",
                "demo_hotel_nights",
                "users",
            )
        )
    return digest, counts


def _fixture_response(payload: object, status_code: int = 200) -> httpx.Response:
    return httpx.Response(status_code, json=payload)


def _queued_client(
    payloads: list[object],
    requests: list[httpx.Request],
) -> httpx.Client:
    queue = list(payloads)

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if not queue:
            raise AssertionError("Unexpected extra provider request")
        item = queue.pop(0)
        if isinstance(item, Exception):
            raise item
        if isinstance(item, httpx.Response):
            return item
        return _fixture_response(item)

    return httpx.Client(transport=httpx.MockTransport(handler))


def _assert_supported_provider_schema(schema: dict[str, object]) -> None:
    assert set(schema) <= SUPPORTED_PROVIDER_SCHEMA_KEYWORDS
    assert not (set(schema) & UNSUPPORTED_PROVIDER_SCHEMA_KEYWORDS)
    properties = schema.get("properties")
    if isinstance(properties, dict):
        for property_schema in properties.values():
            assert isinstance(property_schema, dict)
            _assert_supported_provider_schema(property_schema)
    items = schema.get("items")
    if isinstance(items, dict):
        _assert_supported_provider_schema(items)
    for union_keyword in ("anyOf", "oneOf"):
        variants = schema.get(union_keyword)
        if isinstance(variants, list):
            for variant in variants:
                assert isinstance(variant, dict)
                _assert_supported_provider_schema(variant)


def _structured_fixture(payload: dict[str, object]) -> dict[str, object]:
    return {
        "candidates": [
            {
                "content": {
                    "role": "model",
                    "parts": [
                        {
                            "text": json.dumps(
                                payload,
                                ensure_ascii=False,
                                separators=(",", ":"),
                            )
                        }
                    ],
                },
                "finishReason": "STOP",
            }
        ]
    }


def test_sql_prompt_requires_all_non_limit_values_to_be_bound() -> None:
    system_instruction, question = _sql_request_parts(LIVE_QUESTION)

    assert question == LIVE_QUESTION
    assert (
        "Every text, date, postcode, status, threshold, price, room count, "
        "night count, zero, positive number, negative number, and comparison "
        "value must use an unnumbered ? placeholder."
        in system_instruction
    )
    assert (
        "Numeric constants in WHERE, HAVING, CASE, and expressions must be "
        "bound parameters."
        in system_instruction
    )
    assert (
        "The only permitted value literal is the final top-level LIMIT "
        "integer between 1 and 20."
        in system_instruction
    )
    assert "Parameters must appear in exact left-to-right placeholder order." in system_instruction
    assert (
        "both the positive-availability threshold and required-night count "
        "must be parameters"
        in system_instruction
    )
    assert "AND n.rooms_available > ?" in system_instruction
    assert "HAVING COUNT(DISTINCT n.stay_date) = ?" in system_instruction
    assert '["2026-10-10", "2026-10-11", 0, 2]' in system_instruction
    assert (
        "October 12 is checkout and therefore is not one of the occupied "
        "dates or parameters for this example."
        in system_instruction
    )


@pytest.mark.parametrize(
    ("unsafe_sql", "parameters"),
    (
        (
            """SELECT h.hotel_id, h.name,
                      SUM(n.nightly_rate_cents) AS total_cost_cents
               FROM saved_hotels AS h
               JOIN demo_hotel_nights AS n ON h.hotel_id = n.hotel_id
               WHERE n.stay_date IN (?, ?) AND n.rooms_available > 0
               GROUP BY h.hotel_id, h.name
               HAVING COUNT(DISTINCT n.stay_date) = ?
               LIMIT 20""",
            ["2026-10-10", "2026-10-11", 2],
        ),
        (
            """SELECT h.hotel_id, h.name,
                      SUM(n.nightly_rate_cents) AS total_cost_cents
               FROM saved_hotels AS h
               JOIN demo_hotel_nights AS n ON h.hotel_id = n.hotel_id
               WHERE n.stay_date IN (?, ?) AND n.rooms_available > ?
               GROUP BY h.hotel_id, h.name
               HAVING COUNT(DISTINCT n.stay_date) = 2
               LIMIT 20""",
            ["2026-10-10", "2026-10-11", 0],
        ),
    ),
)
def test_unbound_availability_or_night_count_is_rejected_before_request_two(
    unsafe_sql: str,
    parameters: list[object],
    rag_database: Path,
) -> None:
    requests: list[httpx.Request] = []
    before = _snapshot(rag_database)
    proposal = _structured_fixture(
        {
            "sql": unsafe_sql,
            "parameters": parameters,
            "intent": "Unsafe unbound numeric comparison fixture.",
        }
    )
    with _queued_client([proposal], requests) as client:
        result = answer_saved_hotel_question(
            LIVE_QUESTION, rag_database, api_key=FAKE_KEY, client=client
        )

    assert result.outcome is RagOutcome.REJECTED_QUERY
    assert result.provider_request_count == 1
    assert result.safe_message == "Query values must use bound parameters."
    assert len(requests) == 1
    assert _snapshot(rag_database) == before


def test_four_bound_values_preserve_order_and_reach_grounded_request_two(
    rag_database: Path,
) -> None:
    valid_sql = """SELECT h.hotel_id, h.name,
                           SUM(n.nightly_rate_cents) AS total_cost_cents
                    FROM saved_hotels AS h
                    JOIN demo_hotel_nights AS n ON h.hotel_id = n.hotel_id
                    WHERE n.stay_date IN (?, ?) AND n.rooms_available > ?
                    GROUP BY h.hotel_id, h.name
                    HAVING COUNT(DISTINCT n.stay_date) = ?
                    LIMIT 20"""
    ordered_parameters = ["2026-10-10", "2026-10-11", 0, 2]
    requests: list[httpx.Request] = []
    before = _snapshot(rag_database)
    proposal = _structured_fixture(
        {
            "sql": valid_sql,
            "parameters": ordered_parameters,
            "intent": "Retrieve hotels available on both occupied nights.",
        }
    )
    answer = _structured_fixture(
        {
            "answer": (
                "Scholar Hotel State College has a two-night simulated total "
                "of $220.00 with positive simulated availability."
            ),
            "referenced_row_numbers": [1],
            "explanation": (
                "Row 1 is the bounded aggregate for both occupied nights; "
                "October 12 checkout is excluded."
            ),
            "limitation": (
                "Rates and room counts are simulated classroom data."
            ),
        }
    )

    with _queued_client([proposal, answer], requests) as client:
        result = answer_saved_hotel_question(
            LIVE_QUESTION, rag_database, api_key=FAKE_KEY, client=client
        )

    assert result.outcome is RagOutcome.SUCCESS
    assert result.provider_request_count == 2
    assert result.proposed_sql is not None
    assert result.proposed_sql.rstrip().endswith("LIMIT 20")
    assert [parameter.value for parameter in result.parameters] == ordered_parameters
    assert result.records is not None
    assert result.records.rows == (
        ("hotel-a", "Scholar Hotel State College", 22_000),
    )
    assert result.referenced_row_numbers == (1,)
    assert result.answer is not None and "$220.00" in result.answer
    assert len(requests) == 2
    assert _snapshot(rag_database) == before


def test_unauthorized_table_proposal_is_rejected_without_request_two(
    rag_database: Path,
) -> None:
    requests: list[httpx.Request] = []
    before = _snapshot(rag_database)
    proposal = _structured_fixture(
        {
            "sql": "SELECT user_id FROM users LIMIT 20",
            "parameters": [],
            "intent": "Attempt an unauthorized read.",
        }
    )
    with _queued_client([proposal], requests) as client:
        result = answer_saved_hotel_question(
            LIVE_QUESTION, rag_database, api_key=FAKE_KEY, client=client
        )

    assert result.outcome is RagOutcome.REJECTED_QUERY
    assert result.provider_request_count == 1
    assert len(requests) == 1
    assert _snapshot(rag_database) == before


def test_success_uses_exactly_two_schema_constrained_requests(
    scenarios: dict[str, object],
    rag_database: Path,
) -> None:
    requests: list[httpx.Request] = []
    before = _snapshot(rag_database)
    with _queued_client(
        [scenarios["successful_sql"], scenarios["successful_answer"]],
        requests,
    ) as client:
        result = answer_saved_hotel_question(
            QUESTION,
            rag_database,
            api_key=FAKE_KEY,
            client=client,
        )

    assert result.outcome is RagOutcome.SUCCESS
    assert result.provider_request_count == 2
    assert result.model_identifier == GEMINI_MODEL_ID
    assert result.diagnostic_code is None
    assert result.proposed_sql is not None
    assert "n.stay_date < ?" in result.proposed_sql
    assert "n.rooms_available > ?" in result.proposed_sql
    assert [parameter.value for parameter in result.parameters] == [
        "hotel-a",
        "2026-10-10",
        "2026-10-12",
        0,
    ]
    assert result.records is not None
    assert result.records.rows == (
        ("hotel-a", "Scholar Hotel State College", "2026-10-10", 10_000, 2),
        ("hotel-a", "Scholar Hotel State College", "2026-10-11", 12_000, 3),
    )
    assert result.referenced_row_numbers == (1, 2)
    assert result.answer is not None and "$220.00" in result.answer
    assert len(requests) == 2
    assert _snapshot(rag_database) == before

    for request in requests:
        assert str(request.url) == GEMINI_GENERATE_CONTENT_URL
        assert request.url.query == b""
        assert request.headers["x-goog-api-key"] == FAKE_KEY
        assert "authorization" not in request.headers
        assert FAKE_KEY.encode() not in request.content
        timeout = request.extensions["timeout"]
        assert timeout == {
            "connect": GEMINI_CONNECT_TIMEOUT_SECONDS,
            "read": GEMINI_READ_TIMEOUT_SECONDS,
            "write": GEMINI_WRITE_TIMEOUT_SECONDS,
            "pool": GEMINI_POOL_TIMEOUT_SECONDS,
        }
        body = json.loads(request.content)
        generation_config = body["generationConfig"]
        assert generation_config["candidateCount"] == 1
        assert generation_config["responseMimeType"] == "application/json"
        assert "responseFormat" not in generation_config
        response_schema = generation_config["responseJsonSchema"]
        assert response_schema["type"] == "object"
        _assert_supported_provider_schema(response_schema)
        assert "tools" not in body
        assert "model" not in body
        assert "fallback" not in json.dumps(body).lower()

    second_user_payload = json.loads(
        json.loads(requests[1].content)["contents"][0]["parts"][0]["text"]
    )
    assert set(second_user_payload) == {"question", "retrieved_records"}
    serialized_second = json.dumps(second_user_payload).lower()
    assert "users" not in serialized_second
    assert "bookings" not in serialized_second
    assert "api_key" not in serialized_second
    assert "sqlite3" not in serialized_second


@pytest.mark.parametrize(
    ("proposal", "diagnostic"),
    (
        (
            {"sql": " ", "parameters": []},
            ProposalDiagnostic.INVALID_SQL_FIELD,
        ),
        (
            {"sql": "S" * (MAX_SQL_CHARACTERS + 1), "parameters": []},
            ProposalDiagnostic.SQL_FIELD_TOO_LARGE,
        ),
        (
            {
                "sql": "SELECT hotel_id FROM saved_hotels WHERE hotel_id = ? LIMIT 20",
                "parameters": ["x" * (MAX_PARAMETER_CHARACTERS + 1)],
            },
            ProposalDiagnostic.PARAMETER_VALUE_TOO_LARGE,
        ),
        (
            {
                "sql": "SELECT hotel_id FROM saved_hotels LIMIT 20",
                "parameters": [0] * (MAX_BOUND_PARAMETERS + 1),
            },
            ProposalDiagnostic.TOO_MANY_PARAMETERS,
        ),
        (
            {
                "sql": "SELECT hotel_id FROM saved_hotels LIMIT 20",
                "parameters": [
                    "x" * MAX_PARAMETER_CHARACTERS
                ] * min(
                    MAX_BOUND_PARAMETERS,
                    MAX_PARAMETER_PAYLOAD_BYTES // MAX_PARAMETER_CHARACTERS + 2,
                ),
            },
            ProposalDiagnostic.PARAMETER_PAYLOAD_TOO_LARGE,
        ),
        (
            {
                "sql": "SELECT hotel_id FROM saved_hotels LIMIT 20",
                "parameters": [],
                "unexpected": "not allowed",
            },
            ProposalDiagnostic.UNKNOWN_FIELDS,
        ),
    ),
)
def test_application_side_proposal_bounds_survive_provider_schema_reduction(
    proposal: dict[str, object],
    diagnostic: ProposalDiagnostic,
    rag_database: Path,
) -> None:
    requests: list[httpx.Request] = []
    before = _snapshot(rag_database)
    with _queued_client([_structured_fixture(proposal)], requests) as client:
        result = answer_saved_hotel_question(
            QUESTION, rag_database, api_key=FAKE_KEY, client=client
        )
    assert result.outcome is RagOutcome.MALFORMED_RESPONSE
    assert result.diagnostic_code == diagnostic.value
    assert result.provider_request_count == 1
    assert len(requests) == 1
    assert _snapshot(rag_database) == before


@pytest.mark.parametrize(
    "answer_payload",
    (
        {
            "answer": "A" * 1_201,
            "referenced_row_numbers": [1],
            "explanation": "Rows support the answer.",
        },
        {
            "answer": "Grounded answer.",
            "referenced_row_numbers": [1, 1],
            "explanation": "Duplicate row references are invalid.",
        },
        {
            "answer": "Grounded answer.",
            "referenced_row_numbers": [1],
            "explanation": "Rows support the answer.",
            "unexpected": "not allowed",
        },
    ),
)
def test_application_side_answer_bounds_survive_provider_schema_reduction(
    answer_payload: dict[str, object],
    scenarios: dict[str, object],
    rag_database: Path,
) -> None:
    requests: list[httpx.Request] = []
    before = _snapshot(rag_database)
    with _queued_client(
        [scenarios["successful_sql"], _structured_fixture(answer_payload)],
        requests,
    ) as client:
        result = answer_saved_hotel_question(
            QUESTION, rag_database, api_key=FAKE_KEY, client=client
        )
    assert result.outcome is RagOutcome.GROUNDING_FAILURE
    assert result.provider_request_count == 2
    assert len(requests) == 2
    assert _snapshot(rag_database) == before


def test_zero_rows_is_no_match_and_skips_request_two(
    scenarios: dict[str, object],
    rag_database: Path,
) -> None:
    requests: list[httpx.Request] = []
    before = _snapshot(rag_database)
    with _queued_client([scenarios["no_match_sql"]], requests) as client:
        result = answer_saved_hotel_question(
            QUESTION, rag_database, api_key=FAKE_KEY, client=client
        )
    after = _snapshot(rag_database)

    assert result.outcome is RagOutcome.NO_MATCH
    assert result.provider_request_count == 1
    assert result.proposed_sql == (
        "SELECT hotel_id, name FROM saved_hotels "
        "WHERE hotel_id = ? LIMIT 20"
    )
    assert [parameter.value for parameter in result.parameters] == ["absent-hotel"]
    assert result.records is not None and result.records.rows == ()
    assert result.answer is None
    assert result.explanation is None
    assert result.referenced_row_numbers == ()
    assert result.limitation is None
    assert result.safe_message == (
        "No saved local hotel records matched the question. "
        "No generated answer was requested."
    )
    assert len(requests) == 1
    assert after == before


def test_rejected_mutation_executes_no_sql_and_skips_request_two(
    scenarios: dict[str, object],
    rag_database: Path,
) -> None:
    requests: list[httpx.Request] = []
    before = _snapshot(rag_database)
    with _queued_client([scenarios["mutation_sql"]], requests) as client:
        result = answer_saved_hotel_question(
            QUESTION, rag_database, api_key=FAKE_KEY, client=client
        )
    after = _snapshot(rag_database)

    assert result.outcome is RagOutcome.REJECTED_QUERY
    assert result.provider_request_count == 1
    assert result.proposed_sql == "DELETE FROM saved_hotels WHERE hotel_id = ?"
    assert result.records is None
    assert result.answer is None
    assert result.explanation is None
    assert result.referenced_row_numbers == ()
    assert result.limitation is None
    assert result.safe_message == "Only one read-only SELECT statement is allowed."
    assert len(requests) == 1
    assert after == before


@pytest.mark.parametrize(
    ("scenario_name", "diagnostic"),
    (
        ("missing_sql", ProposalDiagnostic.MISSING_SQL),
        ("missing_parameters", ProposalDiagnostic.MISSING_PARAMETERS),
        ("unknown_field", ProposalDiagnostic.UNKNOWN_FIELDS),
        ("invalid_parameters", ProposalDiagnostic.INVALID_PARAMETER_TYPE),
    ),
)
def test_schema_invalid_proposals_stop_before_sql_and_request_two(
    scenario_name: str,
    diagnostic: ProposalDiagnostic,
    scenarios: dict[str, object],
    rag_database: Path,
) -> None:
    requests: list[httpx.Request] = []
    before = _snapshot(rag_database)
    with _queued_client([scenarios[scenario_name]], requests) as client:
        result = answer_saved_hotel_question(
            QUESTION, rag_database, api_key=FAKE_KEY, client=client
        )
    assert result.outcome is RagOutcome.MALFORMED_RESPONSE
    assert result.diagnostic_code == diagnostic.value
    assert result.provider_request_count == 1
    assert len(requests) == 1
    assert _snapshot(rag_database) == before


@pytest.mark.parametrize("scenario_name", ("malformed_json", "top_level_array"))
def test_malformed_structured_output_is_safe_and_stops(
    scenario_name: str,
    scenarios: dict[str, object],
    rag_database: Path,
) -> None:
    requests: list[httpx.Request] = []
    with _queued_client([scenarios[scenario_name]], requests) as client:
        result = answer_saved_hotel_question(
            QUESTION, rag_database, api_key=FAKE_KEY, client=client
        )
    assert result.outcome is RagOutcome.MALFORMED_RESPONSE
    assert result.provider_request_count == 1
    assert result.diagnostic_code is None
    assert len(requests) == 1


@pytest.mark.parametrize(
    ("scenario_name", "outcome"),
    (
        ("empty_candidates", RagOutcome.EMPTY_RESPONSE),
        ("safety_blocked_prompt", RagOutcome.SAFETY_BLOCKED),
        ("safety_blocked_candidate", RagOutcome.SAFETY_BLOCKED),
    ),
)
def test_empty_and_safety_blocked_candidates_are_distinct(
    scenario_name: str,
    outcome: RagOutcome,
    scenarios: dict[str, object],
    rag_database: Path,
) -> None:
    requests: list[httpx.Request] = []
    with _queued_client([scenarios[scenario_name]], requests) as client:
        result = answer_saved_hotel_question(
            QUESTION, rag_database, api_key=FAKE_KEY, client=client
        )
    assert result.outcome is outcome
    assert result.provider_request_count == 1
    assert len(requests) == 1


def test_invalid_grounding_is_rejected_after_exactly_two_requests(
    scenarios: dict[str, object],
    rag_database: Path,
) -> None:
    requests: list[httpx.Request] = []
    before = _snapshot(rag_database)
    with _queued_client(
        [scenarios["successful_sql"], scenarios["invalid_row_reference"]],
        requests,
    ) as client:
        result = answer_saved_hotel_question(
            QUESTION, rag_database, api_key=FAKE_KEY, client=client
        )
    assert result.outcome is RagOutcome.GROUNDING_FAILURE
    assert result.provider_request_count == 2
    assert result.diagnostic_code == ProposalDiagnostic.INVALID_RESPONSE_ENVELOPE
    assert len(requests) == 2
    assert _snapshot(rag_database) == before


@pytest.mark.parametrize(
    ("status_code", "body", "outcome"),
    (
        (401, {"error": {"status": "UNAUTHENTICATED"}}, RagOutcome.AUTHENTICATION_FAILURE),
        (403, {"error": {"status": "PERMISSION_DENIED"}}, RagOutcome.PERMISSION_FAILURE),
        (400, {"error": {"status": "INVALID_ARGUMENT"}}, RagOutcome.INVALID_PROVIDER_REQUEST),
        (429, {"error": {"status": "RESOURCE_EXHAUSTED"}}, RagOutcome.RATE_LIMIT_FAILURE),
        (503, {"error": {"status": "UNAVAILABLE"}}, RagOutcome.PROVIDER_FAILURE),
    ),
)
def test_provider_http_failures_are_safe_distinct_and_not_retried(
    status_code: int,
    body: dict[str, object],
    outcome: RagOutcome,
    rag_database: Path,
) -> None:
    requests: list[httpx.Request] = []
    response = _fixture_response(body, status_code=status_code)
    with _queued_client([response], requests) as client:
        result = answer_saved_hotel_question(
            QUESTION, rag_database, api_key=FAKE_KEY, client=client
        )
    assert result.outcome is outcome
    assert result.provider_request_count == 1
    assert len(requests) == 1
    assert "UNAUTHENTICATED" not in (result.safe_message or "")


def test_daily_quota_failure_is_distinct_from_rate_limit(
    rag_database: Path,
) -> None:
    requests: list[httpx.Request] = []
    quota_body = {
        "error": {
            "status": "RESOURCE_EXHAUSTED",
            "details": [
                {
                    "@type": "type.googleapis.com/google.rpc.QuotaFailure",
                    "violations": [
                        {"quotaId": "GenerateRequestsPerDayPerProjectPerModel-FreeTier"}
                    ],
                }
            ],
        }
    }
    with _queued_client([_fixture_response(quota_body, 429)], requests) as client:
        result = answer_saved_hotel_question(
            QUESTION, rag_database, api_key=FAKE_KEY, client=client
        )
    assert result.outcome is RagOutcome.QUOTA_FAILURE
    assert len(requests) == 1


def test_timeout_is_safe_and_not_retried(rag_database: Path) -> None:
    requests: list[httpx.Request] = []
    timeout = httpx.ReadTimeout("private transport detail")
    with _queued_client([timeout], requests) as client:
        result = answer_saved_hotel_question(
            QUESTION, rag_database, api_key=FAKE_KEY, client=client
        )
    assert result.outcome is RagOutcome.TIMEOUT_FAILURE
    assert result.provider_request_count == 1
    assert len(requests) == 1
    assert "private" not in (result.safe_message or "")


def test_oversized_request_is_rejected_before_transport() -> None:
    called = False

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal called
        called = True
        return _fixture_response({})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(GeminiInvalidRequestError):
            request_structured_json(
                api_key=FAKE_KEY,
                system_instruction="x" * MAX_PROVIDER_REQUEST_BYTES,
                user_content="question",
                response_schema={"type": "object"},
                max_output_tokens=512,
                client=client,
            )
    assert called is False


def test_oversized_and_duplicate_provider_responses_are_rejected() -> None:
    responses = (
        b"x" * (MAX_PROVIDER_RESPONSE_BYTES + 1),
        b'{"candidates":[],"candidates":[]}',
    )
    for raw_response in responses:
        calls = 0

        def handler(_request: httpx.Request) -> httpx.Response:
            nonlocal calls
            calls += 1
            return httpx.Response(200, content=raw_response)

        with httpx.Client(transport=httpx.MockTransport(handler)) as client:
            with pytest.raises(GeminiMalformedResponseError):
                request_structured_json(
                    api_key=FAKE_KEY,
                    system_instruction="fixed",
                    user_content="question",
                    response_schema={"type": "object"},
                    max_output_tokens=512,
                    client=client,
                )
        assert calls == 1


def test_missing_configuration_and_invalid_question_make_zero_requests(
    rag_database: Path,
) -> None:
    requests: list[httpx.Request] = []
    with _queued_client([], requests) as client:
        missing = answer_saved_hotel_question(
            QUESTION, rag_database, api_key="   ", client=client
        )
        invalid = answer_saved_hotel_question(
            " ", rag_database, api_key=FAKE_KEY, client=client
        )
    assert missing.outcome is RagOutcome.MISSING_CONFIGURATION
    assert invalid.outcome is RagOutcome.INVALID_QUESTION
    assert missing.provider_request_count == invalid.provider_request_count == 0
    assert requests == []


def test_fixture_and_contract_are_credential_free_and_fixed(
    scenarios: dict[str, object],
) -> None:
    assert scenarios["fixture"]["contains_credentials"] is False
    assert scenarios["fixture"]["network_required"] is False
    fixture_text = FIXTURE_PATH.read_text(encoding="utf-8")
    assert FAKE_KEY not in fixture_text
    assert "GEMINI_API_KEY" not in fixture_text
    assert GEMINI_MODEL_ID == "gemini-3.5-flash-lite"
    assert GEMINI_GENERATE_CONTENT_URL == (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        "gemini-3.5-flash-lite:generateContent"
    )

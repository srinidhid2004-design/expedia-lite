import json
from pathlib import Path
import sqlite3

import httpx
from fastapi.testclient import TestClient
import pytest

from app.chatbot_retrieval import RetrievedRecords
from app.config import GEMINI_GENERATE_CONTENT_URL, GEMINI_MODEL_ID
from app.main import create_app
from app.rag_service import (
    ProposalDiagnostic,
    RagOutcome,
    RagServiceResult,
    SafeParameterDisplay,
    answer_saved_hotel_question,
)
from app.saved_hotel_data import SIMULATED_DATA_NOTICE


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "gemini_rag_scenarios.json"
FAKE_KEY = "fixture-route-key-not-a-real-credential"
QUESTION = (
    "Can hotel-a accommodate October 10 through checkout October 12, "
    "and what is the simulated total?"
)


@pytest.fixture
def scenarios() -> dict[str, object]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


@pytest.fixture
def route_database(tmp_path: Path) -> Path:
    database_path = tmp_path / "chatbot-route.sqlite3"
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
            """
        )
        connection.execute(
            """
            INSERT INTO saved_hotels
                (hotel_id, name, address, latitude, longitude)
            VALUES (?, ?, ?, ?, ?)
            """,
            ("hotel-a", "Scholar Hotel State College", None, 40.79, -77.85),
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
            ),
        )
    return database_path


def _fixture_response(payload: object) -> httpx.Response:
    return httpx.Response(200, json=payload)


def test_route_preserves_complete_success_trace_with_mocked_gemini(
    scenarios: dict[str, object],
    route_database: Path,
    tmp_path: Path,
) -> None:
    requests: list[httpx.Request] = []
    queue = [scenarios["successful_sql"], scenarios["successful_answer"]]

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return _fixture_response(queue.pop(0))

    with httpx.Client(transport=httpx.MockTransport(handler)) as provider_client:
        def service(question: str, database_path: Path) -> RagServiceResult:
            return answer_saved_hotel_question(
                question,
                database_path,
                api_key=FAKE_KEY,
                client=provider_client,
            )

        app = create_app(
            route_database,
            env_path=tmp_path / "missing-test-env",
            chatbot_service=service,
        )
        with TestClient(app) as client:
            response = client.post(
                "/api/chatbot/query",
                json={"question": QUESTION},
            )

    assert response.status_code == 200
    payload = response.json()
    assert payload["outcome"] == "success"
    assert payload["provider_request_count"] == 2
    assert payload["diagnostic_code"] is None
    assert payload["question"] == QUESTION
    assert payload["model_identifier"] == GEMINI_MODEL_ID
    assert payload["proposed_sql"].endswith("ORDER BY n.stay_date LIMIT 20")
    assert payload["parameters"] == [
        {"position": 1, "value": "hotel-a"},
        {"position": 2, "value": "2026-10-10"},
        {"position": 3, "value": "2026-10-12"},
        {"position": 4, "value": 0},
    ]
    assert payload["records"] == {
        "columns": [
            "hotel_id",
            "name",
            "stay_date",
            "nightly_rate_cents",
            "rooms_available",
        ],
        "rows": [
            ["hotel-a", "Scholar Hotel State College", "2026-10-10", 10000, 2],
            ["hotel-a", "Scholar Hotel State College", "2026-10-11", 12000, 3],
        ],
    }
    assert "$220.00" in payload["answer"]
    assert payload["referenced_row_numbers"] == [1, 2]
    assert payload["simulated_data_notice"] == SIMULATED_DATA_NOTICE
    assert len(requests) == 2
    assert all(str(request.url) == GEMINI_GENERATE_CONTENT_URL for request in requests)


@pytest.mark.parametrize(
    ("outcome", "status_code"),
    (
        (RagOutcome.SUCCESS, 200),
        (RagOutcome.NO_MATCH, 200),
        (RagOutcome.INVALID_QUESTION, 400),
        (RagOutcome.MISSING_CONFIGURATION, 503),
        (RagOutcome.AUTHENTICATION_FAILURE, 502),
        (RagOutcome.PERMISSION_FAILURE, 502),
        (RagOutcome.QUOTA_FAILURE, 429),
        (RagOutcome.RATE_LIMIT_FAILURE, 429),
        (RagOutcome.TIMEOUT_FAILURE, 504),
        (RagOutcome.INVALID_PROVIDER_REQUEST, 502),
        (RagOutcome.PROVIDER_FAILURE, 502),
        (RagOutcome.SAFETY_BLOCKED, 502),
        (RagOutcome.EMPTY_RESPONSE, 502),
        (RagOutcome.MALFORMED_RESPONSE, 502),
        (RagOutcome.REJECTED_QUERY, 422),
        (RagOutcome.DATABASE_FAILURE, 500),
        (RagOutcome.GROUNDING_FAILURE, 502),
    ),
)
def test_every_outcome_has_a_stable_http_mapping(
    outcome: RagOutcome,
    status_code: int,
    route_database: Path,
    tmp_path: Path,
) -> None:
    records = (
        RetrievedRecords(columns=("hotel_id",), rows=())
        if outcome is RagOutcome.NO_MATCH
        else None
    )

    def service(question: str, _database_path: Path) -> RagServiceResult:
        return RagServiceResult(
            outcome=outcome,
            question=question,
            provider_request_count=0,
            records=records,
            safe_message="A safe fixed message.",
        )

    app = create_app(
        route_database,
        env_path=tmp_path / "missing-test-env",
        chatbot_service=service,
    )
    with TestClient(app) as client:
        response = client.post("/api/chatbot/query", json={"question": QUESTION})
    assert response.status_code == status_code
    assert response.json()["model_identifier"] == GEMINI_MODEL_ID


def test_rejected_sql_trace_is_returned_but_never_executed(
    route_database: Path,
    tmp_path: Path,
) -> None:
    with sqlite3.connect(route_database) as connection:
        before = connection.execute("SELECT COUNT(*) FROM saved_hotels").fetchone()[0]

    def service(question: str, _database_path: Path) -> RagServiceResult:
        return RagServiceResult(
            outcome=RagOutcome.REJECTED_QUERY,
            question=question,
            provider_request_count=1,
            proposed_sql="DELETE FROM saved_hotels WHERE hotel_id = ?",
            parameters=(SafeParameterDisplay(1, "hotel-a"),),
            safe_message="The proposed retrieval query was rejected.",
        )

    app = create_app(
        route_database,
        env_path=tmp_path / "missing-test-env",
        chatbot_service=service,
    )
    with TestClient(app) as client:
        response = client.post("/api/chatbot/query", json={"question": QUESTION})
    assert response.status_code == 422
    assert response.json()["proposed_sql"].startswith("DELETE")
    with sqlite3.connect(route_database) as connection:
        after = connection.execute("SELECT COUNT(*) FROM saved_hotels").fetchone()[0]
    assert after == before


def test_only_fixed_diagnostics_are_exposed(
    route_database: Path,
    tmp_path: Path,
) -> None:
    for diagnostic in ProposalDiagnostic:
        def service(question: str, _database_path: Path) -> RagServiceResult:
            return RagServiceResult(
                outcome=RagOutcome.MALFORMED_RESPONSE,
                question=question,
                provider_request_count=1,
                diagnostic_code=diagnostic.value,
                safe_message="The provider returned invalid structured output.",
            )

        app = create_app(
            route_database,
            env_path=tmp_path / "missing-test-env",
            chatbot_service=service,
        )
        with TestClient(app) as client:
            payload = client.post(
                "/api/chatbot/query", json={"question": QUESTION}
            ).json()
        assert payload["diagnostic_code"] == diagnostic.value

    unsafe = "Bearer secret C:\\private\\database.sqlite3 SELECT private"

    def unsafe_service(question: str, _database_path: Path) -> RagServiceResult:
        return RagServiceResult(
            outcome=RagOutcome.MALFORMED_RESPONSE,
            question=question,
            provider_request_count=1,
            diagnostic_code=unsafe,
            safe_message="A safe fixed message.",
        )

    app = create_app(
        route_database,
        env_path=tmp_path / "missing-test-env",
        chatbot_service=unsafe_service,
    )
    with TestClient(app) as client:
        response_text = client.post(
            "/api/chatbot/query", json={"question": QUESTION}
        ).text
    assert unsafe not in response_text
    assert "private" not in response_text.lower()


@pytest.mark.parametrize(
    "request_body",
    (
        {},
        {"question": 123},
        {"question": QUESTION, "model": "browser-selected"},
        {"question": QUESTION, "endpoint": "https://example.invalid"},
        {"question": QUESTION, "api_key": "browser-secret"},
        {"question": QUESTION, "sql": "SELECT 1"},
        {"question": QUESTION, "database_path": "private.sqlite3"},
        {"question": QUESTION, "prompt": "override"},
    ),
)
def test_route_accepts_only_one_question_string(
    request_body: dict[str, object],
    route_database: Path,
    tmp_path: Path,
) -> None:
    called = False

    def service(_question: str, _database_path: Path) -> RagServiceResult:
        nonlocal called
        called = True
        raise AssertionError("Invalid request must not call the service")

    app = create_app(
        route_database,
        env_path=tmp_path / "missing-test-env",
        chatbot_service=service,
    )
    with TestClient(app) as client:
        response = client.post("/api/chatbot/query", json=request_body)
    assert response.status_code == 422
    assert response.json()["outcome"] == "invalid_question"
    assert called is False


def test_safe_health_and_existing_routes_remain_registered(
    route_database: Path,
    tmp_path: Path,
) -> None:
    env_path = tmp_path / "test.env"
    env_path.write_text(
        "GEOAPIFY_API_KEY=\nGEMINI_API_KEY=\n",
        encoding="utf-8",
    )
    app = create_app(route_database, env_path=env_path)
    route_paths = {route.path for route in app.routes}
    assert {
        "/api/health",
        "/api/chatbot/query",
        "/api/demo/zip-location",
        "/api/zip-location",
        "/api/hotels/nearby",
        "/api/hotels/saved",
        "/api/hotels/search",
        "/api/users",
        "/api/bookings",
    } <= route_paths
    with TestClient(app) as client:
        response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "geoapify_api_key": "key is not configured",
        "gemini_api_key": "key is not configured",
    }


def test_response_contract_cannot_echo_credentials_or_internal_requests(
    route_database: Path,
    tmp_path: Path,
) -> None:
    attempted_secret = "attempted-fixture-secret"

    def service(question: str, _database_path: Path) -> RagServiceResult:
        return RagServiceResult(
            outcome=RagOutcome.PROVIDER_FAILURE,
            question=question,
            provider_request_count=1,
            safe_message="The language-model provider request failed.",
        )

    app = create_app(
        route_database,
        env_path=tmp_path / "missing-test-env",
        chatbot_service=service,
    )
    with TestClient(app) as client:
        response_text = client.post(
            "/api/chatbot/query", json={"question": QUESTION}
        ).text
    for forbidden in (
        attempted_secret,
        "x-goog-api-key",
        GEMINI_GENERATE_CONTENT_URL,
        "systemInstruction",
        str(route_database),
        "authorization",
    ):
        assert forbidden not in response_text

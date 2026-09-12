from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health() -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_search_returns_joined_stays() -> None:
    response = client.get("/api/hotels/search", params={"name": "Harbor"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["query"] == "Harbor"
    assert payload["count"] == 2
    assert [stay["trip_id"] for stay in payload["results"]] == ["T001", "T009"]


def test_search_returns_clear_empty_result() -> None:
    response = client.get("/api/hotels/search", params={"name": "Ocean Palace"})

    assert response.status_code == 200
    assert response.json()["count"] == 0
    assert response.json()["results"] == []


def test_search_rejects_whitespace_only_name() -> None:
    response = client.get("/api/hotels/search", params={"name": "   "})

    assert response.status_code == 400
    assert response.json() == {"detail": "Enter a hotel name."}


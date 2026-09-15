from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client(tmp_path) -> Iterator[TestClient]:
    with TestClient(create_app(tmp_path / "api.sqlite3")) as test_client:
        yield test_client


def test_health(client: TestClient) -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_search_returns_joined_stays(client: TestClient) -> None:
    response = client.get("/api/hotels/search", params={"name": "Harbor"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["query"] == "Harbor"
    assert payload["count"] == 2
    assert [stay["trip_id"] for stay in payload["results"]] == ["T001", "T009"]


def test_search_returns_clear_empty_result(client: TestClient) -> None:
    response = client.get("/api/hotels/search", params={"name": "Ocean Palace"})

    assert response.status_code == 200
    assert response.json()["count"] == 0
    assert response.json()["results"] == []


def test_search_rejects_whitespace_only_name(client: TestClient) -> None:
    response = client.get("/api/hotels/search", params={"name": "   "})

    assert response.status_code == 400
    assert response.json() == {"detail": "Enter a hotel name."}


def test_lists_demo_travelers_and_seeded_history(client: TestClient) -> None:
    users_response = client.get("/api/users")
    history_response = client.get("/api/bookings", params={"user_id": "U001"})

    assert users_response.status_code == 200
    assert users_response.json()["count"] == 6
    assert users_response.json()["results"][0] == {
        "user_id": "U001",
        "display_name": "Demo Traveler 1",
    }

    assert history_response.status_code == 200
    assert history_response.json()["count"] == 2
    assert [booking["status"] for booking in history_response.json()["results"]] == [
        "confirmed",
        "cancelled",
    ]


def test_create_cancel_and_delete_booking_through_api(client: TestClient) -> None:
    create_response = client.post(
        "/api/bookings",
        json={"user_id": "U006", "trip_id": "T012"},
    )

    assert create_response.status_code == 201
    created = create_response.json()["booking"]
    assert created["booking_id"] == "B007"
    assert created["user_id"] == "U006"
    assert created["trip_id"] == "T012"
    assert created["status"] == "confirmed"

    read_response = client.get("/api/bookings", params={"user_id": "U006"})
    assert read_response.json()["results"] == [created]

    cancel_response = client.patch("/api/bookings/B007/cancel")
    assert cancel_response.status_code == 200
    assert cancel_response.json()["booking"]["status"] == "cancelled"

    retained_response = client.get("/api/bookings", params={"user_id": "U006"})
    assert retained_response.json()["count"] == 1
    assert retained_response.json()["results"][0]["status"] == "cancelled"

    delete_response = client.delete("/api/bookings/B007")
    assert delete_response.status_code == 200
    assert delete_response.json() == {"deleted_booking_id": "B007"}

    final_response = client.get("/api/bookings", params={"user_id": "U006"})
    assert final_response.json() == {"count": 0, "results": []}


@pytest.mark.parametrize(
    ("payload", "detail"),
    [
        (
            {"user_id": "U999", "trip_id": "T001"},
            "The selected traveler does not exist.",
        ),
        (
            {"user_id": "U001", "trip_id": "T999"},
            "The selected stay does not exist.",
        ),
    ],
)
def test_create_rejects_unknown_records(
    client: TestClient,
    payload: dict[str, str],
    detail: str,
) -> None:
    response = client.post("/api/bookings", json=payload)

    assert response.status_code == 400
    assert response.json() == {"detail": detail}


def test_booking_mutations_return_not_found(client: TestClient) -> None:
    cancel_response = client.patch("/api/bookings/B999/cancel")
    delete_response = client.delete("/api/bookings/B999")

    assert cancel_response.status_code == 404
    assert delete_response.status_code == 404

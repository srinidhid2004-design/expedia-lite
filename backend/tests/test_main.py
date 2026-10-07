from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.location_controller import (
    GeoapifyConfigurationError,
    GeoapifyRequestError,
    ZipLocation,
    ZipLookupUnresolvedError,
)


@pytest.fixture
def client(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[TestClient]:
    monkeypatch.delenv("GEOAPIFY_API_KEY", raising=False)
    with TestClient(
        create_app(tmp_path / "api.sqlite3", tmp_path / ".env")
    ) as test_client:
        yield test_client


def test_health(client: TestClient) -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "geoapify_api_key": "key is not configured",
    }


def test_demo_zip_location_returns_controller_response(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.main.lookup_zip_location",
        lambda postcode: ZipLocation(
            postcode=postcode,
            country_code="US",
            latitude=40.7982,
            longitude=-77.8599,
            locality="University Park",
        ),
    )

    response = client.get("/api/demo/zip-location")

    assert response.status_code == 200
    assert response.json() == {
        "postcode": "16802",
        "country_code": "US",
        "latitude": 40.7982,
        "longitude": -77.8599,
        "locality": "University Park",
    }


def test_zip_location_returns_controller_response_for_16802(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    requested_postcodes: list[str] = []

    def lookup(postcode: str) -> ZipLocation:
        requested_postcodes.append(postcode)
        return ZipLocation(
            postcode=postcode,
            country_code="US",
            latitude=40.7982,
            longitude=-77.8599,
            locality="University Park",
        )

    monkeypatch.setattr("app.main.lookup_zip_location", lookup)

    response = client.get(
        "/api/zip-location",
        params={"postcode": "16802"},
    )

    assert response.status_code == 200
    assert requested_postcodes == ["16802"]
    assert response.json() == {
        "postcode": "16802",
        "country_code": "US",
        "latitude": 40.7982,
        "longitude": -77.8599,
        "locality": "University Park",
    }


def test_zip_location_preserves_leading_zero_as_a_string(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    requested_postcodes: list[str] = []

    def lookup(postcode: str) -> ZipLocation:
        requested_postcodes.append(postcode)
        return ZipLocation(
            postcode=postcode,
            country_code="US",
            latitude=41.0,
            longitude=-72.0,
        )

    monkeypatch.setattr("app.main.lookup_zip_location", lookup)

    response = client.get(
        "/api/zip-location",
        params={"postcode": "01234"},
    )

    assert response.status_code == 200
    assert requested_postcodes == ["01234"]
    assert response.json()["postcode"] == "01234"


@pytest.mark.parametrize(
    "postcode",
    ["1680", "168020", "1680A", " 16802", "１２３４５"],
)
def test_zip_location_rejects_invalid_input(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    postcode: str,
) -> None:
    def unexpected_lookup(_postcode: str) -> ZipLocation:
        pytest.fail("Invalid input must not call the location controller.")

    monkeypatch.setattr("app.main.lookup_zip_location", unexpected_lookup)

    response = client.get(
        "/api/zip-location",
        params={"postcode": postcode},
    )

    assert response.status_code == 400
    assert response.json() == {
        "detail": "Enter exactly five digits for a U.S. ZIP code."
    }


@pytest.mark.parametrize(
    ("error", "status_code", "detail"),
    [
        (
            ZipLookupUnresolvedError("private provider result"),
            404,
            "ZIP code 99999 could not be resolved.",
        ),
        (
            GeoapifyRequestError("private provider request"),
            502,
            "The location provider request failed.",
        ),
    ],
)
def test_zip_location_maps_safe_lookup_errors(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    error: Exception,
    status_code: int,
    detail: str,
) -> None:
    def fail_lookup(_postcode: str) -> ZipLocation:
        raise error

    monkeypatch.setattr("app.main.lookup_zip_location", fail_lookup)

    response = client.get(
        "/api/zip-location",
        params={"postcode": "99999"},
    )

    assert response.status_code == status_code
    assert response.json() == {"detail": detail}


@pytest.mark.parametrize(
    ("error", "status_code", "detail"),
    [
        (
            GeoapifyConfigurationError("private configuration details"),
            503,
            "Geoapify is not configured.",
        ),
        (
            ZipLookupUnresolvedError("private provider result"),
            404,
            "ZIP code 16802 could not be resolved.",
        ),
        (
            GeoapifyRequestError("private provider request"),
            502,
            "The location provider request failed.",
        ),
    ],
)
def test_demo_zip_location_maps_safe_errors(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    error: Exception,
    status_code: int,
    detail: str,
) -> None:
    def fail_lookup(_postcode: str) -> ZipLocation:
        raise error

    monkeypatch.setattr("app.main.lookup_zip_location", fail_lookup)

    response = client.get("/api/demo/zip-location")

    assert response.status_code == status_code
    assert response.json() == {"detail": detail}


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

import json
from pathlib import Path

import httpx
import pytest

from app.hotel_discovery import (
    GEOAPIFY_PLACES_TIMEOUT_SECONDS,
    HOTEL_CATEGORY,
    HOTEL_RESULT_LIMIT,
    HOTEL_SEARCH_RADIUS_METERS,
    DiscoveredHotel,
    HotelDiscoveryProviderError,
    HotelDiscoveryRateLimitError,
    HotelDiscoveryResponseError,
    discover_hotels_by_zip,
)
from app.location_controller import (
    GeoapifyConfigurationError,
    ZipLocation,
    ZipLookupUnresolvedError,
)


FIXTURE_PATH = (
    Path(__file__).parent
    / "fixtures"
    / "geoapify_places_hotels.json"
)


def _configure_test_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.location_controller.get_geoapify_api_key",
        lambda: "test-key",
    )
    monkeypatch.setattr(
        "app.hotel_discovery.get_geoapify_api_key",
        lambda: "test-key",
    )


def _geocode_response() -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "results": [
                {
                    "postcode": "16802",
                    "country_code": "us",
                    "lat": 40.7982,
                    "lon": -77.8599,
                    "city": "University Park",
                }
            ]
        },
    )


def _client_with_places_response(
    places_response,
) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/geocode/search":
            return _geocode_response()
        if request.url.path == "/v2/places":
            return places_response(request)
        raise AssertionError(f"Unexpected mocked path: {request.url.path}")

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_discover_hotels_normalizes_credential_free_fixture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_test_key(monkeypatch)
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    assert fixture["fixture"]["contains_credentials"] is False

    def places_response(request: httpx.Request) -> httpx.Response:
        assert request.url.params["categories"] == HOTEL_CATEGORY
        assert request.url.params["filter"] == (
            "circle:-77.8599,40.7982,5000"
        )
        assert request.url.params["bias"] == (
            "proximity:-77.8599,40.7982"
        )
        assert request.url.params["limit"] == str(HOTEL_RESULT_LIMIT)
        assert request.url.params["lang"] == "en"
        assert request.url.params["apiKey"] == "test-key"
        assert request.extensions["timeout"]["connect"] == (
            GEOAPIFY_PLACES_TIMEOUT_SECONDS
        )
        return httpx.Response(200, json=fixture)

    with _client_with_places_response(places_response) as client:
        result = discover_hotels_by_zip("16802", client=client)

    assert result.search_center == ZipLocation(
        postcode="16802",
        country_code="US",
        latitude=40.7982,
        longitude=-77.8599,
        locality="University Park",
    )
    assert result.search_radius_meters == HOTEL_SEARCH_RADIUS_METERS
    assert result.result_limit == HOTEL_RESULT_LIMIT
    assert result.omitted_provider_records == 1
    assert result.hotels == (
        DiscoveredHotel(
            provider_place_id="fixture-hotel-complete",
            name="Fixture Hotel One",
            formatted_address=(
                "100 Fixture Avenue, State College, PA 16801, "
                "United States of America"
            ),
            latitude=40.8001,
            longitude=-77.8602,
            distance_meters=487.4,
        ),
        DiscoveredHotel(
            provider_place_id="fixture-hotel-missing-optional-fields",
            name=None,
            formatted_address=None,
            latitude=40.8075,
            longitude=-77.851,
            distance_meters=None,
        ),
    )

    payload = result.to_dict()
    assert payload["count"] == 2
    assert "name" not in payload["hotels"][1]
    assert "formatted_address" not in payload["hotels"][1]
    assert "distance_meters" not in payload["hotels"][1]


def test_discover_hotels_returns_successful_zero_results(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_test_key(monkeypatch)

    def places_response(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"type": "FeatureCollection", "features": []},
        )

    with _client_with_places_response(places_response) as client:
        result = discover_hotels_by_zip("16802", client=client)

    assert result.hotels == ()
    assert result.omitted_provider_records == 0


@pytest.mark.parametrize(
    "payload",
    [
        {"type": "FeatureCollection", "features": "not-a-list"},
        {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {
                        "place_id": "missing-coordinates"
                    },
                }
            ],
        },
    ],
)
def test_discover_hotels_rejects_malformed_results(
    monkeypatch: pytest.MonkeyPatch,
    payload: object,
) -> None:
    _configure_test_key(monkeypatch)

    def places_response(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload)

    with _client_with_places_response(places_response) as client:
        with pytest.raises(
            HotelDiscoveryResponseError,
            match="provider response",
        ):
            discover_hotels_by_zip("16802", client=client)


def test_discover_hotels_hides_timeout_details(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_test_key(monkeypatch)

    def places_response(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout(
            "private provider URL or credential details",
            request=request,
        )

    with _client_with_places_response(places_response) as client:
        with pytest.raises(
            HotelDiscoveryProviderError,
            match="hotel provider request failed",
        ) as captured:
            discover_hotels_by_zip("16802", client=client)

    assert "private provider" not in str(captured.value)


def test_discover_hotels_maps_provider_failure_safely(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_test_key(monkeypatch)

    def places_response(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            503,
            json={"message": "private upstream details"},
        )

    with _client_with_places_response(places_response) as client:
        with pytest.raises(
            HotelDiscoveryProviderError,
            match="hotel provider request failed",
        ) as captured:
            discover_hotels_by_zip("16802", client=client)

    assert "private upstream" not in str(captured.value)


def test_discover_hotels_distinguishes_rate_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_test_key(monkeypatch)

    def places_response(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            429,
            json={"message": "quota exhausted for a private project"},
        )

    with _client_with_places_response(places_response) as client:
        with pytest.raises(
            HotelDiscoveryRateLimitError,
            match="rate or quota limit",
        ) as captured:
            discover_hotels_by_zip("16802", client=client)

    assert "private project" not in str(captured.value)


def test_discover_hotels_distinguishes_missing_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.location_controller.get_geoapify_api_key",
        lambda: "",
    )
    request_count = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1
        return httpx.Response(500)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(GeoapifyConfigurationError):
            discover_hotels_by_zip("16802", client=client)

    assert request_count == 0


def test_discover_hotels_preserves_unresolved_zip_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_test_key(monkeypatch)
    request_paths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        request_paths.append(request.url.path)
        return httpx.Response(
            200,
            json={
                "results": [
                    {
                        "postcode": "16801",
                        "country_code": "us",
                        "lat": 40.7934,
                        "lon": -77.86,
                    }
                ]
            },
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(ZipLookupUnresolvedError):
            discover_hotels_by_zip("16802", client=client)

    assert request_paths == ["/v1/geocode/search"]

import httpx
import pytest

from app.location_controller import (
    GEOAPIFY_TIMEOUT_SECONDS,
    GeoapifyRequestError,
    ZipLocation,
    ZipLookupUnresolvedError,
    lookup_zip_location,
)


def test_lookup_zip_location_returns_valid_us_postcode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.location_controller.get_geoapify_api_key",
        lambda: "test-key",
    )

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["postcode"] == "16802"
        assert request.url.params["type"] == "postcode"
        assert request.url.params["filter"] == "countrycode:us"
        assert request.url.params["format"] == "json"
        assert request.url.params["apiKey"] == "test-key"
        assert request.extensions["timeout"]["connect"] == GEOAPIFY_TIMEOUT_SECONDS
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

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        location = lookup_zip_location("16802", client=client)

    assert location == ZipLocation(
        postcode="16802",
        country_code="US",
        latitude=40.7982,
        longitude=-77.8599,
        locality="University Park",
    )


def test_lookup_zip_location_preserves_leading_zero_with_mocked_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.location_controller.get_geoapify_api_key",
        lambda: "test-key",
    )

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["postcode"] == "01234"
        return httpx.Response(
            200,
            json={
                "results": [
                    {
                        "postcode": "01234",
                        "country_code": "us",
                        "lat": 41.0,
                        "lon": -72.0,
                    }
                ]
            },
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        location = lookup_zip_location("01234", client=client)

    assert location.postcode == "01234"


def test_lookup_zip_location_rejects_mismatched_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.location_controller.get_geoapify_api_key",
        lambda: "test-key",
    )

    def handler(_request: httpx.Request) -> httpx.Response:
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
        with pytest.raises(
            ZipLookupUnresolvedError,
            match="ZIP code could not be resolved",
        ):
            lookup_zip_location("16802", client=client)


def test_lookup_zip_location_hides_provider_failure_details(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.location_controller.get_geoapify_api_key",
        lambda: "test-key",
    )

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("private transport details", request=request)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(
            GeoapifyRequestError,
            match="location provider request failed",
        ) as captured:
            lookup_zip_location("16802", client=client)

    assert "private transport details" not in str(captured.value)

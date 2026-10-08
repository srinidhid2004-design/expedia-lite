"""Backend-only ZIP lookup through Geoapify forward geocoding."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import math

import httpx

from .config import get_geoapify_api_key


GEOAPIFY_FORWARD_URL = "https://api.geoapify.com/v1/geocode/search"
GEOAPIFY_TIMEOUT_SECONDS = 5.0


class ZipLookupUnresolvedError(LookupError):
    """Raised when Geoapify returns no acceptable match for the ZIP code."""


class GeoapifyRequestError(RuntimeError):
    """Raised when the provider request cannot produce a usable response."""


class GeoapifyConfigurationError(GeoapifyRequestError):
    """Raised when the backend has no usable Geoapify API key."""


@dataclass(frozen=True)
class ZipLocation:
    """A postcode location independent of hotel pricing data."""

    postcode: str
    country_code: str
    latitude: float
    longitude: float
    locality: str | None = None

    def to_dict(self) -> dict[str, str | float]:
        """Return a small response, omitting locality when unavailable."""

        payload = asdict(self)
        if self.locality is None:
            del payload["locality"]
        return payload


def lookup_zip_location(
    postcode: str,
    *,
    client: httpx.Client | None = None,
) -> ZipLocation:
    """Resolve one U.S. postcode or raise a safe, specific lookup error."""

    requested_postcode = postcode.strip()
    if not requested_postcode:
        raise ZipLookupUnresolvedError("The ZIP code could not be resolved.")

    api_key = get_geoapify_api_key()
    if not api_key:
        raise GeoapifyConfigurationError(
            "The location provider is not configured."
        )

    parameters = {
        "postcode": requested_postcode,
        "type": "postcode",
        "filter": "countrycode:us",
        "format": "json",
        "apiKey": api_key,
    }

    try:
        if client is None:
            with httpx.Client() as owned_client:
                response = owned_client.get(
                    GEOAPIFY_FORWARD_URL,
                    params=parameters,
                    timeout=GEOAPIFY_TIMEOUT_SECONDS,
                )
        else:
            response = client.get(
                GEOAPIFY_FORWARD_URL,
                params=parameters,
                timeout=GEOAPIFY_TIMEOUT_SECONDS,
            )
        response.raise_for_status()
        payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise GeoapifyRequestError(
            "The location provider request failed."
        ) from None

    if not isinstance(payload, dict) or not isinstance(payload.get("results"), list):
        raise GeoapifyRequestError("The location provider response was invalid.")

    for result in payload["results"]:
        location = _matching_location(result, requested_postcode)
        if location is not None:
            return location

    raise ZipLookupUnresolvedError("The ZIP code could not be resolved.")


def _matching_location(
    result: object,
    requested_postcode: str,
) -> ZipLocation | None:
    if not isinstance(result, dict):
        return None

    postcode = str(result.get("postcode", "")).strip()
    country_code = str(result.get("country_code", "")).strip().casefold()
    latitude = _valid_coordinate(result.get("lat"), -90.0, 90.0)
    longitude = _valid_coordinate(result.get("lon"), -180.0, 180.0)
    if (
        postcode != requested_postcode
        or country_code != "us"
        or latitude is None
        or longitude is None
    ):
        return None

    return ZipLocation(
        postcode=postcode,
        country_code="US",
        latitude=latitude,
        longitude=longitude,
        locality=_locality(result),
    )


def _valid_coordinate(
    value: object,
    minimum: float,
    maximum: float,
) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        coordinate = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(coordinate) or not minimum <= coordinate <= maximum:
        return None
    return coordinate


def _locality(result: dict[str, object]) -> str | None:
    for field in ("city", "town", "village", "municipality", "county"):
        value = result.get(field)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None

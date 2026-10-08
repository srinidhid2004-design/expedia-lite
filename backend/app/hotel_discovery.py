"""Backend-only nearby-hotel discovery using Geoapify Places."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import math

import httpx

from .config import get_geoapify_api_key
from .location_controller import (
    GeoapifyConfigurationError,
    ZipLocation,
    lookup_zip_location,
)


GEOAPIFY_PLACES_URL = "https://api.geoapify.com/v2/places"
GEOAPIFY_PLACES_TIMEOUT_SECONDS = 5.0
HOTEL_CATEGORY = "accommodation.hotel"
HOTEL_SEARCH_RADIUS_METERS = 5_000
# One bounded provider page keeps the classroom request predictable and is not
# presented as an exhaustive hotel inventory.
HOTEL_RESULT_LIMIT = 20


class HotelDiscoveryProviderError(RuntimeError):
    """Raised when the Places provider request fails safely."""


class HotelDiscoveryRateLimitError(HotelDiscoveryProviderError):
    """Raised when the Places provider reports rate or quota exhaustion."""


class HotelDiscoveryResponseError(HotelDiscoveryProviderError):
    """Raised when the Places provider response cannot be normalized."""


@dataclass(frozen=True)
class DiscoveredHotel:
    """A provider-independent hotel record without commercial claims."""

    provider_place_id: str
    latitude: float
    longitude: float
    name: str | None = None
    formatted_address: str | None = None
    distance_meters: float | None = None

    def to_dict(self) -> dict[str, str | float]:
        """Return supported fields, omitting optional data that is unavailable."""

        payload = asdict(self)
        return {
            key: value
            for key, value in payload.items()
            if value is not None
        }


@dataclass(frozen=True)
class HotelDiscoveryResult:
    """One bounded nearby-hotel page centered on an exact ZIP result."""

    search_center: ZipLocation
    hotels: tuple[DiscoveredHotel, ...]
    omitted_provider_records: int = 0
    search_radius_meters: int = HOTEL_SEARCH_RADIUS_METERS
    result_limit: int = HOTEL_RESULT_LIMIT

    def to_dict(self) -> dict[str, object]:
        """Return a future-route-ready response without provider credentials."""

        return {
            "search_center": self.search_center.to_dict(),
            "search_radius_meters": self.search_radius_meters,
            "result_limit": self.result_limit,
            "count": len(self.hotels),
            "omitted_provider_records": self.omitted_provider_records,
            "hotels": [hotel.to_dict() for hotel in self.hotels],
        }


def discover_hotels_by_zip(
    postcode: str,
    *,
    client: httpx.Client | None = None,
) -> HotelDiscoveryResult:
    """Resolve an exact U.S. ZIP and return up to 20 hotels within 5 km."""

    if client is None:
        with httpx.Client() as owned_client:
            return _discover_hotels_by_zip(postcode, owned_client)
    return _discover_hotels_by_zip(postcode, client)


def _discover_hotels_by_zip(
    postcode: str,
    client: httpx.Client,
) -> HotelDiscoveryResult:
    search_center = lookup_zip_location(postcode, client=client)

    api_key = get_geoapify_api_key()
    if not api_key:
        raise GeoapifyConfigurationError(
            "The location provider is not configured."
        )

    longitude = search_center.longitude
    latitude = search_center.latitude
    parameters = {
        "categories": HOTEL_CATEGORY,
        "filter": (
            f"circle:{longitude},{latitude},"
            f"{HOTEL_SEARCH_RADIUS_METERS}"
        ),
        "bias": f"proximity:{longitude},{latitude}",
        "limit": HOTEL_RESULT_LIMIT,
        "lang": "en",
        "apiKey": api_key,
    }

    try:
        response = client.get(
            GEOAPIFY_PLACES_URL,
            params=parameters,
            timeout=GEOAPIFY_PLACES_TIMEOUT_SECONDS,
        )
    except httpx.HTTPError:
        raise HotelDiscoveryProviderError(
            "The hotel provider request failed."
        ) from None

    if response.status_code == 429:
        raise HotelDiscoveryRateLimitError(
            "The hotel provider rate or quota limit was reached."
        )

    try:
        response.raise_for_status()
    except httpx.HTTPStatusError:
        raise HotelDiscoveryProviderError(
            "The hotel provider request failed."
        ) from None

    try:
        payload = response.json()
    except ValueError:
        raise HotelDiscoveryResponseError(
            "The hotel provider response was invalid."
        ) from None

    hotels, omitted_count = _normalize_places_payload(payload)
    return HotelDiscoveryResult(
        search_center=search_center,
        hotels=hotels,
        omitted_provider_records=omitted_count,
    )


def _normalize_places_payload(
    payload: object,
) -> tuple[tuple[DiscoveredHotel, ...], int]:
    if (
        not isinstance(payload, dict)
        or payload.get("type") != "FeatureCollection"
        or not isinstance(payload.get("features"), list)
    ):
        raise HotelDiscoveryResponseError(
            "The hotel provider response was invalid."
        )

    features = payload["features"]
    hotels: list[DiscoveredHotel] = []
    seen_place_ids: set[str] = set()
    omitted_count = 0

    for feature in features:
        hotel = _normalize_hotel_feature(feature)
        if (
            hotel is None
            or hotel.provider_place_id in seen_place_ids
        ):
            omitted_count += 1
            continue
        seen_place_ids.add(hotel.provider_place_id)
        hotels.append(hotel)

    if features and not hotels:
        raise HotelDiscoveryResponseError(
            "The hotel provider response contained no usable place records."
        )

    return tuple(hotels), omitted_count


def _normalize_hotel_feature(feature: object) -> DiscoveredHotel | None:
    if not isinstance(feature, dict):
        return None

    properties = feature.get("properties")
    if not isinstance(properties, dict):
        return None

    place_id = _optional_text(properties.get("place_id"))
    latitude = _valid_number(properties.get("lat"), -90.0, 90.0)
    longitude = _valid_number(properties.get("lon"), -180.0, 180.0)
    if place_id is None or latitude is None or longitude is None:
        return None

    return DiscoveredHotel(
        provider_place_id=place_id,
        name=_optional_text(properties.get("name")),
        formatted_address=_provider_address(properties),
        latitude=latitude,
        longitude=longitude,
        distance_meters=_valid_number(
            properties.get("distance"),
            0.0,
            float(HOTEL_SEARCH_RADIUS_METERS),
        ),
    )


def _provider_address(properties: dict[str, object]) -> str | None:
    formatted = _optional_text(properties.get("formatted"))
    if formatted is not None:
        return formatted

    house_number = _optional_text(properties.get("housenumber"))
    street = _optional_text(properties.get("street"))
    street_line = " ".join(
        part for part in (house_number, street) if part is not None
    )
    parts = [
        street_line or None,
        _optional_text(properties.get("city")),
        _optional_text(properties.get("state")),
        _optional_text(properties.get("postcode")),
        _optional_text(properties.get("country")),
    ]
    available_parts = [part for part in parts if part is not None]
    return ", ".join(available_parts) or None


def _optional_text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized or None


def _valid_number(
    value: object,
    minimum: float,
    maximum: float,
) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number) or not minimum <= number <= maximum:
        return None
    return number

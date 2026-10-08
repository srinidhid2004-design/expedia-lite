"""Local persistence for provider hotels and simulated classroom nights."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from pathlib import Path
import sqlite3

from .database import DATABASE_PATH, TravelDataError, connect_database
from .hotel_discovery import DiscoveredHotel, HOTEL_SEARCH_RADIUS_METERS
from .location_controller import ZipLocation


SIMULATED_STAY_DATES = tuple(
    f"2026-10-{day:02d}" for day in range(10, 15)
)
SIMULATED_NIGHTLY_RATE_CENTS = 10_000
SIMULATED_ROOMS_AVAILABLE = 20
SIMULATED_DATA_NOTICE = (
    "Nightly rates and room counts are simulated classroom data, "
    "not API-supplied inventory."
)
LOCAL_SUBSET_NOTICE = (
    "Saved locally; this stored subset is not a complete hotel inventory."
)


class SavedHotelValidationError(ValueError):
    """Raised when a local-hotel request contains invalid supported data."""


class SavedHotelNotFoundError(LookupError):
    """Raised when a requested saved provider hotel does not exist."""


@dataclass(frozen=True)
class DemoHotelNight:
    """One dated simulated classroom rate and room count."""

    stay_date: str
    nightly_rate_cents: int
    rooms_available: int

    def to_dict(self) -> dict[str, str | int]:
        return asdict(self)


@dataclass(frozen=True)
class SavedHotel:
    """A provider hotel stored locally with its classroom demo nights."""

    provider_place_id: str
    latitude: float
    longitude: float
    demo_nights: tuple[DemoHotelNight, ...]
    name: str | None = None
    formatted_address: str | None = None

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "provider_place_id": self.provider_place_id,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "saved_locally": True,
            "demo_nights": [night.to_dict() for night in self.demo_nights],
            "simulated_data_notice": SIMULATED_DATA_NOTICE,
        }
        if self.name is not None:
            payload["name"] = self.name
        if self.formatted_address is not None:
            payload["formatted_address"] = self.formatted_address
        return payload


@dataclass(frozen=True)
class SavedHotelSearchResult:
    """Saved hotels associated with one exact searched ZIP."""

    postcode: str
    hotels: tuple[SavedHotel, ...]
    saved_provider_ids: tuple[str, ...]
    search_center: ZipLocation | None = None

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "source": "local",
            "postcode": self.postcode,
            "search_radius_meters": HOTEL_SEARCH_RADIUS_METERS,
            "count": len(self.hotels),
            "hotels": [hotel.to_dict() for hotel in self.hotels],
            "saved_provider_ids": list(self.saved_provider_ids),
            "inventory_notice": LOCAL_SUBSET_NOTICE,
            "simulated_data_notice": SIMULATED_DATA_NOTICE,
        }
        if self.search_center is not None:
            payload["search_center"] = self.search_center.to_dict()
        return payload


@dataclass(frozen=True)
class SavedHotelSaveResult:
    """Outcome of an idempotent save operation."""

    created: bool
    hotel: SavedHotel

    def to_dict(self) -> dict[str, object]:
        return {
            "created": self.created,
            "hotel": self.hotel.to_dict(),
            "simulated_data_notice": SIMULATED_DATA_NOTICE,
        }


def save_hotel(
    hotel: DiscoveredHotel,
    search_center: ZipLocation,
    database_path: Path = DATABASE_PATH,
) -> SavedHotelSaveResult:
    """Save one provider hotel, ZIP association, and five demo nights."""

    _validate_hotel(hotel)
    _validate_search_center(search_center)
    connection = connect_database(database_path)
    try:
        with connection:
            result = connection.execute(
                """
                INSERT OR IGNORE INTO saved_hotels (
                    hotel_id, name, address, latitude, longitude
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    hotel.provider_place_id,
                    hotel.name,
                    hotel.formatted_address,
                    hotel.latitude,
                    hotel.longitude,
                ),
            )
            created = result.rowcount == 1
            connection.execute(
                """
                INSERT OR IGNORE INTO saved_search_contexts (
                    postcode, country_code, locality, latitude, longitude
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    search_center.postcode,
                    search_center.country_code,
                    search_center.locality,
                    search_center.latitude,
                    search_center.longitude,
                ),
            )
            connection.execute(
                """
                INSERT OR IGNORE INTO saved_hotel_zip_associations (
                    hotel_id, postcode
                ) VALUES (?, ?)
                """,
                (hotel.provider_place_id, search_center.postcode),
            )
            connection.executemany(
                """
                INSERT OR IGNORE INTO demo_hotel_nights (
                    hotel_id, stay_date
                ) VALUES (?, ?)
                """,
                (
                    (hotel.provider_place_id, stay_date)
                    for stay_date in SIMULATED_STAY_DATES
                ),
            )
            saved_hotel = _load_saved_hotel(
                connection,
                hotel.provider_place_id,
            )
            if saved_hotel is None:
                raise TravelDataError("Unable to read the saved hotel.")
        return SavedHotelSaveResult(created=created, hotel=saved_hotel)
    except (SavedHotelValidationError, TravelDataError):
        raise
    except sqlite3.Error as exc:
        raise TravelDataError("Unable to save the hotel locally.") from exc
    finally:
        connection.close()


def list_saved_hotels_for_postcode(
    postcode: str,
    database_path: Path = DATABASE_PATH,
) -> SavedHotelSearchResult:
    """Return the local subset associated with one exact ZIP string."""

    _validate_postcode(postcode)
    connection = connect_database(database_path)
    try:
        saved_provider_ids = tuple(
            row["hotel_id"]
            for row in connection.execute(
                "SELECT hotel_id FROM saved_hotels ORDER BY hotel_id"
            )
        )
        context = connection.execute(
            """
            SELECT postcode, country_code, locality, latitude, longitude
            FROM saved_search_contexts
            WHERE postcode = ?
              AND EXISTS (
                  SELECT 1
                  FROM saved_hotel_zip_associations AS association
                  WHERE association.postcode = saved_search_contexts.postcode
              )
            """,
            (postcode,),
        ).fetchone()
        if context is None:
            return SavedHotelSearchResult(
                postcode=postcode,
                hotels=(),
                saved_provider_ids=saved_provider_ids,
            )

        hotel_ids = [
            row["hotel_id"]
            for row in connection.execute(
                """
                SELECT hotel.hotel_id
                FROM saved_hotels AS hotel
                JOIN saved_hotel_zip_associations AS association
                  ON association.hotel_id = hotel.hotel_id
                WHERE association.postcode = ?
                ORDER BY COALESCE(hotel.name, hotel.hotel_id) COLLATE NOCASE,
                         hotel.hotel_id
                """,
                (postcode,),
            )
        ]
        hotels = tuple(
            saved_hotel
            for hotel_id in hotel_ids
            if (saved_hotel := _load_saved_hotel(connection, hotel_id))
            is not None
        )
        return SavedHotelSearchResult(
            postcode=postcode,
            hotels=hotels,
            saved_provider_ids=saved_provider_ids,
            search_center=ZipLocation(
                postcode=context["postcode"],
                country_code=context["country_code"],
                locality=context["locality"],
                latitude=context["latitude"],
                longitude=context["longitude"],
            ),
        )
    except SavedHotelValidationError:
        raise
    except sqlite3.Error as exc:
        raise TravelDataError("Unable to read saved hotels.") from exc
    finally:
        connection.close()


def remove_saved_hotel(
    provider_place_id: str,
    database_path: Path = DATABASE_PATH,
) -> str:
    """Remove one hotel, its nights, and its ZIP associations atomically."""

    _validate_provider_place_id(provider_place_id)
    connection = connect_database(database_path)
    try:
        with connection:
            exists = connection.execute(
                "SELECT 1 FROM saved_hotels WHERE hotel_id = ?",
                (provider_place_id,),
            ).fetchone()
            if exists is None:
                raise SavedHotelNotFoundError(
                    "The saved hotel could not be found."
                )
            associated_postcodes = [
                row["postcode"]
                for row in connection.execute(
                    """
                    SELECT postcode
                    FROM saved_hotel_zip_associations
                    WHERE hotel_id = ?
                    """,
                    (provider_place_id,),
                )
            ]
            connection.execute(
                "DELETE FROM demo_hotel_nights WHERE hotel_id = ?",
                (provider_place_id,),
            )
            connection.execute(
                """
                DELETE FROM saved_hotel_zip_associations
                WHERE hotel_id = ?
                """,
                (provider_place_id,),
            )
            connection.execute(
                "DELETE FROM saved_hotels WHERE hotel_id = ?",
                (provider_place_id,),
            )
            for postcode in associated_postcodes:
                connection.execute(
                    """
                    DELETE FROM saved_search_contexts
                    WHERE postcode = ?
                      AND NOT EXISTS (
                          SELECT 1
                          FROM saved_hotel_zip_associations
                          WHERE saved_hotel_zip_associations.postcode =
                                saved_search_contexts.postcode
                      )
                    """,
                    (postcode,),
                )
        return provider_place_id
    except (SavedHotelNotFoundError, SavedHotelValidationError):
        raise
    except sqlite3.Error as exc:
        raise TravelDataError("Unable to remove the saved hotel.") from exc
    finally:
        connection.close()


def _load_saved_hotel(
    connection: sqlite3.Connection,
    provider_place_id: str,
) -> SavedHotel | None:
    row = connection.execute(
        """
        SELECT hotel_id, name, address, latitude, longitude
        FROM saved_hotels
        WHERE hotel_id = ?
        """,
        (provider_place_id,),
    ).fetchone()
    if row is None:
        return None
    demo_nights = tuple(
        DemoHotelNight(
            stay_date=night["stay_date"],
            nightly_rate_cents=night["nightly_rate_cents"],
            rooms_available=night["rooms_available"],
        )
        for night in connection.execute(
            """
            SELECT stay_date, nightly_rate_cents, rooms_available
            FROM demo_hotel_nights
            WHERE hotel_id = ?
            ORDER BY stay_date
            """,
            (provider_place_id,),
        )
    )
    return SavedHotel(
        provider_place_id=row["hotel_id"],
        name=row["name"],
        formatted_address=row["address"],
        latitude=row["latitude"],
        longitude=row["longitude"],
        demo_nights=demo_nights,
    )


def _validate_hotel(hotel: DiscoveredHotel) -> None:
    _validate_provider_place_id(hotel.provider_place_id)
    _validate_coordinate(hotel.latitude, -90.0, 90.0, "latitude")
    _validate_coordinate(hotel.longitude, -180.0, 180.0, "longitude")


def _validate_search_center(search_center: ZipLocation) -> None:
    _validate_postcode(search_center.postcode)
    if search_center.country_code != "US":
        raise SavedHotelValidationError(
            "The search context must identify the United States."
        )
    _validate_coordinate(search_center.latitude, -90.0, 90.0, "latitude")
    _validate_coordinate(search_center.longitude, -180.0, 180.0, "longitude")


def _validate_postcode(postcode: str) -> None:
    if not (
        len(postcode) == 5
        and postcode.isascii()
        and postcode.isdigit()
    ):
        raise SavedHotelValidationError(
            "Enter exactly five digits for a U.S. ZIP code."
        )


def _validate_provider_place_id(provider_place_id: str) -> None:
    if not provider_place_id or not provider_place_id.strip():
        raise SavedHotelValidationError("A provider place ID is required.")


def _validate_coordinate(
    value: float,
    minimum: float,
    maximum: float,
    label: str,
) -> None:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or not minimum <= value <= maximum
    ):
        raise SavedHotelValidationError(f"The {label} is invalid.")

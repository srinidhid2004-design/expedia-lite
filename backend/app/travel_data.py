"""Read and search hotel stays from the Part 2 SQLite database."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
import sqlite3

from .database import DATABASE_PATH, TravelDataError, connect_database


@dataclass(frozen=True)
class HotelStay:
    """A trip enriched with the hotel fields needed by the results table."""

    trip_id: str
    trip_name: str
    hotel_id: str
    hotel_name: str
    city: str
    state: str
    check_in: str
    check_out: str
    nights: int
    nightly_rate_usd: float
    estimated_total_usd: float

    def to_dict(self) -> dict[str, str | int | float]:
        """Return a JSON-ready representation of this stay."""

        return asdict(self)


def load_hotel_stays(
    database_path: Path = DATABASE_PATH,
) -> list[HotelStay]:
    """Return every offered stay joined to its hotel from SQLite."""

    connection = connect_database(database_path)
    try:
        rows = connection.execute(
            """
            SELECT
                t.trip_id,
                t.trip_name,
                h.hotel_id,
                h.hotel_name,
                h.city,
                h.state,
                t.check_in,
                t.check_out,
                h.nightly_rate_usd
            FROM trips AS t
            JOIN hotels AS h ON h.hotel_id = t.hotel_id
            ORDER BY t.trip_id
            """
        ).fetchall()
    finally:
        connection.close()

    return [_row_to_hotel_stay(row) for row in rows]


def _row_to_hotel_stay(row: sqlite3.Row) -> HotelStay:
    try:
        check_in = date.fromisoformat(row["check_in"])
        check_out = date.fromisoformat(row["check_out"])
        nightly_rate = float(row["nightly_rate_usd"])
        nights = (check_out - check_in).days
        if nights <= 0:
            raise ValueError("A stay must have at least one night.")
        return HotelStay(
            trip_id=row["trip_id"],
            trip_name=row["trip_name"],
            hotel_id=row["hotel_id"],
            hotel_name=row["hotel_name"],
            city=row["city"],
            state=row["state"],
            check_in=row["check_in"],
            check_out=row["check_out"],
            nights=nights,
            nightly_rate_usd=nightly_rate,
            estimated_total_usd=nightly_rate * nights,
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise TravelDataError("The stored travel data is invalid.") from exc


def search_hotel_stays(
    hotel_name: str,
    database_path: Path = DATABASE_PATH,
) -> list[HotelStay]:
    """Return stays whose hotel name contains the query, ignoring case."""

    normalized_query = hotel_name.strip().casefold()
    if not normalized_query:
        raise ValueError("Enter a hotel name.")

    return [
        stay
        for stay in load_hotel_stays(database_path)
        if normalized_query in stay.hotel_name.casefold()
    ]

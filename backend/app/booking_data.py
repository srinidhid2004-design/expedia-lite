"""Booking and traveler operations backed by SQLite."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
import sqlite3

from .database import DATABASE_PATH, TravelDataError, connect_database


class BookingValidationError(ValueError):
    """Raised when a booking request refers to invalid input."""


class BookingNotFoundError(LookupError):
    """Raised when a requested booking does not exist."""


@dataclass(frozen=True)
class Traveler:
    user_id: str
    display_name: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class Booking:
    booking_id: str
    user_id: str
    display_name: str
    trip_id: str
    trip_name: str
    hotel_name: str
    city: str
    state: str
    check_in: str
    check_out: str
    nights: int
    nightly_rate_usd: float
    estimated_total_usd: float
    booked_on: str
    status: str

    def to_dict(self) -> dict[str, str | int | float]:
        return asdict(self)


_BOOKING_SELECT = """
SELECT
    b.booking_id,
    b.user_id,
    u.display_name,
    b.trip_id,
    t.trip_name,
    h.hotel_name,
    h.city,
    h.state,
    t.check_in,
    t.check_out,
    CAST(julianday(t.check_out) - julianday(t.check_in) AS INTEGER) AS nights,
    h.nightly_rate_usd,
    h.nightly_rate_usd *
        CAST(julianday(t.check_out) - julianday(t.check_in) AS INTEGER)
        AS estimated_total_usd,
    b.booked_on,
    b.status
FROM bookings AS b
JOIN users AS u ON u.user_id = b.user_id
JOIN trips AS t ON t.trip_id = b.trip_id
JOIN hotels AS h ON h.hotel_id = t.hotel_id
"""


def _row_to_booking(row: sqlite3.Row) -> Booking:
    return Booking(
        booking_id=row["booking_id"],
        user_id=row["user_id"],
        display_name=row["display_name"],
        trip_id=row["trip_id"],
        trip_name=row["trip_name"],
        hotel_name=row["hotel_name"],
        city=row["city"],
        state=row["state"],
        check_in=row["check_in"],
        check_out=row["check_out"],
        nights=int(row["nights"]),
        nightly_rate_usd=float(row["nightly_rate_usd"]),
        estimated_total_usd=float(row["estimated_total_usd"]),
        booked_on=row["booked_on"],
        status=row["status"],
    )


def list_travelers(database_path: Path = DATABASE_PATH) -> list[Traveler]:
    connection = connect_database(database_path)
    try:
        rows = connection.execute(
            "SELECT user_id, display_name FROM users ORDER BY user_id"
        ).fetchall()
        return [Traveler(row["user_id"], row["display_name"]) for row in rows]
    finally:
        connection.close()


def list_bookings(
    user_id: str | None = None,
    database_path: Path = DATABASE_PATH,
) -> list[Booking]:
    connection = connect_database(database_path)
    try:
        parameters: tuple[str, ...] = ()
        query = _BOOKING_SELECT
        if user_id is not None:
            normalized_user_id = user_id.strip().upper()
            if not normalized_user_id:
                raise BookingValidationError("Select a traveler.")
            if connection.execute(
                "SELECT 1 FROM users WHERE user_id = ?", (normalized_user_id,)
            ).fetchone() is None:
                raise BookingValidationError("The selected traveler does not exist.")
            query += " WHERE b.user_id = ?"
            parameters = (normalized_user_id,)
        query += " ORDER BY b.booked_on, b.booking_id"
        rows = connection.execute(query, parameters).fetchall()
        return [_row_to_booking(row) for row in rows]
    finally:
        connection.close()


def _booking_from_connection(
    connection: sqlite3.Connection,
    booking_id: str,
) -> Booking:
    row = connection.execute(
        _BOOKING_SELECT + " WHERE b.booking_id = ?",
        (booking_id,),
    ).fetchone()
    if row is None:
        raise BookingNotFoundError(f"Booking {booking_id} was not found.")
    return _row_to_booking(row)


def _allocate_booking_id(connection: sqlite3.Connection) -> str:
    row = connection.execute(
        "SELECT value FROM app_metadata WHERE key = 'next_booking_number'"
    ).fetchone()
    if row is None:
        raise TravelDataError("The booking ID sequence is unavailable.")

    number = int(row["value"])
    while True:
        booking_id = f"B{number:03d}"
        exists = connection.execute(
            "SELECT 1 FROM bookings WHERE booking_id = ?", (booking_id,)
        ).fetchone()
        number += 1
        if exists is None:
            connection.execute(
                "UPDATE app_metadata SET value = ? WHERE key = 'next_booking_number'",
                (str(number),),
            )
            return booking_id


def create_booking(
    user_id: str,
    trip_id: str,
    database_path: Path = DATABASE_PATH,
    booked_on: str | None = None,
) -> Booking:
    normalized_user_id = user_id.strip().upper()
    normalized_trip_id = trip_id.strip().upper()
    if not normalized_user_id or not normalized_trip_id:
        raise BookingValidationError("Select a traveler and stay.")

    connection = connect_database(database_path)
    try:
        connection.execute("BEGIN IMMEDIATE")
        if connection.execute(
            "SELECT 1 FROM users WHERE user_id = ?", (normalized_user_id,)
        ).fetchone() is None:
            raise BookingValidationError("The selected traveler does not exist.")
        if connection.execute(
            "SELECT 1 FROM trips WHERE trip_id = ?", (normalized_trip_id,)
        ).fetchone() is None:
            raise BookingValidationError("The selected stay does not exist.")

        booking_id = _allocate_booking_id(connection)
        connection.execute(
            """
            INSERT INTO bookings (booking_id, user_id, trip_id, booked_on, status)
            VALUES (?, ?, ?, ?, 'confirmed')
            """,
            (
                booking_id,
                normalized_user_id,
                normalized_trip_id,
                booked_on or date.today().isoformat(),
            ),
        )
        booking = _booking_from_connection(connection, booking_id)
        connection.commit()
        return booking
    except BookingValidationError:
        connection.rollback()
        raise
    except (TypeError, ValueError, sqlite3.Error) as exc:
        connection.rollback()
        raise TravelDataError("Unable to create the booking.") from exc
    finally:
        connection.close()


def cancel_booking(
    booking_id: str,
    database_path: Path = DATABASE_PATH,
) -> Booking:
    normalized_booking_id = booking_id.strip().upper()
    connection = connect_database(database_path)
    try:
        with connection:
            result = connection.execute(
                "UPDATE bookings SET status = 'cancelled' WHERE booking_id = ?",
                (normalized_booking_id,),
            )
            if result.rowcount == 0:
                raise BookingNotFoundError(
                    f"Booking {normalized_booking_id} was not found."
                )
        return _booking_from_connection(connection, normalized_booking_id)
    finally:
        connection.close()


def delete_booking(
    booking_id: str,
    database_path: Path = DATABASE_PATH,
) -> str:
    normalized_booking_id = booking_id.strip().upper()
    connection = connect_database(database_path)
    try:
        with connection:
            result = connection.execute(
                "DELETE FROM bookings WHERE booking_id = ?",
                (normalized_booking_id,),
            )
            if result.rowcount == 0:
                raise BookingNotFoundError(
                    f"Booking {normalized_booking_id} was not found."
                )
        return normalized_booking_id
    finally:
        connection.close()

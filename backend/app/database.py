"""SQLite schema and one-time seeding for Expedia Lite."""

from __future__ import annotations

import csv
import sqlite3
from pathlib import Path
from threading import Lock


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
DATABASE_PATH = PROJECT_ROOT / "backend" / "expedia_lite.sqlite3"

_INITIALIZE_LOCK = Lock()

_SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS hotels (
    hotel_id TEXT PRIMARY KEY,
    hotel_name TEXT NOT NULL,
    city TEXT NOT NULL,
    state TEXT NOT NULL,
    nightly_rate_usd REAL NOT NULL CHECK (nightly_rate_usd >= 0)
);

CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS trips (
    trip_id TEXT PRIMARY KEY,
    hotel_id TEXT NOT NULL REFERENCES hotels (hotel_id),
    trip_name TEXT NOT NULL,
    check_in TEXT NOT NULL,
    check_out TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS bookings (
    booking_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users (user_id),
    trip_id TEXT NOT NULL REFERENCES trips (trip_id),
    booked_on TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('confirmed', 'cancelled'))
);

CREATE TABLE IF NOT EXISTS app_metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""

_ASSIGNMENT_2_PART_2_MIGRATION = """
CREATE TABLE IF NOT EXISTS saved_hotels (
    hotel_id TEXT PRIMARY KEY NOT NULL,
    name TEXT,
    address TEXT,
    latitude REAL NOT NULL CHECK (latitude >= -90.0 AND latitude <= 90.0),
    longitude REAL NOT NULL CHECK (longitude >= -180.0 AND longitude <= 180.0)
);

-- Rates and room counts in this table are simulated classroom data.
-- They are not supplied by Geoapify or another hotel provider.
CREATE TABLE IF NOT EXISTS demo_hotel_nights (
    hotel_id TEXT NOT NULL REFERENCES saved_hotels (hotel_id),
    stay_date TEXT NOT NULL CHECK (
        stay_date GLOB
            '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'
        AND date(stay_date, '+0 days') = stay_date
    ),
    nightly_rate_cents INTEGER NOT NULL DEFAULT 10000 CHECK (
        typeof(nightly_rate_cents) = 'integer' AND nightly_rate_cents >= 0
    ),
    rooms_available INTEGER NOT NULL DEFAULT 20 CHECK (
        typeof(rooms_available) = 'integer' AND rooms_available >= 0
    ),
    PRIMARY KEY (hotel_id, stay_date)
);

CREATE TABLE IF NOT EXISTS saved_search_contexts (
    postcode TEXT PRIMARY KEY NOT NULL CHECK (
        length(postcode) = 5 AND postcode NOT GLOB '*[^0-9]*'
    ),
    country_code TEXT NOT NULL CHECK (country_code = 'US'),
    locality TEXT,
    latitude REAL NOT NULL CHECK (latitude >= -90.0 AND latitude <= 90.0),
    longitude REAL NOT NULL CHECK (longitude >= -180.0 AND longitude <= 180.0)
);

CREATE TABLE IF NOT EXISTS saved_hotel_zip_associations (
    hotel_id TEXT NOT NULL REFERENCES saved_hotels (hotel_id),
    postcode TEXT NOT NULL REFERENCES saved_search_contexts (postcode),
    PRIMARY KEY (hotel_id, postcode)
);
"""


class TravelDataError(RuntimeError):
    """Raised when the supplied data or local database cannot be used safely."""


def _connect(database_path: Path) -> sqlite3.Connection:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def _read_csv(
    path: Path,
    required_columns: set[str],
) -> list[dict[str, str]]:
    try:
        with path.open(newline="", encoding="utf-8-sig") as source:
            reader = csv.DictReader(source)
            columns = set(reader.fieldnames or [])
            missing = required_columns - columns
            if missing:
                names = ", ".join(sorted(missing))
                raise TravelDataError(f"{path.name} is missing required columns: {names}")
            return [dict(row) for row in reader]
    except OSError as exc:
        raise TravelDataError(f"Unable to read {path.name}.") from exc


def _next_booking_number(bookings: list[dict[str, str]]) -> int:
    numbers = []
    for booking in bookings:
        booking_id = booking["booking_id"]
        if booking_id.startswith("B") and booking_id[1:].isdigit():
            numbers.append(int(booking_id[1:]))
    return max(numbers, default=0) + 1


def initialize_database(
    database_path: Path = DATABASE_PATH,
    data_dir: Path = DATA_DIR,
) -> None:
    """Create the schema and import the instructor CSVs exactly once."""

    with _INITIALIZE_LOCK:
        connection: sqlite3.Connection | None = None
        try:
            connection = _connect(database_path)
            connection.executescript(_SCHEMA)
            connection.executescript(_ASSIGNMENT_2_PART_2_MIGRATION)
            connection.execute("BEGIN IMMEDIATE")
            seeded = connection.execute(
                "SELECT value FROM app_metadata WHERE key = 'seeded'"
            ).fetchone()
            if seeded is not None:
                connection.rollback()
                return

            hotels = _read_csv(
                data_dir / "hotels.csv",
                {"hotel_id", "hotel_name", "city", "state", "nightly_rate_usd"},
            )
            trips = _read_csv(
                data_dir / "trips.csv",
                {"trip_id", "hotel_id", "trip_name", "check_in", "check_out"},
            )
            users = _read_csv(
                data_dir / "users.csv",
                {"user_id", "display_name"},
            )
            bookings = _read_csv(
                data_dir / "bookings.csv",
                {"booking_id", "user_id", "trip_id", "booked_on", "status"},
            )

            invalid_statuses = {
                booking["status"]
                for booking in bookings
                if booking["status"] not in {"confirmed", "cancelled"}
            }
            if invalid_statuses:
                raise TravelDataError("bookings.csv contains an invalid status.")

            connection.executemany(
                """
                INSERT INTO hotels (
                    hotel_id, hotel_name, city, state, nightly_rate_usd
                ) VALUES (
                    :hotel_id, :hotel_name, :city, :state, :nightly_rate_usd
                )
                """,
                hotels,
            )
            connection.executemany(
                """
                INSERT INTO users (user_id, display_name)
                VALUES (:user_id, :display_name)
                """,
                users,
            )
            connection.executemany(
                """
                INSERT INTO trips (
                    trip_id, hotel_id, trip_name, check_in, check_out
                ) VALUES (
                    :trip_id, :hotel_id, :trip_name, :check_in, :check_out
                )
                """,
                trips,
            )
            connection.executemany(
                """
                INSERT INTO bookings (
                    booking_id, user_id, trip_id, booked_on, status
                ) VALUES (
                    :booking_id, :user_id, :trip_id, :booked_on, :status
                )
                """,
                bookings,
            )
            connection.executemany(
                "INSERT INTO app_metadata (key, value) VALUES (?, ?)",
                (
                    ("seeded", "1"),
                    ("next_booking_number", str(_next_booking_number(bookings))),
                ),
            )
            connection.commit()
        except TravelDataError:
            if connection is not None and connection.in_transaction:
                connection.rollback()
            raise
        except (KeyError, TypeError, ValueError, sqlite3.Error) as exc:
            if connection is not None and connection.in_transaction:
                connection.rollback()
            raise TravelDataError("Unable to initialize the travel database.") from exc
        finally:
            if connection is not None:
                connection.close()


def connect_database(database_path: Path = DATABASE_PATH) -> sqlite3.Connection:
    """Return a configured connection to an initialized database."""

    initialize_database(database_path)
    try:
        return _connect(database_path)
    except sqlite3.Error as exc:
        raise TravelDataError("Unable to open the travel database.") from exc

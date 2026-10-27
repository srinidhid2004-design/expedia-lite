import shutil
import sqlite3
from pathlib import Path

import pytest

from app.booking_data import (
    cancel_booking,
    create_booking,
    delete_booking,
    list_bookings,
)
from app.database import DATA_DIR, initialize_database


_LEGACY_ASSIGNMENT_1_SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE hotels (
    hotel_id TEXT PRIMARY KEY,
    hotel_name TEXT NOT NULL,
    city TEXT NOT NULL,
    state TEXT NOT NULL,
    nightly_rate_usd REAL NOT NULL CHECK (nightly_rate_usd >= 0)
);

CREATE TABLE users (
    user_id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL
);

CREATE TABLE trips (
    trip_id TEXT PRIMARY KEY,
    hotel_id TEXT NOT NULL REFERENCES hotels (hotel_id),
    trip_name TEXT NOT NULL,
    check_in TEXT NOT NULL,
    check_out TEXT NOT NULL
);

CREATE TABLE bookings (
    booking_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users (user_id),
    trip_id TEXT NOT NULL REFERENCES trips (trip_id),
    booked_on TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('confirmed', 'cancelled'))
);

CREATE TABLE app_metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


def test_database_seeds_all_csv_tables_once(tmp_path: Path) -> None:
    database_path = tmp_path / "travel.sqlite3"
    copied_data = tmp_path / "data"
    copied_data.mkdir()
    for filename in ("hotels.csv", "trips.csv", "users.csv", "bookings.csv"):
        shutil.copyfile(DATA_DIR / filename, copied_data / filename)

    initialize_database(database_path, copied_data)

    with sqlite3.connect(database_path) as connection:
        counts = {
            table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in ("hotels", "trips", "users", "bookings")
        }
    assert counts == {"hotels": 8, "trips": 12, "users": 6, "bookings": 6}

    for csv_file in copied_data.glob("*.csv"):
        csv_file.unlink()
    initialize_database(database_path, copied_data)

    with sqlite3.connect(database_path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM bookings").fetchone()[0] == 6


def test_booking_changes_persist_and_deleted_seed_is_not_restored(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "travel.sqlite3"

    created = create_booking(
        "U006",
        "T012",
        database_path,
        booked_on="2026-09-15",
    )
    assert created.booking_id == "B007"

    cancelled = cancel_booking(created.booking_id, database_path)
    assert cancelled.status == "cancelled"

    initialize_database(database_path)
    reopened = list_bookings("U006", database_path)
    assert [(booking.booking_id, booking.status) for booking in reopened] == [
        ("B007", "cancelled")
    ]

    delete_booking("B006", database_path)
    delete_booking("B007", database_path)
    initialize_database(database_path)
    all_booking_ids = {booking.booking_id for booking in list_bookings(None, database_path)}
    assert "B006" not in all_booking_ids
    assert "B007" not in all_booking_ids

    replacement = create_booking(
        "U006",
        "T011",
        database_path,
        booked_on="2026-09-16",
    )
    assert replacement.booking_id == "B008"


def test_api_hotel_schema_migrates_an_existing_seeded_database(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "existing.sqlite3"
    missing_data_dir = tmp_path / "missing-data"

    with sqlite3.connect(database_path) as connection:
        connection.executescript(_LEGACY_ASSIGNMENT_1_SCHEMA)
        connection.execute(
            """
            INSERT INTO hotels (
                hotel_id, hotel_name, city, state, nightly_rate_usd
            ) VALUES ('H900', 'Preserved Hotel', 'State College', 'PA', 125.00)
            """
        )
        connection.executemany(
            "INSERT INTO app_metadata (key, value) VALUES (?, ?)",
            (("seeded", "1"), ("next_booking_number", "7")),
        )

    initialize_database(database_path, missing_data_dir)
    initialize_database(database_path, missing_data_dir)

    with sqlite3.connect(database_path) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        preserved_hotel = connection.execute(
            "SELECT hotel_name FROM hotels WHERE hotel_id = 'H900'"
        ).fetchone()
        metadata = dict(connection.execute("SELECT key, value FROM app_metadata"))

    assert {
        "saved_hotels",
        "demo_hotel_nights",
        "saved_search_contexts",
        "saved_hotel_zip_associations",
    } <= tables
    assert preserved_hotel == ("Preserved Hotel",)
    assert metadata == {"seeded": "1", "next_booking_number": "7"}


def test_api_hotel_schema_constraints_defaults_and_foreign_key(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "fresh.sqlite3"
    initialize_database(database_path)

    with sqlite3.connect(database_path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        provider_id = "  provider:Exact-ID  "
        connection.execute(
            """
            INSERT INTO saved_hotels (
                hotel_id, name, address, latitude, longitude
            ) VALUES (?, NULL, NULL, ?, ?)
            """,
            (provider_id, 40.7934, -77.86),
        )
        connection.execute(
            """
            INSERT INTO demo_hotel_nights (hotel_id, stay_date)
            VALUES (?, '2026-10-08')
            """,
            (provider_id,),
        )

        saved_hotel = connection.execute(
            """
            SELECT hotel_id, name, address, latitude, longitude
            FROM saved_hotels
            """
        ).fetchone()
        demo_night = connection.execute(
            """
            SELECT hotel_id, stay_date, nightly_rate_cents, rooms_available
            FROM demo_hotel_nights
            """
        ).fetchone()
        foreign_keys = connection.execute(
            "PRAGMA foreign_key_list(demo_hotel_nights)"
        ).fetchall()

        assert saved_hotel == (provider_id, None, None, 40.7934, -77.86)
        assert demo_night == (provider_id, "2026-10-08", 10000, 20)
        assert any(
            row[2] == "saved_hotels"
            and row[3] == "hotel_id"
            and row[4] == "hotel_id"
            for row in foreign_keys
        )

        invalid_statements = (
            (
                """
                INSERT INTO saved_hotels (
                    hotel_id, name, address, latitude, longitude
                ) VALUES (?, NULL, NULL, 40.0, -77.0)
                """,
                (provider_id,),
            ),
            (
                """
                INSERT INTO saved_hotels (
                    hotel_id, name, address, latitude, longitude
                ) VALUES ('bad-latitude', NULL, NULL, 90.1, -77.0)
                """,
                (),
            ),
            (
                """
                INSERT INTO saved_hotels (
                    hotel_id, name, address, latitude, longitude
                ) VALUES ('bad-longitude', NULL, NULL, 40.0, -180.1)
                """,
                (),
            ),
            (
                """
                INSERT INTO demo_hotel_nights (hotel_id, stay_date)
                VALUES (?, '10/09/2026')
                """,
                (provider_id,),
            ),
            (
                """
                INSERT INTO demo_hotel_nights (
                    hotel_id, stay_date, nightly_rate_cents
                ) VALUES (?, '2026-10-09', -1)
                """,
                (provider_id,),
            ),
            (
                """
                INSERT INTO demo_hotel_nights (
                    hotel_id, stay_date, rooms_available
                ) VALUES (?, '2026-10-09', -1)
                """,
                (provider_id,),
            ),
            (
                """
                INSERT INTO demo_hotel_nights (hotel_id, stay_date)
                VALUES ('missing-provider-id', '2026-10-09')
                """,
                (),
            ),
        )
        for statement, parameters in invalid_statements:
            with pytest.raises(sqlite3.IntegrityError):
                connection.execute(statement, parameters)


def test_demo_hotel_night_composite_key_prevents_duplicate_dates(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "fresh.sqlite3"
    initialize_database(database_path)

    with sqlite3.connect(database_path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute(
            """
            INSERT INTO saved_hotels (
                hotel_id, name, address, latitude, longitude
            ) VALUES ('place-1', 'Demo Hotel', '1 College Ave', 40.8, -77.8)
            """
        )
        connection.execute(
            """
            INSERT INTO demo_hotel_nights (hotel_id, stay_date)
            VALUES ('place-1', '2026-10-08')
            """
        )

        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """
                INSERT INTO demo_hotel_nights (hotel_id, stay_date)
                VALUES ('place-1', '2026-10-08')
                """
            )

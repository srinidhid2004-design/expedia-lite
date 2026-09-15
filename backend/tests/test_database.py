import shutil
import sqlite3
from pathlib import Path

from app.booking_data import (
    cancel_booking,
    create_booking,
    delete_booking,
    list_bookings,
)
from app.database import DATA_DIR, initialize_database


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

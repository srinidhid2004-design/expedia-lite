import sqlite3
from pathlib import Path

import pytest

from app.database import TravelDataError
from app.hotel_discovery import DiscoveredHotel
from app.location_controller import ZipLocation
from app.saved_hotel_data import (
    SIMULATED_NIGHTLY_RATE_CENTS,
    SIMULATED_ROOMS_AVAILABLE,
    SIMULATED_STAY_DATES,
    list_saved_hotels_for_postcode,
    remove_saved_hotel,
    save_hotel,
)


def _hotel(
    provider_place_id: str,
    *,
    name: str | None = "Example Hotel",
) -> DiscoveredHotel:
    return DiscoveredHotel(
        provider_place_id=provider_place_id,
        name=name,
        formatted_address="1 Example Street",
        latitude=40.801,
        longitude=-77.861,
        distance_meters=250.0,
    )


def _center(postcode: str = "16802") -> ZipLocation:
    return ZipLocation(
        postcode=postcode,
        country_code="US",
        locality="University Park",
        latitude=40.7982,
        longitude=-77.8599,
    )


def test_repeat_save_preserves_exact_id_and_does_not_overwrite_demo_nights(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "saved-hotels.sqlite3"
    provider_id = "  provider:Exact-ID  "

    first = save_hotel(_hotel(provider_id), _center(), database_path)
    assert first.created is True

    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            UPDATE demo_hotel_nights
            SET nightly_rate_cents = 12345, rooms_available = 7
            WHERE hotel_id = ? AND stay_date = '2026-10-10'
            """,
            (provider_id,),
        )

    changed_provider_record = DiscoveredHotel(
        provider_place_id=provider_id,
        name="Changed provider name",
        formatted_address="Changed provider address",
        latitude=41.0,
        longitude=-78.0,
    )
    repeated = save_hotel(
        changed_provider_record,
        _center(),
        database_path,
    )

    assert repeated.created is False
    assert repeated.hotel.provider_place_id == provider_id
    assert repeated.hotel.name == "Example Hotel"
    assert len(repeated.hotel.demo_nights) == 5
    assert repeated.hotel.demo_nights[0].stay_date == "2026-10-10"
    assert repeated.hotel.demo_nights[0].nightly_rate_cents == 12345
    assert repeated.hotel.demo_nights[0].rooms_available == 7
    assert {
        night.stay_date for night in repeated.hotel.demo_nights
    } == set(SIMULATED_STAY_DATES)
    assert all(
        night.nightly_rate_cents == SIMULATED_NIGHTLY_RATE_CENTS
        and night.rooms_available == SIMULATED_ROOMS_AVAILABLE
        for night in repeated.hotel.demo_nights[1:]
    )

    with sqlite3.connect(database_path) as connection:
        counts = {
            table: connection.execute(
                f"SELECT COUNT(*) FROM {table}"
            ).fetchone()[0]
            for table in (
                "saved_hotels",
                "saved_search_contexts",
                "saved_hotel_zip_associations",
                "demo_hotel_nights",
            )
        }
    assert counts == {
        "saved_hotels": 1,
        "saved_search_contexts": 1,
        "saved_hotel_zip_associations": 1,
        "demo_hotel_nights": 5,
    }


def test_local_lookup_returns_only_hotels_associated_with_requested_zip(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "saved-hotels.sqlite3"
    save_hotel(_hotel("place-16802"), _center("16802"), database_path)
    save_hotel(_hotel("place-01234"), _center("01234"), database_path)

    result = list_saved_hotels_for_postcode("16802", database_path)
    empty_result = list_saved_hotels_for_postcode("99999", database_path)

    assert result.search_center == _center("16802")
    assert [hotel.provider_place_id for hotel in result.hotels] == [
        "place-16802"
    ]
    assert result.saved_provider_ids == ("place-01234", "place-16802")
    assert empty_result.search_center is None
    assert empty_result.hotels == ()
    assert empty_result.saved_provider_ids == (
        "place-01234",
        "place-16802",
    )


def test_remove_saved_hotel_is_transactional_and_preserves_unrelated_rows(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "saved-hotels.sqlite3"
    save_hotel(_hotel("place-a"), _center(), database_path)
    save_hotel(_hotel("place-b"), _center(), database_path)

    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            CREATE TRIGGER block_place_a_delete
            BEFORE DELETE ON saved_hotels
            WHEN OLD.hotel_id = 'place-a'
            BEGIN
                SELECT RAISE(ABORT, 'test rollback');
            END
            """
        )

    with pytest.raises(TravelDataError):
        remove_saved_hotel("place-a", database_path)

    with sqlite3.connect(database_path) as connection:
        failed_removal_counts = {
            table: connection.execute(
                f"SELECT COUNT(*) FROM {table} WHERE hotel_id = 'place-a'"
            ).fetchone()[0]
            for table in (
                "saved_hotels",
                "saved_hotel_zip_associations",
                "demo_hotel_nights",
            )
        }
        connection.execute("DROP TRIGGER block_place_a_delete")

    assert failed_removal_counts == {
        "saved_hotels": 1,
        "saved_hotel_zip_associations": 1,
        "demo_hotel_nights": 5,
    }

    assert remove_saved_hotel("place-a", database_path) == "place-a"

    with sqlite3.connect(database_path) as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM saved_hotels WHERE hotel_id = 'place-a'"
        ).fetchone()[0] == 0
        assert connection.execute(
            """
            SELECT COUNT(*) FROM saved_hotel_zip_associations
            WHERE hotel_id = 'place-a'
            """
        ).fetchone()[0] == 0
        assert connection.execute(
            """
            SELECT COUNT(*) FROM demo_hotel_nights
            WHERE hotel_id = 'place-a'
            """
        ).fetchone()[0] == 0
        assert connection.execute(
            "SELECT COUNT(*) FROM saved_hotels WHERE hotel_id = 'place-b'"
        ).fetchone()[0] == 1
        assert connection.execute(
            """
            SELECT COUNT(*) FROM demo_hotel_nights
            WHERE hotel_id = 'place-b'
            """
        ).fetchone()[0] == 5
        assert connection.execute(
            """
            SELECT COUNT(*) FROM saved_search_contexts
            WHERE postcode = '16802'
            """
        ).fetchone()[0] == 1

    remove_saved_hotel("place-b", database_path)
    with sqlite3.connect(database_path) as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM saved_search_contexts"
        ).fetchone()[0] == 0

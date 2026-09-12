from pathlib import Path

import pytest

from app.travel_data import TravelDataError, load_hotel_stays, search_hotel_stays


def test_load_hotel_stays_joins_records_and_calculates_price() -> None:
    stays = load_hotel_stays()

    first = next(stay for stay in stays if stay.trip_id == "T001")
    assert first.hotel_id == "H001"
    assert first.hotel_name == "Harbor Lantern Hotel"
    assert first.nights == 2
    assert first.nightly_rate_usd == 150
    assert first.estimated_total_usd == 300


def test_search_matches_partial_hotel_name_without_case_sensitivity() -> None:
    matches = search_hotel_stays("  harbor LANTERN  ")

    assert [stay.trip_id for stay in matches] == ["T001", "T009"]


def test_search_returns_empty_list_for_unknown_hotel() -> None:
    assert search_hotel_stays("Ocean Palace") == []


def test_search_rejects_blank_hotel_name() -> None:
    with pytest.raises(ValueError, match="Enter a hotel name"):
        search_hotel_stays("   ")


def test_join_rejects_unknown_hotel_reference(tmp_path: Path) -> None:
    hotels = tmp_path / "hotels.csv"
    trips = tmp_path / "trips.csv"
    hotels.write_text(
        "hotel_id,hotel_name,city,state,nightly_rate_usd\n"
        "H001,Example Hotel,Boston,MA,100\n",
        encoding="utf-8-sig",
    )
    trips.write_text(
        "trip_id,hotel_id,trip_name,check_in,check_out\n"
        "T001,H999,Example Stay,2026-09-18,2026-09-20\n",
        encoding="utf-8-sig",
    )

    with pytest.raises(TravelDataError, match="unknown hotel_id"):
        load_hotel_stays(hotels, trips)


from pathlib import Path

import pytest

from app.travel_data import load_hotel_stays, search_hotel_stays


def test_load_hotel_stays_joins_records_and_calculates_price(tmp_path: Path) -> None:
    stays = load_hotel_stays(tmp_path / "travel.sqlite3")

    first = next(stay for stay in stays if stay.trip_id == "T001")
    assert first.hotel_id == "H001"
    assert first.hotel_name == "Harbor Lantern Hotel"
    assert first.nights == 2
    assert first.nightly_rate_usd == 150
    assert first.estimated_total_usd == 300


def test_search_matches_partial_hotel_name_without_case_sensitivity(
    tmp_path: Path,
) -> None:
    matches = search_hotel_stays(
        "  harbor LANTERN  ",
        tmp_path / "travel.sqlite3",
    )

    assert [stay.trip_id for stay in matches] == ["T001", "T009"]


def test_search_returns_empty_list_for_unknown_hotel(tmp_path: Path) -> None:
    assert search_hotel_stays("Ocean Palace", tmp_path / "travel.sqlite3") == []


def test_search_rejects_blank_hotel_name(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Enter a hotel name"):
        search_hotel_stays("   ", tmp_path / "travel.sqlite3")

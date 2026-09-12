"""Read and search the instructor-provided Part 1 travel data."""

from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
HOTELS_CSV = DATA_DIR / "hotels.csv"
TRIPS_CSV = DATA_DIR / "trips.csv"


class TravelDataError(RuntimeError):
    """Raised when the supplied Part 1 data cannot be joined safely."""


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


def _read_csv(path: Path, required_columns: set[str]) -> list[dict[str, str]]:
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


def load_hotel_stays(
    hotels_path: Path = HOTELS_CSV,
    trips_path: Path = TRIPS_CSV,
) -> list[HotelStay]:
    """Join the Part 1 hotel and trip files by ``hotel_id``."""

    hotel_rows = _read_csv(
        hotels_path,
        {"hotel_id", "hotel_name", "city", "state", "nightly_rate_usd"},
    )
    trip_rows = _read_csv(
        trips_path,
        {"trip_id", "hotel_id", "trip_name", "check_in", "check_out"},
    )

    hotels_by_id: dict[str, dict[str, str]] = {}
    for hotel in hotel_rows:
        hotel_id = hotel["hotel_id"]
        if hotel_id in hotels_by_id:
            raise TravelDataError(f"Duplicate hotel_id in hotels.csv: {hotel_id}")
        hotels_by_id[hotel_id] = hotel

    stays: list[HotelStay] = []
    seen_trip_ids: set[str] = set()
    for trip in trip_rows:
        trip_id = trip["trip_id"]
        if trip_id in seen_trip_ids:
            raise TravelDataError(f"Duplicate trip_id in trips.csv: {trip_id}")
        seen_trip_ids.add(trip_id)

        hotel_id = trip["hotel_id"]
        hotel = hotels_by_id.get(hotel_id)
        if hotel is None:
            raise TravelDataError(
                f"Trip {trip_id} refers to unknown hotel_id: {hotel_id}"
            )

        try:
            check_in = date.fromisoformat(trip["check_in"])
            check_out = date.fromisoformat(trip["check_out"])
            nightly_rate = float(hotel["nightly_rate_usd"])
        except ValueError as exc:
            raise TravelDataError(f"Invalid date or rate for trip {trip_id}.") from exc

        nights = (check_out - check_in).days
        if nights <= 0:
            raise TravelDataError(f"Trip {trip_id} must have at least one night.")

        stays.append(
            HotelStay(
                trip_id=trip_id,
                trip_name=trip["trip_name"],
                hotel_id=hotel_id,
                hotel_name=hotel["hotel_name"],
                city=hotel["city"],
                state=hotel["state"],
                check_in=trip["check_in"],
                check_out=trip["check_out"],
                nights=nights,
                nightly_rate_usd=nightly_rate,
                estimated_total_usd=nightly_rate * nights,
            )
        )

    return stays


def search_hotel_stays(hotel_name: str) -> list[HotelStay]:
    """Return stays whose hotel name contains the query, ignoring case."""

    normalized_query = hotel_name.strip().casefold()
    if not normalized_query:
        raise ValueError("Enter a hotel name.")

    return [
        stay
        for stay in load_hotel_stays()
        if normalized_query in stay.hotel_name.casefold()
    ]


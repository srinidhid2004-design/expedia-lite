"""FastAPI entry point for Expedia Lite Part 2."""

from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from .booking_data import (
    BookingNotFoundError,
    BookingValidationError,
    cancel_booking,
    create_booking,
    delete_booking,
    list_bookings,
    list_travelers,
)
from .config import PROJECT_ROOT_ENV_PATH, geoapify_key_status
from .database import DATABASE_PATH
from .hotel_discovery import (
    DiscoveredHotel,
    HotelDiscoveryProviderError,
    HotelDiscoveryRateLimitError,
    discover_hotels_by_zip,
)
from .location_controller import (
    GeoapifyConfigurationError,
    GeoapifyRequestError,
    ZipLocation,
    ZipLookupUnresolvedError,
    lookup_zip_location,
)
from .saved_hotel_data import (
    SavedHotelNotFoundError,
    SavedHotelValidationError,
    list_saved_hotels_for_postcode,
    remove_saved_hotel,
    save_hotel,
)
from .travel_data import TravelDataError, search_hotel_stays


class BookingCreate(BaseModel):
    user_id: str
    trip_id: str


class SavedSearchContextCreate(BaseModel):
    postcode: str
    country_code: str
    latitude: float
    longitude: float
    locality: str | None = None


class SavedHotelCreate(BaseModel):
    provider_place_id: str
    latitude: float
    longitude: float
    name: str | None = None
    formatted_address: str | None = None
    search_context: SavedSearchContextCreate


def create_app(
    database_path: Path = DATABASE_PATH,
    env_path: Path = PROJECT_ROOT_ENV_PATH,
) -> FastAPI:
    """Build an application bound to one SQLite database path."""

    application = FastAPI(title="Expedia Lite API", version="2.0.0")
    configuration_status = geoapify_key_status(env_path)

    @application.exception_handler(TravelDataError)
    async def handle_travel_data_error(
        _request,
        _exc: TravelDataError,
    ) -> JSONResponse:
        """Return a useful response without exposing local filesystem details."""

        return JSONResponse(
            status_code=500,
            content={"detail": "The travel database could not be used."},
        )

    @application.get("/api/health")
    def health() -> dict[str, str]:
        return {
            "status": "ok",
            "geoapify_api_key": configuration_status,
        }

    def zip_location_response(postcode: str) -> dict[str, str | float]:
        """Resolve a validated postcode and map controller errors safely."""

        try:
            location = lookup_zip_location(postcode)
        except GeoapifyConfigurationError as exc:
            raise HTTPException(
                status_code=503,
                detail="Geoapify is not configured.",
            ) from exc
        except ZipLookupUnresolvedError as exc:
            raise HTTPException(
                status_code=404,
                detail=f"ZIP code {postcode} could not be resolved.",
            ) from exc
        except GeoapifyRequestError as exc:
            raise HTTPException(
                status_code=502,
                detail="The location provider request failed.",
            ) from exc
        return location.to_dict()

    @application.get("/api/demo/zip-location")
    def demo_zip_location() -> dict[str, str | float]:
        return zip_location_response("16802")

    @application.get("/api/zip-location")
    def zip_location(
        postcode: Annotated[
            str,
            Query(description="Exactly five ASCII digits"),
        ],
    ) -> dict[str, str | float]:
        if not (
            len(postcode) == 5
            and postcode.isascii()
            and postcode.isdigit()
        ):
            raise HTTPException(
                status_code=400,
                detail="Enter exactly five digits for a U.S. ZIP code.",
            )
        return zip_location_response(postcode)

    @application.get("/api/hotels/nearby")
    def nearby_hotels(
        postcode: Annotated[
            str,
            Query(description="Exactly five ASCII digits"),
        ],
    ) -> dict[str, object]:
        if not (
            len(postcode) == 5
            and postcode.isascii()
            and postcode.isdigit()
        ):
            raise HTTPException(
                status_code=400,
                detail="Enter exactly five digits for a U.S. ZIP code.",
            )

        try:
            result = discover_hotels_by_zip(postcode)
        except GeoapifyConfigurationError as exc:
            raise HTTPException(
                status_code=503,
                detail="Geoapify is not configured.",
            ) from exc
        except ZipLookupUnresolvedError as exc:
            raise HTTPException(
                status_code=404,
                detail=f"ZIP code {postcode} could not be resolved.",
            ) from exc
        except HotelDiscoveryRateLimitError as exc:
            raise HTTPException(
                status_code=429,
                detail=(
                    "The hotel provider rate or quota limit was reached. "
                    "Please try again later."
                ),
            ) from exc
        except (GeoapifyRequestError, HotelDiscoveryProviderError) as exc:
            raise HTTPException(
                status_code=502,
                detail="The hotel discovery provider request failed.",
            ) from exc

        return result.to_dict()

    @application.get("/api/hotels/saved")
    def saved_hotels(
        postcode: Annotated[
            str,
            Query(description="Exactly five ASCII digits"),
        ],
    ) -> dict[str, object]:
        try:
            result = list_saved_hotels_for_postcode(
                postcode,
                database_path,
            )
        except SavedHotelValidationError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return result.to_dict()

    @application.post("/api/hotels/saved")
    def post_saved_hotel(request: SavedHotelCreate) -> dict[str, object]:
        try:
            result = save_hotel(
                DiscoveredHotel(
                    provider_place_id=request.provider_place_id,
                    name=request.name,
                    formatted_address=request.formatted_address,
                    latitude=request.latitude,
                    longitude=request.longitude,
                ),
                ZipLocation(
                    postcode=request.search_context.postcode,
                    country_code=request.search_context.country_code,
                    locality=request.search_context.locality,
                    latitude=request.search_context.latitude,
                    longitude=request.search_context.longitude,
                ),
                database_path,
            )
        except SavedHotelValidationError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return result.to_dict()

    @application.delete("/api/hotels/saved")
    def delete_saved_hotel(
        hotel_id: Annotated[
            str,
            Query(description="Exact provider place identifier"),
        ],
    ) -> dict[str, str]:
        try:
            deleted_hotel_id = remove_saved_hotel(
                hotel_id,
                database_path,
            )
        except SavedHotelValidationError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except SavedHotelNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return {"deleted_hotel_id": deleted_hotel_id}

    @application.get("/api/hotels/search")
    def search_hotels(
        name: Annotated[str, Query(description="Full or partial hotel name")],
    ) -> dict[str, object]:
        normalized_name = name.strip()
        if not normalized_name:
            raise HTTPException(status_code=400, detail="Enter a hotel name.")

        matches = search_hotel_stays(normalized_name, database_path)
        return {
            "query": normalized_name,
            "count": len(matches),
            "results": [stay.to_dict() for stay in matches],
        }

    @application.get("/api/users")
    def get_users() -> dict[str, object]:
        travelers = list_travelers(database_path)
        return {
            "count": len(travelers),
            "results": [traveler.to_dict() for traveler in travelers],
        }

    @application.get("/api/bookings")
    def get_bookings(
        user_id: Annotated[
            str | None,
            Query(description="Optional traveler ID used to filter history"),
        ] = None,
    ) -> dict[str, object]:
        try:
            bookings = list_bookings(user_id, database_path)
        except BookingValidationError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {
            "count": len(bookings),
            "results": [booking.to_dict() for booking in bookings],
        }

    @application.post("/api/bookings", status_code=201)
    def post_booking(request: BookingCreate) -> dict[str, object]:
        try:
            booking = create_booking(
                request.user_id,
                request.trip_id,
                database_path,
            )
        except BookingValidationError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"booking": booking.to_dict()}

    @application.patch("/api/bookings/{booking_id}/cancel")
    def patch_booking_cancel(booking_id: str) -> dict[str, object]:
        try:
            booking = cancel_booking(booking_id, database_path)
        except BookingNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return {"booking": booking.to_dict()}

    @application.delete("/api/bookings/{booking_id}")
    def remove_booking(booking_id: str) -> dict[str, str]:
        try:
            deleted_booking_id = delete_booking(booking_id, database_path)
        except BookingNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return {"deleted_booking_id": deleted_booking_id}

    return application


app = create_app()

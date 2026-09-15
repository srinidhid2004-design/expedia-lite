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
from .database import DATABASE_PATH
from .travel_data import TravelDataError, search_hotel_stays


class BookingCreate(BaseModel):
    user_id: str
    trip_id: str


def create_app(database_path: Path = DATABASE_PATH) -> FastAPI:
    """Build an application bound to one SQLite database path."""

    application = FastAPI(title="Expedia Lite API", version="2.0.0")

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
        return {"status": "ok"}

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

"""FastAPI entry point for Expedia Lite Part 2."""

from pathlib import Path
from typing import Annotated, Callable

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from .booking_data import (
    BookingNotFoundError,
    BookingValidationError,
    cancel_booking,
    create_booking,
    delete_booking,
    list_bookings,
    list_travelers,
)
from .config import (
    GEMINI_MODEL_ID,
    PROJECT_ROOT_ENV_PATH,
    gemini_key_status,
    geoapify_key_status,
    get_gemini_api_key,
)
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
from .rag_service import (
    ProposalDiagnostic,
    RagOutcome,
    RagServiceResult,
    answer_saved_hotel_question,
)
from .saved_hotel_data import (
    SIMULATED_DATA_NOTICE,
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


class ChatbotQueryRequest(BaseModel):
    """The only browser-controlled field accepted by the chatbot route."""

    model_config = ConfigDict(extra="forbid", strict=True)

    question: str


class ChatbotParameterResponse(BaseModel):
    position: int
    value: str | int | float | None


class ChatbotRecordsResponse(BaseModel):
    columns: list[str]
    rows: list[list[str | int | float | None]]


class ChatbotQueryResponse(BaseModel):
    outcome: str
    provider_request_count: Annotated[int, Field(ge=0, le=2)]
    diagnostic_code: ProposalDiagnostic | None
    question: str
    model_identifier: str
    proposed_sql: str | None
    parameters: list[ChatbotParameterResponse]
    records: ChatbotRecordsResponse | None
    answer: str | None
    explanation: str | None
    referenced_row_numbers: list[int]
    limitation: str | None
    message: str | None
    simulated_data_notice: str


ChatbotQueryService = Callable[[str, Path], RagServiceResult]

_CHATBOT_OUTCOME_NAMES = {
    RagOutcome.INVALID_QUESTION: "invalid_question",
    RagOutcome.MISSING_CONFIGURATION: "missing_configuration",
    RagOutcome.AUTHENTICATION_FAILURE: "authentication_failure",
    RagOutcome.PERMISSION_FAILURE: "permission_failure",
    RagOutcome.QUOTA_FAILURE: "quota_failure",
    RagOutcome.RATE_LIMIT_FAILURE: "rate_limit_failure",
    RagOutcome.TIMEOUT_FAILURE: "timeout",
    RagOutcome.INVALID_PROVIDER_REQUEST: "invalid_request",
    RagOutcome.PROVIDER_FAILURE: "provider_failure",
    RagOutcome.SAFETY_BLOCKED: "safety_blocked",
    RagOutcome.EMPTY_RESPONSE: "empty_response",
    RagOutcome.MALFORMED_RESPONSE: "malformed_response",
    RagOutcome.REJECTED_QUERY: "rejected_sql",
    RagOutcome.DATABASE_FAILURE: "database_failure",
    RagOutcome.NO_MATCH: "no_match",
    RagOutcome.GROUNDING_FAILURE: "grounding_failure",
    RagOutcome.SUCCESS: "success",
}

_CHATBOT_STATUS_CODES = {
    "success": 200,
    "no_match": 200,
    "invalid_question": 400,
    "missing_configuration": 503,
    "authentication_failure": 502,
    "permission_failure": 502,
    "quota_failure": 429,
    "rate_limit_failure": 429,
    "timeout": 504,
    "invalid_request": 502,
    "provider_failure": 502,
    "safety_blocked": 502,
    "empty_response": 502,
    "malformed_response": 502,
    "rejected_sql": 422,
    "database_failure": 500,
    "grounding_failure": 502,
}

_STRUCTURAL_DIAGNOSTIC_OUTCOMES = {
    RagOutcome.MALFORMED_RESPONSE,
    RagOutcome.GROUNDING_FAILURE,
}


def _safe_provider_request_count(value: object) -> int:
    if (
        isinstance(value, int)
        and not isinstance(value, bool)
        and 0 <= value <= 2
    ):
        return value
    return 0


def _safe_diagnostic_code(
    result: RagServiceResult,
) -> ProposalDiagnostic | None:
    if (
        result.outcome not in _STRUCTURAL_DIAGNOSTIC_OUTCOMES
        or not isinstance(result.diagnostic_code, str)
    ):
        return None
    try:
        return ProposalDiagnostic(result.diagnostic_code)
    except ValueError:
        return None


def _chatbot_response(result: RagServiceResult) -> ChatbotQueryResponse:
    records = None
    if result.records is not None:
        records = ChatbotRecordsResponse(
            columns=list(result.records.columns),
            rows=[list(row) for row in result.records.rows],
        )
    return ChatbotQueryResponse(
        outcome=_CHATBOT_OUTCOME_NAMES[result.outcome],
        provider_request_count=_safe_provider_request_count(
            result.provider_request_count
        ),
        diagnostic_code=_safe_diagnostic_code(result),
        question=result.question,
        model_identifier=GEMINI_MODEL_ID,
        proposed_sql=result.proposed_sql,
        parameters=[
            ChatbotParameterResponse(
                position=parameter.position,
                value=parameter.value,
            )
            for parameter in result.parameters
        ],
        records=records,
        answer=result.answer,
        explanation=result.explanation,
        referenced_row_numbers=list(result.referenced_row_numbers),
        limitation=result.limitation,
        message=result.safe_message,
        simulated_data_notice=SIMULATED_DATA_NOTICE,
    )


def _invalid_chatbot_request_response() -> ChatbotQueryResponse:
    return ChatbotQueryResponse(
        outcome="invalid_question",
        provider_request_count=0,
        diagnostic_code=None,
        question="",
        model_identifier=GEMINI_MODEL_ID,
        proposed_sql=None,
        parameters=[],
        records=None,
        answer=None,
        explanation=None,
        referenced_row_numbers=[],
        limitation=None,
        message="The request must contain only one question string.",
        simulated_data_notice=SIMULATED_DATA_NOTICE,
    )


def create_app(
    database_path: Path = DATABASE_PATH,
    env_path: Path = PROJECT_ROOT_ENV_PATH,
    chatbot_service: ChatbotQueryService | None = None,
) -> FastAPI:
    """Build an application bound to one SQLite database path."""

    application = FastAPI(title="Expedia Lite API", version="2.0.0")

    @application.exception_handler(RequestValidationError)
    async def handle_request_validation_error(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        if request.url.path == "/api/chatbot/query":
            response = _invalid_chatbot_request_response()
            return JSONResponse(
                status_code=422,
                content=response.model_dump(mode="json"),
            )
        return await request_validation_exception_handler(request, exc)

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
            "geoapify_api_key": geoapify_key_status(env_path),
            "gemini_api_key": gemini_key_status(env_path),
        }

    @application.post(
        "/api/chatbot/query",
        response_model=ChatbotQueryResponse,
    )
    def chatbot_query(request: ChatbotQueryRequest) -> JSONResponse:
        if chatbot_service is None:
            result = answer_saved_hotel_question(
                request.question,
                database_path,
                api_key=get_gemini_api_key(env_path),
            )
        else:
            result = chatbot_service(request.question, database_path)
        response = _chatbot_response(result)
        return JSONResponse(
            status_code=_CHATBOT_STATUS_CODES[response.outcome],
            content=response.model_dump(mode="json"),
        )

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

"""FastAPI entry point for Expedia Lite Part 1."""

from typing import Annotated

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse

from .travel_data import TravelDataError, search_hotel_stays


app = FastAPI(title="Expedia Lite API", version="1.0.0")


@app.exception_handler(TravelDataError)
async def handle_travel_data_error(_request, _exc: TravelDataError) -> JSONResponse:
    """Return a useful response without exposing local filesystem details."""

    return JSONResponse(
        status_code=500,
        content={"detail": "The travel data could not be loaded."},
    )


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/hotels/search")
def search_hotels(
    name: Annotated[str, Query(description="Full or partial hotel name")],
) -> dict[str, object]:
    normalized_name = name.strip()
    if not normalized_name:
        raise HTTPException(status_code=400, detail="Enter a hotel name.")

    matches = search_hotel_stays(normalized_name)
    return {
        "query": normalized_name,
        "count": len(matches),
        "results": [stay.to_dict() for stay in matches],
    }


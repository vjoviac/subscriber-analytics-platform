from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: Literal["healthy"]


app = FastAPI(
    title="Subscriber Analytics Platform API",
    description=(
        "HTTP interface for operational subscriber profile access."
    ),
)


@app.get(
    "/health",
    response_model=HealthResponse,
    summary="Check API liveness",
    description=(
        "Confirms that the API process is running. "
        "This endpoint does not check MongoDB readiness."
    ),
)
def get_health() -> HealthResponse:
    return HealthResponse(
        status="healthy"
    )

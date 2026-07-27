import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from pymongo.errors import PyMongoError

from infrastructure.mongodb_config import (
    MongoDBConfigurationError,
    create_mongodb_client,
    ping_mongodb,
)


logger = logging.getLogger(__name__)


class HealthResponse(BaseModel):
    status: Literal["healthy"]


class ReadinessResponse(BaseModel):
    status: Literal["ready"]


class ReadinessErrorResponse(BaseModel):
    status: Literal["not_ready"]
    detail: str


@asynccontextmanager
async def lifespan(
    application: FastAPI,
) -> AsyncIterator[None]:
    application.state.mongodb_client = None

    try:
        application.state.mongodb_client = (
            create_mongodb_client()
        )
    except (
        MongoDBConfigurationError,
        PyMongoError,
    ):
        logger.warning(
            "MongoDB client could not be initialized."
        )

    try:
        yield
    finally:
        mongodb_client = (
            application.state.mongodb_client
        )

        if mongodb_client is not None:
            mongodb_client.close()


app = FastAPI(
    title="Subscriber Analytics Platform API",
    description=(
        "HTTP interface for operational subscriber profile access."
    ),
    lifespan=lifespan,
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


@app.get(
    "/ready",
    response_model=ReadinessResponse,
    responses={
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "model": ReadinessErrorResponse,
            "description": "MongoDB is unavailable.",
        }
    },
    summary="Check API readiness",
    description=(
        "Confirms that MongoDB is available and the API "
        "can serve operational subscriber data."
    ),
)
def get_readiness(
    request: Request,
) -> ReadinessResponse | JSONResponse:
    mongodb_client = getattr(
        request.app.state,
        "mongodb_client",
        None,
    )

    if mongodb_client is None:
        return build_not_ready_response()

    try:
        ping_mongodb(
            mongodb_client
        )
    except PyMongoError:
        logger.warning(
            "MongoDB readiness check failed."
        )

        return build_not_ready_response()

    return ReadinessResponse(
        status="ready"
    )


def build_not_ready_response() -> JSONResponse:
    response = ReadinessErrorResponse(
        status="not_ready",
        detail="MongoDB is unavailable.",
    )

    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content=response.model_dump(),
    )

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated, Literal

from fastapi import (
    FastAPI,
    HTTPException,
    Path,
    Query,
    Request,
    status,
)
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from pymongo.errors import PyMongoError

from api.models import (
    ErrorResponse,
    PaginationMetadata,
    SubscriberProfileListResponse,
    SubscriberProfileResponse,
)

from infrastructure.mongodb_config import (
    MongoDBConfigurationError,
    create_mongodb_client,
    ping_mongodb,
)

from serving.mongodb_profiles import (
    count_subscriber_profiles,
    find_subscriber_profile,
    find_subscriber_profiles_page,
    get_subscriber_profiles_collection,
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

@app.get(
    "/subscribers",
    response_model=SubscriberProfileListResponse,
    responses={
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "model": ErrorResponse,
            "description": (
                "Subscriber profile service is unavailable."
            ),
        },
    },
    summary="List subscriber profiles",
    description=(
        "Returns a bounded page of current MongoDB-backed "
        "subscriber profiles ordered by subscriber ID."
    ),
)
def list_subscriber_profiles(
    request: Request,
    page: Annotated[
        int,
        Query(
            ge=1,
            description="One-based page number.",
        ),
    ] = 1,
    page_size: Annotated[
        int,
        Query(
            ge=1,
            le=100,
            description="Profiles returned per page.",
        ),
    ] = 20,
) -> SubscriberProfileListResponse:
    mongodb_client = getattr(
        request.app.state,
        "mongodb_client",
        None,
    )

    if mongodb_client is None:
        raise HTTPException(
            status_code=(
                status.HTTP_503_SERVICE_UNAVAILABLE
            ),
            detail=(
                "Subscriber profile service is unavailable."
            ),
        )

    try:
        collection = (
            get_subscriber_profiles_collection(
                mongodb_client
            )
        )
        total_items = count_subscriber_profiles(
            collection
        )
        profile_documents = (
            find_subscriber_profiles_page(
                collection,
                page,
                page_size,
            )
        )
    except (
        MongoDBConfigurationError,
        PyMongoError,
    ):
        logger.warning(
            "Subscriber profile listing failed."
        )

        raise HTTPException(
            status_code=(
                status.HTTP_503_SERVICE_UNAVAILABLE
            ),
            detail=(
                "Subscriber profile service is unavailable."
            ),
        ) from None

    total_pages = (
        total_items + page_size - 1
    ) // page_size

    return SubscriberProfileListResponse(
        items=[
            SubscriberProfileResponse.model_validate(
                profile_document
            )
            for profile_document in profile_documents
        ],
        pagination=PaginationMetadata(
            page=page,
            page_size=page_size,
            total_items=total_items,
            total_pages=total_pages,
        ),
    )

@app.get(
    "/subscribers/{subscriber_id}",
    response_model=SubscriberProfileResponse,
    responses={
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorResponse,
            "description": "Subscriber profile not found.",
        },
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "model": ErrorResponse,
            "description": (
                "Subscriber profile service is unavailable."
            ),
        },
    },
    summary="Get subscriber profile",
    description=(
        "Returns the current MongoDB-backed profile for "
        "the canonical subscriber ID."
    ),
)
def get_subscriber_profile(
    subscriber_id: Annotated[
        str,
        Path(
            min_length=1,
            max_length=64,
            description="Canonical subscriber identifier.",
        ),
    ],
    request: Request,
) -> SubscriberProfileResponse:
    mongodb_client = getattr(
        request.app.state,
        "mongodb_client",
        None,
    )

    if mongodb_client is None:
        raise HTTPException(
            status_code=(
                status.HTTP_503_SERVICE_UNAVAILABLE
            ),
            detail=(
                "Subscriber profile service is unavailable."
            ),
        )

    try:
        collection = (
            get_subscriber_profiles_collection(
                mongodb_client
            )
        )
        profile_document = find_subscriber_profile(
            collection,
            subscriber_id,
        )
    except (
        MongoDBConfigurationError,
        PyMongoError,
    ):
        logger.warning(
            "Subscriber profile lookup failed."
        )

        raise HTTPException(
            status_code=(
                status.HTTP_503_SERVICE_UNAVAILABLE
            ),
            detail=(
                "Subscriber profile service is unavailable."
            ),
        ) from None

    if profile_document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscriber profile not found.",
        )

    return SubscriberProfileResponse.model_validate(
        profile_document
    )
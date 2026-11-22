import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.config import Settings, get_settings
from app.schemas import PostRequest, PostingResponse, ValidationFailure
from app.services.posting_service import PostingService, platform_status

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s :: %(message)s",
)
logger = logging.getLogger("app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    registered, configured = platform_status(settings)
    logger.info("registered platforms: %s", ", ".join(registered))
    logger.info("configured platforms: %s", ", ".join(configured) or "none")
    yield


app = FastAPI(
    title="Automated Multi-Platform Posting Service",
    description=(
        "Publishes a single validated message to Telegram, Discord, Mastodon, "
        "Bluesky and Dev.to in one request."
    ),
    version="1.0.0",
    lifespan=lifespan,
)


@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError):
    errors = [
        {
            "field": ".".join(str(part) for part in error["loc"][1:]) or "body",
            "message": error["msg"].removeprefix("Value error, "),
            "type": error["type"],
        }
        for error in exc.errors()
    ]
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"success": False, "detail": "request validation failed", "errors": errors},
    )


def get_service(settings: Settings = Depends(get_settings)) -> PostingService:
    return PostingService(settings)


@app.get("/health", tags=["system"])
async def health(settings: Settings = Depends(get_settings)) -> dict[str, object]:
    registered, configured = platform_status(settings)
    return {
        "status": "ok",
        "environment": settings.app_env,
        "platforms": registered,
        "configured": configured,
    }


@app.post(
    "/posting",
    response_model=PostingResponse,
    status_code=status.HTTP_200_OK,
    tags=["posting"],
    summary="Publish a message to every configured platform",
    responses={
        status.HTTP_200_OK: {"description": "Per-platform posting results"},
        status.HTTP_422_UNPROCESSABLE_ENTITY: {
            "model": ValidationFailure,
            "description": "Message failed validation",
        },
    },
)
async def create_post(
    payload: PostRequest,
    service: PostingService = Depends(get_service),
) -> PostingResponse:
    return await service.publish(payload.message)

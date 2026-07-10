from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware

from app.api.v1.router import api_v1_router
from app.config import settings

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(SessionMiddleware, secret_key=settings.jwt_secret_key)

app.include_router(api_v1_router, prefix="/v1")


@app.get("/health", tags=["health"])
def root_health() -> dict[str, str]:
    return {"status": "ok"}

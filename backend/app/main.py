from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.api.v1.router import api_v1_router
from app.config import settings
from app.core.cors import cors_allow_origin_regex, cors_allow_origins

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Session first so CORS is outermost and still labels error / preflight responses.
app.add_middleware(SessionMiddleware, secret_key=settings.jwt_secret_key)
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_allow_origins(settings),
    allow_origin_regex=cors_allow_origin_regex(settings),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_v1_router, prefix="/v1")


@app.get("/health", tags=["health"])
def root_health() -> dict[str, str]:
    return {"status": "ok"}

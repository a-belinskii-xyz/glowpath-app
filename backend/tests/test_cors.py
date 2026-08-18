from app.config import Settings
from app.core.cors import (
    cors_allow_origin_regex,
    cors_allow_origins,
    localhost_origin_aliases,
)
from app.main import app
from fastapi.testclient import TestClient


def test_localhost_origin_aliases_include_loopback() -> None:
    aliases = localhost_origin_aliases("http://localhost:5173")
    assert "http://localhost:5173" in aliases
    assert "http://127.0.0.1:5173" in aliases
    assert "http://[::1]:5173" in aliases


def test_non_local_origin_is_not_aliased() -> None:
    assert localhost_origin_aliases("https://app.example.com") == ["https://app.example.com"]


def test_cors_allow_origins_includes_frontend_url_and_loopback() -> None:
    settings = Settings(
        cors_origins="https://app.example.com",
        frontend_url="http://localhost:5173",
        debug=False,
    )
    origins = cors_allow_origins(settings)
    assert "https://app.example.com" in origins
    assert "http://localhost:5173" in origins
    assert "http://127.0.0.1:5173" in origins


def test_cors_allow_origin_regex_only_in_debug() -> None:
    assert (
        cors_allow_origin_regex(Settings(debug=False, cors_origins="https://app.example.com"))
        is None
    )
    assert (
        cors_allow_origin_regex(Settings(debug=True, cors_origins="https://app.example.com"))
        is not None
    )


def test_preflight_register_allows_localhost_and_loopback() -> None:
    client = TestClient(app)
    for origin in ("http://localhost:5173", "http://127.0.0.1:5173"):
        response = client.options(
            "/v1/auth/register",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type,accept-language",
            },
        )
        assert response.status_code == 200, response.text
        assert response.headers["access-control-allow-origin"] == origin

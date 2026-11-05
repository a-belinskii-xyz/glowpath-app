import logging
from collections.abc import Iterator
from typing import Any

import pytest
import sentry_sdk
from app.core import sentry as app_sentry
from app.main import app
from fastapi.testclient import TestClient
from sentry_sdk.envelope import Envelope
from sentry_sdk.transport import Transport

FAKE_DSN = "https://public@o0.ingest.de.sentry.io/0"
TOKEN_URL = '127.0.0.1:5000 - "GET /v1/auth/verify-email?token=secret-token HTTP/1.1" 200'


class CaptureTransport(Transport):
    """Keeps envelopes in memory instead of sending them."""

    def __init__(self) -> None:
        super().__init__()
        self.envelopes: list[Envelope] = []
        # Extra sentry_sdk.init() options a test wants on top of init_sentry()'s.
        self.extra_init_kwargs: dict[str, Any] = {}

    def capture_envelope(self, envelope: Envelope) -> None:
        self.envelopes.append(envelope)

    def item_types(self) -> list[str]:
        return [item.headers.get("type", "") for env in self.envelopes for item in env.items]

    def payload(self) -> str:
        items = (item for env in self.envelopes for item in env.items)
        return "".join(item.get_bytes().decode(errors="replace") for item in items)


@pytest.fixture
def transport(monkeypatch: pytest.MonkeyPatch) -> Iterator[CaptureTransport]:
    capture = CaptureTransport()
    real_init = sentry_sdk.init

    def init_with_capture(**kwargs: Any) -> Any:
        return real_init(transport=capture, **{**kwargs, **capture.extra_init_kwargs})

    monkeypatch.setattr(app_sentry.settings, "sentry_dsn", FAKE_DSN)
    # Restored after the test so /health keeps reporting "off".
    monkeypatch.setattr(app_sentry, "_status", "off")
    monkeypatch.setattr(sentry_sdk, "init", init_with_capture)
    yield capture
    sentry_sdk.get_client().close()
    sentry_sdk.get_global_scope().set_client(None)


def _emit_access_logs(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO, logger="uvicorn.access")
    access = logging.getLogger("uvicorn.access")
    access.info(TOKEN_URL)
    access.error(TOKEN_URL)


def test_init_sends_no_logs(transport: CaptureTransport, caplog: pytest.LogCaptureFixture) -> None:
    app_sentry.init_sentry()
    assert app_sentry.sentry_status() == "on"

    _emit_access_logs(caplog)
    # An event right after would carry access lines as breadcrumbs if they leaked.
    sentry_sdk.capture_message("probe event")
    sentry_sdk.flush()

    assert "log" not in transport.item_types()
    assert "probe event" in transport.payload()
    assert "secret-token" not in transport.payload()


def test_access_logs_stay_out_if_logs_get_enabled(
    transport: CaptureTransport, caplog: pytest.LogCaptureFixture
) -> None:
    transport.extra_init_kwargs["enable_logs"] = True
    app_sentry.init_sentry()

    caplog.set_level(logging.INFO, logger="app.sentry_probe")
    logging.getLogger("app.sentry_probe").info("probe line")
    _emit_access_logs(caplog)
    sentry_sdk.flush()

    # The probe proves the logs pipeline works here, so the absence below means something.
    assert "probe line" in transport.payload()
    assert "secret-token" not in transport.payload()


def _context(path: str, parent_sampled: bool | None) -> dict[str, Any]:
    # Shape the ASGI integration really passes: full URL as the name, clean path in the scope.
    return {
        "asgi_scope": {"path": path},
        "transaction_context": {"name": f"http://testserver{path}"},
        "parent_sampled": parent_sampled,
    }


@pytest.mark.parametrize("path", ["/health", "/v1/health"])
@pytest.mark.parametrize("parent_sampled", [None, True])
def test_sampler_drops_health_checks(path: str, parent_sampled: bool | None) -> None:
    assert app_sentry._traces_sampler(_context(path, parent_sampled)) == 0.0


def test_sampler_falls_back_to_url_path_without_asgi_scope() -> None:
    context = {"transaction_context": {"name": "http://testserver/v1/health?x=1"}}
    assert app_sentry._traces_sampler(context) == 0.0


def test_sampler_uses_configured_rate(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(app_sentry.settings, "sentry_traces_sample_rate", 0.2)
    assert app_sentry._traces_sampler(_context("/v1/entries", None)) == 0.2


def test_sampler_follows_parent_for_regular_paths() -> None:
    assert app_sentry._traces_sampler(_context("/v1/entries", True)) == 1.0


def test_health_requests_are_not_traced(
    transport: CaptureTransport, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(app_sentry.settings, "sentry_traces_sample_rate", 1.0)
    sentry_sdk.init(dsn=FAKE_DSN, traces_sampler=app_sentry._traces_sampler)
    client = TestClient(app)

    client.get("/health")
    client.get("/v1/health")
    sentry_sdk.flush()
    assert "transaction" not in transport.item_types()

    # Control: any other endpoint is traced, so the empty result above is meaningful.
    client.get("/openapi.json")
    sentry_sdk.flush()
    assert "transaction" in transport.item_types()

from __future__ import annotations

from typing import Any

import httpx

from bot.config import settings


class ApiClientError(Exception):
    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class MoodTrackerApiClient:
    def __init__(self) -> None:
        self._base = settings.api_base_url.rstrip("/")
        self._token = settings.telegram_bot_service_token

    def _headers(self, *, json_body: bool = True) -> dict[str, str]:
        headers = {
            "Accept": "application/json",
            "X-Telegram-Bot-Service-Token": self._token,
        }
        if json_body:
            headers["Content-Type"] = "application/json"
        return headers

    async def link(
        self,
        *,
        code: str,
        telegram_user_id: int,
        telegram_chat_id: int,
        locale: str | None,
    ) -> dict[str, Any]:
        return await self._request(
            "POST",
            "/v1/telegram/bot/link",
            json={
                "code": code,
                "telegram_user_id": telegram_user_id,
                "telegram_chat_id": telegram_chat_id,
                "locale": locale,
            },
        )

    async def confirm_login(
        self,
        *,
        code: str,
        telegram_user_id: int,
        locale: str | None,
    ) -> dict[str, Any]:
        return await self._request(
            "POST",
            "/v1/telegram/bot/login-confirm",
            json={"code": code, "telegram_user_id": telegram_user_id, "locale": locale},
        )

    async def unlink(self, *, telegram_user_id: int) -> dict[str, Any]:
        return await self._request(
            "POST",
            "/v1/telegram/bot/unlink",
            json={"telegram_user_id": telegram_user_id},
        )

    async def me(self, *, telegram_user_id: int) -> dict[str, Any]:
        return await self._request(
            "GET",
            "/v1/telegram/bot/me",
            params={"telegram_user_id": telegram_user_id},
        )

    async def catalog(self, *, telegram_user_id: int, locale: str | None = None) -> dict[str, Any]:
        params: dict[str, Any] = {"telegram_user_id": telegram_user_id}
        if locale:
            params["locale"] = locale
        return await self._request("GET", "/v1/telegram/bot/catalog", params=params)

    async def create_entry(
        self,
        *,
        telegram_user_id: int,
        score: int,
        tag_ids: list[str],
        goal_ids: list[str],
        note: str | None,
        source: str | None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "telegram_user_id": telegram_user_id,
            "score": score,
            "tag_ids": tag_ids,
            "goal_ids": goal_ids,
        }
        if note is not None:
            payload["note"] = note
        if source is not None:
            payload["source"] = source
        return await self._request("POST", "/v1/telegram/bot/entries", json=payload)

    async def upload_attachment(
        self,
        *,
        telegram_user_id: int,
        entry_id: str,
        kind: str,
        filename: str,
        content_type: str,
        data: bytes,
    ) -> dict[str, Any]:
        url = f"{self._base}/v1/telegram/bot/entries/{entry_id}/attachments"
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                url,
                headers=self._headers(json_body=False),
                data={"telegram_user_id": str(telegram_user_id), "kind": kind},
                files={"file": (filename, data, content_type)},
            )
        if response.status_code >= 400:
            raise ApiClientError(_extract_detail(response), status_code=response.status_code)
        payload = response.json()
        if not isinstance(payload, dict):
            raise ApiClientError("Unexpected API response")
        return payload

    async def get_session(self, *, telegram_user_id: int) -> dict[str, Any]:
        return await self._request("GET", f"/v1/telegram/bot/sessions/{telegram_user_id}")

    async def put_session(self, *, telegram_user_id: int, state: dict[str, Any]) -> dict[str, Any]:
        return await self._request(
            "PUT",
            f"/v1/telegram/bot/sessions/{telegram_user_id}",
            json={"state": state},
        )

    async def delete_session(self, *, telegram_user_id: int) -> None:
        await self._request("DELETE", f"/v1/telegram/bot/sessions/{telegram_user_id}")

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        url = f"{self._base}{path}"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(
                method,
                url,
                headers=self._headers(),
                json=json,
                params=params,
            )
        if response.status_code >= 400:
            detail = _extract_detail(response)
            raise ApiClientError(detail, status_code=response.status_code)
        if response.status_code == 204 or not response.content:
            return {}
        data = response.json()
        if not isinstance(data, dict):
            raise ApiClientError("Unexpected API response")
        return data


def _extract_detail(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return response.text or f"API error ({response.status_code})"
    if isinstance(payload, dict):
        detail = payload.get("detail")
        if isinstance(detail, str):
            return detail
    return f"API error ({response.status_code})"


api_client = MoodTrackerApiClient()

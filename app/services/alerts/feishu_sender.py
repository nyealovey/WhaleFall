"""飞书机器人发送器."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from flask import current_app

from app.repositories.email_alerts_repository import EmailAlertsRepository

if TYPE_CHECKING:
    from app.services.alerts.email_alert_settings_service import EmailAlertSettingsService


class FeishuSender:
    """使用飞书自定义机器人发送文本通知."""

    def __init__(
        self,
        settings_service: EmailAlertSettingsService | None = None,
        repository: EmailAlertsRepository | None = None,
    ) -> None:
        self._settings_service = settings_service
        self._repository = repository or EmailAlertsRepository()

    def is_ready(self) -> bool:
        return bool(self._get_saved_webhook_url())

    def send_text(self, *, title: str, text_body: str, webhook_url: str | None = None) -> None:
        webhook_url = webhook_url or self._get_saved_webhook_url()
        if not webhook_url:
            raise RuntimeError("飞书机器人 URL 未配置")

        payload = {
            "msg_type": "text",
            "content": {
                "text": f"{title}\n\n{text_body}".strip(),
            },
        }
        request = Request(
            webhook_url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json; charset=utf-8"},
            method="POST",
        )
        timeout = int(current_app.config.get("FEISHU_REQUEST_TIMEOUT_SECONDS") or 10)
        try:
            with urlopen(request, timeout=timeout) as response:
                response_body = response.read().decode("utf-8")
        except HTTPError as exc:
            raise RuntimeError(f"飞书机器人请求失败: HTTP {exc.code}") from exc
        except URLError as exc:
            raise RuntimeError(f"飞书机器人请求失败: {exc.reason}") from exc

        self._raise_for_response(response_body)

    @staticmethod
    def _raise_for_response(response_body: str) -> None:
        if not response_body.strip():
            return
        try:
            payload = json.loads(response_body)
        except json.JSONDecodeError:
            return

        status_code = payload.get("StatusCode", payload.get("code", 0))
        if status_code not in {0, "0"}:
            message = payload.get("StatusMessage") or payload.get("msg") or payload.get("message") or "未知错误"
            raise RuntimeError(f"飞书机器人返回失败: {message}")

    def _get_saved_webhook_url(self) -> str:
        settings_service = self._settings_service
        if settings_service is None:
            settings = self._repository.get_settings()
            if settings is None:
                return ""
            return settings.get_feishu_webhook_url()
        return settings_service.get_feishu_webhook_url()

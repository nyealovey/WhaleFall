"""邮件发送器."""

from __future__ import annotations

import smtplib
from email.message import EmailMessage

from flask import current_app


class EmailSender:
    """使用 SMTP 发送邮件."""

    def is_ready(self) -> bool:
        host = str(current_app.config.get("MAIL_SMTP_HOST") or "").strip()
        from_address = str(current_app.config.get("MAIL_FROM_ADDRESS") or "").strip()
        username = str(current_app.config.get("MAIL_SMTP_USERNAME") or "").strip()
        password = str(current_app.config.get("MAIL_SMTP_PASSWORD") or "").strip()
        use_tls = bool(current_app.config.get("MAIL_USE_TLS"))
        use_ssl = bool(current_app.config.get("MAIL_USE_SSL"))
        if not host or not from_address:
            return False
        if use_tls and use_ssl:
            return False
        return not ((username and not password) or (password and not username))

    def send_email(self, *, recipients: list[str], subject: str, text_body: str) -> None:
        if not self.is_ready():
            raise RuntimeError("SMTP 配置未完成")

        message = EmailMessage()
        from_address = str(current_app.config.get("MAIL_FROM_ADDRESS") or "").strip()
        from_name = str(current_app.config.get("MAIL_FROM_NAME") or "").strip()
        message["Subject"] = subject
        message["From"] = f"{from_name} <{from_address}>" if from_name else from_address
        message["To"] = ", ".join(recipients)
        message.set_content(text_body)

        host = str(current_app.config.get("MAIL_SMTP_HOST") or "").strip()
        port = int(current_app.config.get("MAIL_SMTP_PORT") or 25)
        username = str(current_app.config.get("MAIL_SMTP_USERNAME") or "").strip()
        password = str(current_app.config.get("MAIL_SMTP_PASSWORD") or "").strip()
        timeout = int(current_app.config.get("MAIL_TIMEOUT_SECONDS") or 10)
        use_tls = bool(current_app.config.get("MAIL_USE_TLS"))
        use_ssl = bool(current_app.config.get("MAIL_USE_SSL"))

        smtp_class = smtplib.SMTP_SSL if use_ssl else smtplib.SMTP
        with smtp_class(host, port, timeout=timeout) as client:
            if use_tls:
                client.starttls()
            if username and password:
                client.login(username, password)
            client.send_message(message)

"""Отправка писем через Resend API.

Вся email-логика живёт здесь, а не в auth-роутах. Секреты не логируются,
ошибки отправки оборачиваются в понятное EmailSendError без деталей ключей.
"""

import html
from typing import Any

import resend

from app.config import settings


class EmailSendError(Exception):
    """Не удалось отправить письмо через Resend."""


def _render_verification_html(username: str, verification_url: str, expire_minutes: int) -> str:
    """Красивое HTML-письмо с кнопкой подтверждения (username экранируем)."""
    safe_name = html.escape(username)
    return f"""\
<!doctype html>
<html>
  <body style="margin:0;padding:0;background-color:#0d0d10;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:#0d0d10;padding:32px 12px;">
      <tr>
        <td align="center">
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:520px;background-color:#16161b;border:1px solid #2a2a31;border-radius:20px;padding:40px 36px;font-family:Segoe UI,Arial,sans-serif;">
            <tr>
              <td style="padding-bottom:8px;">
                <span style="font-size:26px;font-weight:800;color:#ff9a2e;letter-spacing:-0.5px;">Vedro</span>
              </td>
            </tr>
            <tr>
              <td style="padding-bottom:24px;">
                <h1 style="margin:0;font-size:22px;color:#ffffff;font-weight:700;">Подтвердите ваш email</h1>
              </td>
            </tr>
            <tr>
              <td style="padding-bottom:16px;font-size:15px;line-height:1.6;color:#c9c9d1;">
                Здравствуйте, <b style="color:#ffffff;">{safe_name}</b>!<br/>
                Спасибо за регистрацию в Vedro. Остался последний шаг —
                подтвердить email, чтобы вы могли входить в аккаунт.
              </td>
            </tr>
            <tr>
              <td align="center" style="padding:12px 0 28px;">
                <a href="{verification_url}"
                   style="display:inline-block;padding:15px 36px;background:linear-gradient(135deg,#ff9a2e,#ff7a00);
                          color:#141414;font-size:16px;font-weight:700;text-decoration:none;border-radius:14px;">
                  Подтвердить email
                </a>
              </td>
            </tr>
            <tr>
              <td style="padding-bottom:10px;font-size:13px;line-height:1.6;color:#8f8f99;">
                Если кнопка не работает, скопируйте ссылку в браузер:<br/>
                <a href="{verification_url}" style="color:#ff9a2e;word-break:break-all;">{verification_url}</a>
              </td>
            </tr>
            <tr>
              <td style="padding-top:10px;font-size:12px;line-height:1.6;color:#6d6d77;border-top:1px solid #2a2a31;">
                Ссылка действительна {expire_minutes} минут.<br/>
                Если вы не регистрировались в Vedro — просто проигнорируйте это письмо.
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>"""


def _friendly_resend_error(exc: Exception) -> EmailSendError:
    """Обернуть ошибку Resend в понятный русский текст (без секретов)."""
    text = str(exc)
    if "You can only send testing emails" in text:
        return EmailSendError(
            "Resend без своего домена отправляет письма только на email "
            "владельца аккаунта (он указан в скобках в ответе Resend). "
            "Варианты: зарегистрируй этот адрес; подключи свой домен на "
            "resend.com/domains и поменяй EMAIL_FROM в backend/.env; "
            "или включи EMAIL_DEV_MODE=true для тестов без писем. "
            f"Ответ Resend: {text[:200]}"
        )
    return EmailSendError(
        f"Не удалось отправить письмо: {text[:200] or type(exc).__name__}"
    )


def send_verification_email(email: str, username: str, verification_token: str) -> str:
    """Отправить письмо со ссылкой подтверждения через Resend.

    Токен уходит ТОЛЬКО в письмо (в ссылке) и нигде не логируется.

    Returns:
        Ссылка подтверждения (verification_url). Используется маршрутом
        только в dev-режиме (EMAIL_DEV_MODE=true или ключ Resend не задан).

    Raises:
        EmailSendError: если Resend недоступен или отверг запрос
            (текст ошибки Resend сохраняется — он без секретов).
    """
    verification_url = (
        f"{settings.app_base_url}/verify-email?token={verification_token}"
    )

    # DEV-режим: письма не отправляем, ссылку вернёт маршрут
    if settings.email_dev_mode:
        print(f"[email][dev] письмо не отправляется; ссылка: {verification_url}")
        return verification_url

    if not settings.resend_api_key:
        # Почта не настроена: регистрация работает, письма не уходят
        print("[email] RESEND_API_KEY не задан — письмо не отправляется (dev-режим)")
        return verification_url

    params: dict[str, Any] = {
        "from": settings.email_from,
        "to": [email],
        "subject": "Подтвердите ваш email — Vedro",
        "html": _render_verification_html(
            username,
            verification_url,
            settings.email_verification_token_expire_minutes,
        ),
    }

    try:
        resend.api_key = settings.resend_api_key
        resend.Emails.send(params)
    except Exception as exc:  # ошибки SDK/сети/квот — оборачиваем без секретов
        raise _friendly_resend_error(exc) from exc

    return verification_url
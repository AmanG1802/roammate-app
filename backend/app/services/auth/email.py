"""Resend wrapper for transactional auth emails."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

_TEMPLATES_DIR = Path(__file__).parent / "templates"


def _load_template(name: str) -> str:
    return (_TEMPLATES_DIR / name).read_text(encoding="utf-8")


def _send(to: str, subject: str, html: str) -> None:  # pragma: no cover — Resend API
    if not settings.RESEND_API_KEY:
        # In development we log instead of failing — the verify/reset URL is
        # printed so the developer can click through.
        logger.warning(
            "RESEND_API_KEY not set; would send to=%s subject=%r\n--- BODY ---\n%s",
            to, subject, html,
        )
        return

    try:
        import resend  # type: ignore
    except ImportError:
        logger.warning("`resend` package not installed; cannot send email to %s", to)
        return

    resend.api_key = settings.RESEND_API_KEY
    payload = {
        "from": settings.EMAIL_FROM,
        "to": [to],
        "subject": subject,
        "html": html,
    }
    try:
        resend.Emails.send(payload)
    except Exception as exc:
        logger.exception("Resend send failed: %s", exc)
        try:
            resend.Emails.send(payload)
        except Exception:
            logger.exception("Resend send retry failed; giving up")


def send_verify_email(to: str, name: Optional[str], verify_url: str) -> None:
    html = _load_template("verify_email.html").format(
        name=name or "traveler",
        verify_url=verify_url,
    )
    _send(to, "Verify your Roammate email", html)


def send_password_reset(to: str, name: Optional[str], reset_url: str) -> None:
    html = _load_template("reset_password.html").format(
        name=name or "traveler",
        reset_url=reset_url,
    )
    _send(to, "Reset your Roammate password", html)


def send_email_changed_notice(to: str, name: Optional[str], new_email: str) -> None:
    html = _load_template("email_changed.html").format(
        name=name or "traveler",
        new_email=new_email,
    )
    _send(to, "Your Roammate email was changed", html)


def send_password_changed_notice(to: str, name: Optional[str]) -> None:
    html = _load_template("password_changed.html").format(name=name or "traveler")
    _send(to, "Your Roammate password was changed", html)


def send_account_deleted_notice(to: str, name: Optional[str]) -> None:
    html = _load_template("account_deleted.html").format(name=name or "traveler")
    _send(to, "Your Roammate account has been deleted", html)

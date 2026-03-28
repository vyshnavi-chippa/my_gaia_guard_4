"""Zone-entry alerts: optional Twilio SMS, in-memory cooldown, log fallback."""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass

from app.core.config import settings

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_last_alert_ts: dict[str, float] = {}


def _cooldown_key(user_id: str, zone_id: int, suffix: str = "") -> str:
    return f"{user_id}:{zone_id}{suffix}"


def _twilio_configured() -> bool:
    return bool(
        settings.twilio_account_sid
        and settings.twilio_auth_token
        and settings.twilio_from_number
        and settings.alert_to_number
    )


def _send_sms_twilio(body: str) -> bool:
    if not _twilio_configured():
        return False
    if not settings.twilio_enabled:
        return False
    try:
        from twilio.rest import Client

        client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
        client.messages.create(
            body=body[:1600],
            from_=settings.twilio_from_number,
            to=settings.alert_to_number,
        )
        return True
    except Exception:
        logger.exception("Twilio SMS send failed")
        return False


@dataclass(frozen=True)
class AlertOutcome:
    triggered: bool
    channel: str
    detail: str


def try_zone_entry_alert(
    *,
    user_id: str,
    zone_id: int,
    severity: str,
    distance_meters: float,
    user_lat: float,
    user_lon: float,
) -> AlertOutcome:
    if not settings.alerts_enabled:
        return AlertOutcome(False, "none", "alerts_disabled")

    key = _cooldown_key(user_id, zone_id)
    now = time.monotonic()

    with _lock:
        last = _last_alert_ts.get(key)
        if last is not None and (now - last) < settings.alert_cooldown_seconds:
            return AlertOutcome(False, "none", "cooldown")

    body = (
        f"GaiaGuard: entered danger zone #{zone_id} ({severity}). "
        f"~{distance_meters:.0f}m from center. "
        f"Location {user_lat:.5f},{user_lon:.5f}"
    )

    if settings.twilio_enabled and _twilio_configured():
        if _send_sms_twilio(body):
            with _lock:
                _last_alert_ts[key] = now
            return AlertOutcome(True, "sms", "sent")

    logger.warning("ALERT %s", body)
    with _lock:
        _last_alert_ts[key] = now
    return AlertOutcome(True, "log", "logged_console")


def try_near_zone_alert(
    *,
    user_id: str,
    zone_id: int,
    severity: str,
    distance_meters: float,
    distance_to_edge_meters: float,
    user_lat: float,
    user_lon: float,
) -> AlertOutcome:
    """Alert when user is outside but within the nearby warning buffer."""
    if not settings.alerts_enabled:
        return AlertOutcome(False, "none", "alerts_disabled")

    key = _cooldown_key(user_id, zone_id, ":near")
    now = time.monotonic()

    with _lock:
        last = _last_alert_ts.get(key)
        if last is not None and (now - last) < settings.alert_cooldown_seconds:
            return AlertOutcome(False, "none", "cooldown")

    body = (
        f"GaiaGuard: NEAR danger zone #{zone_id} ({severity}). "
        f"~{distance_meters:.0f}m to center; ~{distance_to_edge_meters:.0f}m from edge. "
        f"Location {user_lat:.5f},{user_lon:.5f}"
    )

    if settings.twilio_enabled and _twilio_configured():
        if _send_sms_twilio(body):
            with _lock:
                _last_alert_ts[key] = now
            return AlertOutcome(True, "sms", "sent")

    logger.warning("ALERT %s", body)
    with _lock:
        _last_alert_ts[key] = now
    return AlertOutcome(True, "log", "logged_console")

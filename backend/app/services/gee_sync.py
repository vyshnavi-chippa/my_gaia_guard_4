"""Sync Earth-Engine-derived danger zones into PostgreSQL."""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.core.config import settings
from app.services.gee_client import detect_vegetation_loss_zones
from app.services.zone_ingestion import upsert_danger_zones_from_gee

logger = logging.getLogger(__name__)


def sync_gee_danger_zones(db: Session, latitude: float, longitude: float) -> dict:
    """
    Run GEE change detection for the given point and upsert danger zones if loss is detected.
    """
    if not settings.gee_enabled:
        return {
            "ok": True,
            "skipped": True,
            "reason": "gee_disabled",
            "change_detected": False,
            "zones_upserted": 0,
            "gee": None,
        }

    try:
        zones, debug = detect_vegetation_loss_zones(latitude, longitude)
    except Exception:
        logger.exception("Earth Engine sync failed")
        raise

    count = 0
    if zones:
        count = upsert_danger_zones_from_gee(db, zones)
        logger.warning("GEE: upserted %s danger zone(s) (change_detected=%s)", count, True)
    else:
        logger.info("GEE: no danger zone written (change_detected=%s)", debug.get("change_detected"))

    return {
        "ok": True,
        "skipped": False,
        "change_detected": debug.get("change_detected", False),
        "zones_upserted": count,
        "gee": debug,
    }

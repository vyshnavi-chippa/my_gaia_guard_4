"""
Google Earth Engine: NDVI-based vegetation loss heuristic for demo danger zones.

Requires: earthengine-api, Earth Engine enabled project, and local auth:
  earthengine authenticate
or service account JSON via GEE_CREDENTIALS_JSON (uses client_email inside file).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import ee

from app.core.config import settings
import os

project = os.getenv("GEE_PROJECT_ID")


logger = logging.getLogger(__name__)

_initialized = False


def ensure_ee_initialized() -> None:
    global _initialized
    if _initialized:
        return
    if not settings.gee_enabled:
        raise RuntimeError("Google Earth Engine is disabled (GEE_ENABLED=false).")
    project = settings.gee_project
    if not project:
        raise RuntimeError("Set GEE_PROJECT to your Earth Engine / GCP project id.")

    creds_path = settings.gee_credentials_json
    if creds_path:
        path = Path(creds_path)
        sa = json.loads(path.read_text(encoding="utf-8"))
        email = sa["client_email"]
        credentials = ee.ServiceAccountCredentials(email, str(path))
        ee.Initialize(credentials, project="gaia-guard")
    else:
        ee.Initialize(project="gaia-guard")

    _initialized = True
    logger.info("Earth Engine initialized for project %s", project)


def detect_vegetation_loss_zones(
    latitude: float,
    longitude: float,
) -> tuple[list[dict], dict]:
    """
    Compare median Sentinel-2 NDVI before vs after; if loss fraction exceeds threshold,
    return one danger zone centered on the AOI (demo simplification).

    Returns:
        (zones, debug_info): zones list for zone_ingestion, stats for API/UI.
    """
    ensure_ee_initialized()

    lon, lat = float(longitude), float(latitude)
    point = ee.Geometry.Point([lon, lat])
    aoi = point.buffer(float(settings.gee_buffer_meters))

    collection_id = settings.gee_s2_collection
    before = (
        ee.ImageCollection(collection_id)
        .filterBounds(aoi)
        .filterDate(settings.gee_before_start, settings.gee_before_end)
        .select(["B8", "B4"])
        .median()
    )
    after = (
        ee.ImageCollection(collection_id)
        .filterBounds(aoi)
        .filterDate(settings.gee_after_start, settings.gee_after_end)
        .select(["B8", "B4"])
        .median()
    )

    ndvi_before = before.normalizedDifference(["B8", "B4"])
    ndvi_after = after.normalizedDifference(["B8", "B4"])
    ndvi_change = ndvi_after.subtract(ndvi_before)
    loss = ndvi_change.lt(-float(settings.gee_ndvi_drop_threshold)).rename("loss")

    stats = loss.reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=aoi,
        scale=30,
        maxPixels=1e9,
    )
    info = stats.getInfo() or {}
    mean_loss = float(info.get("loss", 0) or 0)

    debug = {
        "mean_loss_fraction": round(mean_loss, 6),
        "threshold": settings.gee_loss_mean_threshold,
        "aoi_buffer_m": settings.gee_buffer_meters,
        "center_lat": lat,
        "center_lon": lon,
    }

    zones: list[dict] = []
    if mean_loss >= float(settings.gee_loss_mean_threshold):
        zones.append(
            {
                "latitude": lat,
                "longitude": lon,
                "radius_m": float(settings.gee_zone_radius_meters),
                "severity": "high",
            }
        )
        debug["change_detected"] = True
    else:
        debug["change_detected"] = False

    return zones, debug

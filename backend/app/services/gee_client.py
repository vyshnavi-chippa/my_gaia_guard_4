from __future__ import annotations
"""
Google Earth Engine: NDVI-based vegetation loss heuristic for demo danger zones.

Requires: earthengine-api, Earth Engine enabled project, and local auth:
  earthengine authenticate
or service account JSON via GEE_CREDENTIALS_JSON (uses client_email inside file).
"""

"""
Google Earth Engine: NDVI-based vegetation loss heuristic for demo danger zones.
"""


import json
import logging
from pathlib import Path

import ee

from app.core.config import settings

logger = logging.getLogger(__name__)

_initialized = False


# =============================
# 🔑 INIT EARTH ENGINE
# =============================
def ensure_ee_initialized() -> None:
    global _initialized
    if _initialized:
        return

    if not settings.gee_enabled:
        raise RuntimeError("GEE is disabled. Set GEE_ENABLED=true")

    project = settings.gee_project
    if not project:
        raise RuntimeError("Set GEE_PROJECT in .env")

    creds_path = settings.gee_credentials_json

    try:
        if creds_path:
            path = Path(creds_path)
            sa = json.loads(path.read_text(encoding="utf-8"))
            email = sa["client_email"]

            credentials = ee.ServiceAccountCredentials(email, str(path))
            ee.Initialize(credentials, project=project)

        else:
            ee.Initialize(project=project)

        _initialized = True
        logger.info(f"✅ Earth Engine initialized for project: {project}")

    except Exception as e:
        logger.exception("❌ Failed to initialize Earth Engine")
        raise


# =============================
# 🌿 DETECT VEGETATION LOSS
# =============================
def detect_vegetation_loss_zones(
    latitude: float,
    longitude: float,
) -> tuple[list[dict], dict]:

    ensure_ee_initialized()

    lon, lat = float(longitude), float(latitude)

    point = ee.Geometry.Point([lon, lat])
    aoi = point.buffer(float(settings.gee_buffer_meters))

    # ✅ Use UPDATED dataset (IMPORTANT)
    collection_id = "COPERNICUS/S2_SR_HARMONIZED"

    # =============================
    # 📅 BEFORE COLLECTION
    # =============================
    collection_before = (
        ee.ImageCollection(collection_id)
        .filterBounds(aoi)
        .filterDate(settings.gee_before_start, settings.gee_before_end)
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 80))
        .select(["B8", "B4"])
    )

    # =============================
    # 📅 AFTER COLLECTION
    # =============================
    collection_after = (
        ee.ImageCollection(collection_id)
        .filterBounds(aoi)
        .filterDate(settings.gee_after_start, settings.gee_after_end)
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 80))
        .select(["B8", "B4"])
    )

    # =============================
    # 🔍 DEBUG: CHECK DATA AVAILABILITY
    # =============================
    before_size = collection_before.size().getInfo()
    after_size = collection_after.size().getInfo()

    print(f"Before images: {before_size}")
    print(f"After images: {after_size}")

    # 🚨 DEMO SAFE: HANDLE EMPTY DATA
    if before_size == 0 or after_size == 0:
        logger.warning("⚠️ No satellite data found")

        return [], {
            "error": "No satellite data",
            "before_images": before_size,
            "after_images": after_size,
        }

    # =============================
    # 🌱 NDVI CALCULATION
    # =============================
    before = collection_before.median()
    after = collection_after.median()

    ndvi_before = before.normalizedDifference(["B8", "B4"])
    ndvi_after = after.normalizedDifference(["B8", "B4"])

    ndvi_change = ndvi_after.subtract(ndvi_before)

    loss = ndvi_change.lt(-float(settings.gee_ndvi_drop_threshold)).rename("loss")

    # =============================
    # 📊 REGION REDUCTION
    # =============================
    stats = loss.reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=aoi,
        scale=30,
        maxPixels=1e9,
    )

    info = stats.getInfo() or {}
    mean_loss = float(info.get("loss", 0) or 0)

    # =============================
    # 🧠 DEBUG INFO
    # =============================
    debug = {
        "mean_loss_fraction": round(mean_loss, 6),
        "threshold": settings.gee_loss_mean_threshold,
        "before_images": before_size,
        "after_images": after_size,
        "aoi_buffer_m": settings.gee_buffer_meters,
        "center_lat": lat,
        "center_lon": lon,
    }

    zones: list[dict] = []

    # =============================
    # 🚨 ZONE CREATION
    # =============================
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

from __future__ import annotations
"""
Google Earth Engine: NDVI-based vegetation loss detection (AUTO + REAL-TIME)

✔ Uses dynamic dates (no hardcoding)
✔ Uses latest Sentinel-2 dataset
✔ Handles empty data safely
✔ Ready for automatic danger zone creation
"""

import json
import logging
from pathlib import Path
from datetime import datetime, timedelta

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

    except Exception:
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

    # ✅ Latest dataset
    collection_id = "COPERNICUS/S2_SR_HARMONIZED"

    # =============================
    # 📅 🔥 DYNAMIC DATE LOGIC
    # =============================
    today = datetime.utcnow()

    before_start = (today - timedelta(days=730)).strftime("%Y-%m-%d")
    before_end = (today - timedelta(days=365)).strftime("%Y-%m-%d")

    after_start = (today - timedelta(days=60)).strftime("%Y-%m-%d")
    after_end = today.strftime("%Y-%m-%d")

    print(f"📅 BEFORE: {before_start} → {before_end}")
    print(f"📅 AFTER : {after_start} → {after_end}")

    # =============================
    # 📅 BEFORE COLLECTION
    # =============================
    collection_before = (
        ee.ImageCollection(collection_id)
        .filterBounds(aoi)
        .filterDate(before_start, before_end)
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 80))
        .select(["B8", "B4"])
    )

    # =============================
    # 📅 AFTER COLLECTION
    # =============================
    collection_after = (
        ee.ImageCollection(collection_id)
        .filterBounds(aoi)
        .filterDate(after_start, after_end)
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 80))
        .select(["B8", "B4"])
    )

    # =============================
    # 🔍 DEBUG DATA CHECK
    # =============================
    before_size = collection_before.size().getInfo()
    after_size = collection_after.size().getInfo()

    print(f"🛰️ Before images: {before_size}")
    print(f"🛰️ After images : {after_size}")

    # 🚨 Handle no data
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
    # 📊 REGION ANALYSIS
    # =============================
    stats = loss.reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=aoi,
        scale=30,
        maxPixels=1e9,
    )

    info = stats.getInfo() or {}
    mean_loss = float(info.get("loss", 0) or 0)

    print(f"🌿 Mean NDVI loss: {mean_loss}")

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
    # 🚨 AUTO ZONE CREATION
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
        print("🚨 CHANGE DETECTED → ZONE CREATED")

    else:
        debug["change_detected"] = False
        print("✅ No significant change")

    return zones, debug
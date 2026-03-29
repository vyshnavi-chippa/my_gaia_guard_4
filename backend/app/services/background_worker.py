import time
import logging

from app.db import SessionLocal
from app.services.gee_sync import sync_gee_danger_zones
from app.services.grid import generate_grid   # ✅ NEW IMPORT

logger = logging.getLogger(__name__)

INTERVAL_SECONDS = 600  # 10 minutes


def run_background_worker():
    logger.info("🚀 Starting AUTO GEE GRID SCAN...")

    grid = generate_grid()   # ✅ generate once

    logger.info(f"🌍 Total grid points: {len(grid)}")

    while True:
        db = SessionLocal()

        try:
            for i, cell in enumerate(grid):
                lat = cell["lat"]
                lon = cell["lon"]

                logger.info(f"🔍 [{i+1}/{len(grid)}] Checking {lat}, {lon}")

                try:
                    result = sync_gee_danger_zones(db, lat, lon)

                    if result.get("zones_detected"):
                        logger.info(f"🔥 Zone detected at {lat},{lon}")

                except Exception:
                    logger.warning(f"⚠️ Failed at {lat},{lon}")

        finally:
            db.close()

        logger.info(f"⏳ Sleeping {INTERVAL_SECONDS}s...\n")
        time.sleep(INTERVAL_SECONDS)
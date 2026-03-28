from typing import Iterable
from sqlalchemy.orm import Session
from app.models import DangerZone

def upsert_danger_zones_from_gee(db: Session, gee_zones: Iterable[dict]) -> int:
    count = 0

    for z in gee_zones:
        lat = float(z["latitude"])
        lon = float(z["longitude"])
        radius = float(z.get("radius_m", 1000))
        severity = z.get("severity", "medium")

        existing = (
            db.query(DangerZone)
            .filter(
                DangerZone.latitude == lat,
                DangerZone.longitude == lon,
            )
            .first()
        )

        if existing:
            existing.radius = radius
            existing.severity = severity
        else:
            new_zone = DangerZone(
                latitude=lat,
                longitude=lon,
                radius=radius,
                severity=severity,
            )
            db.add(new_zone)

        count += 1

    db.commit()
    return count
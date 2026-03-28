import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db import get_db
from app.models import DangerZone
from app.schemas import (
    DangerZoneCreate,
    DangerZoneRead,
    GeeSyncRequest,
    GeeSyncResponse,
    LocationUpdateRequest,
    LocationUpdateResponse,
)
from app.services.alerts import try_near_zone_alert, try_zone_entry_alert
from app.services.gee_sync import sync_gee_danger_zones
from app.services.geofencing import assess_location_risk
from app.services.risk_messages import build_user_message

logger = logging.getLogger(__name__)

router = APIRouter(tags=["danger-zones"])


@router.post("/add-danger-zone", response_model=DangerZoneRead)
def add_danger_zone(payload: DangerZoneCreate, db: Session = Depends(get_db)) -> DangerZoneRead:
    zone = DangerZone(
        latitude=payload.latitude,
        longitude=payload.longitude,
        radius=payload.radius,
        severity=payload.severity,
    )
    db.add(zone)
    db.commit()
    db.refresh(zone)
    return zone


@router.get("/danger-zones", response_model=list[DangerZoneRead])
def list_danger_zones(db: Session = Depends(get_db)) -> list[DangerZoneRead]:
    zones = db.query(DangerZone).order_by(DangerZone.id.desc()).all()
    return zones


@router.post("/gee/sync", response_model=GeeSyncResponse)
def gee_sync(payload: GeeSyncRequest, db: Session = Depends(get_db)) -> GeeSyncResponse:
    """Run Earth Engine change detection and upsert danger zones into the database."""
    out = sync_gee_danger_zones(db, payload.latitude, payload.longitude)
    return GeeSyncResponse(
        ok=out["ok"],
        skipped=out.get("skipped", False),
        change_detected=out.get("change_detected", False),
        zones_upserted=out.get("zones_upserted", 0),
        reason=out.get("reason"),
        gee=out.get("gee"),
    )


@router.post("/update-location", response_model=LocationUpdateResponse)
def update_location(
    payload: LocationUpdateRequest, db: Session = Depends(get_db)
) -> LocationUpdateResponse:
    gee_sync_info: dict | None = None
    if settings.gee_enabled and settings.gee_auto_sync_on_location:
        try:
            gee_sync_info = sync_gee_danger_zones(db, payload.latitude, payload.longitude)
        except Exception:
            logger.exception("GEE sync during /update-location failed")
            gee_sync_info = {
                "ok": False,
                "skipped": False,
                "error": "gee_request_failed",
                "change_detected": False,
                "zones_upserted": 0,
            }

    zones = db.query(DangerZone).all()
    result = assess_location_risk(
        payload.latitude,
        payload.longitude,
        zones,
        settings.nearby_alert_buffer_meters,
    )

    alert_triggered = False
    alert_channel: str | None = None
    alert_detail: str | None = None
    proximity_alert_triggered = False
    proximity_alert_channel: str | None = None
    proximity_alert_detail: str | None = None

    if result["risk_level"] == "inside" and result["zone"] and result["zone_id"] is not None:
        zone = result["zone"]
        outcome = try_zone_entry_alert(
            user_id=payload.user_id or "default",
            zone_id=result["zone_id"],
            severity=zone["severity"],
            distance_meters=result["distance_meters"] or 0.0,
            user_lat=payload.latitude,
            user_lon=payload.longitude,
        )
        alert_triggered = outcome.triggered
        alert_channel = outcome.channel if outcome.triggered else None
        alert_detail = outcome.detail
    elif result["risk_level"] == "near" and result["near_zone"] and result["near_zone_id"] is not None:
        nz = result["near_zone"]
        out_near = try_near_zone_alert(
            user_id=payload.user_id or "default",
            zone_id=result["near_zone_id"],
            severity=nz["severity"],
            distance_meters=result["near_distance_meters"] or 0.0,
            distance_to_edge_meters=result["distance_to_edge_meters"] or 0.0,
            user_lat=payload.latitude,
            user_lon=payload.longitude,
        )
        proximity_alert_triggered = out_near.triggered
        proximity_alert_channel = out_near.channel if out_near.triggered else None
        proximity_alert_detail = out_near.detail

    gee_detected = None
    if isinstance(gee_sync_info, dict):
        gee_detected = gee_sync_info.get("change_detected")

    zone_sev = None
    if result["zone"]:
        zone_sev = result["zone"].get("severity")
    elif result["near_zone"]:
        zone_sev = result["near_zone"].get("severity")

    user_message = build_user_message(
        risk_level=result["risk_level"],
        inside_zone=result["inside_zone"],
        near_danger=result["near_danger"],
        zone_severity=zone_sev,
        distance_meters=result["distance_meters"],
        distance_to_edge_meters=result["distance_to_edge_meters"],
        gee_change_detected=gee_detected,
    )

    return LocationUpdateResponse(
        inside_zone=result["inside_zone"],
        near_danger=result["near_danger"],
        risk_level=result["risk_level"],
        zone=result["zone"],
        near_zone=result["near_zone"],
        distance_meters=result["distance_meters"],
        distance_to_edge_meters=result["distance_to_edge_meters"],
        near_distance_meters=result["near_distance_meters"],
        user_message=user_message,
        alert_triggered=alert_triggered,
        alert_channel=alert_channel,
        alert_detail=alert_detail,
        proximity_alert_triggered=proximity_alert_triggered,
        proximity_alert_channel=proximity_alert_channel,
        proximity_alert_detail=proximity_alert_detail,
        gee_sync=gee_sync_info,
    )

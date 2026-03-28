from datetime import datetime

from pydantic import BaseModel, Field


class DangerZoneCreate(BaseModel):
    latitude: float
    longitude: float
    radius: float = Field(gt=0, description="Radius in meters")
    severity: str = "low"


class DangerZoneRead(BaseModel):
    id: int
    latitude: float
    longitude: float
    radius: float
    severity: str
    created_at: datetime

    model_config = {"from_attributes": True}


class LocationUpdateRequest(BaseModel):
    latitude: float
    longitude: float
    user_id: str | None = Field(
        default=None,
        description="Optional id for per-user alert cooldown (defaults to 'default')",
    )


class ZoneMatch(BaseModel):
    latitude: float
    longitude: float
    radius: float
    severity: str


class LocationUpdateResponse(BaseModel):
    inside_zone: bool
    near_danger: bool = False
    risk_level: str = "clear"
    zone: ZoneMatch | None
    near_zone: ZoneMatch | None = None
    distance_meters: float | None = None
    distance_to_edge_meters: float | None = None
    near_distance_meters: float | None = None
    user_message: str = ""
    alert_triggered: bool = False
    alert_channel: str | None = None
    alert_detail: str | None = None
    proximity_alert_triggered: bool = False
    proximity_alert_channel: str | None = None
    proximity_alert_detail: str | None = None
    gee_sync: dict | None = None


class GeeSyncRequest(BaseModel):
    latitude: float
    longitude: float


class GeeSyncResponse(BaseModel):
    ok: bool
    skipped: bool
    change_detected: bool = False
    zones_upserted: int = 0
    reason: str | None = None
    gee: dict | None = None

"""Human-readable risk copy for API / UI."""


def build_user_message(
    *,
    risk_level: str,
    inside_zone: bool,
    near_danger: bool,
    zone_severity: str | None,
    distance_meters: float | None,
    distance_to_edge_meters: float | None,
    gee_change_detected: bool | None,
) -> str:
    sev = (zone_severity or "unknown").upper()

    gee_note = ""
    if gee_change_detected is True:
        gee_note = (
            " Satellite (Earth Engine) flagged vegetation loss here; "
            "a danger zone was added or updated. "
        )

    if risk_level == "inside" or inside_zone:
        dist = int(distance_meters) if distance_meters is not None else 0
        return (
            f"⚠️ ALERT: Deforestation / environmental risk zone (severity {sev}). "
            f"You are inside the monitored zone (~{dist} m from center).{gee_note}"
        ).strip()

    if risk_level == "near" or near_danger:
        d = int(distance_meters) if distance_meters is not None else 0
        edge = int(distance_to_edge_meters) if distance_to_edge_meters is not None else 0
        return (
            f"⚠️ CAUTION: You are near a monitored risk zone ({sev}). "
            f"~{d} m to zone center; ~{edge} m to the zone boundary."
        ).strip()

    return "✅ No environmental threats detected near your location."

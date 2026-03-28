import math


def haversine_distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    earth_radius_m = 6_371_000

    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)

    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return earth_radius_m * c


def _quick_bounding_box_match(
    user_lat: float, user_lon: float, zone_lat: float, zone_lon: float, outer_radius_m: float
) -> bool:
    lat_delta = outer_radius_m / 111_320
    cos_lat = max(math.cos(math.radians(zone_lat)), 1e-6)
    lon_delta = outer_radius_m / (111_320 * cos_lat)

    return (zone_lat - lat_delta) <= user_lat <= (zone_lat + lat_delta) and (
        zone_lon - lon_delta
    ) <= user_lon <= (zone_lon + lon_delta)


def _zone_match_dict(zone) -> dict:
    return {
        "latitude": zone.latitude,
        "longitude": zone.longitude,
        "radius": zone.radius,
        "severity": zone.severity,
    }


def assess_location_risk(user_lat: float, user_lon: float, zones, nearby_buffer_m: float):
    """
    Classify risk as inside a zone, near a zone (within radius + buffer), or clear.
    Returns dict compatible with LocationUpdateResponse construction.
    """
    inside_id = None
    inside_zone_dict = None
    inside_dist = float("inf")

    near_id = None
    near_zone_dict = None
    near_dist = float("inf")

    for zone in zones:
        outer = float(zone.radius) + float(nearby_buffer_m)
        if not _quick_bounding_box_match(
            user_lat, user_lon, zone.latitude, zone.longitude, outer
        ):
            continue

        d = haversine_distance_meters(user_lat, user_lon, zone.latitude, zone.longitude)
        r = float(zone.radius)

        if d <= r:
            if d < inside_dist:
                inside_dist = d
                inside_id = zone.id
                inside_zone_dict = _zone_match_dict(zone)
        elif d <= r + float(nearby_buffer_m):
            if d < near_dist:
                near_dist = d
                near_id = zone.id
                near_zone_dict = _zone_match_dict(zone)

    if inside_zone_dict is not None:
        r_in = float(inside_zone_dict["radius"])
        depth_inside = max(0.0, r_in - inside_dist)
        return {
            "risk_level": "inside",
            "inside_zone": True,
            "near_danger": False,
            "zone": inside_zone_dict,
            "zone_id": inside_id,
            "distance_meters": round(inside_dist, 2),
            "distance_to_edge_meters": round(depth_inside, 2),
            "near_zone": None,
            "near_zone_id": None,
            "near_distance_meters": None,
        }

    if near_zone_dict is not None:
        r = float(near_zone_dict["radius"])
        edge = max(0.0, near_dist - r)
        return {
            "risk_level": "near",
            "inside_zone": False,
            "near_danger": True,
            "zone": None,
            "zone_id": None,
            "distance_meters": round(near_dist, 2),
            "distance_to_edge_meters": round(edge, 2),
            "near_zone": near_zone_dict,
            "near_zone_id": near_id,
            "near_distance_meters": round(near_dist, 2),
        }

    return {
        "risk_level": "clear",
        "inside_zone": False,
        "near_danger": False,
        "zone": None,
        "zone_id": None,
        "distance_meters": None,
        "distance_to_edge_meters": None,
        "near_zone": None,
        "near_zone_id": None,
        "near_distance_meters": None,
    }


def check_user_in_zones(user_lat: float, user_lon: float, zones):
    """Backward-compatible: inside-only check."""
    r = assess_location_risk(user_lat, user_lon, zones, nearby_buffer_m=0.0)
    return {
        "inside_zone": r["inside_zone"],
        "zone": r["zone"],
        "zone_id": r["zone_id"],
        "distance_meters": r["distance_meters"],
    }

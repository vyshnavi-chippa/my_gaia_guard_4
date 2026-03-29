# grid.py

def generate_grid():
    """
    Generate grid points across India (or any region).
    Each point will be scanned by GEE.
    """

    grid = []

    # 🇮🇳 India bounding box
    min_lat, max_lat = 8, 37
    min_lon, max_lon = 68, 97

    step = 1.0  # 🔥 change to 0.5 or 0.1 for higher resolution

    lat = min_lat
    while lat <= max_lat:
        lon = min_lon
        while lon <= max_lon:
            grid.append({
                "lat": round(lat, 4),
                "lon": round(lon, 4)
            })
            lon += step
        lat += step

    return grid
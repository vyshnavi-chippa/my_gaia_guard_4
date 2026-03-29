import os

import folium
import pandas as pd
import requests
import streamlit as st
from dotenv import load_dotenv
from streamlit_folium import st_folium

load_dotenv()

st.set_page_config(
    page_title="GaiaGuard",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
<style>
    .block-container {
        padding-top: 1rem;
        padding-bottom: 2rem;
        max-width: 100%;
    }
    h1 {
        font-size: 1.75rem !important;
        margin-bottom: 0.25rem !important;
    }
    /* Left control column panel */
    div[data-testid="stHorizontalBlock"] > div:nth-child(1) div[data-testid="stVerticalBlockBorderWrapper"] {
        background: linear-gradient(180deg, rgba(15, 32, 39, 0.95) 0%, rgba(32, 58, 67, 0.92) 100%);
        border: 1px solid rgba(0, 230, 230, 0.25);
        border-radius: 14px;
        padding: 1rem 1rem 1.25rem 1rem;
    }
    div[data-testid="stVerticalBlockBorderWrapper"] label,
    div[data-testid="stVerticalBlockBorderWrapper"] p,
    div[data-testid="stVerticalBlockBorderWrapper"] span {
        color: #e8f4f4 !important;
    }
</style>
""",
    unsafe_allow_html=True,
)

api_base_url = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")


def fetch_danger_zones():
    try:
        response = requests.get(f"{api_base_url}/danger-zones", timeout=10)
        response.raise_for_status()
        return response.json(), None
    except Exception as exc:
        return [], str(exc)


if "zones_cache" not in st.session_state:
    st.session_state.zones_cache = fetch_danger_zones()

st.title("🌍 GaiaGuard")
st.caption("Environmental monitoring & danger zones")

col_left, col_right = st.columns([0.34, 0.66], gap="large")

with col_left:
    with st.container(border=True):
        st.markdown("### Controls")
        lat_col, lon_col = st.columns(2, gap="small")
        with lat_col:
            user_latitude = st.number_input(
                "Latitude",
                value=28.6140,
                format="%.6f",
                key="map_lat",
                label_visibility="visible",
            )
        with lon_col:
            user_longitude = st.number_input(
                "Longitude",
                value=77.2092,
                format="%.6f",
                key="map_lon",
                label_visibility="visible",
            )

        user_id = st.text_input("User ID (alerts)", value="default")

        analyze = st.button(
            "🔍 Analyze area",
            type="primary",
            use_container_width=True,
            key="analyze_area",
        )
        sync_gee = st.button(
            "🛰️ Sync satellite (GEE)",
            use_container_width=True,
            key="sync_gee",
        )

        if analyze:
            try:
                payload = {
                    "latitude": user_latitude,
                    "longitude": user_longitude,
                    "user_id": user_id.strip() or "default",
                }
                response = requests.post(
                    f"{api_base_url}/update-location",
                    json=payload,
                    timeout=120,
                )
                response.raise_for_status()
                st.session_state.last_risk = response.json()
                st.session_state.zones_cache = fetch_danger_zones()
                st.success("Analysis complete.")
            except Exception as exc:
                st.session_state.pop("last_risk", None)
                st.error(f"Request failed: {exc}")

        if sync_gee:
            try:
                r = requests.post(
                    f"{api_base_url}/gee/sync",
                    json={
                        "latitude": user_latitude,
                        "longitude": user_longitude,
                    },
                    timeout=120,
                )
                r.raise_for_status()
                body = r.json()
                if body.get("skipped"):
                    st.warning(f"GEE skipped: {body.get('reason', 'unknown')}")
                elif body.get("change_detected"):
                    st.success(
                        f"Change detected — {body.get('zones_upserted', 0)} zone(s) updated."
                    )
                else:
                    st.info("No zone change above threshold.")
                st.session_state.zones_cache = fetch_danger_zones()
                st.rerun()
            except Exception as e:
                st.error(f"GEE sync failed: {e}")

        st.caption(
            f"Zones in DB: **{len(st.session_state.zones_cache[0])}** · "
            f"`GEE_AUTO_SYNC_ON_LOCATION` runs on **Analyze** when enabled."
        )

        result = st.session_state.get("last_risk")
        if result:
            st.divider()
            st.markdown("**Last result**")
            msg = result.get("user_message") or ""
            risk = result.get("risk_level", "clear")
            if risk == "inside":
                st.error(msg)
            elif risk == "near":
                st.warning(msg)
            else:
                st.success(msg)
            if result.get("alert_triggered") or result.get("proximity_alert_triggered"):
                st.caption("Alert path fired — check SMS/logs if configured.")
            with st.expander("JSON"):
                st.json(result)

zones, zone_error = st.session_state.zones_cache

with col_right:
    st.subheader("Map")
    ulat = float(user_latitude)
    ulon = float(user_longitude)
    m = folium.Map(
        location=[ulat, ulon],
        zoom_start=12,
        tiles="OpenStreetMap",
        control_scale=True,
    )

    folium.Marker(
        location=[ulat, ulon],
        popup=folium.Popup(
            f"<b>Your location</b><br>{ulat:.6f}, {ulon:.6f}",
            max_width=240,
        ),
        tooltip="Your location",
        icon=folium.Icon(color="blue"),
    ).add_to(m)

    lats = [ulat]
    lons = [ulon]
    if zones:
        for zone in zones:
            sev = str(zone["severity"]).lower()
            color = "green" if sev == "low" else "orange" if sev == "medium" else "red"
            lat, lon = float(zone["latitude"]), float(zone["longitude"])
            r = float(zone["radius"])
            lats.append(lat)
            lons.append(lon)
            folium.Circle(
                location=[lat, lon],
                radius=r,
                color=color,
                weight=2,
                fill=True,
                fill_opacity=0.22,
                popup=folium.Popup(
                    f"<b>Danger zone</b><br>{sev.upper()} · {r:.0f} m",
                    max_width=220,
                ),
                tooltip=f"{sev.upper()} · {r:.0f} m",
            ).add_to(m)

    span_lat = max(lats) - min(lats)
    span_lon = max(lons) - min(lons)
    if span_lat > 1e-5 or span_lon > 1e-5:
        pad_lat = max(0.008, span_lat * 0.15)
        pad_lon = max(0.008, span_lon * 0.15)
        m.fit_bounds(
            [
                [min(lats) - pad_lat, min(lons) - pad_lon],
                [max(lats) + pad_lat, max(lons) + pad_lon],
            ]
        )

    _map_key = f"gaia_map_{ulat:.6f}_{ulon:.6f}"
    st_folium(
        m,
        height=420,
        use_container_width=True,
        key=_map_key,
    )

    st.subheader("Danger zone list")
    if zone_error:
        st.error(f"Could not load zones: {zone_error}")
    elif zones:
        df = pd.DataFrame(
            [
                {
                    "Lat": z["latitude"],
                    "Lon": z["longitude"],
                    "Radius (m)": z["radius"],
                    "Severity": str(z["severity"]).upper(),
                }
                for z in zones
            ]
        )
        st.dataframe(df, width="stretch", hide_index=True)
    else:
        st.info("No danger zones yet. Run **Analyze** or **Sync satellite (GEE)**.")

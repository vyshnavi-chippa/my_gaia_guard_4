from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "GaiaGuard"
    env: str = "development"
    database_url: str

    alerts_enabled: bool = True
    alert_cooldown_seconds: int = 300
    nearby_alert_buffer_meters: float = 800.0

    twilio_account_sid: str | None = None
    twilio_auth_token: str | None = None
    twilio_from_number: str | None = None
    alert_to_number: str | None = None
    twilio_enabled: bool = False

    # Google Earth Engine (optional). Set GEE_ENABLED=true after authenticating.
    gee_enabled: bool = False
    gee_project: str | None = None
    gee_credentials_json: str | None = None
    gee_auto_sync_on_location: bool = True
    gee_buffer_meters: float = 5000
    gee_loss_mean_threshold: float = 0.01
    gee_ndvi_drop_threshold: float = 0.2
    gee_zone_radius_meters: float = 1500
    gee_before_start: str = "2022-01-01"
    gee_before_end: str = "2022-06-01"
    gee_after_start: str = "2023-01-01"
    gee_after_end: str = "2023-06-01"
    gee_s2_collection: str = "COPERNICUS/S2_SR_HARMONIZED"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()

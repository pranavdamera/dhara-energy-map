from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql://dhara_user:dhara_pass@localhost:5433/dhara"
    gee_project_id: str = "your-google-earth-engine-project-id"
    analysis_district: str = "Anantapur"
    analysis_state: str = "Andhra Pradesh"
    target_storage_crs: str = "EPSG:4326"
    target_metric_crs: str = "EPSG:32644"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()

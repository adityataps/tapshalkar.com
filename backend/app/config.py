from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    gcs_bucket: str = "placeholder-bucket"
    allowed_origin_pattern: str = r"https://.*\.tapshalkar\.com"
    resend_api_key: str = ""
    anthropic_api_key: str = ""
    model_armor_template: str = ""  # full resource name, e.g. projects/p/locations/r/templates/t

    model_config = {"env_file": ".env"}


settings = Settings()

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    gcs_bucket: str = "placeholder-bucket"
    allowed_origin: str = "https://tapshalkar.com"
    resend_api_key: str = ""

    model_config = {"env_file": ".env"}


settings = Settings()

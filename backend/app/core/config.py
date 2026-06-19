from pydantic_settings import BaseSettings
from pydantic import Field, AnyUrl


class Settings(BaseSettings):
    environment: str = Field("development", env="ENVIRONMENT")
    database_url: str = Field(..., env="DATABASE_URL")
    openai_api_key: str = Field(..., env="OPENAI_API_KEY")
    deepgram_api_key: str = Field(..., env="DEEPGRAM_API_KEY")
    elevenlabs_api_key: str = Field(..., env="ELEVENLABS_API_KEY")
    crm_base_url: str = Field(..., env="CRM_BASE_URL")
    crm_api_key: str = Field(..., env="CRM_API_KEY")
    jwt_secret: str = Field(..., env="JWT_SECRET")
    jwt_algorithm: str = Field("HS256", env="JWT_ALGORITHM")
    jwt_expiration_minutes: int = Field(1440, env="JWT_EXPIRATION_MINUTES")
    allowed_hosts: list[str] = Field(["*"], env="ALLOWED_HOSTS")
    openai_model: str = Field("gpt-4o-mini", env="OPENAI_MODEL")
    default_voice_id: str = Field("eleven_monolingual_v1", env="DEFAULT_VOICE_ID")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()

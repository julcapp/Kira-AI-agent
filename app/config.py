from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_api_key: str = "dev-only-local"
    max_webhook_secret: str = ""
    max_bot_token: str = ""
    max_allowed_user_ids: str = ""
    max_enabled: bool = False
    tts_api_key: str = ""
    tts_base_url: str = "https://api.openai.com/v1"
    tts_model: str = "gpt-4o-mini-tts"
    tts_voice: str = "alloy"
    tts_enabled: bool = False
    database_url: str = "sqlite:///./data/kiryusha.db"
    llm_base_url: str = ""
    llm_api_key: str = ""
    llm_model: str = ""
    default_timezone: str = "Europe/Moscow"
    prompt_auto_upgrade_enabled: bool = True
    scheduler_enabled: bool = True
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def allowed_users(self) -> set[int]:
        return {int(x.strip()) for x in self.max_allowed_user_ids.split(",") if x.strip().isdigit()}

settings = Settings()

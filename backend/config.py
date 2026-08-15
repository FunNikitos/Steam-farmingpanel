from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    panel_password_hash: str = ""
    session_secret: str
    telegram_token: str = ""
    telegram_user_id: int = 0
    steam_api_key: str = ""
    asf_ipc_password: str = ""
    asf_ipc_url: str = "http://127.0.0.1:1242"
    scan_cron: str = "0 10 * * *"
    sync_cron: str = "0 * * * *"
    deals_cron: str = "0 11 * * *"
    db_path: str = "/opt/steam-panel/panel.db"

    model_config = {"env_file": ".env"}


settings = Settings()

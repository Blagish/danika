from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE = ".env"


class Config(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE, env_file_encoding="utf-8")

    # Production configuration
    run_mode: str = "dev"

    # Discord configuration
    discord_id: str = ""
    discord_token: str = ""
    command_prefix: str = "/"
    dev_guild_id: int | None = None


config = Config()


def get_config() -> Config:
    return config

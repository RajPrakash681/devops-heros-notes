from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL


class Settings(BaseSettings):
    """All configuration comes from environment variables.

    In Kubernetes the non-secret values come from a ConfigMap (APP_ENV, DB_HOST, ...)
    and the credentials from a Secret (DB_USER, DB_PASSWORD). DATABASE_URL, if set,
    wins over the individual DB_* values - Docker Compose and the tests use it.
    """

    app_name: str = "TaskBoard API"
    app_version: str = "1.1.0"
    app_env: str = "local"
    git_sha: str = "dev"  # baked into the image at build time (--build-arg GIT_SHA)

    database_url: str | None = None
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "taskboard"
    db_user: str = "taskboard"
    db_password: str = ""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def sqlalchemy_url(self) -> str:
        if self.database_url:
            return self.database_url
        # URL.create escapes special characters in the password; string formatting does not.
        return URL.create(
            "postgresql+psycopg",
            username=self.db_user,
            password=self.db_password,
            host=self.db_host,
            port=self.db_port,
            database=self.db_name,
        ).render_as_string(hide_password=False)


settings = Settings()

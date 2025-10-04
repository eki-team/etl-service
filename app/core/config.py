from pydantic_settings import BaseSettings, SettingsConfigDict
import os
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode

class Settings(BaseSettings):
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    DB_HOST: str = "localhost"
    DB_PORT: str = "5432"

    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int

    @staticmethod
    def _normalize_db_url(raw: str) -> str:
        if not raw:
            return raw
        p = urlparse(raw)

        scheme = p.scheme
        if scheme in ("postgres", "postgresql"):
            scheme = "postgresql+psycopg2"

        if "+psycopg2" not in scheme and scheme.startswith("postgresql"):
            scheme = "postgresql+psycopg2"

        query = p.query or ""
        if (p.hostname or "").endswith("render.com") and "sslmode=" not in query:
            q = parse_qs(query)
            q["sslmode"] = ["require"]
            query = urlencode(q, doseq=True)

        return urlunparse((scheme, p.netloc, p.path, p.params, query, p.fragment))

    @property
    def DATABASE_URL(self) -> str:
        raw = os.getenv("DATABASE_URL")
        if raw:
            return self._normalize_db_url(raw)

        built = (
            f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.POSTGRES_DB}"
        )
        return self._normalize_db_url(built)

    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    # MongoDB Configuration
    MONGO_USER: str = "admin"
    MONGO_PASSWORD: str = "admin"
    MONGO_HOST: str = "localhost"
    MONGO_PORT: str = "27017"
    MONGO_DB: str = "mydb"
    MONGO_URI: Optional[str] = None
    
    # Environment
    ENVIRONMENT: str = "development"

    @property
    def MONGO_URL(self) -> str:
        """MongoDB connection URL - uses MONGO_URI if set, otherwise builds from components"""
        # Si existe MONGO_URI en el .env, usarla directamente
        if self.MONGO_URI:
            # Remover comillas si existen
            uri = self.MONGO_URI.strip().strip('"').strip("'")
            return uri
        
        # Si no, construir desde componentes individuales
        return (
            f"mongodb://{self.MONGO_USER}:{self.MONGO_PASSWORD}"
            f"@{self.MONGO_HOST}:{self.MONGO_PORT}/{self.MONGO_DB}?authSource=admin"
        )

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore"  # Ignora variables extras del .env
    )

settings = Settings()

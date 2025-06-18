import os
from typing import List

from pydantic import Field, ValidationInfo, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Установка переменной окружения для GRPC
os.environ["GRPC_DNS_RESOLVER"] = "native"


class Settings(BaseSettings):
    # Обязательные параметры
    TG_BOT_TOKEN: str
    # NOTE: Убрать данное поле, так как есть ADMIN_IDS
    ADMIN_SECRET: str
    SECRET_KEY: str

    # Параметры с дефолтными значениями
    DB_USER: str = "sciuser"
    DB_PASS: str = "sci_password"
    DB_HOST: str = "localhost"
    DB_PORT: str = "5432"
    DB_NAME: str = "scientia_db"
    GRPC_DNS_RESOLVER: str = "native"

    API_URL: str = "http://localhost:8000"
    ALGORITHM: str = "HS256"
    DEEPSEEK_API_URL: str = "https://api.deepseek.com/v1"

    # Опциональные параметры
    DATABASE_URL: str = ""  # Будет собрано автоматически
    WEAVIATE_URL: str = ""
    WEAVIATE_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    DEEPSEEK_API_KEY: str = ""

    # Специальное поле с преобразованием типа
    ADMIN_IDS: List[int] = Field(default_factory=list)

    # Валидатор для преобразования разных форматов ADMIN_IDS
    @field_validator("ADMIN_IDS", mode="before")
    def parse_admin_ids(cls, v):
        if v is None:
            return []
        if isinstance(v, int):
            return [v]
        if isinstance(v, str):
            if not v.strip():
                return []
            return [int(x.strip()) for x in v.split(",")]
        return v

    # Автоматическая сборка DATABASE_URL при отсутствии
    @field_validator("DATABASE_URL", mode="before")
    def assemble_db_url(cls, v, info: ValidationInfo):
        if v:
            return v
        data = info.data
        try:
            return (
                f"postgresql+asyncpg://{data['DB_USER']}:{data['DB_PASS']}"
                f"@{data['DB_HOST']}:{data['DB_PORT']}/{data['DB_NAME']}"
            )
        except KeyError as e:
            raise ValueError(f"Missing database configuration: {e}") from e

    # Конфигурация загрузки настроек
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # Игнорировать лишние переменные окружения
    )


# Инициализация настроек
settings = Settings()

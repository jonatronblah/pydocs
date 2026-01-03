import os
import pathlib
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


class BaseConfig:
    BASE_DIR: pathlib.Path = pathlib.Path(__file__).parent.parent

    DATABASE_URL: str = os.environ.get(
        "DATABASE_URL", f"sqlite:///{BASE_DIR}/db.sqlite3"
    )
    ECHO_SQL: str | bool = os.environ.get("ECHO_SQL", False)

    # redis queue config
    REDIS_HOST: str = os.environ.get("REDIS_HOST", "redis")

    DATABASE_CONNECT_DICT: dict = {}

    # File upload configuration
    UPLOAD_DIR: pathlib.Path = BASE_DIR / "uploads"
    MAX_UPLOAD_SIZE: int = int(
        os.environ.get("MAX_UPLOAD_SIZE", 50 * 1024 * 1024)
    )  # 50MB default
    ALLOWED_EXTENSIONS: set = {".txt", ".pdf", ".md", ".html", ".htm"}
    ALLOWED_MIME_TYPES: set = {
        "text/plain",
        "application/pdf",
        "text/markdown",
        "text/html",
        "application/octet-stream",
    }

    # llm config
    OPENROUTER_API_KEY: str = os.environ.get("OPENROUTER_API_KEY", "")
    HF_TOKEN: str = os.environ.get("HF_TOKEN", "")
    MODEL: str = os.environ.get("MODEL", "")
    HF_MODEL: str = os.environ.get("HF_MODEL", "")


class DevelopmentConfig(BaseConfig):
    CORS_MIDDLEWARE: bool = True


class ProductionConfig(BaseConfig):
    pass


class TestingConfig(BaseConfig):
    CORS_MIDDLEWARE: bool = False


@lru_cache()
def get_settings():
    config_cls_dict = {
        "development": DevelopmentConfig,
        "production": ProductionConfig,
        "testing": TestingConfig,
    }

    config_name = os.environ.get("APP_CONFIG", "development")
    config_cls = config_cls_dict[config_name]
    return config_cls()


settings = get_settings()

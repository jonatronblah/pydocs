import pytest
import os
from pathlib import Path
from pydocs.config import (
    BaseConfig,
    DevelopmentConfig,
    ProductionConfig,
    TestingConfig,
    get_settings,
)


class TestBaseConfig:
    """Test cases for BaseConfig."""

    def test_base_config_defaults(self):
        """Test BaseConfig default values."""
        config = BaseConfig()

        # Test base directory
        assert isinstance(config.BASE_DIR, Path)
        assert config.BASE_DIR.name == "pydocs"

        # Test database URL defaults
        assert config.DATABASE_URL == f"sqlite:///{config.BASE_DIR}/db.sqlite3"

        # Test echo SQL defaults
        assert config.ECHO_SQL is False

        # Test Redis host defaults
        assert config.REDIS_HOST == "redis"

        # Test database connect dict
        assert config.DATABASE_CONNECT_DICT == {}

        # Test file upload configuration
        assert config.UPLOAD_DIR == config.BASE_DIR / "uploads"
        assert config.MAX_UPLOAD_SIZE == 50 * 1024 * 1024  # 50MB
        assert config.ALLOWED_EXTENSIONS == {".txt", ".pdf", ".md", ".html", ".htm"}
        assert config.ALLOWED_MIME_TYPES == {
            "text/plain",
            "application/pdf",
            "text/markdown",
            "text/html",
            "application/octet-stream",
        }


class TestEnvironmentConfigs:
    """Test cases for environment-specific configs."""

    def test_development_config(self):
        """Test DevelopmentConfig."""
        config = DevelopmentConfig()

        # Should inherit from BaseConfig
        assert isinstance(config, BaseConfig)

        # Development-specific settings
        assert config.CORS_MIDDLEWARE is True

    def test_production_config(self):
        """Test ProductionConfig."""
        config = ProductionConfig()

        # Should inherit from BaseConfig
        assert isinstance(config, BaseConfig)

        # Production-specific settings (currently empty, but should exist)
        # Add specific production settings here as needed

    def test_testing_config(self):
        """Test TestingConfig."""
        config = TestingConfig()

        # Should inherit from BaseConfig
        assert isinstance(config, BaseConfig)

        # Testing-specific settings
        assert config.CORS_MIDDLEWARE is False


class TestGetSettings:
    """Test cases for get_settings function."""

    def test_get_settings_default(self, monkeypatch):
        """Test get_settings with default configuration."""
        # Remove any APP_CONFIG environment variable
        monkeypatch.delenv("APP_CONFIG", raising=False)

        settings = get_settings()

        # Should default to DevelopmentConfig
        assert isinstance(settings, DevelopmentConfig)

    def test_get_settings_development(self, monkeypatch):
        """Test get_settings with development configuration."""
        monkeypatch.setenv("APP_CONFIG", "development")

        settings = get_settings()

        assert isinstance(settings, DevelopmentConfig)

    def test_get_settings_production(self, monkeypatch):
        """Test get_settings with production configuration."""
        monkeypatch.setenv("APP_CONFIG", "production")

        settings = get_settings()

        assert isinstance(settings, ProductionConfig)

    def test_get_settings_testing(self, monkeypatch):
        """Test get_settings with testing configuration."""
        monkeypatch.setenv("APP_CONFIG", "testing")

        settings = get_settings()

        assert isinstance(settings, TestingConfig)

    def test_get_settings_invalid(self, monkeypatch):
        """Test get_settings with invalid configuration."""
        monkeypatch.setenv("APP_CONFIG", "invalid")

        # Should raise KeyError for invalid config name
        with pytest.raises(KeyError):
            get_settings()

    def test_get_settings_caching(self, monkeypatch):
        """Test that get_settings uses caching."""
        monkeypatch.delenv("APP_CONFIG", raising=False)

        # Get settings twice
        settings1 = get_settings()
        settings2 = get_settings()

        # Should return the same instance due to @lru_cache
        assert settings1 is settings2


class TestEnvironmentVariableOverrides:
    """Test cases for environment variable overrides."""

    def test_database_url_override(self, monkeypatch):
        """Test overriding DATABASE_URL with environment variable."""
        test_db_url = "postgresql://test:test@localhost/testdb"
        monkeypatch.setenv("DATABASE_URL", test_db_url)

        config = BaseConfig()
        assert config.DATABASE_URL == test_db_url

    def test_echo_sql_override(self, monkeypatch):
        """Test overriding ECHO_SQL with environment variable."""
        monkeypatch.setenv("ECHO_SQL", "True")

        config = BaseConfig()
        assert config.ECHO_SQL is True

    def test_redis_host_override(self, monkeypatch):
        """Test overriding REDIS_HOST with environment variable."""
        test_redis_host = "test-redis"
        monkeypatch.setenv("REDIS_HOST", test_redis_host)

        config = BaseConfig()
        assert config.REDIS_HOST == test_redis_host

    def test_max_upload_size_override(self, monkeypatch):
        """Test overriding MAX_UPLOAD_SIZE with environment variable."""
        test_max_size = "104857600"  # 100MB in bytes
        monkeypatch.setenv("MAX_UPLOAD_SIZE", test_max_size)

        config = BaseConfig()
        assert config.MAX_UPLOAD_SIZE == int(test_max_size)

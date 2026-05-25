"""Unit tests for app.core.config — Settings computed properties."""
import pytest
from unittest.mock import patch

from app.core.config import Settings


class TestSqlalchemyDatabaseUri:
    def test_database_url_takes_priority(self):
        # Test 1a - When DATABASE_URL is set, it's used (with asyncpg prefix)
        s = Settings(DATABASE_URL="postgresql://user:pass@host:5432/db")
        assert s.SQLALCHEMY_DATABASE_URI == "postgresql+asyncpg://user:pass@host:5432/db"

    def test_falls_back_to_components(self):
        # Test 1b - When DATABASE_URL is None, components are assembled
        s = Settings(
            DATABASE_URL=None,
            POSTGRES_USER="myuser",
            POSTGRES_PASSWORD="mypass",
            POSTGRES_SERVER="localhost",
            POSTGRES_PORT="5433",
            POSTGRES_DB="testdb",
        )
        expected = "postgresql+asyncpg://myuser:mypass@localhost:5433/testdb"
        assert s.SQLALCHEMY_DATABASE_URI == expected

    def test_replaces_only_first_occurrence(self):
        # Test 1c - Only the first postgresql:// is replaced
        s = Settings(DATABASE_URL="postgresql://x:y@z/postgresql://literal")
        uri = s.SQLALCHEMY_DATABASE_URI
        assert uri.startswith("postgresql+asyncpg://")
        assert "postgresql://literal" in uri


class TestSettingsDefaults:
    def test_default_values(self):
        # Test 1a - Key defaults are correct
        s = Settings()
        assert s.PROJECT_NAME == "Roammate"
        assert s.LLM_ENABLED is False
        assert s.LLM_PROVIDER == "openai"
        assert s.LLM_MODEL == "gpt-4o-mini"
        assert s.FREE_ACTIVE_TRIPS_CAP == 2
        assert s.FREE_BRAINSTORM_MONTHLY_CAP == 15
        assert s.GOOGLE_MAPS_MOCK is True
        assert s.ACCESS_TOKEN_TTL_MIN == 15
        assert s.REFRESH_TOKEN_TTL_DAYS == 30
        assert s.DB_POOL_SIZE == 20

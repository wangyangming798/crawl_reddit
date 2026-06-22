import os
import pytest
from config import load_config, ConfigError


def test_load_config_requires_api_key(monkeypatch):
    """ConfigError raised when DASHSCOPE_API_KEY is missing."""
    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)
    with pytest.raises(ConfigError, match="DASHSCOPE_API_KEY"):
        load_config()


def test_load_config_defaults(monkeypatch):
    """Defaults are applied when optional env vars are missing."""
    monkeypatch.setenv("DASHSCOPE_API_KEY", "test-key")
    monkeypatch.setenv("REDDIT_CLIENT_ID", "test-cid")
    monkeypatch.setenv("REDDIT_CLIENT_SECRET", "test-secret")
    # Clear optional vars
    for var in ["LLM_MODEL", "DB_HOST", "DEFAULT_COUNTRY", "SCHEDULE_ENABLED"]:
        monkeypatch.delenv(var, raising=False)

    config = load_config()

    assert config.llm.model == "qwen3.7-plus"
    assert config.db.host == "localhost"
    assert config.crawl.default_country == "us"
    assert config.scheduler.enabled is False


def test_load_config_parses_lists(monkeypatch):
    """Comma-separated env vars become lists."""
    monkeypatch.setenv("DASHSCOPE_API_KEY", "test-key")
    monkeypatch.setenv("REDDIT_CLIENT_ID", "test-cid")
    monkeypatch.setenv("REDDIT_CLIENT_SECRET", "test-secret")
    monkeypatch.setenv("DEFAULT_SUBREDDITS", "r/one, r/two, r/three")

    config = load_config()

    assert config.crawl.default_subreddits == ["r/one", "r/two", "r/three"]


def test_load_config_db_url(monkeypatch):
    """DB URL is constructed correctly."""
    monkeypatch.setenv("DASHSCOPE_API_KEY", "test-key")
    monkeypatch.setenv("REDDIT_CLIENT_ID", "test-cid")
    monkeypatch.setenv("REDDIT_CLIENT_SECRET", "test-secret")
    monkeypatch.setenv("DB_USER", "admin")
    monkeypatch.setenv("DB_PASSWORD", "pass123")
    monkeypatch.setenv("DB_HOST", "db.example.com")
    monkeypatch.setenv("DB_PORT", "5433")
    monkeypatch.setenv("DB_NAME", "mydb")

    config = load_config()

    assert "admin:pass123@db.example.com:5433/mydb" in config.db.url
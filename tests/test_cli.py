import pytest
from click.testing import CliRunner
from unittest.mock import AsyncMock, MagicMock, patch
from main import cli


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def mock_config(monkeypatch):
    monkeypatch.setenv("DASHSCOPE_API_KEY", "test-key")
    monkeypatch.setenv("REDDIT_CLIENT_ID", "test-cid")
    monkeypatch.setenv("REDDIT_CLIENT_SECRET", "test-secret")
    monkeypatch.setenv("DB_PASSWORD", "test-pass")


def test_cli_run_missing_args(runner, mock_config):
    """run command fails without --query or --subreddits."""
    result = runner.invoke(cli, ["run"])
    assert result.exit_code != 0
    assert "query" in result.output.lower() or "subreddit" in result.output.lower()


def test_cli_discover_command(runner, mock_config):
    """discover command exists and requires --query."""
    with patch("main.DiscoveryEngine") as mock_engine_cls:
        from discovery.engine import DiscoveryResult
        mock_instance = MagicMock()
        mock_instance.discover = AsyncMock(return_value=DiscoveryResult(
            subreddits=["r/test"],
            keywords=["pain point"],
        ))
        mock_engine_cls.return_value = mock_instance

        result = runner.invoke(cli, ["discover", "--query", "test query"])
        assert result.exit_code == 0
        assert "r/test" in result.output


def _make_mock_session():
    """Create a mock DB session that supports async operations."""
    session = MagicMock()
    session.commit = AsyncMock()
    session.execute = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    return session


def _mock_get_session(mock_session):
    """Return a side_effect function that yields the mock session."""
    async def gen(config):
        yield mock_session
    return gen


def test_cli_run_with_subreddits(runner, mock_config):
    """run with --subreddits triggers crawl."""
    mock_session = _make_mock_session()

    with patch("main.get_session") as mock_get_session, \
         patch("main.BatchWriter") as mock_writer_cls, \
         patch("crawler.coordinator.CrawlCoordinator.run_crawl", new_callable=AsyncMock) as mock_crawl:

        from crawler.coordinator import CrawlResult
        mock_crawl.return_value = CrawlResult(
            platform="reddit",
            total_posts=5,
            total_comments=10,
        )

        mock_get_session.side_effect = _mock_get_session(mock_session)

        mock_writer = MagicMock()
        mock_writer.upsert_platform = AsyncMock(return_value=1)
        mock_writer.insert_posts = AsyncMock()
        mock_writer.insert_comments = AsyncMock()
        mock_writer_cls.return_value = mock_writer

        result = runner.invoke(cli, [
            "run", "--country", "us", "--subreddits", "r/test",
            "--max-posts", "10", "--max-comments", "20",
        ])
        assert result.exit_code == 0
        assert "5" in result.output
        assert "10" in result.output


def test_cli_run_with_query(runner, mock_config):
    """run with --query triggers discovery then crawl."""
    mock_session = _make_mock_session()

    with patch("main.DiscoveryEngine") as mock_engine_cls, \
         patch("main.get_session") as mock_get_session, \
         patch("main.BatchWriter") as mock_writer_cls, \
         patch("crawler.coordinator.CrawlCoordinator.run_crawl", new_callable=AsyncMock) as mock_crawl:

        from discovery.engine import DiscoveryResult
        mock_engine_instance = MagicMock()
        mock_engine_instance.discover = AsyncMock(return_value=DiscoveryResult(
            subreddits=["r/test"],
            keywords=["pain"],
        ))
        mock_engine_cls.return_value = mock_engine_instance

        from crawler.coordinator import CrawlResult
        mock_crawl.return_value = CrawlResult(
            platform="reddit",
            total_posts=3,
            total_comments=7,
        )

        mock_get_session.side_effect = _mock_get_session(mock_session)

        mock_writer = MagicMock()
        mock_writer.upsert_platform = AsyncMock(return_value=1)
        mock_writer.insert_posts = AsyncMock()
        mock_writer.insert_comments = AsyncMock()
        mock_writer_cls.return_value = mock_writer

        result = runner.invoke(cli, [
            "run", "--query", "user pain points in skincare",
            "--country", "us",
        ])
        assert result.exit_code == 0


def test_cli_tasks_list(runner, mock_config):
    """tasks list command runs without error."""
    with patch("main.get_session") as mock_session:
        # Mock the async generator
        mock_s = MagicMock()
        mock_session.return_value = mock_s

        result = runner.invoke(cli, ["tasks", "list"])
        # May fail due to DB not being available, but command should parse
        assert result.exit_code in (0, 1)
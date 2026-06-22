import pytest
from unittest.mock import MagicMock, patch
from discovery.engine import DiscoveryEngine, DiscoveryResult


@pytest.fixture
def llm_config():
    from config import LLMConfig
    return LLMConfig(api_key="test-key", model="qwen3.7-plus")


def _make_engine(llm_config, mock_client=None):
    return DiscoveryEngine(llm_config, client=mock_client)


def _make_mock_response(output_text: str):
    mock_response = MagicMock()
    mock_response.output_text = output_text
    return mock_response


def _make_mock_client(mock_response):
    mock_client = MagicMock()
    mock_client.responses = MagicMock()
    mock_client.responses.create = MagicMock(return_value=mock_response)
    return mock_client


def test_discovery_result_fields():
    result = DiscoveryResult(
        subreddits=["r/SkincareAddiction", "r/30PlusSkinCare"],
        keywords=["broke me out", "irritated", "worst moisturizer"],
    )
    assert len(result.subreddits) == 2
    assert len(result.keywords) == 3


def test_discovery_result_empty():
    result = DiscoveryResult(subreddits=[], keywords=[])
    assert result.subreddits == []
    assert result.keywords == []


@pytest.mark.asyncio
async def test_discover_returns_structured_output(llm_config):
    """discover() calls the LLM and parses JSON response."""
    mock_response = _make_mock_response('''{
        "subreddits": ["r/SkincareAddiction", "r/AsianBeauty"],
        "keywords": ["broke me out", "irritation", "worst product", "not worth it"]
    }''')
    mock_client = _make_mock_client(mock_response)
    engine = _make_engine(llm_config, mock_client)

    result = await engine.discover(
        query="美国市场护肤品类用户吐槽痛点",
        country="us",
    )

    assert isinstance(result, DiscoveryResult)
    assert "r/SkincareAddiction" in result.subreddits
    assert "broke me out" in result.keywords
    assert len(result.subreddits) > 0
    assert len(result.keywords) > 0


@pytest.mark.asyncio
async def test_discover_handles_malformed_json(llm_config):
    """If LLM returns bad JSON, return empty result and log error."""
    mock_response = _make_mock_response("not valid json at all")
    mock_client = _make_mock_client(mock_response)
    engine = _make_engine(llm_config, mock_client)

    result = await engine.discover(query="test query", country="us")

    assert result.subreddits == []
    assert result.keywords == []


@pytest.mark.asyncio
async def test_discover_handles_missing_keys(llm_config):
    """If JSON is valid but missing expected keys, defaults to empty lists."""
    mock_response = _make_mock_response('{"subreddits": ["r/test"]}')
    mock_client = _make_mock_client(mock_response)
    engine = _make_engine(llm_config, mock_client)

    result = await engine.discover(query="test", country="us")

    assert result.subreddits == ["r/test"]
    assert result.keywords == []


@pytest.mark.asyncio
async def test_discover_prompt_includes_country(llm_config):
    """The prompt sent to the LLM includes the target country."""
    mock_response = _make_mock_response('{"subreddits": [], "keywords": []}')
    mock_client = _make_mock_client(mock_response)
    engine = _make_engine(llm_config, mock_client)

    await engine.discover(query="test", country="uk")

    # Verify the prompt included the country
    call_args = mock_client.responses.create.call_args
    input_text = call_args.kwargs.get("input", "")
    assert "uk" in input_text.lower() or "UK" in input_text
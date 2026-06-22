import json
import logging
import os
from dataclasses import dataclass, field

from openai import OpenAI

from config import LLMConfig

logger = logging.getLogger(__name__)

DISCOVERY_PROMPT = """You are a market research assistant. Given a natural language query about user pain points, find relevant Reddit subreddits and search keywords.

Target country: {country}

Return ONLY valid JSON in this exact format:
{{
    "subreddits": ["r/SubredditName1", "r/SubredditName2", ...],
    "keywords": ["keyword phrase 1", "keyword phrase 2", ...]
}}

Rules:
- Suggest 5-10 subreddits that are most relevant to the query AND the target country
- If the query is about a specific country, include region-specific subreddits (e.g. r/AskUK, r/UKFrugal for UK)
- Suggest 5-15 keyword phrases that would surface complaints/pain points/negative experiences
- Keywords should include complaint-language patterns (e.g. "broke me out", "worst", "waste of money", "regret buying", "doesn't work")
- Return the JSON object only, no markdown, no explanation
"""


@dataclass
class DiscoveryResult:
    """AI-discovered subreddits and keywords for a research query."""
    subreddits: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)


class DiscoveryEngine:
    """Uses DashScope Qwen to discover relevant subreddits and keywords
    from a natural language research query."""

    def __init__(self, config: LLMConfig, client=None):
        self.config = config
        self._client = client or OpenAI(
            api_key=config.api_key,
            base_url=config.base_url,
        )

    async def discover(self, query: str, country: str = "us") -> DiscoveryResult:
        """Given a natural language query, return discovered subreddits and keywords."""
        prompt = DISCOVERY_PROMPT.format(country=country)

        try:
            response = self._client.responses.create(
                model=self.config.model,
                input=f"{prompt}\n\nUser query: {query}",
                extra_body={
                    "enable_thinking": self.config.enable_thinking,
                },
            )

            output_text = response.output_text.strip()

            # Handle markdown code blocks
            if output_text.startswith("```"):
                lines = output_text.split("\n")
                output_text = "\n".join(lines[1:-1])

            data = json.loads(output_text)
            return DiscoveryResult(
                subreddits=data.get("subreddits", []),
                keywords=data.get("keywords", []),
            )

        except (json.JSONDecodeError, KeyError) as e:
            logger.error("Failed to parse LLM response: %s", e)
            logger.debug("Raw response: %s", getattr(response, 'output_text', 'N/A'))
            return DiscoveryResult(subreddits=[], keywords=[])
        except Exception as e:
            logger.error("LLM call failed: %s", e)
            return DiscoveryResult(subreddits=[], keywords=[])
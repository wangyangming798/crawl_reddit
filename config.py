import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()


class ConfigError(Exception):
    """Raised when required config is missing."""


@dataclass
class LLMConfig:
    api_key: str
    base_url: str = "https://dashscope.aliyuncs.com/api/v2/apps/protocols/compatible-mode/v1"
    model: str = "qwen3.7-plus"
    enable_thinking: bool = True


@dataclass
class RedditConfig:
    client_id: str
    client_secret: str
    user_agent: str


@dataclass
class DBConfig:
    host: str = "localhost"
    port: int = 5432
    name: str = "reddit_research"
    user: str = "postgres"
    password: str = ""

    @property
    def url(self) -> str:
        return f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"


@dataclass
class CrawlConfig:
    default_country: str = "us"
    default_subreddits: list[str] = field(default_factory=list)
    default_keywords: list[str] = field(default_factory=list)
    default_lookback_days: int = 30
    max_posts_per_subreddit: int = 100
    max_comments_per_post: int = 200


@dataclass
class SchedulerConfig:
    enabled: bool = False
    cron: str = "0 8 * * 1"


@dataclass
class Config:
    llm: LLMConfig
    reddit: RedditConfig
    db: DBConfig
    crawl: CrawlConfig
    scheduler: SchedulerConfig


def load_config() -> Config:
    """Load and validate all configuration from .env."""

    # LLM
    llm_api_key = os.getenv("DASHSCOPE_API_KEY", "")
    if not llm_api_key:
        raise ConfigError("DASHSCOPE_API_KEY is required")
    llm = LLMConfig(
        api_key=llm_api_key,
        model=os.getenv("LLM_MODEL", "qwen3.7-plus"),
        enable_thinking=os.getenv("LLM_ENABLE_THINKING", "true").lower() == "true",
    )

    # Reddit
    reddit = RedditConfig(
        client_id=os.getenv("REDDIT_CLIENT_ID", ""),
        client_secret=os.getenv("REDDIT_CLIENT_SECRET", ""),
        user_agent=os.getenv("REDDIT_USER_AGENT", "crawl_reddit/1.0"),
    )

    # DB
    db = DBConfig(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        name=os.getenv("DB_NAME", "reddit_research"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", ""),
    )

    # Crawl defaults
    default_subreddits = os.getenv("DEFAULT_SUBREDDITS", "")
    default_keywords = os.getenv("DEFAULT_KEYWORDS", "")
    crawl = CrawlConfig(
        default_country=os.getenv("DEFAULT_COUNTRY", "us"),
        default_subreddits=[s.strip() for s in default_subreddits.split(",") if s.strip()],
        default_keywords=[k.strip() for k in default_keywords.split(",") if k.strip()],
        default_lookback_days=int(os.getenv("DEFAULT_LOOKBACK_DAYS", "30")),
        max_posts_per_subreddit=int(os.getenv("MAX_POSTS_PER_SUBREDDIT", "100")),
        max_comments_per_post=int(os.getenv("MAX_COMMENTS_PER_POST", "200")),
    )

    # Scheduler
    scheduler = SchedulerConfig(
        enabled=os.getenv("SCHEDULE_ENABLED", "false").lower() == "true",
        cron=os.getenv("SCHEDULE_CRON", "0 8 * * 1"),
    )

    return Config(llm=llm, reddit=reddit, db=db, crawl=crawl, scheduler=scheduler)
import asyncio
import logging
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import click

from config import load_config, Config
from crawler.base import SearchQuery
from crawler.coordinator import CrawlCoordinator
from crawler.reddit.api import RedditAdapter
from discovery.engine import DiscoveryEngine
from pipeline.normalize import normalize_post, normalize_comment
from writer.db import Post, Comment, ResearchTask, get_session
from writer.batch import BatchWriter


# Ensure data directory exists
Path("data").mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler("data/crawl.log"),
        logging.StreamHandler(),
    ],
)

logger = logging.getLogger(__name__)


def _build_coordinator(config: Config) -> CrawlCoordinator:
    """Build the crawl coordinator with available adapters."""
    adapters = {
        "reddit": RedditAdapter(config.reddit),
    }
    return CrawlCoordinator(adapters=adapters)


async def _run_crawl(
    config: Config,
    query: str | None,
    country: str,
    subreddits: list[str],
    keywords: list[str],
    max_posts: int,
    max_comments: int,
) -> None:
    """Execute a full crawl-and-write pipeline."""
    start_time = time.time()

    # Step 1: Discovery (if needed)
    if query:
        logger.info("Running AI discovery for: %s", query)
        engine = DiscoveryEngine(config.llm)
        discovery_result = await engine.discover(query=query, country=country)
        subreddits = discovery_result.subreddits or subreddits
        keywords = discovery_result.keywords or keywords
        logger.info("Discovered subreddits: %s", subreddits)
        logger.info("Discovered keywords: %s", keywords)

    if not subreddits and not keywords:
        logger.error("No subreddits or keywords to search. Provide --query, --subreddits, or --keywords.")
        return

    # Step 2: Create research task
    task_id = str(uuid.uuid4())
    async for session in get_session(config):
        task = ResearchTask(
            task_id=task_id,
            natural_query=query,
            countries=[country],
            subreddits=subreddits,
            keywords=keywords,
            status="running",
        )
        session.add(task)
        await session.commit()
        break

    # Step 3: Crawl
    coordinator = _build_coordinator(config)
    crawl_result = await coordinator.run_crawl(
        SearchQuery(
            subreddits=subreddits,
            keywords=keywords,
            country=country,
            limit=max_posts,
        ),
        platform="reddit",
    )

    logger.info("Crawl complete: %d posts, %d comments",
                crawl_result.total_posts, crawl_result.total_comments)

    # Step 4: Normalize and write
    async for session in get_session(config):
        writer = BatchWriter(session)
        platform_id = await writer.upsert_platform("reddit")

        # Write posts
        post_models = []
        for raw_post in crawl_result.posts:
            common = normalize_post(raw_post, platform="reddit", country=country)
            post_models.append(Post(
                platform_id=platform_id,
                post_id=common.post_id,
                title=common.title,
                body=common.body,
                author_id=common.author_id,
                sub_community=common.sub_community,
                country_code=common.country,
                url=raw_post.url,
                upvotes=common.metrics.upvotes,
                comment_count=common.metrics.comment_count,
                created_at_utc=common.created_at,
                task_id=task_id,
                raw_json=common.raw_json,
            ))
        await writer.insert_posts(post_models)
        logger.info("Wrote %d posts to DB", len(post_models))

        # Write comments
        comment_models = []
        for raw_comment in crawl_result.comments:
            common = normalize_comment(raw_comment, platform="reddit")
            comment_models.append(Comment(
                platform_id=platform_id,
                comment_id=common.comment_id,
                post_id=common.post_id,
                parent_id=common.parent_id,
                body=common.body,
                author_id=common.author_id,
                upvotes=common.metrics.upvotes,
                created_at_utc=common.created_at,
                task_id=task_id,
                raw_json=common.raw_json,
            ))
        await writer.insert_comments(comment_models)
        logger.info("Wrote %d comments to DB", len(comment_models))

        # Update task status
        import sqlalchemy as sa
        await session.execute(
            sa.update(ResearchTask)
            .where(ResearchTask.task_id == task_id)
            .values(status="done", finished_at=datetime.now(timezone.utc))
        )
        await session.commit()
        break

    elapsed = time.time() - start_time
    click.echo(f"\n✅ Crawl complete!")
    click.echo(f"   Task ID: {task_id}")
    click.echo(f"   Posts: {crawl_result.total_posts}")
    click.echo(f"   Comments: {crawl_result.total_comments}")
    click.echo(f"   Time: {elapsed:.1f}s")


@click.group()
def cli():
    """Reddit crawler for user pain-point research."""
    pass


@cli.command()
@click.option("--query", "-q", default=None, help="Natural language research query")
@click.option("--country", "-c", default=None, help="Target country code (e.g. us, uk)")
@click.option("--subreddits", "-s", default=None, help="Comma-separated subreddit list")
@click.option("--keywords", "-k", default=None, help="Comma-separated keyword list")
@click.option("--max-posts", default=None, type=int, help="Max posts per subreddit")
@click.option("--max-comments", default=None, type=int, help="Max comments per post")
def run(query, country, subreddits, keywords, max_posts, max_comments):
    """Run a crawl — discover subreddits via AI, or crawl manually specified ones."""
    config = load_config()

    country = country or config.crawl.default_country
    subreddit_list = [s.strip() for s in subreddits.split(",") if s.strip()] if subreddits else config.crawl.default_subreddits
    keyword_list = [k.strip() for k in keywords.split(",") if k.strip()] if keywords else config.crawl.default_keywords
    max_posts = max_posts if max_posts is not None else config.crawl.max_posts_per_subreddit
    max_comments = max_comments if max_comments is not None else config.crawl.max_comments_per_post

    if not query and not subreddit_list and not keyword_list:
        raise click.UsageError("Must provide --query, --subreddits, or --keywords")

    asyncio.run(_run_crawl(
        config=config,
        query=query,
        country=country,
        subreddits=subreddit_list,
        keywords=keyword_list,
        max_posts=max_posts,
        max_comments=max_comments,
    ))


@cli.command()
@click.option("--query", "-q", required=True, help="Natural language research query")
@click.option("--country", "-c", default="us", help="Target country code")
def discover(query, country):
    """Run AI discovery only — see what subreddits and keywords would be searched."""
    config = load_config()
    engine = DiscoveryEngine(config.llm)

    async def _run():
        result = await engine.discover(query=query, country=country)
        click.echo(f"\n🔍 Discovery results for: {query}")
        click.echo(f"   Country: {country}")
        click.echo(f"\n   Subreddits ({len(result.subreddits)}):")
        for s in result.subreddits:
            click.echo(f"     - {s}")
        click.echo(f"\n   Keywords ({len(result.keywords)}):")
        for k in result.keywords:
            click.echo(f"     - {k}")

    asyncio.run(_run())


@cli.group()
def tasks():
    """Manage research tasks."""
    pass


@tasks.command("list")
def tasks_list():
    """List recent research tasks."""
    config = load_config()

    async def _run():
        import sqlalchemy as sa
        async for session in get_session(config):
            result = await session.execute(
                sa.select(ResearchTask).order_by(ResearchTask.created_at.desc()).limit(20)
            )
            rows = result.scalars().all()
            if not rows:
                click.echo("No tasks found.")
                return
            click.echo(f"\n{'Task ID':<38} {'Status':<12} {'Query':<40} {'Created'}")
            click.echo("-" * 100)
            for t in rows:
                query_str = (t.natural_query or "")[:38]
                created = t.created_at.strftime("%Y-%m-%d %H:%M") if t.created_at else ""
                click.echo(f"{t.task_id:<38} {t.status:<12} {query_str:<40} {created}")
            break

    asyncio.run(_run())


@tasks.command("status")
@click.option("--task-id", required=True, help="Task UUID")
def tasks_status(task_id):
    """Show details for a specific task."""
    config = load_config()

    async def _run():
        import sqlalchemy as sa
        async for session in get_session(config):
            result = await session.execute(
                sa.select(ResearchTask).where(ResearchTask.task_id == task_id)
            )
            task = result.scalar_one_or_none()
            if not task:
                click.echo(f"Task {task_id} not found.")
                return

            click.echo(f"\nTask: {task.task_id}")
            click.echo(f"Status: {task.status}")
            click.echo(f"Query: {task.natural_query}")
            click.echo(f"Countries: {task.countries}")
            click.echo(f"Subreddits: {task.subreddits}")
            click.echo(f"Keywords: {task.keywords}")
            click.echo(f"Created: {task.created_at}")
            click.echo(f"Finished: {task.finished_at}")

            # Count associated data
            post_count = await session.execute(
                sa.select(sa.func.count()).select_from(Post).where(Post.task_id == task_id)
            )
            comment_count = await session.execute(
                sa.select(sa.func.count()).select_from(Comment).where(Comment.task_id == task_id)
            )
            click.echo(f"Posts collected: {post_count.scalar()}")
            click.echo(f"Comments collected: {comment_count.scalar()}")
            break

    asyncio.run(_run())


@cli.group()
def scheduler():
    """Manage scheduled crawl jobs."""
    pass


@scheduler.command("start")
def scheduler_start():
    """Start the scheduler (runs in foreground)."""
    config = load_config()
    if not config.scheduler.enabled:
        click.echo("Scheduler is disabled in .env (SCHEDULE_ENABLED=false)")
        return

    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.cron import CronTrigger

    async def scheduled_job():
        click.echo(f"[{datetime.now()}] Running scheduled crawl...")
        await _run_crawl(
            config=config,
            query=None,
            country=config.crawl.default_country,
            subreddits=config.crawl.default_subreddits,
            keywords=config.crawl.default_keywords,
            max_posts=config.crawl.max_posts_per_subreddit,
            max_comments=config.crawl.max_comments_per_post,
        )

    sched = AsyncIOScheduler()
    trigger = CronTrigger.from_crontab(config.scheduler.cron)
    sched.add_job(scheduled_job, trigger=trigger)
    sched.start()

    click.echo(f"Scheduler started. Cron: {config.scheduler.cron}")
    click.echo("Press Ctrl+C to stop.")

    try:
        asyncio.get_event_loop().run_forever()
    except KeyboardInterrupt:
        sched.shutdown()
        click.echo("Scheduler stopped.")


@scheduler.command("stop")
def scheduler_stop():
    """Placeholder — scheduler stops via Ctrl+C."""
    click.echo("Scheduler runs in foreground. Use Ctrl+C to stop.")


if __name__ == "__main__":
    cli()
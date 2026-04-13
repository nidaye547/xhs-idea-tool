import os
import sys
import logging
from datetime import datetime
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from .config import (
    KEYWORDS_FILE, CRAWL_HOUR, CRAWL_MINUTE, CRAWL_INTERVAL_HOURS
)
from .storage import Storage
from .crawler import XiaohongshuCrawler
from .ai_analyzer import AIAnalyzer

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_keywords() -> list:
    """Load keywords from file, one per line."""
    keywords_file = Path(KEYWORDS_FILE)
    if not keywords_file.exists():
        logger.warning(f"Keywords file not found: {KEYWORDS_FILE}")
        return []

    with open(keywords_file, 'r', encoding='utf-8') as f:
        keywords = [line.strip() for line in f if line.strip()]
    return keywords


def crawl_all_keywords():
    """Main crawl job."""
    logger.info("Starting scheduled crawl job")
    keywords = load_keywords()

    if not keywords:
        logger.warning("No keywords to crawl")
        return

    storage = Storage()
    crawler = XiaohongshuCrawler(storage)

    import asyncio

    async def run():
        await crawler.start()
        try:
            for keyword in keywords:
                logger.info(f"Crawling keyword: {keyword}")
                try:
                    notes = await crawler.crawl_keyword(keyword)
                    logger.info(f"Crawled {len(notes)} notes for '{keyword}'")
                except Exception as e:
                    logger.error(f"Error crawling '{keyword}': {e}")
        finally:
            await crawler.close()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(run())
    finally:
        loop.close()

    logger.info("Crawl job completed")


def analyze_all_comments():
    """AI analysis job."""
    logger.info("Starting AI analysis job")
    storage = Storage()
    analyzer = AIAnalyzer(storage)

    keywords = load_keywords()
    for keyword in keywords:
        logger.info(f"Analyzing comments for keyword: {keyword}")
        try:
            summary = analyzer.analyze_all_notes(keyword=keyword)
            logger.info(f"Analysis summary: {summary}")
        except Exception as e:
            logger.error(f"Error analyzing '{keyword}': {e}")

    # Export high feasibility results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    analyzer.export_high_feasibility(
        min_score=3,
        output_file=f"feasibility_results_{timestamp}.json"
    )
    logger.info("Analysis job completed")


def run_scheduler():
    """Run the scheduler with cron jobs."""
    scheduler = BackgroundScheduler()

    # Daily full crawl at configured hour
    scheduler.add_job(
        crawl_all_keywords,
        CronTrigger(hour=CRAWL_HOUR, minute=CRAWL_MINUTE),
        id='daily_crawl',
        name='Daily keyword crawl'
    )

    # AI analysis now happens during crawling (in real-time)
    # Periodic AI analysis is disabled - comments are cleaned and exported to CSV during crawl
    # scheduler.add_job(
    #     analyze_all_comments,
    #     'interval',
    #     hours=CRAWL_INTERVAL_HOURS,
    #     id='periodic_analysis',
    #     name='Periodic AI analysis'
    # )

    scheduler.start()
    logger.info(f"Scheduler started. Daily crawl at {CRAWL_HOUR:02d}:{CRAWL_MINUTE:02d}")

    return scheduler


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description='Xiaohongshu Crawler')
    parser.add_argument('--mode', choices=['crawl', 'analyze', 'both', 'daemon'],
                       default='daemon', help='Run mode')
    parser.add_argument('--keyword', type=str, help='Crawl specific keyword')
    args = parser.parse_args()

    if args.mode == 'crawl':
        if args.keyword:
            storage = Storage()
            crawler = XiaohongshuCrawler(storage)
            import asyncio
            async def run():
                await crawler.start()
                try:
                    await crawler.crawl_keyword(args.keyword)
                finally:
                    await crawler.close()
            asyncio.new_event_loop().run_until_complete(run())
        else:
            crawl_all_keywords()

    elif args.mode == 'analyze':
        if args.keyword:
            storage = Storage()
            analyzer = AIAnalyzer(storage)
            analyzer.analyze_all_notes(keyword=args.keyword)
        else:
            analyze_all_comments()

    elif args.mode == 'both':
        crawl_all_keywords()
        analyze_all_comments()

    else:  # daemon mode
        scheduler = run_scheduler()
        logger.info("Running in daemon mode. Press Ctrl+C to exit.")

        try:
            import time
            while True:
                time.sleep(60)
        except KeyboardInterrupt:
            logger.info("Shutting down...")
            scheduler.shutdown()


if __name__ == '__main__':
    main()

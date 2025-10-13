import asyncio
import logging
import threading
from pathlib import Path
import uvicorn

from app.core.config import get_settings
from app.services.twitch_bot import TwitchAutoClipBot
from app.services.database_manager import DatabaseManager
from app.services.clip_manager import ClipManager
from app.services.analytics_service import AnalyticsService
from app.services.monitoring import MonitoringService
from app.api.dashboard import app as dashboard_app

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/bot.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


def create_directories():
    Path("logs").mkdir(exist_ok=True)
    Path("static/css").mkdir(parents=True, exist_ok=True)
    Path("static/js").mkdir(parents=True, exist_ok=True)
    Path("templates").mkdir(exist_ok=True)


def run_dashboard():
    uvicorn.run(dashboard_app, host="0.0.0.0", port=8000, log_level="info")


def run_bot(bot):
    bot.run()


async def main():
    create_directories()
    settings = get_settings()

    db_manager = DatabaseManager()
    db_manager.init_db()

    clip_manager = ClipManager(
        settings.twitch_client_id,
        settings.twitch_access_token,
        settings.channel_name,
        settings.clip_cooldown_seconds
    )
    await clip_manager.init()

    analytics = AnalyticsService(db_manager, clip_manager, settings.analytics_update_interval)
    analytics_task = asyncio.create_task(analytics.start())

    monitoring = MonitoringService(settings.discord_webhook_url)
    await monitoring.send_startup_alert()

    dashboard_thread = threading.Thread(target=run_dashboard, daemon=True)
    dashboard_thread.start()

    bot = TwitchAutoClipBot()
    bot_thread = threading.Thread(target=run_bot, args=(bot,), daemon=True)
    bot_thread.start()

    logger.info("All services started")

    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        analytics.stop()
        analytics_task.cancel()
        logger.info("Shutdown complete")


if __name__ == "__main__":
    asyncio.run(main())
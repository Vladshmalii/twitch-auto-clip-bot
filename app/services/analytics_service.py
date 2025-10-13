import asyncio
import logging
from datetime import datetime

from app.services.database_manager import DatabaseManager
from app.services.clip_manager import ClipManager

logger = logging.getLogger(__name__)


class AnalyticsService:
    def __init__(self, db_manager: DatabaseManager, clip_manager: ClipManager, update_interval: int = 3600):
        self.db_manager = db_manager
        self.clip_manager = clip_manager
        self.update_interval = update_interval
        self.running = False

    async def start(self):
        self.running = True
        logger.info("Analytics service started")

        while self.running:
            try:
                await self._update_clip_views()
                await self._update_daily_stats()
                await asyncio.sleep(self.update_interval)
            except Exception as e:
                logger.error(f"Analytics update error: {e}")
                await asyncio.sleep(60)

    async def _update_clip_views(self):
        clips = self.db_manager.get_recent_clips(limit=100)

        for clip in clips:
            try:
                view_count = await self.clip_manager.get_clip_views(clip.clip_id)
                if view_count != clip.view_count:
                    self.db_manager.update_clip_views(clip.clip_id, view_count)
            except Exception as e:
                logger.error(f"Failed to update views for clip {clip.clip_id}: {e}")

        logger.info(f"Updated views for {len(clips)} clips")

    async def _update_daily_stats(self):
        self.db_manager.update_daily_statistics()
        logger.info("Daily statistics updated")

    def stop(self):
        self.running = False
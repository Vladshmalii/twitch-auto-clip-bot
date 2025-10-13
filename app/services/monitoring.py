import aiohttp
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class MonitoringService:
    def __init__(self, webhook_url: str | None = None):
        self.webhook_url = webhook_url
        self.metrics = {
            'clips_created': 0,
            'signals_processed': 0,
            'errors': 0,
            'start_time': datetime.utcnow()
        }

    def record_clip(self):
        self.metrics['clips_created'] += 1

    def record_signal(self):
        self.metrics['signals_processed'] += 1

    def record_error(self):
        self.metrics['errors'] += 1

    def get_metrics(self) -> dict:
        uptime = (datetime.utcnow() - self.metrics['start_time']).total_seconds()
        return {
            **self.metrics,
            'uptime_seconds': uptime,
            'uptime_hours': uptime / 3600
        }

    async def send_alert(self, message: str, level: str = "info"):
        if not self.webhook_url:
            return

        color_map = {
            'info': 3447003,
            'warning': 16776960,
            'error': 15158332,
            'success': 3066993
        }

        payload = {
            "embeds": [{
                "title": f"Twitch Auto-Clip Bot - {level.upper()}",
                "description": message,
                "color": color_map.get(level, 0),
                "timestamp": datetime.utcnow().isoformat()
            }]
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.webhook_url, json=payload) as response:
                    if response.status != 204:
                        logger.warning(f"Discord webhook failed: {response.status}")
        except Exception as e:
            logger.error(f"Failed to send Discord alert: {e}")

    async def send_startup_alert(self):
        await self.send_alert("Bot started successfully", "success")

    async def send_clip_alert(self, clip_url: str, score: float):
        await self.send_alert(f"New clip created!\nScore: {score:.2f}\nURL: {clip_url}", "success")

    async def send_error_alert(self, error: str):
        await self.send_alert(f"Error occurred: {error}", "error")
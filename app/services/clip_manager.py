import aiohttp
import asyncio
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class ClipManager:
    def __init__(self, client_id: str, access_token: str, broadcaster_name: str, cooldown: int = 10):
        self.client_id = client_id
        self.access_token = access_token.replace("oauth:", "")
        self.broadcaster_name = broadcaster_name
        self.cooldown = cooldown
        self.last_clip_time = None
        self.broadcaster_id = None

    async def init(self):
        self.broadcaster_id = await self._get_broadcaster_id()

    async def _get_broadcaster_id(self) -> str:
        url = "https://api.twitch.tv/helix/users"
        headers = {
            "Client-ID": self.client_id,
            "Authorization": f"Bearer {self.access_token}"
        }
        params = {"login": self.broadcaster_name}

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params) as response:
                data = await response.json()
                return data['data'][0]['id']

    def can_create_clip(self) -> bool:
        if self.last_clip_time is None:
            return True
        return (datetime.utcnow() - self.last_clip_time).total_seconds() >= self.cooldown

    async def create_clip(self) -> dict | None:
        if not self.can_create_clip():
            return None

        url = "https://api.twitch.tv/helix/clips"
        headers = {
            "Client-ID": self.client_id,
            "Authorization": f"Bearer {self.access_token}"
        }
        params = {"broadcaster_id": self.broadcaster_id}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, params=params) as response:
                    if response.status == 202:
                        data = await response.json()
                        clip_data = data['data'][0]

                        self.last_clip_time = datetime.utcnow()

                        await asyncio.sleep(15)

                        clip_info = await self._verify_clip(clip_data['id'])
                        return clip_info
                    else:
                        logger.error(f"Failed to create clip: {response.status}")
                        return None
        except Exception as e:
            logger.error(f"Clip creation error: {e}")
            return None

    async def _verify_clip(self, clip_id: str) -> dict | None:
        url = "https://api.twitch.tv/helix/clips"
        headers = {
            "Client-ID": self.client_id,
            "Authorization": f"Bearer {self.access_token}"
        }
        params = {"id": clip_id}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data['data']:
                            return data['data'][0]
            return None
        except Exception as e:
            logger.error(f"Clip verification error: {e}")
            return None

    async def get_clip_views(self, clip_id: str) -> int:
        url = "https://api.twitch.tv/helix/clips"
        headers = {
            "Client-ID": self.client_id,
            "Authorization": f"Bearer {self.access_token}"
        }
        params = {"id": clip_id}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data['data']:
                            return data['data'][0]['view_count']
            return 0
        except Exception as e:
            logger.error(f"Failed to get clip views: {e}")
            return 0
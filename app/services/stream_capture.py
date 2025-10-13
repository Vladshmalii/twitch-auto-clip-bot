import asyncio
import streamlink
import subprocess
import logging
from typing import Callable

logger = logging.getLogger(__name__)


class StreamAudioCapture:
    def __init__(self, channel_name: str, sample_rate: int = 44100):
        self.channel_name = channel_name
        self.sample_rate = sample_rate
        self.process = None
        self.running = False

    async def start_capture(self, callback: Callable[[bytes], None]):
        self.running = True
        stream_url = f"https://twitch.tv/{self.channel_name}"
        retry_delay = 30
        max_retries = 20
        retries = 0

        while self.running and retries < max_retries:
            try:
                streams = streamlink.streams(stream_url)

                if not streams:
                    logger.warning(f"Stream offline, retry {retries}/{max_retries}")
                    await asyncio.sleep(retry_delay)
                    retries += 1
                    continue

                stream = streams.get("audio_only") or streams.get("worst")
                stream_url_direct = stream.url
                retries = 0

                self.process = subprocess.Popen(
                    [
                        "ffmpeg",
                        "-i", stream_url_direct,
                        "-f", "s16le",
                        "-ar", str(self.sample_rate),
                        "-ac", "1",
                        "-loglevel", "error",
                        "pipe:1"
                    ],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    bufsize=self.sample_rate * 2
                )

                chunk_size = self.sample_rate * 2

                while self.running:
                    chunk = self.process.stdout.read(chunk_size)
                    if not chunk:
                        break
                    await asyncio.to_thread(callback, chunk)

            except Exception as e:
                logger.error(f"Audio capture error: {e}")
                await asyncio.sleep(retry_delay)
                retries += 1
            finally:
                self.stop_capture()

        logger.error("Max retries reached")

    def stop_capture(self):
        self.running = False
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except:
                self.process.kill()
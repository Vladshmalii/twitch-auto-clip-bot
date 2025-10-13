import asyncio
import cv2
import numpy as np
import streamlink
import subprocess
import logging
from asyncio import Queue

logger = logging.getLogger(__name__)


class StreamVideoCapture:
    def __init__(self, channel_name: str, fps: int = 5):
        self.channel_name = channel_name
        self.fps = fps
        self.frame_interval = 1.0 / fps
        self.process = None
        self.running = False

    async def start_capture(self, frame_queue: Queue):
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

                stream = streams.get("720p") or streams.get("worst")
                stream_url_direct = stream.url
                retries = 0

                self.process = subprocess.Popen(
                    [
                        "ffmpeg",
                        "-i", stream_url_direct,
                        "-f", "rawvideo",
                        "-pix_fmt", "bgr24",
                        "-r", str(self.fps),
                        "-loglevel", "error",
                        "pipe:1"
                    ],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    bufsize=10 ** 8
                )

                width, height = 1280, 720
                frame_size = width * height * 3

                while self.running:
                    raw_frame = self.process.stdout.read(frame_size)
                    if len(raw_frame) != frame_size:
                        break

                    frame = np.frombuffer(raw_frame, dtype=np.uint8).reshape((height, width, 3))

                    if frame_queue.full():
                        try:
                            frame_queue.get_nowait()
                        except:
                            pass

                    await frame_queue.put(frame)

            except Exception as e:
                logger.error(f"Video capture error: {e}")
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
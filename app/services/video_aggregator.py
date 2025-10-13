import numpy as np
import asyncio
from asyncio import Queue
import logging
import threading

from app.services.scene_detector import SceneDetector
from app.services.motion_detector import MotionDetector
from app.services.object_detector import ObjectDetector

logger = logging.getLogger(__name__)


class VideoAggregator:
    def __init__(self, scene_threshold: float, motion_threshold: int,
                 yolo_model_size: str, yolo_confidence: float, action_person_count: int):
        self.scene_detector = SceneDetector(scene_threshold)
        self.motion_detector = MotionDetector(motion_threshold)
        self.object_detector = ObjectDetector(yolo_model_size, yolo_confidence, action_person_count)

        self.weights = {'scene': 0.3, 'motion': 0.4, 'action': 0.3}

        self.latest_signals = {
            'scene_change': False,
            'scene_score': 0.0,
            'high_motion': False,
            'motion_area': 0.0,
            'action_detected': False,
            'person_count': 0,
            'weapon_count': 0,
            'video_score': 0.0
        }
        self.lock = threading.Lock()

    async def process_frames(self, frame_queue: Queue):
        while True:
            try:
                frame = await asyncio.wait_for(frame_queue.get(), timeout=1.0)

                scene_result = self.scene_detector.detect(frame)
                motion_result = self.motion_detector.detect(frame)
                action_result = self.object_detector.detect(frame)

                scene_score = 1.0 if scene_result['scene_change'] else min(scene_result['score'] / 50.0, 1.0)
                motion_score = min(motion_result['motion_area'] / 10000.0, 1.0)
                action_score = 1.0 if action_result['action_detected'] else 0.0

                video_score = (
                        scene_score * self.weights['scene'] +
                        motion_score * self.weights['motion'] +
                        action_score * self.weights['action']
                )

                with self.lock:
                    self.latest_signals.update({
                        'scene_change': scene_result['scene_change'],
                        'scene_score': scene_result['score'],
                        'high_motion': motion_result['high_motion'],
                        'motion_area': motion_result['motion_area'],
                        'action_detected': action_result['action_detected'],
                        'person_count': action_result['person_count'],
                        'weapon_count': action_result['weapon_count'],
                        'video_score': video_score
                    })

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Video processing error: {e}")

    def get_signals(self) -> dict:
        with self.lock:
            return self.latest_signals.copy()
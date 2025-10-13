import cv2
import numpy as np
import logging

logger = logging.getLogger(__name__)


class SceneDetector:
    def __init__(self, threshold: float = 27.0):
        self.threshold = threshold
        self.prev_frame = None

    def detect(self, frame: np.ndarray) -> dict:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.resize(gray, (320, 180))

        if self.prev_frame is None:
            self.prev_frame = gray
            return {'scene_change': False, 'score': 0.0}

        diff = cv2.absdiff(self.prev_frame, gray)
        score = float(np.mean(diff))

        scene_change = score > self.threshold

        self.prev_frame = gray

        return {
            'scene_change': scene_change,
            'score': score
        }
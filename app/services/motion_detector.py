import cv2
import numpy as np
import logging

logger = logging.getLogger(__name__)


class MotionDetector:
    def __init__(self, threshold: int = 5000):
        self.threshold = threshold
        self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(
            history=500,
            varThreshold=16,
            detectShadows=False
        )

    def detect(self, frame: np.ndarray) -> dict:
        resized = cv2.resize(frame, (640, 360))

        fg_mask = self.bg_subtractor.apply(resized)

        _, thresh = cv2.threshold(fg_mask, 244, 255, cv2.THRESH_BINARY)

        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)
        thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)

        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        motion_area = sum(cv2.contourArea(c) for c in contours if cv2.contourArea(c) > 100)

        is_high_motion = motion_area > self.threshold

        return {
            'high_motion': is_high_motion,
            'motion_area': float(motion_area)
        }
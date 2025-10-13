import numpy as np
import torch
import logging

logger = logging.getLogger(__name__)


class ObjectDetector:
    def __init__(self, model_size: str = "n", confidence: float = 0.5, action_person_count: int = 3):
        self.confidence = confidence
        self.action_person_count = action_person_count
        self.model = None
        self.weapon_classes = {39, 41, 43}

        try:
            from ultralytics import YOLO
            self.model = YOLO(f"yolo11{model_size}.pt")
            device = 'cuda' if torch.cuda.is_available() else 'cpu'
            self.model.to(device)
            logger.info(f"YOLO loaded on {device}")
        except Exception as e:
            logger.error(f"YOLO initialization failed: {e}")

    def detect(self, frame: np.ndarray) -> dict:
        if self.model is None:
            return {'action_detected': False, 'person_count': 0, 'weapon_count': 0}

        try:
            results = self.model(frame, conf=self.confidence, verbose=False)
            person_count = 0
            weapon_count = 0

            for result in results:
                for box in result.boxes:
                    class_id = int(box.cls[0])
                    if class_id == 0:
                        person_count += 1
                    elif class_id in self.weapon_classes:
                        weapon_count += 1

            is_action = person_count >= self.action_person_count or weapon_count > 0

            return {
                'action_detected': is_action,
                'person_count': person_count,
                'weapon_count': weapon_count
            }
        except Exception as e:
            logger.error(f"Detection error: {e}")
            return {'action_detected': False, 'person_count': 0, 'weapon_count': 0}
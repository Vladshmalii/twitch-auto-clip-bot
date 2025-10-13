import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
import logging

logger = logging.getLogger(__name__)


class MLOptimizer:
    def __init__(self, success_threshold: int = 10):
        self.success_threshold = success_threshold
        self.model = LogisticRegression(max_iter=1000)
        self.scaler = StandardScaler()
        self.is_trained = False

    def train_model(self, signals_data: list) -> dict | None:
        if len(signals_data) < 50:
            logger.warning(f"Not enough data for training: {len(signals_data)} samples")
            return None

        X = []
        y = []

        for signal in signals_data:
            features = [
                signal.chat_velocity / 100.0,
                signal.audio_rms * 10.0,
                signal.audio_onsets / 10.0,
                signal.motion_score / 10000.0
            ]
            X.append(features)

            clip_success = 1 if signal.clip and signal.clip.view_count >= self.success_threshold else 0
            y.append(clip_success)

        X = np.array(X)
        y = np.array(y)

        X_scaled = self.scaler.fit_transform(X)

        self.model.fit(X_scaled, y)
        self.is_trained = True

        coefficients = np.abs(self.model.coef_[0])
        total = np.sum(coefficients)

        weights = {
            'chat_velocity': float(coefficients[0] / total),
            'audio_rms': float(coefficients[1] / total * 0.5),
            'audio_onsets': float(coefficients[2] / total * 0.5),
            'video_score': float(coefficients[3] / total)
        }

        weights['keywords'] = 0.1

        total_weight = sum(weights.values())
        weights = {k: v / total_weight for k, v in weights.items()}

        logger.info(f"Model trained with optimized weights: {weights}")

        return weights

    def predict_success(self, features: dict) -> float:
        if not self.is_trained:
            return 0.5

        X = np.array([[
            features['chat_velocity'] / 100.0,
            features['audio_rms'] * 10.0,
            features['audio_onsets'] / 10.0,
            features['video_score']
        ]])

        X_scaled = self.scaler.transform(X)

        return float(self.model.predict_proba(X_scaled)[0][1])
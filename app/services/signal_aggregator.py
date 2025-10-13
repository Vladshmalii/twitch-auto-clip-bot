import logging

logger = logging.getLogger(__name__)


class MultiSignalAggregator:
    def __init__(self, threshold: float = 0.7):
        self.threshold = threshold
        self.weights = {
            'chat_velocity': 0.4,
            'audio_rms': 0.2,
            'audio_onsets': 0.1,
            'video_score': 0.2,
            'keywords': 0.1
        }

    def calculate_scores(self, signals: dict) -> dict:
        chat_velocity = signals.get('chat_velocity', 0)
        audio_rms = signals.get('audio_rms', 0.0)
        audio_onsets = signals.get('audio_onsets', 0)
        video_score = signals.get('video_score', 0.0)
        keywords = signals.get('keywords', 0)

        chat_score = min(chat_velocity / 100.0, 1.0)
        audio_rms_score = min(audio_rms * 10.0, 1.0)
        audio_onset_score = min(audio_onsets / 10.0, 1.0)
        keyword_score = min(keywords / 5.0, 1.0)

        audio_score = (audio_rms_score + audio_onset_score) / 2.0

        final_score = (
                chat_score * self.weights['chat_velocity'] +
                audio_rms_score * self.weights['audio_rms'] +
                audio_onset_score * self.weights['audio_onsets'] +
                video_score * self.weights['video_score'] +
                keyword_score * self.weights['keywords']
        )

        return {
            'chat_score': chat_score,
            'audio_score': audio_score,
            'video_score': video_score,
            'final_score': final_score,
            'should_clip': final_score > self.threshold
        }

    def update_weights(self, new_weights: dict):
        self.weights.update(new_weights)
        logger.info(f"Updated weights: {self.weights}")
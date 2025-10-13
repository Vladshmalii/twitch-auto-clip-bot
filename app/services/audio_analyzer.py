import numpy as np
import librosa
from collections import deque
import logging

logger = logging.getLogger(__name__)


class AudioAnalyzer:
    def __init__(self, sample_rate: int = 44100, window_size: int = 10):
        self.sr = sample_rate
        self.baseline_rms = deque(maxlen=window_size)
        self.baseline_initialized = False

    def analyze_chunk(self, audio_data: bytes) -> dict:
        audio_array = np.frombuffer(audio_data, dtype=np.int16)
        audio_float = audio_array.astype(np.float32) / 32768.0

        rms = float(np.sqrt(np.mean(audio_float ** 2)))

        onsets = librosa.onset.onset_detect(
            y=audio_float,
            sr=self.sr,
            delta=0.7,
            backtrack=False
        )
        onset_count = len(onsets)

        if not self.baseline_initialized:
            self.baseline_rms.append(rms)
            if len(self.baseline_rms) == self.baseline_rms.maxlen:
                self.baseline_initialized = True
            baseline = rms
        else:
            baseline = np.mean(self.baseline_rms)
            self.baseline_rms.append(rms)

        is_spike = rms > baseline * 1.5 if baseline > 0 else False

        return {
            'rms': rms,
            'onsets': onset_count,
            'is_spike': is_spike,
            'spike_ratio': rms / baseline if baseline > 0 else 1.0
        }
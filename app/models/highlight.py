from collections import deque
from datetime import datetime, timedelta


class ChatVelocityTracker:
    def __init__(self, window_seconds: int = 10):
        self.messages = deque()
        self.window = timedelta(seconds=window_seconds)
        self.keywords = {"pog", "poggers", "clip", "wow", "holy", "wtf", "omg", "insane"}
        self.keyword_count = 0

    def add_message(self, content: str = ""):
        now = datetime.utcnow()
        self.messages.append(now)
        self._cleanup_old(now)

        lower_content = content.lower()
        if any(keyword in lower_content for keyword in self.keywords):
            self.keyword_count += 1

    def _cleanup_old(self, now: datetime):
        cutoff = now - self.window
        while self.messages and self.messages[0] < cutoff:
            self.messages.popleft()

    def get_velocity(self) -> int:
        now = datetime.utcnow()
        self._cleanup_old(now)
        return len(self.messages)

    def get_keyword_count(self) -> int:
        count = self.keyword_count
        self.keyword_count = 0
        return count

    def is_spike(self, threshold: int) -> bool:
        return self.get_velocity() > threshold
from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache


class Settings(BaseSettings):
    twitch_client_id: str
    twitch_client_secret: str
    twitch_access_token: str
    channel_name: str

    database_url: str

    chat_velocity_threshold: int = 50
    combined_score_threshold: float = 0.7
    clip_cooldown_seconds: int = 10

    enable_audio_analysis: bool = True
    enable_video_analysis: bool = False
    yolo_model_size: str = "n"

    discord_webhook_url: str | None = None

    audio_window_seconds: int = 2
    audio_sample_rate: int = 44100
    video_fps: int = 5
    video_frame_buffer_size: int = 10

    scene_threshold: float = 27.0
    motion_threshold: int = 5000
    yolo_confidence: float = 0.5
    yolo_action_person_count: int = 3

    ml_training_days: int = 30
    ml_success_view_threshold: int = 10

    analytics_update_interval: int = 3600

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()
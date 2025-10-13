from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime, date, timedelta
from typing import List
from contextlib import contextmanager
import logging

from app.models.database import Base, Clip, Signal, Trigger, Statistic
from app.core.config import get_settings

logger = logging.getLogger(__name__)


class DatabaseManager:
    def __init__(self):
        settings = get_settings()
        self.engine = create_engine(settings.database_url, pool_pre_ping=True, pool_size=10, max_overflow=20)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

    def init_db(self):
        Base.metadata.create_all(bind=self.engine)
        logger.info("Database initialized")

    @contextmanager
    def get_session(self):
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            session.close()

    def create_clip(self, clip_id: str, url: str, final_score: float,
                    chat_score: float, audio_score: float, video_score: float,
                    triggers: dict) -> Clip:
        with self.get_session() as session:
            clip = Clip(
                clip_id=clip_id,
                url=url,
                final_score=final_score,
                chat_score=chat_score,
                audio_score=audio_score,
                video_score=video_score
            )
            session.add(clip)
            session.flush()

            for trigger_type, trigger_value in triggers.items():
                trigger = Trigger(
                    clip_id=clip.id,
                    trigger_type=trigger_type,
                    trigger_value=trigger_value
                )
                session.add(trigger)

            session.refresh(clip)
            return clip

    def log_signal(self, chat_velocity: int, audio_rms: float, audio_onsets: int,
                   motion_score: float, scene_change: bool, action_detected: bool,
                   final_score: float, clip_created: bool, clip_id: str = None):
        with self.get_session() as session:
            signal = Signal(
                chat_velocity=chat_velocity,
                audio_rms=audio_rms,
                audio_onsets=audio_onsets,
                motion_score=motion_score,
                scene_change=scene_change,
                action_detected=action_detected,
                final_score=final_score,
                clip_created=clip_created,
                clip_id=clip_id
            )
            session.add(signal)

    def update_clip_views(self, clip_id: str, view_count: int):
        with self.get_session() as session:
            clip = session.query(Clip).filter(Clip.clip_id == clip_id).first()
            if clip:
                clip.view_count = view_count

    def get_recent_clips(self, limit: int = 50) -> List[Clip]:
        with self.get_session() as session:
            clips = session.query(Clip).order_by(Clip.created_at.desc()).limit(limit).all()
            return [self._detach_clip(c) for c in clips]

    def get_signals_with_clips(self, days: int = 30) -> List[Signal]:
        with self.get_session() as session:
            cutoff = datetime.utcnow() - timedelta(days=days)
            signals = session.query(Signal).filter(
                Signal.timestamp >= cutoff,
                Signal.clip_created == True
            ).all()
            return [self._detach_signal(s) for s in signals]

    def update_daily_statistics(self):
        with self.get_session() as session:
            today = date.today()

            clips = session.query(Clip).filter(func.date(Clip.created_at) == today).all()
            total_clips = len(clips)

            if total_clips == 0:
                return

            successful_clips = sum(1 for c in clips if c.view_count >= 10)
            avg_chat = sum(c.chat_score for c in clips) / total_clips
            avg_audio = sum(c.audio_score for c in clips) / total_clips
            avg_video = sum(c.video_score for c in clips) / total_clips
            avg_final = sum(c.final_score for c in clips) / total_clips
            total_views = sum(c.view_count for c in clips)
            avg_views = total_views / total_clips

            stat = session.query(Statistic).filter(Statistic.date == today).first()
            if not stat:
                stat = Statistic(date=today)
                session.add(stat)

            stat.total_clips = total_clips
            stat.successful_clips = successful_clips
            stat.avg_chat_score = avg_chat
            stat.avg_audio_score = avg_audio
            stat.avg_video_score = avg_video
            stat.avg_final_score = avg_final
            stat.avg_views = avg_views
            stat.total_views = total_views

    def _detach_clip(self, clip: Clip) -> Clip:
        detached = Clip(
            id=clip.id,
            clip_id=clip.clip_id,
            url=clip.url,
            view_count=clip.view_count,
            final_score=clip.final_score,
            chat_score=clip.chat_score,
            audio_score=clip.audio_score,
            video_score=clip.video_score,
            created_at=clip.created_at
        )
        return detached

    def _detach_signal(self, signal: Signal) -> Signal:
        detached = Signal(
            id=signal.id,
            timestamp=signal.timestamp,
            chat_velocity=signal.chat_velocity,
            audio_rms=signal.audio_rms,
            audio_onsets=signal.audio_onsets,
            motion_score=signal.motion_score,
            scene_change=signal.scene_change,
            action_detected=signal.action_detected,
            final_score=signal.final_score,
            clip_created=signal.clip_created,
            clip_id=signal.clip_id
        )
        if signal.clip:
            detached.clip = self._detach_clip(signal.clip)
        return detached
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Date
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


class Clip(Base):
    __tablename__ = "clips"

    id = Column(Integer, primary_key=True, index=True)
    clip_id = Column(String, unique=True, index=True, nullable=False)
    url = Column(String, nullable=False)
    view_count = Column(Integer, default=0)

    final_score = Column(Float, nullable=False)
    chat_score = Column(Float, default=0.0)
    audio_score = Column(Float, default=0.0)
    video_score = Column(Float, default=0.0)

    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    triggers = relationship("Trigger", back_populates="clip", cascade="all, delete-orphan")


class Signal(Base):
    __tablename__ = "signals"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    chat_velocity = Column(Integer, default=0)
    audio_rms = Column(Float, default=0.0)
    audio_onsets = Column(Integer, default=0)
    motion_score = Column(Float, default=0.0)
    scene_change = Column(Boolean, default=False)
    action_detected = Column(Boolean, default=False)

    final_score = Column(Float, nullable=False)
    clip_created = Column(Boolean, default=False)
    clip_id = Column(String, nullable=True)


class Trigger(Base):
    __tablename__ = "triggers"

    id = Column(Integer, primary_key=True, index=True)
    clip_id = Column(Integer, ForeignKey("clips.id"), nullable=False)
    trigger_type = Column(String, nullable=False)
    trigger_value = Column(Float, nullable=False)

    clip = relationship("Clip", back_populates="triggers")


class Statistic(Base):
    __tablename__ = "statistics"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, unique=True, index=True, nullable=False)

    total_clips = Column(Integer, default=0)
    successful_clips = Column(Integer, default=0)

    avg_chat_score = Column(Float, default=0.0)
    avg_audio_score = Column(Float, default=0.0)
    avg_video_score = Column(Float, default=0.0)
    avg_final_score = Column(Float, default=0.0)

    avg_views = Column(Float, default=0.0)
    total_views = Column(Integer, default=0)
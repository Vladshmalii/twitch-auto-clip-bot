from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func
from datetime import datetime, timedelta
import logging

from app.services.database_manager import DatabaseManager
from app.models.database import Clip, Signal, Statistic, Trigger

logger = logging.getLogger(__name__)

app = FastAPI(title="Twitch Auto-Clip Dashboard")
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

db_manager = DatabaseManager()


@app.get("/")
async def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.get("/api/stats/overview")
async def get_overview_stats():
    with db_manager.get_session() as session:
        total_clips = session.query(Clip).count()

        if total_clips == 0:
            return {
                "total_clips": 0,
                "successful_clips": 0,
                "success_rate": 0.0,
                "total_views": 0,
                "avg_score": 0.0,
                "recent_clips": []
            }

        clips = session.query(Clip).all()
        successful_clips = sum(1 for c in clips if c.view_count >= 10)
        total_views = sum(c.view_count for c in clips)
        avg_score = sum(c.final_score for c in clips) / total_clips

        recent_clips = session.query(Clip).order_by(Clip.created_at.desc()).limit(5).all()

        return {
            "total_clips": total_clips,
            "successful_clips": successful_clips,
            "success_rate": round((successful_clips / total_clips * 100), 2),
            "total_views": total_views,
            "avg_score": round(avg_score, 2),
            "recent_clips": [
                {
                    "id": c.clip_id,
                    "url": c.url,
                    "score": round(c.final_score, 2),
                    "views": c.view_count,
                    "created_at": c.created_at.isoformat()
                }
                for c in recent_clips
            ]
        }


@app.get("/api/stats/trigger-effectiveness")
async def get_trigger_effectiveness():
    with db_manager.get_session() as session:
        triggers = session.query(Trigger).all()

        trigger_stats = {}

        for trigger in triggers:
            trigger_type = trigger.trigger_type
            if trigger_type not in trigger_stats:
                trigger_stats[trigger_type] = {
                    'count': 0,
                    'total_value': 0.0,
                    'total_views': 0
                }

            trigger_stats[trigger_type]['count'] += 1
            trigger_stats[trigger_type]['total_value'] += trigger.trigger_value
            trigger_stats[trigger_type]['total_views'] += trigger.clip.view_count

        result = []
        for trigger_type, stats in trigger_stats.items():
            count = stats['count']
            result.append({
                'trigger_type': trigger_type,
                'count': count,
                'avg_value': round(stats['total_value'] / count, 2),
                'avg_views': round(stats['total_views'] / count, 2)
            })

        return sorted(result, key=lambda x: x['avg_views'], reverse=True)


@app.get("/api/stats/daily-trends")
async def get_daily_trends():
    with db_manager.get_session() as session:
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)

        stats = session.query(Statistic).filter(
            Statistic.date >= thirty_days_ago.date()
        ).order_by(Statistic.date).all()

        return [
            {
                'date': s.date.isoformat(),
                'total_clips': s.total_clips,
                'successful_clips': s.successful_clips,
                'avg_score': round(s.avg_final_score, 2),
                'avg_views': round(s.avg_views, 2)
            }
            for s in stats
        ]


@app.get("/api/stats/signal-correlation")
async def get_signal_correlation():
    with db_manager.get_session() as session:
        clips = session.query(Clip).filter(Clip.view_count >= 10).all()

        if len(clips) < 5:
            return {
                'chat_correlation': 0.0,
                'audio_correlation': 0.0,
                'video_correlation': 0.0
            }

        chat_scores = [c.chat_score for c in clips]
        audio_scores = [c.audio_score for c in clips]
        video_scores = [c.video_score for c in clips]
        views = [c.view_count for c in clips]

        import numpy as np

        chat_corr = np.corrcoef(chat_scores, views)[0, 1]
        audio_corr = np.corrcoef(audio_scores, views)[0, 1]
        video_corr = np.corrcoef(video_scores, views)[0, 1]

        return {
            'chat_correlation': round(chat_corr, 3),
            'audio_correlation': round(audio_corr, 3),
            'video_correlation': round(video_corr, 3)
        }


@app.get("/api/stats/hourly-distribution")
async def get_hourly_distribution():
    with db_manager.get_session() as session:
        clips = session.query(Clip).all()

        hourly_stats = {hour: {'count': 0, 'total_views': 0} for hour in range(24)}

        for clip in clips:
            hour = clip.created_at.hour
            hourly_stats[hour]['count'] += 1
            hourly_stats[hour]['total_views'] += clip.view_count

        return [
            {
                'hour': hour,
                'count': stats['count'],
                'avg_views': round(stats['total_views'] / stats['count'], 2) if stats['count'] > 0 else 0
            }
            for hour, stats in hourly_stats.items()
        ]


@app.get("/api/stats/recent-signals")
async def get_recent_signals():
    with db_manager.get_session() as session:
        signals = session.query(Signal).order_by(Signal.timestamp.desc()).limit(100).all()

        return [
            {
                'timestamp': s.timestamp.isoformat(),
                'chat_velocity': s.chat_velocity,
                'audio_rms': round(s.audio_rms, 3),
                'motion_score': round(s.motion_score, 2),
                'final_score': round(s.final_score, 2),
                'clip_created': s.clip_created
            }
            for s in signals
        ]


@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}
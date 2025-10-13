from twitchio.ext import commands
import asyncio
import logging
from asyncio import Queue

from app.models.highlight import ChatVelocityTracker
from app.services.clip_manager import ClipManager
from app.services.stream_capture import StreamAudioCapture
from app.services.audio_analyzer import AudioAnalyzer
from app.services.video_capture import StreamVideoCapture
from app.services.video_aggregator import VideoAggregator
from app.services.signal_aggregator import MultiSignalAggregator
from app.services.database_manager import DatabaseManager
from app.services.analytics_service import AnalyticsService
from app.services.ml_optimizer import MLOptimizer
from app.services.monitoring import MonitoringService
from app.core.config import get_settings

logger = logging.getLogger(__name__)


class TwitchAutoClipBot(commands.Bot):
    def __init__(self):
        settings = get_settings()

        super().__init__(
            token=settings.twitch_access_token,
            prefix='!',
            initial_channels=[settings.channel_name]
        )

        self.settings = settings
        self.velocity_tracker = ChatVelocityTracker()

        self.clip_manager = ClipManager(
            settings.twitch_client_id,
            settings.twitch_access_token,
            settings.channel_name,
            settings.clip_cooldown_seconds
        )

        self.db_manager = DatabaseManager()
        self.db_manager.init_db()

        self.signal_aggregator = MultiSignalAggregator(settings.combined_score_threshold)
        self.monitoring = MonitoringService(settings.discord_webhook_url)

        self.audio_analyzer = None
        self.audio_capture = None
        self.video_capture = None
        self.video_aggregator = None
        self.frame_queue = None

        self.ml_optimizer = MLOptimizer(settings.ml_success_view_threshold)
        self.analytics_service = AnalyticsService(
            self.db_manager,
            self.clip_manager,
            settings.analytics_update_interval
        )

        self.latest_audio_signals = {'rms': 0.0, 'onsets': 0}

    async def event_ready(self):
        logger.info(f'Bot ready | {self.nick}')
        await self.clip_manager.init()

        if self.settings.enable_audio_analysis:
            self.audio_analyzer = AudioAnalyzer(self.settings.audio_sample_rate)
            self.audio_capture = StreamAudioCapture(
                self.settings.channel_name,
                self.settings.audio_sample_rate
            )
            asyncio.create_task(self.audio_capture.start_capture(self._handle_audio_chunk))
            logger.info("Audio analysis enabled")

        if self.settings.enable_video_analysis:
            self.frame_queue = Queue(maxsize=self.settings.video_frame_buffer_size)
            self.video_capture = StreamVideoCapture(
                self.settings.channel_name,
                self.settings.video_fps
            )
            self.video_aggregator = VideoAggregator(
                self.settings.scene_threshold,
                self.settings.motion_threshold,
                self.settings.yolo_model_size,
                self.settings.yolo_confidence,
                self.settings.yolo_action_person_count
            )
            asyncio.create_task(self.video_capture.start_capture(self.frame_queue))
            asyncio.create_task(self.video_aggregator.process_frames(self.frame_queue))
            logger.info("Video analysis enabled")

        asyncio.create_task(self.analytics_service.start())
        asyncio.create_task(self._ml_training_loop())

        await self.monitoring.send_startup_alert()

    async def event_message(self, message):
        if message.echo:
            return

        self.velocity_tracker.add_message(message.content)

        await self._check_highlight_conditions()

    def _handle_audio_chunk(self, chunk: bytes):
        if self.audio_analyzer:
            analysis = self.audio_analyzer.analyze_chunk(chunk)
            self.latest_audio_signals = {
                'rms': analysis['rms'],
                'onsets': analysis['onsets']
            }

    async def _check_highlight_conditions(self):
        chat_velocity = self.velocity_tracker.get_velocity()
        keywords = self.velocity_tracker.get_keyword_count()

        signals = {
            'chat_velocity': chat_velocity,
            'audio_rms': self.latest_audio_signals['rms'],
            'audio_onsets': self.latest_audio_signals['onsets'],
            'keywords': keywords,
            'video_score': 0.0
        }

        if self.video_aggregator:
            video_signals = self.video_aggregator.get_signals()
            signals['video_score'] = video_signals['video_score']

        scores = self.signal_aggregator.calculate_scores(signals)

        self.db_manager.log_signal(
            chat_velocity=chat_velocity,
            audio_rms=self.latest_audio_signals['rms'],
            audio_onsets=self.latest_audio_signals['onsets'],
            motion_score=signals.get('video_score', 0.0) * 10000,
            scene_change=self.video_aggregator.latest_signals.get('scene_change',
                                                                  False) if self.video_aggregator else False,
            action_detected=self.video_aggregator.latest_signals.get('action_detected',
                                                                     False) if self.video_aggregator else False,
            final_score=scores['final_score'],
            clip_created=False
        )

        self.monitoring.record_signal()

        if scores['should_clip']:
            await self._create_highlight_clip(scores, signals)

    async def _create_highlight_clip(self, scores: dict, signals: dict):
        clip_info = await self.clip_manager.create_clip()

        if clip_info:
            triggers = {
                'chat_velocity': signals['chat_velocity'],
                'audio_rms': signals['audio_rms'],
                'video_score': signals['video_score']
            }

            self.db_manager.create_clip(
                clip_id=clip_info['id'],
                url=clip_info['url'],
                final_score=scores['final_score'],
                chat_score=scores['chat_score'],
                audio_score=scores['audio_score'],
                video_score=scores['video_score'],
                triggers=triggers
            )

            self.db_manager.log_signal(
                chat_velocity=signals['chat_velocity'],
                audio_rms=signals['audio_rms'],
                audio_onsets=signals['audio_onsets'],
                motion_score=signals.get('video_score', 0.0) * 10000,
                scene_change=False,
                action_detected=False,
                final_score=scores['final_score'],
                clip_created=True,
                clip_id=clip_info['id']
            )

            self.monitoring.record_clip()
            await self.monitoring.send_clip_alert(clip_info['url'], scores['final_score'])

            logger.info(f"Clip created: {clip_info['url']} (score: {scores['final_score']:.2f})")

    async def _ml_training_loop(self):
        await asyncio.sleep(3600)

        while True:
            try:
                signals_data = self.db_manager.get_signals_with_clips(self.settings.ml_training_days)

                if len(signals_data) >= 50:
                    new_weights = self.ml_optimizer.train_model(signals_data)
                    if new_weights:
                        self.signal_aggregator.update_weights(new_weights)
                        logger.info("ML weights updated successfully")

            except Exception as e:
                logger.error(f"ML training error: {e}")

            await asyncio.sleep(86400)
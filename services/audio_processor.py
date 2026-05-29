"""
Async audio processing service.
Handles STT -> Agent -> TTS pipeline asynchronously with timeout support.
"""

import asyncio
import base64
import os

from core.error_handler import (
    ERR_ALL_TTS_FAILED,
    ERR_INTERNAL_SERVER_ERROR,
    ERR_TRANSCRIPTION_FAILED,
    ErrorCategory,
    ErrorCode,
    ProcessingError,
    handle_exception,
)
from core.logger import get_correlated_logger


class AsyncAudioProcessor:
    """
    Asynchronous audio processor for non-blocking STT -> Agent -> TTS pipeline.

    Features:
    - Async STT transcription
    - Async agent processing
    - Async TTS generation
    - Configurable timeouts
    - Progress tracking

    Usage:
        processor = AsyncAudioProcessor(stt_engine, agent, tts_engine, logger)
        result = await processor.process(audio_path, session_id, customer_id)
    """

    def __init__(self, stt_engine, agent, tts_engine, logger=None):
        """
        Initialize async audio processor.

        Args:
            stt_engine: Speech-to-text engine (FasterWhisperSTTEngine)
            agent: LangChain bank agent
            tts_engine: Text-to-speech engine router
            logger: Loguru logger instance
        """
        self.stt_engine = stt_engine
        self.agent = agent
        self.tts_engine = tts_engine
        self.logger = logger or get_correlated_logger()
        self.timeout_seconds = int(os.getenv(
            "AUDIO_PROCESSING_TIMEOUT_SECONDS", "120"
        ))

    async def process(
        self,
        audio_path: str,
        session_id: str,
        customer_id: str | None = None,
        strictness_level: int = 3,
        model_name: str | None = None,
        tts_engine_name: str | None = None,
    ) -> dict:
        """
        Process audio through full STT -> Agent -> TTS pipeline asynchronously.

        Args:
            audio_path: Path to audio file
            session_id: Session identifier
            customer_id: Optional authenticated customer ID
            strictness_level: Agent strictness level (1-5)
            model_name: Ollama model name
            tts_engine_name: TTS engine to use

        Returns:
            Dictionary with transcription, AI response, and base64 audio
        """
        try:
            # Run entire pipeline with timeout
            result = await asyncio.wait_for(
                self._process_pipeline(
                    audio_path,
                    session_id,
                    customer_id,
                    strictness_level,
                    model_name,
                    tts_engine_name,
                ),
                timeout=self.timeout_seconds,
            )
            return result

        except asyncio.TimeoutError as e:
            timeout_err = ProcessingError(
                category=ErrorCategory.TIMEOUT_ERROR,
                code=ErrorCode.OVERALL_TIMEOUT,
                message_tr=f"İşlem zaman aşımına uğradı ({self.timeout_seconds}s). Lütfen tekrar deneyin.",
                message_en=f"Audio processing timed out after {self.timeout_seconds}s",
                retryable=True,
            )
            return handle_exception(timeout_err, e, logger=self.logger, context="AsyncAudioProcessor.process")

        except Exception as e:
            return handle_exception(ERR_INTERNAL_SERVER_ERROR, e, logger=self.logger, context="AsyncAudioProcessor.process")

    async def _process_pipeline(
        self,
        audio_path: str,
        session_id: str,
        customer_id: str | None,
        strictness_level: int,
        model_name: str | None,
        tts_engine_name: str | None,
    ) -> dict:
        """
        Execute STT -> Agent -> TTS pipeline.

        Each stage runs in a thread pool to avoid blocking the event loop.
        """
        output_file = None
        temp_audio_path = audio_path

        try:
            # Stage 1: Speech-to-Text (run in thread pool)
            self.logger.debug(f"Stage 1: STT - {audio_path}")
            user_text = await asyncio.to_thread(
                self.stt_engine.transcribe_file,
                temp_audio_path,
                initial_prompt="Bu bir bankacılık görüşmesidir. Bakiye, havale, EFT, kredi kartı, valör, faiz işlemleri konuşulmaktadır.",
            )

            if not user_text:
                return {
                    "status": "error",
                    "message": "Ses anlaşılamadı",
                    "error_code": "STT_FAILED",
                }

            self.logger.info(f"STT Result: {user_text}")

            # Stage 2: Agent Processing (run in thread pool)
            self.logger.debug("Stage 2: Agent Processing")
            ai_response_text = await asyncio.to_thread(
                self.agent.handle_turn,
                user_text,
                strictness_level,
                session_id,
                customer_id,
            )

            self.logger.info(f"Agent Response: {ai_response_text}")

            # Stage 3: Text-to-Speech (run in thread pool with fallback)
            self.logger.debug("Stage 3: TTS Generation")
            from core.error_handler import execute_with_fallback
            output_file = await asyncio.to_thread(
                execute_with_fallback,
                primary_fn=lambda: self.tts_engine.generate_audio(text=ai_response_text, engine_name=tts_engine_name),
                fallback_fn=lambda: self.tts_engine.generate_audio(text=ai_response_text, engine_name="google"),
                logger=self.logger,
                context="audio_processor_tts"
            )

            if not output_file or not os.path.exists(output_file):
                return {
                    "status": "error",
                    "message": "TTS motorunda ses üretilemedi.",
                    "user_text": user_text,
                    "ai_text": ai_response_text,
                    "error_code": "TTS_FAILED",
                }

            # Stage 4: Encode audio to base64
            self.logger.debug("Stage 4: Encoding audio")
            with open(output_file, "rb") as audio_file:
                encoded_audio = base64.b64encode(audio_file.read()).decode("utf-8")

            self.logger.info("Audio processing complete")

            return {
                "status": "success",
                "user_text": user_text,
                "ai_text": ai_response_text,
                "audio_base64": encoded_audio,
                "output_file": output_file,
            }

        except Exception as e:
            self.logger.error(f"Pipeline error: {e}")
            raise

        finally:
            # Cleanup temp files (run in thread pool)
            await self._cleanup_files(temp_audio_path, output_file)

    async def _cleanup_files(
        self, temp_audio_path: str | None, output_file: str | None
    ):
        """Clean up temporary audio files asynchronously."""

        def _remove(path: str):
            try:
                if path and os.path.exists(path):
                    os.remove(path)
            except OSError as e:
                self.logger.error(f"Temp file cleanup error: {e}")

        # Run cleanup in background
        if temp_audio_path:
            asyncio.create_task(asyncio.to_thread(_remove, temp_audio_path))
        if output_file:
            asyncio.create_task(asyncio.to_thread(_remove, output_file))

    async def transcribe_only(
        self, audio_path: str, language: str = "tr"
    ) -> dict:
        """
        Transcribe audio without agent processing or TTS.

        Args:
            audio_path: Path to audio file
            language: Language code

        Returns:
            Dictionary with transcription result
        """
        try:
            transcription = await asyncio.to_thread(
                self.stt_engine.transcribe_file, audio_path
            )

            return {
                "status": "success",
                "transcription": transcription or "",
            }

        except Exception as e:
            return handle_exception(
                ERR_TRANSCRIPTION_FAILED,
                e,
                logger=self.logger,
                context="AsyncAudioProcessor.transcribe_only",
            )

    async def generate_speech_only(
        self,
        text: str,
        tts_engine_name: str | None = None,
    ) -> dict:
        """
        Generate speech from text without STT or agent processing.

        Args:
            text: Text to synthesize
            tts_engine_name: TTS engine to use

        Returns:
            Dictionary with base64-encoded audio
        """
        try:
            from core.error_handler import execute_with_fallback
            output_file = await asyncio.to_thread(
                execute_with_fallback,
                primary_fn=lambda: self.tts_engine.generate_audio(text=text, engine_name=tts_engine_name),
                fallback_fn=lambda: self.tts_engine.generate_audio(text=text, engine_name="google"),
                logger=self.logger,
                context="audio_processor_speech_only"
            )

            if not output_file or not os.path.exists(output_file):
                return {
                    "status": "error",
                    "message": "TTS motorunda ses üretilemedi.",
                }

            with open(output_file, "rb") as audio_file:
                encoded_audio = base64.b64encode(audio_file.read()).decode("utf-8")

            # Cleanup output file
            asyncio.create_task(asyncio.to_thread(os.remove, output_file))

            return {
                "status": "success",
                "audio_base64": encoded_audio,
            }

        except Exception as e:
            return handle_exception(
                ERR_ALL_TTS_FAILED,
                e,
                logger=self.logger,
                context="AsyncAudioProcessor.generate_speech_only",
            )

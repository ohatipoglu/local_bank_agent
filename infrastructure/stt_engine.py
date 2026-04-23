"""
Speech-to-Text engine using Faster-Whisper with Turkish language support.
Provides file-based transcription and live microphone listening.
"""

import glob
import os
import time
import uuid

import speech_recognition as sr
from faster_whisper import WhisperModel

from core.config import Config
from core.exceptions import (
    STTError,
    STTModelLoadError,
    STTNoSpeechDetectedError,
)


class FasterWhisperSTTEngine:
    """
    Speech-to-Text engine using Faster-Whisper with Turkish language optimization.

    Features:
    - Domain-specific initial prompts for banking context
    - Dynamic energy threshold for ambient noise adaptation
    - Automatic temporary file cleanup
    - Configurable model size and compute type

    Usage:
        stt = FasterWhisperSTTEngine(logger)
        text = stt.transcribe_file("audio.wav")
    """

    # Default banking context prompt for better recognition
    BANKING_PROMPT = (
        "Bu bir bankacılık görüşmesidir. "
        "Bakiye, havale, EFT, kredi kartı, valör, faiz işlemleri konuşulmaktadır."
    )

    def __init__(
        self,
        logger,
        model_size: str = None,
        device: str = None,
        compute_type: str = None,
    ):
        """
        Initialize STT engine.

        Args:
            logger: Loguru logger instance
            model_size: Whisper model size (default: Config.STT_MODEL_SIZE)
            device: Compute device (default: Config.STT_DEVICE)
            compute_type: Compute precision (default: Config.STT_COMPUTE_TYPE)

        Raises:
            STTModelLoadError: If model fails to load
        """
        self.log = logger
        self.model_size = model_size or Config.STT_MODEL_SIZE
        self.device = device or Config.STT_DEVICE
        self.compute_type = compute_type or Config.STT_COMPUTE_TYPE

        self.log.info(
            f"STT Motoru başlatılıyor... " f"(Model: {self.model_size}, {self.device})"
        )

        try:
            self.model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type,
            )
            self.log.info("Faster-Whisper modeli başarıyla yüklendi.")
        except Exception as e:
            raise STTModelLoadError(f"Whisper modeli yüklenirken hata: {e}") from e

        # Speech recognizer setup
        self.recognizer = sr.Recognizer()
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold = 1.5

        # Microphone instance (created once for performance)
        try:
            self.microphone = sr.Microphone()
            self.log.info("Mikrofon başarıyla başlatıldı.")
        except Exception as e:
            self.log.warning(
                f"Mikrofon başlatılamadı (sadece dosya modu çalışacak): {e}"
            )
            self.microphone = None

        # Cleanup orphaned temp files on startup
        self._cleanup_temp_files()

    def _cleanup_temp_files(self):
        """Remove orphaned temporary audio files."""
        self.log.info("Geçici ses dosyaları temizleniyor...")
        cleaned = 0
        for pattern in ["temp_input_*.wav", "temp_audio_*.wav"]:
            for temp_file in glob.glob(pattern):
                try:
                    os.remove(temp_file)
                    cleaned += 1
                except Exception as e:
                    self.log.warning(f"Geçici dosya silinemedi {temp_file}: {e}")
        if cleaned > 0:
            self.log.debug(f"{cleaned} geçici dosya temizlendi.")

    def listen_and_transcribe(
        self,
        timeout: int = 10,
        phrase_time_limit: int = 15,
        initial_prompt: str = None,
    ) -> str:
        """
        Listen to microphone and transcribe speech with silence detection.

        Args:
            timeout: Seconds to wait for speech to start
            phrase_time_limit: Maximum seconds of speech to record
            initial_prompt: Context prompt for better recognition

        Returns:
            Transcribed text (empty string if no speech detected)

        Raises:
            STTNoSpeechDetectedError: If no speech detected within timeout
        """
        if not self.microphone:
            raise STTError("Mikrofon mevcut değil.")

        prompt = initial_prompt or self.BANKING_PROMPT

        with self.microphone as source:
            self.log.info("Ortam gürültüsü kalibre ediliyor... Lütfen bekleyin.")
            self.recognizer.adjust_for_ambient_noise(source, duration=2)
            self.log.info(
                "Dinliyorum... (Konuşmayı bitirdiğinizde otomatik algılanacak)"
            )

            try:
                audio_data = self.recognizer.listen(
                    source,
                    timeout=timeout,
                    phrase_time_limit=phrase_time_limit,
                )
                self.log.debug("Ses kaydı tamamlandı, metne çevriliyor...")

                # Save to temp file for Whisper
                temp_audio_path = f"temp_input_{uuid.uuid4().hex}.wav"
                with open(temp_audio_path, "wb") as f:
                    f.write(audio_data.get_wav_data())

                # Transcribe
                transcription = self.transcribe_file(temp_audio_path, prompt)

                # Cleanup temp file
                try:
                    if os.path.exists(temp_audio_path):
                        os.remove(temp_audio_path)
                except OSError as e:
                    self.log.error(f"Geçici dosya silinemedi {temp_audio_path}: {e}")

                return transcription

            except sr.WaitTimeoutError:
                raise STTNoSpeechDetectedError(
                    "Zaman aşımı: Herhangi bir ses algılanmadı."
                )
            except Exception as e:
                raise STTError(f"STT Dinleme Hatası: {e}") from e

    def transcribe_file(
        self,
        file_path: str,
        initial_prompt: str = None,
    ) -> str:
        """
        Transcribe an audio file to text.

        Args:
            file_path: Path to WAV/audio file
            initial_prompt: Context prompt for better recognition

        Returns:
            Transcribed text (empty string on failure)
        """
        start_time = time.time()
        prompt = initial_prompt or self.BANKING_PROMPT

        try:
            segments, info = self.model.transcribe(
                file_path,
                beam_size=5,
                language=Config.STT_LANGUAGE,
                condition_on_previous_text=False,
                initial_prompt=prompt,
            )

            transcription = " ".join([segment.text for segment in segments]).strip()

            elapsed = time.time() - start_time
            self.log.info(
                f"STT Tamamlandı. Süre: {elapsed:.2f}sn | " f"Sonuç: '{transcription}'"
            )
            return transcription

        except Exception as e:
            self.log.error(f"STT Dosya Çeviri Hatası: {e}")
            return ""

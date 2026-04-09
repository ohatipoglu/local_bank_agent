"""
Text-to-Speech engines with fallback chain support.
Provides Google Cloud TTS (primary) and Piper TTS (offline fallback).
"""
import os
import subprocess
import time
import re
import uuid
import yaml
import threading
import shutil
from typing import Optional

from google.cloud import texttospeech
from google.api_core.exceptions import RetryError, ServiceUnavailable, GoogleAPIError

from core.exceptions import TTSError, TTSClientNotInitializedError
from core.config import Config
from core.logger import get_correlated_logger


def play_audio_async(file_path: str, logger):
    """
    Play audio file asynchronously via background thread.
    Automatically deletes the file after playback.
    
    Args:
        file_path: Path to WAV file
        logger: Loguru logger instance
    """
    def _play():
        try:
            import winsound
            logger.debug(f"Ses oynatılıyor: {file_path}")
            winsound.PlaySound(file_path, winsound.SND_FILENAME)
            logger.debug("Ses oynatma bitti.")
        except ImportError:
            logger.warning("winsound modülü bulunamadı. (Windows dışı ortam?)")
        except Exception as e:
            logger.error(f"Ses oynatma hatası: {e}")
        finally:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except OSError:
                pass

    thread = threading.Thread(target=_play, daemon=True)
    thread.start()


class TTSEngineBase:
    """
    Base class for TTS engines with text preprocessing.
    
    Features:
    - YAML-configurable text replacements for TTS normalization
    - Common abbreviation expansion (EFT -> "e fe te", etc.)
    """

    def __init__(self, logger):
        self.logger = logger
        self._load_replacements()

    def _load_replacements(self):
        """Load text replacement rules from prompts.yaml."""
        yaml_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "application",
            "prompts.yaml"
        )
        self.replacements = {}
        try:
            if os.path.exists(yaml_path):
                with open(yaml_path, 'r', encoding='utf-8') as file:
                    data = yaml.safe_load(file)
                    self.replacements = data.get("tts_replacements", {})
        except Exception as e:
            self.logger.warning(
                f"TTS kısaltmaları okunamadı, varsayılanlar kullanılacak: {e}"
            )

        # Fallback defaults if YAML not found
        if not self.replacements:
            self.replacements = {
                r'\bSPK\b': 'se pe ka',
                r'\bTL\b': 'Türk Lirası',
                r'\bT.C.\b': 'Te Ce',
                r'\bTC\b': 'Te Ce',
                r'\bATM\b': 'a te me',
                r'\bEFT\b': 'e fe te',
                r'\bFAST\b': 'fast',
                r'\bKDV\b': 'ka de ve',
                r'\bIBAN\b': 'ay ban',
                r'\bMBS\b': 'me be se',
                r'\bT\+1\b': 'te artı bir',
                r'\bT\+2\b': 'te artı iki',
            }

    def _preprocess_text(self, text: str) -> str:
        """
        Normalize text for TTS by expanding abbreviations.
        
        Args:
            text: Raw text
            
        Returns:
            Text with abbreviations expanded for proper pronunciation
        """
        processed_text = text
        for pattern, replacement in self.replacements.items():
            processed_text = re.sub(pattern, replacement, processed_text)
        return processed_text

    def generate_audio(self, text: str) -> Optional[str]:
        """
        Generate audio from text.
        
        Args:
            text: Input text
            
        Returns:
            Path to generated WAV file, or None on failure
        """
        raise NotImplementedError


class PiperTTSEngine(TTSEngineBase):
    """
    Offline TTS engine using Piper (ONNX runtime).
    Suitable as fallback when Google Cloud is unavailable.
    """

    def __init__(self, model_path: str, logger):
        """
        Initialize Piper TTS engine.
        
        Args:
            model_path: Path to Piper ONNX model file
            logger: Loguru logger instance
        """
        super().__init__(logger)
        self.model_path = model_path
        self.piper_available = shutil.which("piper") is not None

        if not self.piper_available:
            self.logger.warning(
                "Piper komutu sistem PATH'inde bulunamadı. "
                "Piper TTS kullanılamayacak."
            )

        if not os.path.exists(self.model_path):
            self.logger.error(
                f"TTS Modeli bulunamadı: {self.model_path}"
            )
            self.piper_available = False

    def generate_audio(self, text: str) -> Optional[str]:
        """
        Generate audio using Piper TTS.
        
        Args:
            text: Input text
            
        Returns:
            Path to generated WAV file, or None on failure
        """
        if not self.piper_available:
            self.logger.warning("Piper kullanılabilir değil, ses üretilemedi.")
            return None

        start_time = time.time()
        self.logger.debug(f"Piper TTS Orijinal Metin: {text}")

        normalized_text = self._preprocess_text(text)
        output_file = f"piper_output_{uuid.uuid4().hex[:8]}.wav"

        try:
            subprocess.run(
                ['piper', '--model', self.model_path, '--output_file', output_file],
                input=normalized_text.encode('utf-8'),
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

            elapsed = time.time() - start_time
            self.logger.info(
                f"Piper TTS Üretimi Tamamlandı. Süre: {elapsed:.2f}sn"
            )
            return output_file

        except subprocess.CalledProcessError as e:
            self.logger.error(f"Piper işlem hatası: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Piper TTS Hatası: {e}")
            return None

    def speak(self, text: str):
        """Generate and play audio asynchronously."""
        output_file = self.generate_audio(text)
        if output_file:
            play_audio_async(output_file, self.logger)


class GoogleCloudTTSEngine(TTSEngineBase):
    """
    Google Cloud Text-to-Speech engine with WaveNet voices.
    Primary TTS engine with retry logic and timeout handling.
    """

    def __init__(self, logger, max_retries: int = None):
        """
        Initialize Google Cloud TTS engine.
        
        Args:
            logger: Loguru logger instance
            max_retries: Maximum retry attempts on failure (default from Config)
        """
        super().__init__(logger)
        self.max_retries = max_retries or Config.TTS_MAX_RETRIES
        self.client = None

        try:
            self.client = texttospeech.TextToSpeechClient()
            self.voice = texttospeech.VoiceSelectionParams(
                language_code=Config.TTS_LANGUAGE_CODE,
                name=Config.TTS_VOICE_NAME,
            )
            self.audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.LINEAR16,
            )
            self.logger.info(
                f"Google Cloud TTS bağlanıldı. Ses: {Config.TTS_VOICE_NAME}"
            )
        except Exception as e:
            self.client = None
            self.logger.error(f"Google Cloud TTS Başlatma Hatası: {e}")

    def generate_audio(self, text: str, max_retries: int = None) -> Optional[str]:
        """
        Generate audio using Google Cloud TTS with retry logic.
        
        Args:
            text: Input text
            max_retries: Override max retries for this call
            
        Returns:
            Path to generated WAV file, or None on failure
        """
        if not self.client:
            self.logger.error("Google TTS istemcisi başlatılamadı.")
            return None

        retries = max_retries if max_retries is not None else self.max_retries
        normalized_text = self._preprocess_text(text)
        output_file = f"google_output_{uuid.uuid4().hex[:8]}.wav"
        synthesis_input = texttospeech.SynthesisInput(text=normalized_text)

        for attempt in range(retries + 1):
            try:
                start_time = time.time()
                response = self.client.synthesize_speech(
                    input=synthesis_input,
                    voice=self.voice,
                    audio_config=self.audio_config,
                    timeout=Config.TTS_TIMEOUT_SECONDS,
                )

                with open(output_file, "wb") as out:
                    out.write(response.audio_content)

                elapsed = time.time() - start_time
                self.logger.info(
                    f"Google TTS Üretimi Tamamlandı. "
                    f"(Deneme {attempt + 1}/{retries + 1}) "
                    f"Süre: {elapsed:.2f}sn"
                )
                return output_file

            except (RetryError, ServiceUnavailable, GoogleAPIError) as e:
                self.logger.warning(
                    f"Google TTS Ağ Hatası (Deneme {attempt + 1}/{retries + 1}): {e}"
                )
                if attempt < retries:
                    time.sleep(2.0)
                else:
                    self.logger.error(
                        "Google TTS Maksimum deneme sayısına ulaştı."
                    )
                    return None

            except Exception as e:
                self.logger.error(f"Google Cloud Beklenmeyen TTS Hatası: {e}")
                return None

    def speak(self, text: str):
        """Generate and play audio asynchronously."""
        output_file = self.generate_audio(text)
        if output_file:
            play_audio_async(output_file, self.logger)


class TTSFallbackChain:
    """
    TTS engine chain with automatic fallback.
    
    Tries engines in order until one succeeds:
    1. Google Cloud TTS (primary, highest quality)
    2. Piper TTS (offline fallback)
    
    Usage:
        tts_chain = TTSFallbackChain(logger, enable_piper=True)
        audio_file = tts_chain.generate_audio("Merhaba dünya")
    """

    def __init__(self, logger, enable_piper: bool = None):
        """
        Initialize TTS fallback chain.
        
        Args:
            logger: Loguru logger instance
            enable_piper: Whether to enable Piper as fallback (default from Config)
        """
        self.logger = logger
        self.engines = []

        # Primary: Google Cloud TTS
        google_engine = GoogleCloudTTSEngine(logger)
        if google_engine.client:
            self.engines.append(("Google Cloud TTS", google_engine))
        else:
            logger.warning("Google Cloud TTS kullanılamıyor.")

        # Fallback: Piper TTS
        use_piper = enable_piper if enable_piper is not None else Config.TTS_ENABLE_PIPER_FALLBACK
        if use_piper and os.path.exists(Config.PIPER_MODEL_PATH):
            piper_engine = PiperTTSEngine(Config.PIPER_MODEL_PATH, logger)
            if piper_engine.piper_available:
                self.engines.append(("Piper TTS", piper_engine))
            else:
                logger.warning("Piper TTS kullanılamıyor.")
        elif use_piper:
            logger.warning(
                f"Piper model bulunamadı: {Config.PIPER_MODEL_PATH}"
            )

        if not self.engines:
            logger.error("Hiçbir TTS motoru kullanılamıyor!")

        self.logger.info(
            f"TTS Fallback Chain hazır. "
            f"Motorlar: {', '.join(name for name, _ in self.engines)}"
        )

    def generate_audio(self, text: str) -> Optional[str]:
        """
        Generate audio by trying each engine in order.
        
        Args:
            text: Input text
            
        Returns:
            Path to generated audio file, or None if all engines failed
        """
        for name, engine in self.engines:
            try:
                self.logger.debug(f"TTS deneniyor: {name}")
                output_file = engine.generate_audio(text)
                if output_file and os.path.exists(output_file):
                    self.logger.info(f"TTS başarılı: {name}")
                    return output_file
                else:
                    self.logger.warning(f"{name} başarısız, deneniyor...")
            except Exception as e:
                self.logger.error(f"{name} hatası: {e}")

        self.logger.error("Tüm TTS motorları başarısız oldu.")
        return None

    def speak(self, text: str):
        """Generate and play audio using the fallback chain."""
        output_file = self.generate_audio(text)
        if output_file:
            play_audio_async(output_file, self.logger)
        else:
            self.logger.error("Ses üretilemedi.")

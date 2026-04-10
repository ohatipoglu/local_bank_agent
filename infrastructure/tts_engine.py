"""
Text-to-Speech engines with fallback chain support.
Provides Google Cloud TTS (primary), Piper TTS (offline fallback),
Coqui XTTS v2 (local, high-quality Turkish with GPU support),
and Edge TTS (Microsoft Edge online TTS, free, no API key).
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


class CoquiTTSEngine(TTSEngineBase):
    """
    Local TTS engine using Coqui XTTS v2 via direct API.

    This engine uses the TTS library directly in the coqui_env conda environment.
    The main app uses subprocess to call this engine to avoid dependency conflicts.

    Features:
    - Multilingual (16+ languages including Turkish)
    - Zero-shot voice cloning from 6-second reference
    - Fully offline, no API calls
    - High-quality neural speech synthesis

    Setup:
    - Requires coqui_env conda environment with TTS installed
    - See coqui_tts_server.py and coqui_tts_config.json
    - Reference voice audio at models/coqui_reference.wav
    """

    def __init__(self, logger, conda_env: str = "coqui_env"):
        """
        Initialize Coqui XTTS v2 engine via subprocess to coqui_env.

        Args:
            logger: Loguru logger instance
            conda_env: Conda environment name where TTS is installed
        """
        super().__init__(logger)
        self.conda_env = conda_env
        self.coqui_available = False

        # Find paths
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.server_script = os.path.join(project_root, "coqui_tts_server.py")

        # Validate speaker_wav from config
        self.speaker_wav = None
        if Config.COQUI_SPEAKER_WAV and os.path.exists(Config.COQUI_SPEAKER_WAV):
            self.speaker_wav = Config.COQUI_SPEAKER_WAV
        elif os.path.exists(Config.COQUI_VOICE_REF_AUDIO):
            self.speaker_wav = Config.COQUI_VOICE_REF_AUDIO
            self.logger.info(f"Using reference voice: {self.speaker_wav}")

        # Check if coqui_env exists and server script is available
        try:
            # Check conda env exists
            result = subprocess.run(
                ["conda", "env", "list"],
                capture_output=True, text=True, timeout=10
            )
            if self.conda_env in result.stdout:
                if os.path.exists(self.server_script):
                    self.coqui_available = True
                    self.logger.info(
                        f"Coqui XTTS: Ready (env: {self.conda_env})"
                    )
                else:
                    self.logger.error(f"Coqui server script not found: {self.server_script}")
            else:
                self.logger.error(f"Conda environment '{self.conda_env}' not found.")
        except Exception as e:
            self.logger.error(f"Coqui XTTS initialization error: {e}")

    def generate_audio(self, text: str) -> Optional[str]:
        """
        Generate audio using Coqui XTTS v2 via subprocess to coqui_env.

        Args:
            text: Input text

        Returns:
            Path to generated WAV file, or None on failure
        """
        if not self.coqui_available:
            self.logger.warning("Coqui XTTS not available, skipping.")
            return None

        start_time = time.time()
        self.logger.debug(f"Coqui XTTS Original Text: {text}")

        normalized_text = self._preprocess_text(text)
        output_file = f"coqui_output_{uuid.uuid4().hex[:8]}.wav"

        # Build command - use conda run to activate environment and execute script
        cmd = [
            "conda", "run", "-n", self.conda_env,
            "python", self.server_script,
            normalized_text, output_file
        ]

        # Add speaker_wav if available
        if self.speaker_wav:
            cmd.append(self.speaker_wav)

        try:
            self.logger.debug(f"Coqui command: {' '.join(cmd[:6])}...")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,  # 2 minutes max for synthesis
                cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            )

            # Log stderr (Coqui prints status there)
            if result.stderr:
                for line in result.stderr.strip().split('\n'):
                    if line.strip():
                        self.logger.debug(f"Coqui stderr: {line.strip()}")

            if result.returncode == 0 and os.path.exists(output_file):
                elapsed = time.time() - start_time
                file_size = os.path.getsize(output_file)
                self.logger.info(
                    f"Coqui XTTS synthesis complete. Time: {elapsed:.2f}s, "
                    f"Size: {file_size/1024:.1f} KB"
                )
                return output_file
            else:
                self.logger.error(
                    f"Coqui XTTS failed (exit code {result.returncode}). "
                    f"Check coqui_tts_server.py and {self.conda_env}."
                )
                return None

        except subprocess.TimeoutExpired:
            self.logger.error("Coqui XTTS: Synthesis timed out (120s limit)")
            return None
        except Exception as e:
            self.logger.error(f"Coqui XTTS Generation Error: {e}")
            return None

    def speak(self, text: str):
        """Generate and play audio asynchronously."""
        output_file = self.generate_audio(text)
        if output_file:
            play_audio_async(output_file, self.logger)


class EdgeTTSEngine(TTSEngineBase):
    """
    Online TTS engine using Microsoft Edge TTS (free, no API key).
    High-quality neural voices, excellent Turkish support.

    Features:
    - Free, no API key required
    - High-quality neural voices (tr-TR-AhmetNeural, tr-TR-EmelNeural)
    - Fast inference (cloud-based)
    - Requires internet connection
    """

    def __init__(self, logger, voice: str = None):
        """
        Initialize Edge TTS engine.

        Args:
            logger: Loguru logger instance
            voice: Edge TTS voice name (default from Config)
        """
        super().__init__(logger)
        self.voice = voice or Config.EDGE_TTS_VOICE
        self.edge_available = False

        try:
            import edge_tts
            self.edge_available = True
            self.logger.info(f"Edge TTS initialized. Voice: {self.voice}")
        except ImportError:
            self.logger.error(
                "edge-tts package not installed. Run: pip install edge-tts"
            )
            self.edge_available = False

    def generate_audio(self, text: str) -> Optional[str]:
        """
        Generate audio using Edge TTS.

        Args:
            text: Input text

        Returns:
            Path to generated WAV file, or None on failure
        """
        if not self.edge_available:
            self.logger.warning("Edge TTS not available, skipping.")
            return None

        import edge_tts
        import asyncio

        start_time = time.time()
        self.logger.debug(f"Edge TTS Orijinal Metin: {text}")

        normalized_text = self._preprocess_text(text)
        output_file = f"edge_output_{uuid.uuid4().hex[:8]}.wav"

        try:
            communicate = edge_tts.Communicate(normalized_text, self.voice)
            # edge_tts outputs to mp3
            mp3_file = output_file.replace(".wav", ".mp3")

            async def _save():
                await communicate.save(mp3_file)

            asyncio.run(_save())

            # Convert MP3 to WAV using available libraries
            if os.path.exists(mp3_file):
                try:
                    # Try pydub first (needs ffmpeg)
                    try:
                        from pydub import AudioSegment
                        audio = AudioSegment.from_mp3(mp3_file)
                        audio.export(output_file, format="wav")
                        if os.path.exists(mp3_file):
                            os.remove(mp3_file)
                    except (ImportError, FileNotFoundError):
                        # Fallback: just rename mp3 as wav (browser can play mp3)
                        import shutil
                        shutil.move(mp3_file, output_file)
                        self.logger.warning(
                            "pydub/ffmpeg not available. Output is MP3 format. "
                            "Install pydub for proper WAV conversion: pip install pydub"
                        )

                    elapsed = time.time() - start_time
                    self.logger.info(
                        f"Edge TTS Üretimi Tamamlandı. Süre: {elapsed:.2f}sn"
                    )
                    return output_file
                except Exception as e:
                    self.logger.error(f"Edge TTS format conversion error: {e}")
                    return None
            else:
                self.logger.error("Edge TTS: MP3 file not created.")
                return None

        except Exception as e:
            self.logger.error(f"Edge TTS Generation Error: {e}")
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


class TTSEngineRouter:
    """
    TTS engine router with selectable engines and automatic fallback.

    Supports four engines:
    1. Google Cloud TTS (primary, cloud-based, WaveNet voices)
    2. Piper TTS (offline fallback, ONNX runtime)
    3. Coqui XTTS v2 (local, high-quality Turkish, GPU-accelerated)
    4. Edge TTS (Microsoft Edge online TTS, free, no API key)

    Usage:
        tts = TTSEngineRouter(logger)
        audio_file = tts.generate_audio("Merhaba dünya", engine_name="edge")
        # Or use the default engine
        audio_file = tts.generate_audio("Merhaba dünya")
    """

    # Engine name constants
    ENGINE_GOOGLE = "google"
    ENGINE_PIPER = "piper"
    ENGINE_COQUI = "coqui"
    ENGINE_EDGE = "edge"

    def __init__(self, logger, enable_piper: bool = None,
                 enable_coqui: bool = None, enable_edge: bool = None):
        """
        Initialize TTS engine router.

        Args:
            logger: Loguru logger instance
            enable_piper: Whether to enable Piper (default from Config)
            enable_coqui: Whether to enable Coqui (default from Config)
            enable_edge: Whether to enable Edge TTS (default from Config)
        """
        self.logger = logger
        self.engines = {}  # name -> engine instance
        self.default_engine_name = None

        # 1. Google Cloud TTS
        try:
            google_engine = GoogleCloudTTSEngine(logger)
            if google_engine.client:
                self.engines[self.ENGINE_GOOGLE] = google_engine
                self.default_engine_name = self.ENGINE_GOOGLE
                logger.info("Google Cloud TTS eklendi.")
            else:
                logger.warning("Google Cloud TTS kullanılamıyor.")
        except Exception as e:
            logger.error(f"Google Cloud TTS başlatma hatası: {e}")

        # 2. Piper TTS
        use_piper = enable_piper if enable_piper is not None else Config.TTS_ENABLE_PIPER_FALLBACK
        if use_piper:
            try:
                if os.path.exists(Config.PIPER_MODEL_PATH):
                    piper_engine = PiperTTSEngine(Config.PIPER_MODEL_PATH, logger)
                    if piper_engine.piper_available:
                        self.engines[self.ENGINE_PIPER] = piper_engine
                        if not self.default_engine_name:
                            self.default_engine_name = self.ENGINE_PIPER
                        logger.info("Piper TTS eklendi.")
                    else:
                        logger.warning("Piper TTS binary bulunamadı.")
                else:
                    logger.warning(f"Piper model bulunamadı: {Config.PIPER_MODEL_PATH}")
            except Exception as e:
                logger.error(f"Piper TTS başlatma hatası: {e}")

        # 3. Coqui XTTS v2
        use_coqui = enable_coqui if enable_coqui is not None else Config.TTS_ENABLE_COQUI_FALLBACK
        if use_coqui:
            try:
                coqui_engine = CoquiTTSEngine(logger)
                if coqui_engine.coqui_available:
                    self.engines[self.ENGINE_COQUI] = coqui_engine
                    if not self.default_engine_name:
                        self.default_engine_name = self.ENGINE_COQUI
                    logger.info("Coqui XTTS v2 eklendi.")
                else:
                    logger.warning("Coqui XTTS başlatılamadı.")
            except Exception as e:
                logger.error(f"Coqui XTTS başlatma hatası: {e}")

        # 4. Edge TTS
        use_edge = enable_edge if enable_edge is not None else Config.TTS_ENABLE_EDGE_FALLBACK
        if use_edge:
            try:
                edge_engine = EdgeTTSEngine(logger)
                if edge_engine.edge_available:
                    self.engines[self.ENGINE_EDGE] = edge_engine
                    if not self.default_engine_name:
                        self.default_engine_name = self.ENGINE_EDGE
                    logger.info("Edge TTS eklendi.")
                else:
                    logger.warning("Edge TTS kullanılamıyor.")
            except Exception as e:
                logger.error(f"Edge TTS başlatma hatası: {e}")

        if not self.engines:
            logger.error("Hiçbir TTS motoru kullanılamıyor!")

        self.logger.info(
            f"TTS Engine Router hazır. "
            f"Motorlar: {', '.join(self.engines.keys())} | "
            f"Varsayılan: {self.default_engine_name}"
        )

    def get_available_engines(self) -> list[dict]:
        """
        Return list of available engines with metadata for frontend display.

        Returns:
            List of dicts with engine info: name, display_name, type, quality, offline
        """
        engine_info = {
            self.ENGINE_GOOGLE: {
                "name": self.ENGINE_GOOGLE,
                "display_name": "Google Cloud",
                "description": "WaveNet ses, bulut tabanlı",
                "quality": "Yüksek",
                "offline": False,
                "type": "cloud",
            },
            self.ENGINE_PIPER: {
                "name": self.ENGINE_PIPER,
                "display_name": "Piper",
                "description": "Çevrimdışı, hafif",
                "quality": "Orta",
                "offline": True,
                "type": "local",
            },
            self.ENGINE_COQUI: {
                "name": self.ENGINE_COQUI,
                "display_name": "Coqui XTTS",
                "description": "Yerel, yüksek kalite, GPU destekli",
                "quality": "Çok Yüksek",
                "offline": True,
                "type": "local",
            },
            self.ENGINE_EDGE: {
                "name": self.ENGINE_EDGE,
                "display_name": "Edge TTS",
                "description": "Microsoft Neural, ücretsiz",
                "quality": "Yüksek",
                "offline": False,
                "type": "cloud",
            },
        }

        available = []
        for eng_name in self.engines:
            info = engine_info.get(eng_name, {}).copy()
            info["available"] = True
            available.append(info)

        return available

    def generate_audio(self, text: str, engine_name: str = None) -> Optional[str]:
        """
        Generate audio using specified engine, or default if none specified.

        Args:
            text: Input text
            engine_name: Engine to use (google, piper, coqui, edge). Uses default if None.

        Returns:
            Path to generated audio file, or None on failure
        """
        # If specific engine requested
        if engine_name:
            if engine_name not in self.engines:
                self.logger.warning(
                    f"TTS motoru '{engine_name}' bulunamadı. "
                    f"Mevcut: {list(self.engines.keys())}"
                )
                # Fallback to default
                if not self.default_engine_name:
                    self.logger.error("Kullanılabilir TTS motoru yok.")
                    return None
                self.logger.info(f"Varsayılana geçiliyor: {self.default_engine_name}")
                engine_name = self.default_engine_name
        else:
            # Use default engine
            if not self.default_engine_name:
                self.logger.error("Kullanılabilir TTS motoru yok.")
                return None
            engine_name = self.default_engine_name

        engine = self.engines.get(engine_name)
        if not engine:
            self.logger.error(f"TTS motoru '{engine_name}' başlatılamadı.")
            return None

        try:
            self.logger.debug(f"TTS deneniyor: {engine_name}")
            output_file = engine.generate_audio(text)
            if output_file and os.path.exists(output_file):
                self.logger.info(f"TTS başarılı: {engine_name}")
                return output_file
            else:
                self.logger.warning(f"{engine_name} başarısız, fallback deneniyor...")
                # Try fallback to other engines
                return self._try_fallback(text, skip_engine=engine_name)
        except Exception as e:
            self.logger.error(f"{engine_name} hatası: {e}")
            return self._try_fallback(text, skip_engine=engine_name)

    def _try_fallback(self, text: str, skip_engine: str) -> Optional[str]:
        """Try remaining engines if primary fails."""
        for name, engine in self.engines.items():
            if name == skip_engine:
                continue
            try:
                self.logger.debug(f"TTS fallback deneniyor: {name}")
                output_file = engine.generate_audio(text)
                if output_file and os.path.exists(output_file):
                    self.logger.info(f"TTS fallback başarılı: {name}")
                    return output_file
            except Exception as e:
                self.logger.error(f"{name} fallback hatası: {e}")

        self.logger.error("Tüm TTS motorları başarısız oldu.")
        return None

    def speak(self, text: str, engine_name: str = None):
        """Generate and play audio using the router."""
        output_file = self.generate_audio(text, engine_name)
        if output_file:
            play_audio_async(output_file, self.logger)
        else:
            self.logger.error("Ses üretilemedi.")


# Keep the old class name for backward compatibility
class TTSFallbackChain(TTSEngineRouter):
    """
    Deprecated: Use TTSEngineRouter instead.
    Kept for backward compatibility.
    """
    pass

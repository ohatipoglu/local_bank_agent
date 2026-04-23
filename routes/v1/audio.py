"""
Audio processing endpoints v1.
"""

import os
import uuid
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from core.config import Config
from core.error_handler import (
    ERR_INTERNAL_SERVER_ERROR,
    create_error_response,
    handle_exception,
)
from core.logger import get_correlated_logger, set_correlation_id
from core.security import sanitize_input, validate_audio_upload
from domain.interfaces import IAccountService
from infrastructure.stt_engine import FasterWhisperSTTEngine
from infrastructure.tts_engine import TTSEngineRouter
from services.audio_processor import AsyncAudioProcessor

router = APIRouter()
log = get_correlated_logger()


# Global processor instance (initialized on first use)
_audio_processor: Optional[AsyncAudioProcessor] = None
_stt_engine: Optional[FasterWhisperSTTEngine] = None
_tts_engine: Optional[TTSEngineRouter] = None
_agent = None


def _get_processor():
    """Lazy initialization of audio processor."""
    global _audio_processor, _stt_engine, _tts_engine, _agent

    if _audio_processor is None:
        # Initialize STT
        _stt_engine = FasterWhisperSTTEngine(
            logger=log,
            model_size=Config.STT_MODEL_SIZE,
            device=Config.STT_DEVICE,
            compute_type=Config.STT_COMPUTE_TYPE,
        )

        # Initialize TTS
        _tts_engine = TTSEngineRouter(logger=log)

        # Initialize Agent
        from application.langchain_agent import LangChainBankAgent
        from infrastructure.mock_services import MockAccountService

        account_service = MockAccountService()
        _agent = LangChainBankAgent(
            account_service=account_service,
            model_name=Config.LLM_MODEL_NAME,
            logger=log,
            max_tokens=Config.LLM_MAX_TOKENS,
        )

        # Create processor
        _audio_processor = AsyncAudioProcessor(
            stt_engine=_stt_engine,
            agent=_agent,
            tts_engine=_tts_engine,
            logger=log,
        )

    return _audio_processor


@router.post("/process")
async def process_audio(
    audio: UploadFile = File(...),
    strictness: int = Form(3),
    model_name: str = Form(None),
    session_id: str = Form(None),
    customer_id: str = Form(None),
    tts_engine: str = Form(None),
):
    """
    Process voice input through full STT -> Agent -> TTS pipeline (v1).

    Accepts audio file, transcribes it, processes through AI agent
    with banking tools, generates speech response.

    Returns JSON with transcription, AI response, and base64-encoded audio.
    """
    # Generate correlation ID for request tracing
    corr_id = str(uuid.uuid4())[:12]
    set_correlation_id(corr_id)

    # Resolve defaults
    if not model_name:
        model_name = Config.LLM_MODEL_NAME
    if not session_id:
        session_id = "default_session"

    # Validate audio upload
    is_valid, error_msg = validate_audio_upload(audio, audio.filename)
    if not is_valid:
        log.warning(f"Audio validation failed: {error_msg}")
        return JSONResponse(
            status_code=400,
            content=create_error_response(
                type("ProcessingError", (), {
                    "category": "AUDIO_VALIDATION_ERROR",
                    "code": "INVALID_AUDIO_FILE",
                    "message_tr": error_msg,
                    "message_en": error_msg,
                    "retryable": False,
                })()
            ).get("error"),
        )

    # Save uploaded audio temporarily
    temp_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
    os.makedirs(temp_dir, exist_ok=True)

    temp_audio_path = os.path.join(
        temp_dir, f"temp_audio_{uuid.uuid4().hex[:8]}_{audio.filename}"
    )

    try:
        # Read audio content
        content = await audio.read()
        with open(temp_audio_path, "wb") as f:
            f.write(content)

        # Get processor
        processor = _get_processor()

        # Process audio asynchronously
        result = await processor.process(
            audio_path=temp_audio_path,
            session_id=session_id,
            customer_id=customer_id,
            strictness_level=strictness,
            model_name=model_name,
            tts_engine_name=tts_engine,
        )

        return result

    except Exception as e:
        log.error(f"Audio processing error: {e}")
        return JSONResponse(
            status_code=500,
            content=handle_exception(
                ERR_INTERNAL_SERVER_ERROR, e, logger=log, context="process_audio_v1"
            ).get("error"),
        )

    finally:
        # Cleanup temp file
        try:
            if os.path.exists(temp_audio_path):
                os.remove(temp_audio_path)
        except OSError:
            pass


@router.post("/transcribe")
async def transcribe_audio(
    audio: UploadFile = File(...),
    language: str = Form("tr"),
):
    """
    Transcribe audio to text without agent processing or TTS (v1).

    Args:
        audio: Audio file to transcribe
        language: Language code (default: tr)

    Returns:
        Transcription result
    """
    corr_id = str(uuid.uuid4())[:12]
    set_correlation_id(corr_id)

    # Validate audio upload
    is_valid, error_msg = validate_audio_upload(audio, audio.filename)
    if not is_valid:
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": error_msg},
        )

    # Save temporarily
    temp_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
    os.makedirs(temp_dir, exist_ok=True)

    temp_audio_path = os.path.join(
        temp_dir, f"temp_audio_{uuid.uuid4().hex[:8]}_{audio.filename}"
    )

    try:
        content = await audio.read()
        with open(temp_audio_path, "wb") as f:
            f.write(content)

        # Get processor
        processor = _get_processor()

        # Transcribe only
        result = await processor.transcribe_only(
            audio_path=temp_audio_path,
            language=language,
        )

        return result

    except Exception as e:
        log.error(f"Transcription error: {e}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )

    finally:
        # Cleanup
        try:
            if os.path.exists(temp_audio_path):
                os.remove(temp_audio_path)
        except OSError:
            pass


@router.post("/synthesize")
async def synthesize_speech(
    text: str = Form(...),
    tts_engine: str = Form(None),
):
    """
    Generate speech from text without STT or agent processing (v1).

    Args:
        text: Text to synthesize
        tts_engine: TTS engine to use (google, piper, coqui, edge)

    Returns:
        Base64-encoded audio
    """
    corr_id = str(uuid.uuid4())[:12]
    set_correlation_id(corr_id)

    # Sanitize input
    text = sanitize_input(text, max_length=1000)
    if not text:
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": "Metin gereklidir."},
        )

    try:
        # Get processor
        processor = _get_processor()

        # Synthesize only
        result = await processor.generate_speech_only(
            text=text,
            tts_engine_name=tts_engine,
        )

        return result

    except Exception as e:
        log.error(f"TTS error: {e}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )

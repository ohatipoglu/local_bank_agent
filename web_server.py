"""
FastAPI web server for Local Bank AI Agent.
Provides voice-enabled banking assistant interface with streaming support.

Endpoints:
    GET  /               - Main web UI
    GET  /logs           - Log monitoring dashboard
    GET  /api/models     - List available Ollama models
    GET  /api/logs       - Application logs (JSON)
    GET  /api/health     - Health check
    GET  /api/session/stats - Session statistics
    GET  /events         - Server-Sent Events for real-time status
    POST /process_audio  - Process voice input (STT -> Agent -> TTS)
    POST /api/auth       - Authenticate customer by ID number
"""
import os
import warnings
import shutil
import base64
import uuid
import json
import asyncio
import httpx
import sqlite3
from typing import Optional
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, File, UploadFile, Form, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.concurrency import run_in_threadpool

# Load environment variables from .env file (must be before Config import)
try:
    from dotenv import load_dotenv
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(env_path):
        load_dotenv(env_path)
        print(f"✅ Loaded environment variables from: {env_path}")
    else:
        print("⚠️  .env file not found, using system environment variables")
except ImportError:
    print("⚠️  python-dotenv not installed, using system environment variables")

# Suppress noisy warnings
warnings.filterwarnings("ignore", category=FutureWarning)

# Configuration (must be imported early for env vars)
from core.config import Config
from core.logger import get_correlated_logger, set_correlation_id, get_correlation_id
from core.exceptions import (
    STTError,
    STTNoSpeechDetectedError,
    TTSError,
    AgentError,
    SessionError,
    AuthenticationError,
)
from core.security import SecurityMiddleware, RateLimiter, validate_audio_upload
from core.session_manager import session_manager
from core.agent_cache import agent_cache
from infrastructure.mock_services import MockAccountService, MockAuthService
from infrastructure.tts_engine import TTSFallbackChain, TTSEngineRouter
from infrastructure.stt_engine import FasterWhisperSTTEngine
from application.langchain_agent import LangChainBankAgent

# Google credentials setup
if Config.GOOGLE_APPLICATION_CREDENTIALS:
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = Config.GOOGLE_APPLICATION_CREDENTIALS

current_dir = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------------------
# Lifespan events (startup/shutdown)
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    # Startup
    Config.print_summary()
    app.state.log.info("🚀 Local Bank AI Agent başlatılıyor...")

    yield

    # Shutdown
    app.state.log.info("👋 Local Bank AI Agent kapatılıyor...")
    agent_cache.clear()

# ---------------------------------------------------------------------------
# App initialization
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Local Bank AI Agent",
    description="Voice-enabled AI banking assistant with Ollama integration",
    version="2.0.0",
    lifespan=lifespan,
)

# Security middleware (rate limiting, input validation)
rate_limiter = RateLimiter(
    max_requests=Config.RATE_LIMIT_REQUESTS,
    window_seconds=Config.RATE_LIMIT_WINDOW_SECONDS,
)
app.add_middleware(SecurityMiddleware, rate_limiter=rate_limiter)

# Templates and static files
templates_dir = os.path.join(current_dir, "templates")
templates = Jinja2Templates(directory=templates_dir)

static_dir = os.path.join(current_dir, "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Logger
log = get_correlated_logger()
app.state.log = log  # Make available to lifespan

# ---------------------------------------------------------------------------
# Service initialization
# ---------------------------------------------------------------------------
log.info("Servisler başlatılıyor...")

account_service = MockAccountService()
auth_service = MockAuthService()

# TTS: Use engine router (Google Cloud -> Piper -> Coqui XTTS)
tts_engine = TTSEngineRouter(logger=log)

# STT
log.info("Whisper modeli yükleniyor...")
stt_engine = FasterWhisperSTTEngine(
    logger=log,
    model_size=Config.STT_MODEL_SIZE,
    device=Config.STT_DEVICE,
    compute_type=Config.STT_COMPUTE_TYPE,
)

log.info("Tüm servisler başarıyla başlatıldı.")


# ---------------------------------------------------------------------------
# Agent factory (thread-safe cache)
# ---------------------------------------------------------------------------
def _create_agent_factory(model_name: str):
    """
    Create a factory function for agent cache.
    
    Args:
        model_name: Ollama model name
        
    Returns:
        Callable that creates LangChainBankAgent
    """
    def factory():
        return LangChainBankAgent(
            account_service=account_service,
            model_name=model_name,
            logger=log,
            max_tokens=Config.LLM_MAX_TOKENS,
        )
    return factory


def get_agent_for_model(model_name: str) -> LangChainBankAgent:
    """
    Get or create a cached agent for the specified model.
    
    Args:
        model_name: Ollama model name
        
    Returns:
        LangChainBankAgent instance
    """
    factory = _create_agent_factory(model_name)
    return agent_cache.get_or_create(model_name, factory)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Serve main web UI."""
    return templates.TemplateResponse(request=request, name="index.html")


@app.get("/favicon.ico")
async def favicon():
    """Handle favicon requests."""
    return JSONResponse(content={"message": "No favicon"})


@app.get(
    "/api/models",
    summary="List Ollama Models",
    description="Retrieve list of available Ollama LLM models from local API",
)
async def get_models():
    """
    List available Ollama models dynamically.
    
    Queries Ollama's local API for installed models.
    Falls back to configured default model if Ollama is unreachable.
    """
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{Config.LLM_BASE_URL}/api/tags")
            if response.status_code == 200:
                data = response.json()
                models = [model["name"] for model in data.get("models", [])]
                if not models:
                    models = [Config.LLM_MODEL_NAME]
                return {"status": "success", "models": models}
            else:
                return {
                    "status": "error",
                    "message": "Ollama API'sine ulaşılamadı.",
                    "models": [Config.LLM_MODEL_NAME],
                }
    except Exception as e:
        log.error(f"Ollama Model Listesi Alınamadı: {e}")
        return {
            "status": "error",
            "message": str(e),
            "models": [Config.LLM_MODEL_NAME],
        }


@app.get(
    "/api/tts_engines",
    summary="List TTS Engines",
    description="Retrieve list of available TTS engines with metadata",
)
async def get_tts_engines():
    """
    List available TTS engines for frontend selection.

    Returns engine metadata including:
    - name: internal engine identifier
    - display_name: human-readable name
    - description: short description
    - quality: quality level
    - offline: whether it works offline
    - type: cloud or local
    """
    try:
        engines = tts_engine.get_available_engines()
        return {"status": "success", "engines": engines}
    except Exception as e:
        log.error(f"TTS Engine Listesi Alınamadı: {e}")
        return {
            "status": "error",
            "message": str(e),
            "engines": [],
        }


@app.get("/logs", response_class=HTMLResponse)
async def read_logs(request: Request):
    """Serve log monitoring dashboard."""
    return templates.TemplateResponse(request=request, name="logs.html")


@app.get("/api/logs")
async def get_logs(limit: int = 100):
    """
    Retrieve recent application logs.
    
    Args:
        limit: Maximum number of log entries to return (default: 100)
    """
    from core.logger import LOG_DB_PATH
    try:
        conn = sqlite3.connect(LOG_DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, timestamp, level, session_id, correlation_id,
                   module, function, line, message
            FROM application_logs
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        )
        logs = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return {"status": "success", "logs": logs}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get(
    "/api/health",
    summary="Health Check",
    description="Verify system readiness (STT, TTS, Ollama, services)",
)
async def health_check():
    """
    Comprehensive health check for all system components.
    
    Returns status of:
    - STT engine (Whisper model loaded)
    - TTS engine (Google Cloud / Piper available)
    - Ollama API connectivity
    - Session manager status
    - Agent cache statistics
    """
    health = {
        "status": "healthy",
        "components": {},
        "timestamp": None,
    }

    # Check STT
    try:
        health["components"]["stt"] = {
            "status": "healthy",
            "model": Config.STT_MODEL_SIZE,
            "device": Config.STT_DEVICE,
        }
    except Exception as e:
        health["components"]["stt"] = {"status": "unhealthy", "error": str(e)}
        health["status"] = "degraded"

    # Check TTS
    try:
        engine_count = len(tts_engine.engines)
        engines_available = list(tts_engine.engines.keys())
        health["components"]["tts"] = {
            "status": "healthy" if engine_count > 0 else "unhealthy",
            "engines_available": engine_count,
            "engines": engines_available,
            "default_engine": tts_engine.default_engine_name,
        }
        if engine_count == 0:
            health["status"] = "degraded"
    except Exception as e:
        health["components"]["tts"] = {"status": "unhealthy", "error": str(e)}
        health["status"] = "degraded"

    # Check Ollama
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            response = await client.get(f"{Config.LLM_BASE_URL}/api/tags")
            health["components"]["ollama"] = {
                "status": "healthy" if response.status_code == 200 else "unhealthy",
                "base_url": Config.LLM_BASE_URL,
            }
    except Exception as e:
        health["components"]["ollama"] = {
            "status": "unhealthy",
            "error": str(e),
        }
        health["status"] = "degraded"

    # Session manager stats
    try:
        health["components"]["sessions"] = session_manager.get_stats()
    except Exception as e:
        health["components"]["sessions"] = {"status": "error", "error": str(e)}

    # Agent cache stats
    try:
        health["components"]["agent_cache"] = agent_cache.get_stats()
    except Exception as e:
        health["components"]["agent_cache"] = {"status": "error", "error": str(e)}

    return health


@app.get("/api/session/stats")
async def session_stats():
    """Get session manager statistics."""
    try:
        return session_manager.get_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/events")
async def sse_events(
    session_id: str = None,
    status: str = None,
):
    """
    Server-Sent Events endpoint for real-time status updates.
    
    Args:
        session_id: Optional session to filter events for
        status: Current processing stage (for client to track progress)
    """
    # Simple SSE event generator
    async def event_generator():
        stages = [
            "received",
            "transcribing",
            "processing",
            "generating_speech",
            "complete",
        ]
        for stage in stages:
            data = json.dumps({"stage": stage, "session_id": session_id})
            yield f"data: {data}\n\n"
            await asyncio.sleep(0.1)  # Small delay for client to process

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/api/auth")
async def authenticate_customer(
    session_id: str = Form(...),
    customer_id: str = Form(...),
):
    """
    Authenticate customer by ID number and bind to session.
    
    Args:
        session_id: Session identifier
        customer_id: 11-digit customer ID number
        
    Returns:
        Authentication result with customer info
    """
    try:
        # Validate session exists
        session = session_manager.get_session(session_id)
        if not session:
            session = session_manager.create_session(session_id)

        # Authenticate
        is_valid = auth_service.verify_customer(customer_id)
        if not is_valid:
            raise HTTPException(
                status_code=401,
                detail="Geçersiz müşteri kimliği.",
            )

        # Bind to session
        session_manager.authenticate_session(session_id, customer_id)
        
        # Get customer info
        customer_info = auth_service.get_customer_info(customer_id)
        
        return {
            "status": "success",
            "authenticated": True,
            "customer_id": customer_id,
            "customer_name": (
                f"{customer_info['first_name']} {customer_info['last_name']}"
                if customer_info
                else "Müşteri"
            ),
        }

    except AuthenticationError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except SessionError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        log.error(f"Kimlik doğrulama hatası: {e}")
        raise HTTPException(status_code=500, detail="Kimlik doğrulanamadı.")


def _process_audio_sync(
    temp_audio_path: str,
    strictness_level: int,
    model_name: str,
    session_id: str,
    customer_id: str = None,
    tts_engine_name: str = None,
) -> dict:
    """
    Synchronous audio processing pipeline.

    Flow: STT -> Agent -> TTS

    Args:
        temp_audio_path: Path to uploaded audio file
        strictness_level: Agent strictness (1-5)
        model_name: Ollama model to use
        session_id: Session identifier
        customer_id: Verified customer ID (optional)
        tts_engine_name: TTS engine to use (google, piper, coqui). None = default.

    Returns:
        Dictionary with transcription, response, and base64 audio
    """
    output_file = None
    try:
        # 1. Speech-to-Text
        user_text = stt_engine.transcribe_file(
            temp_audio_path,
            initial_prompt="Bu bir bankacılık görüşmesidir. Bakiye, havale, EFT, kredi kartı, valör, faiz işlemleri konuşulmaktadır.",
        )

        if not user_text:
            return {"status": "error", "message": "Ses anlaşılamadı"}

        # 2. Get/create agent from thread-safe cache
        agent = get_agent_for_model(model_name)

        # 3. Process with agent (pass customer_id if authenticated)
        ai_response_text = agent.handle_turn(
            user_text,
            strictness_level,
            session_id,
            customer_id,
        )

        # 4. Text-to-Speech (with engine selection)
        output_file = tts_engine.generate_audio(text=ai_response_text, engine_name=tts_engine_name)

        if not output_file or not os.path.exists(output_file):
            return {
                "status": "error",
                "message": "TTS motorunda ses üretilemedi.",
                "user_text": user_text,
                "ai_text": ai_response_text,
            }

        # 5. Encode audio to base64
        with open(output_file, "rb") as audio_file:
            encoded_audio = base64.b64encode(audio_file.read()).decode("utf-8")

        return {
            "status": "success",
            "user_text": user_text,
            "ai_text": ai_response_text,
            "audio_base64": encoded_audio,
        }

    except Exception as e:
        log.error(f"Sync Worker Hatası: {e}")
        return {"status": "error", "message": str(e)}
    finally:
        # Cleanup temp files
        try:
            if os.path.exists(temp_audio_path):
                os.remove(temp_audio_path)
            if output_file and os.path.exists(output_file):
                os.remove(output_file)
        except OSError as e:
            log.error(f"Geçici dosya temizleme hatası: {e}")


@app.post(
    "/process_audio",
    summary="Process Voice Input",
    description="Full pipeline: STT -> AI Agent -> TTS -> Audio Response",
)
async def process_audio(
    audio: UploadFile = File(...),
    strictness: int = Form(3),
    model_name: str = Form(None),
    session_id: str = Form(None),
    customer_id: str = Form(None),
    tts_engine: str = Form(None),
):
    """
    Process voice input through full STT -> Agent -> TTS pipeline.

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

    # Ensure session exists
    session = session_manager.get_session(session_id)
    if not session:
        session = session_manager.create_session(session_id)

    # If customer_id provided, try to authenticate
    if customer_id:
        try:
            session_manager.authenticate_session(session_id, customer_id)
        except (SessionError, AuthenticationError) as e:
            log.warning(f"Müşteri kimlik doğrulama başarısız: {e}")
            customer_id = None  # Proceed without auth

    # Validate audio upload
    is_valid, error_msg = validate_audio_upload(audio, audio.filename)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)

    try:
        # Save temp audio
        unique_id = uuid.uuid4().hex
        filename_str = str(audio.filename or "user_voice.wav")
        temp_audio_path = os.path.join(
            current_dir, f"web_temp_{unique_id}_{filename_str}"
        )

        with open(temp_audio_path, "wb") as buffer:
            shutil.copyfileobj(audio.file, buffer)

        log.info(
            f"Ses alındı. Strictness={strictness}, "
            f"Model={model_name}, Session={session_id}, "
            f"Customer={customer_id or 'doğrulanmamış'}"
        )

        # Process in threadpool
        result = await run_in_threadpool(
            _process_audio_sync,
            temp_audio_path,
            strictness,
            model_name,
            session_id,
            customer_id,
            tts_engine,
        )
        return result

    except Exception as e:
        log.error(f"Web Servis Hatası: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Run server
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "web_server:app",
        host=Config.HOST,
        port=Config.PORT,
        reload=Config.DEBUG,
        log_level=Config.LOG_LEVEL.lower(),
    )

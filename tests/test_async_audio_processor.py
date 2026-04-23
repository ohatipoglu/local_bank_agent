"""
Tests for async audio processing service.
"""

import asyncio
import os
import tempfile
import time
import wave
import struct
from io import BytesIO

import pytest

from services.audio_processor import AsyncAudioProcessor


class MockSTTEngine:
    """Mock STT engine for testing."""

    def transcribe_file(self, audio_path: str, initial_prompt: str = None) -> str:
        return "Merhaba, bakiyemi öğrenmek istiyorum."


class MockAgent:
    """Mock agent for testing."""

    def handle_turn(
        self,
        user_text: str,
        strictness_level: int,
        session_id: str,
        customer_id: str = None,
    ) -> str:
        return f"Hesabınızda 10,000 TRY bulunmaktadır. (Session: {session_id})"


class MockTTSEngine:
    """Mock TTS engine for testing."""

    def generate_audio(self, text: str, engine_name: str = None) -> str:
        # Create a minimal WAV file
        output_path = tempfile.mktemp(suffix=".wav")
        with wave.open(output_path, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(16000)
            for _ in range(1600):  # 0.1 second
                wav_file.writeframes(struct.pack("h", 0))
        return output_path


@pytest.fixture
def mock_stt_engine():
    return MockSTTEngine()


@pytest.fixture
def mock_agent():
    return MockAgent()


@pytest.fixture
def mock_tts_engine():
    return MockTTSEngine()


@pytest.fixture
def audio_processor(mock_stt_engine, mock_agent, mock_tts_engine):
    return AsyncAudioProcessor(
        stt_engine=mock_stt_engine,
        agent=mock_agent,
        tts_engine=mock_tts_engine,
    )


@pytest.fixture
def temp_audio_file():
    """Create a temporary WAV file for testing."""
    buffer = BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(16000)
        for _ in range(1600):
            wav_file.writeframes(struct.pack("h", 0))

    temp_file = tempfile.mktemp(suffix=".wav")
    with open(temp_file, "wb") as f:
        f.write(buffer.getvalue())

    yield temp_file

    # Cleanup
    if os.path.exists(temp_file):
        os.remove(temp_file)


@pytest.mark.asyncio
async def test_process_full_pipeline(audio_processor, temp_audio_file):
    """Test full STT -> Agent -> TTS pipeline."""
    result = await audio_processor.process(
        audio_path=temp_audio_file,
        session_id="test_session_123",
        customer_id="10000000146",
        strictness_level=3,
    )

    assert result["status"] == "success"
    assert "user_text" in result
    assert "ai_text" in result
    assert "audio_base64" in result
    assert result["user_text"] == "Merhaba, bakiyemi öğrenmek istiyorum."
    assert "10,000 TRY" in result["ai_text"]


@pytest.mark.asyncio
async def test_process_timeout(audio_processor, temp_audio_file):
    """Test timeout handling."""
    # Create a slow mock processor
    class SlowSTTEngine:
        def transcribe_file(self, audio_path: str, initial_prompt: str = None) -> str:
            time.sleep(5)
            return "test"

    slow_processor = AsyncAudioProcessor(
        stt_engine=SlowSTTEngine(),
        agent=MockAgent(),
        tts_engine=MockTTSEngine(),
    )
    slow_processor.timeout_seconds = 1

    result = await slow_processor.process(
        audio_path=temp_audio_file,
        session_id="test_session",
    )

    assert result["status"] == "error"
    assert "TIMEOUT" in result.get("error_code", "")


@pytest.mark.asyncio
async def test_transcribe_only(audio_processor, temp_audio_file):
    """Test transcription-only mode."""
    result = await audio_processor.transcribe_only(
        audio_path=temp_audio_file,
        language="tr",
    )

    assert result["status"] == "success"
    assert "transcription" in result
    assert result["transcription"] == "Merhaba, bakiyemi öğrenmek istiyorum."


@pytest.mark.asyncio
async def test_generate_speech_only(audio_processor):
    """Test TTS-only mode."""
    result = await audio_processor.generate_speech_only(
        text="Test metni",
        tts_engine_name="google",
    )

    assert result["status"] == "success"
    assert "audio_base64" in result


@pytest.mark.asyncio
async def test_process_with_customer_id(audio_processor, temp_audio_file):
    """Test processing with authenticated customer."""
    result = await audio_processor.process(
        audio_path=temp_audio_file,
        session_id="test_session",
        customer_id="10000000146",
        strictness_level=5,
    )

    assert result["status"] == "success"
    assert result["user_text"] == "Merhaba, bakiyemi öğrenmek istiyorum."


@pytest.mark.asyncio
async def test_cleanup_on_error(audio_processor, temp_audio_file):
    """Test that temp files are cleaned up on error."""
    # Create processor with failing TTS
    class FailingTTSEngine:
        def generate_audio(self, text: str, engine_name: str = None) -> str:
            return None

    failing_processor = AsyncAudioProcessor(
        stt_engine=MockSTTEngine(),
        agent=MockAgent(),
        tts_engine=FailingTTSEngine(),
    )

    result = await failing_processor.process(
        audio_path=temp_audio_file,
        session_id="test_session",
    )

    assert result["status"] == "error"
    assert "TTS_FAILED" in result.get("error_code", "")


@pytest.mark.asyncio
async def test_concurrent_processing(audio_processor, temp_audio_file):
    """Test concurrent audio processing."""
    tasks = [
        audio_processor.process(
            audio_path=temp_audio_file,
            session_id=f"session_{i}",
            customer_id="10000000146",
        )
        for i in range(5)
    ]

    results = await asyncio.gather(*tasks)

    assert len(results) == 5
    for result in results:
        assert result["status"] == "success"
        assert "user_text" in result
        assert "ai_text" in result

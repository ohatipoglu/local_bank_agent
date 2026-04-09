"""
Tests for TTS engine text preprocessing.
"""
import pytest
from infrastructure.tts_engine import TTSEngineBase
from unittest.mock import MagicMock


class TestTTSEnginePreprocessing:
    """Test TTS text preprocessing for abbreviation expansion."""

    @pytest.fixture
    def tts_engine(self):
        """Create a concrete TTSEngineBase subclass for testing."""
        class TestableTTSEngine(TTSEngineBase):
            def generate_audio(self, text):
                return None

        logger = MagicMock()
        return TestableTTSEngine(logger)

    def test_eft_expansion(self, tts_engine):
        """Test EFT abbreviation expansion."""
        text = "EFT işleminiz yapıldı"
        result = tts_engine._preprocess_text(text)
        assert "e fe te" in result

    def test_tl_expansion(self, tts_engine):
        """Test TL abbreviation expansion."""
        text = "Bakiyeniz 1000 TL"
        result = tts_engine._preprocess_text(text)
        assert "Türk Lirası" in result

    def test_iban_expansion(self, tts_engine):
        """Test IBAN abbreviation expansion."""
        text = "IBAN numaranız TR123"
        result = tts_engine._preprocess_text(text)
        assert "ay ban" in result

    def test_tc_expansion(self, tts_engine):
        """Test TC abbreviation expansion."""
        text = "TC kimlik numaranız"
        result = tts_engine._preprocess_text(text)
        assert "Te Ce" in result

    def test_kdv_expansion(self, tts_engine):
        """Test KDV abbreviation expansion."""
        text = "KDV tutarı"
        result = tts_engine._preprocess_text(text)
        assert "ka de ve" in result

    def test_multiple_replacements(self, tts_engine):
        """Test multiple abbreviations in same text."""
        text = "EFT ile 500 TL gönderildi"
        result = tts_engine._preprocess_text(text)
        assert "e fe te" in result
        assert "Türk Lirası" in result

    def test_no_replacements_needed(self, tts_engine):
        """Test text without abbreviations."""
        text = "Merhaba dünya"
        result = tts_engine._preprocess_text(text)
        assert result == text

    def test_empty_text(self, tts_engine):
        """Test empty text handling."""
        result = tts_engine._preprocess_text("")
        assert result == ""

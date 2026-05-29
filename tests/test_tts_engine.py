"""
Tests for TTS engine text preprocessing.
"""
from unittest.mock import MagicMock

import pytest

from infrastructure.tts_engine import TTSEngineBase


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


class TestTTSEngineRouter:
    """Test TTSEngineRouter selection and fallback behavior."""

    def test_available_engines_listing(self):
        """Test that get_available_engines lists all local and cloud engines with friendly names."""
        from unittest.mock import patch
        from infrastructure.tts_engine import TTSEngineRouter

        with patch('infrastructure.tts_engine.GoogleCloudTTSEngine') as mock_google_cls, \
             patch('infrastructure.tts_engine.PiperTTSEngine') as mock_piper_cls, \
             patch('infrastructure.tts_engine.CoquiTTSEngine') as mock_coqui_cls, \
             patch('infrastructure.tts_engine.EdgeTTSEngine') as mock_edge_cls, \
             patch('os.path.exists', return_value=True):
            
            # Configure instances
            mock_google = mock_google_cls.return_value
            mock_google.client = MagicMock()
            
            mock_piper = mock_piper_cls.return_value
            mock_piper.piper_available = True
            
            mock_coqui = mock_coqui_cls.return_value
            mock_coqui.coqui_available = True
            
            mock_edge = mock_edge_cls.return_value
            mock_edge.edge_available = True
            
            logger = MagicMock()
            router = TTSEngineRouter(logger)
            
            engines = router.get_available_engines()
            names = [e["name"] for e in engines]
            assert "google" in names
            assert "piper" in names
            assert "coqui" in names
            assert "edge" in names
            
            # Check friendly names
            piper_info = next(e for e in engines if e["name"] == "piper")
            assert piper_info["display_name"] == "Piper (Yerel Hafif)"
            
            coqui_info = next(e for e in engines if e["name"] == "coqui")
            assert coqui_info["display_name"] == "Coqui (Yerel)"

    def test_explicit_engine_fallback_bypassing(self):
        """Test that generate_audio skips fallback when coqui/piper is explicitly requested and fails."""
        from unittest.mock import patch
        from infrastructure.tts_engine import TTSEngineRouter

        with patch('infrastructure.tts_engine.GoogleCloudTTSEngine') as mock_google_cls, \
             patch('infrastructure.tts_engine.PiperTTSEngine') as mock_piper_cls, \
             patch('infrastructure.tts_engine.CoquiTTSEngine') as mock_coqui_cls, \
             patch('infrastructure.tts_engine.EdgeTTSEngine') as mock_edge_cls, \
             patch('os.path.exists', return_value=True):
             
            mock_google = mock_google_cls.return_value
            mock_google.client = MagicMock()
            
            mock_piper = mock_piper_cls.return_value
            mock_piper.piper_available = True
            mock_piper.generate_audio.return_value = None  # Failed synthesis
            
            mock_coqui = mock_coqui_cls.return_value
            mock_coqui.coqui_available = True
            mock_coqui.generate_audio.return_value = None  # Failed synthesis
            
            logger = MagicMock()
            router = TTSEngineRouter(logger)
            
            # If user explicitly requests coqui, it fails, and should bypass fallback (return None)
            with patch('os.path.exists', return_value=False):
                res = router.generate_audio("Merhaba", engine_name="coqui")
                assert res is None
                # Verify no fallback was attempted (i.e. google and edge were not called)
                mock_google.generate_audio.assert_not_called()

    def test_try_fallback_respects_config_flags(self):
        """Test that _try_fallback only uses engines that have fallback enabled in the config."""
        from unittest.mock import patch
        from core.config import Config
        from infrastructure.tts_engine import TTSEngineRouter

        with patch('infrastructure.tts_engine.GoogleCloudTTSEngine') as mock_google_cls, \
             patch('infrastructure.tts_engine.PiperTTSEngine') as mock_piper_cls, \
             patch('infrastructure.tts_engine.CoquiTTSEngine') as mock_coqui_cls, \
             patch('infrastructure.tts_engine.EdgeTTSEngine') as mock_edge_cls, \
             patch('os.path.exists', return_value=True):
             
            mock_google = mock_google_cls.return_value
            mock_google.client = MagicMock()
            mock_google.generate_audio.return_value = None  # Fails
            
            mock_piper = mock_piper_cls.return_value
            mock_piper.piper_available = True
            mock_piper.generate_audio.return_value = "piper.wav"
            
            mock_coqui = mock_coqui_cls.return_value
            mock_coqui.coqui_available = True
            mock_coqui.generate_audio.return_value = "coqui.wav"
            
            logger = MagicMock()
            router = TTSEngineRouter(logger)
            
            # Test 1: both coqui and piper enabled for fallback
            with patch.object(Config, 'TTS_ENABLE_COQUI_FALLBACK', True), \
                 patch.object(Config, 'TTS_ENABLE_PIPER_FALLBACK', True), \
                 patch('os.path.exists', return_value=True):
                res = router.generate_audio("Merhaba", engine_name="google")
                assert res == "piper.wav"  # Piper is checked first in engines insertion order
                
            # Test 2: piper disabled, coqui enabled for fallback
            with patch.object(Config, 'TTS_ENABLE_COQUI_FALLBACK', True), \
                 patch.object(Config, 'TTS_ENABLE_PIPER_FALLBACK', False), \
                 patch('os.path.exists', return_value=True):
                # Reset mock calls
                mock_piper.generate_audio.reset_mock()
                mock_coqui.generate_audio.reset_mock()
                res = router.generate_audio("Merhaba", engine_name="google")
                assert res == "coqui.wav"
                mock_piper.generate_audio.assert_not_called()


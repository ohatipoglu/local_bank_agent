"""
Tests for prompt generation module.
"""
import pytest
from application.prompts import get_dynamic_prompt, load_prompts_from_yaml


class TestPromptLoader:
    """Test YAML prompt loading."""

    def test_load_prompts_returns_dict(self):
        """Test that loaded prompts is a dictionary."""
        prompts = load_prompts_from_yaml()
        assert isinstance(prompts, dict)
        assert "base_prompt" in prompts
        assert "empathy_rule" in prompts
        assert "strictness_levels" in prompts

    def test_strictness_levels_present(self):
        """Test all strictness levels are defined."""
        prompts = load_prompts_from_yaml()
        levels = prompts.get("strictness_levels", {})
        for level in range(1, 6):
            assert level in levels, f"Strictness level {level} not defined"


class TestDynamicPrompt:
    """Test dynamic prompt generation."""

    def test_level_1_includes_empathy(self):
        """Test level 1 (most flexible) includes empathy rule."""
        prompt = get_dynamic_prompt(1)
        assert "Local Bank" in prompt
        assert "empati" in prompt.lower() or "EMPAT" in prompt

    def test_level_3_includes_empathy(self):
        """Test level 3 (balanced) includes empathy rule."""
        prompt = get_dynamic_prompt(3)
        assert "empati" in prompt.lower() or "EMPAT" in prompt

    def test_level_4_excludes_empathy(self):
        """Test level 4 (strict) excludes empathy rule."""
        prompt = get_dynamic_prompt(4)
        # Should have strict level 4 rule
        assert "SEVİYESİ 4" in prompt or "KISITLAMA SEVİYESİ 4" in prompt
        # Should NOT have empathy
        assert "empati" not in prompt.lower() and "EMPAT" not in prompt

    def test_level_5_excludes_empathy(self):
        """Test level 5 (most strict) excludes empathy rule."""
        prompt = get_dynamic_prompt(5)
        assert "SEVİYESİ 5" in prompt or "KISITLAMA SEVİYESİ 5" in prompt
        assert "empati" not in prompt.lower() and "EMPAT" not in prompt

    def test_all_levels_have_content(self):
        """Test all levels generate non-empty prompts."""
        for level in range(1, 6):
            prompt = get_dynamic_prompt(level)
            assert len(prompt) > 50, f"Level {level} prompt too short"
            assert "Local Bank" in prompt

    def test_invalid_level_returns_default(self):
        """Test invalid level generates usable prompt."""
        prompt = get_dynamic_prompt(99)
        assert len(prompt) > 0
        assert "Local Bank" in prompt

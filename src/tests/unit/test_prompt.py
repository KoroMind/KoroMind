"""Tests for koro.prompt module."""

from datetime import datetime

from koro.prompt import PromptManager, build_dynamic_prompt


class TestLoadSystemPrompt:
    """Tests for load_system_prompt function."""

    def test_load_from_file(self, tmp_path, monkeypatch):
        """load_system_prompt reads from file."""
        prompt_file = tmp_path / "prompt.md"
        prompt_file.write_text("You are a test assistant.")

        import koro.config

        monkeypatch.setattr(koro.config, "SYSTEM_PROMPT_FILE", str(prompt_file))

        import importlib

        import koro.prompt

        importlib.reload(koro.prompt)

        content = koro.prompt.load_system_prompt(str(prompt_file))
        assert content == "You are a test assistant."

    def test_replaces_placeholders(self, tmp_path, monkeypatch):
        """load_system_prompt replaces placeholders."""
        prompt_file = tmp_path / "prompt.md"
        prompt_file.write_text("Sandbox: {sandbox_dir}, Read: {read_dir}")

        import koro.core.prompt

        monkeypatch.setattr(koro.core.prompt, "SANDBOX_DIR", "/test/sandbox")
        monkeypatch.setattr(koro.core.prompt, "CLAUDE_WORKING_DIR", "/test/working")
        monkeypatch.setattr(koro.core.prompt, "BASE_DIR", tmp_path)

        content = koro.core.prompt.load_system_prompt(str(prompt_file))
        assert "/test/sandbox" in content
        assert "/test/working" in content

    def test_fallback_default_when_missing(self, tmp_path, monkeypatch):
        """load_system_prompt returns default when file missing."""
        import koro.core.prompt

        monkeypatch.setattr(koro.core.prompt, "SYSTEM_PROMPT_FILE", "")
        monkeypatch.setattr(koro.core.prompt, "SANDBOX_DIR", "/sandbox")
        monkeypatch.setattr(koro.core.prompt, "CLAUDE_WORKING_DIR", "/working")

        content = koro.core.prompt.load_system_prompt()
        assert "voice assistant" in content.lower()
        assert "/sandbox" in content
        assert "/working" in content

    def test_relative_path_resolved(self, tmp_path, monkeypatch):
        """load_system_prompt resolves relative paths."""
        prompt_dir = tmp_path / "prompts"
        prompt_dir.mkdir()
        prompt_file = prompt_dir / "test.md"
        prompt_file.write_text("Relative prompt content")

        import koro.core.prompt

        monkeypatch.setattr(koro.core.prompt, "BASE_DIR", tmp_path)

        content = koro.core.prompt.load_system_prompt("prompts/test.md")
        assert content == "Relative prompt content"

    def test_path_traversal_blocked(self, tmp_path, monkeypatch):
        """load_system_prompt blocks path traversal attempts."""
        # Create a file outside BASE_DIR
        outside_dir = tmp_path / "outside"
        outside_dir.mkdir()
        secret_file = outside_dir / "secret.txt"
        secret_file.write_text("SECRET DATA")

        # Set BASE_DIR to a subdirectory
        base_dir = tmp_path / "app"
        base_dir.mkdir()

        import koro.core.prompt

        monkeypatch.setattr(koro.core.prompt, "BASE_DIR", base_dir)
        monkeypatch.setattr(koro.core.prompt, "SYSTEM_PROMPT_FILE", "")
        monkeypatch.setattr(koro.core.prompt, "SANDBOX_DIR", "/sandbox")
        monkeypatch.setattr(koro.core.prompt, "CLAUDE_WORKING_DIR", "/working")

        # Try to access file outside BASE_DIR via path traversal
        content = koro.core.prompt.load_system_prompt("../outside/secret.txt")

        # Should return default prompt, not the secret file
        assert "SECRET DATA" not in content
        assert "voice assistant" in content.lower()


class TestBuildDynamicPrompt:
    """Tests for build_dynamic_prompt function."""

    def test_adds_timestamp(self):
        """build_dynamic_prompt adds current date/time."""
        base = "Base prompt"

        result = build_dynamic_prompt(base)

        assert "Current date and time:" in result
        # Should contain year
        assert str(datetime.now().year) in result

    def test_includes_base_prompt(self):
        """build_dynamic_prompt includes base prompt."""
        base = "This is the base prompt content"

        result = build_dynamic_prompt(base)

        assert "This is the base prompt content" in result

    def test_adds_audio_disabled_note(self):
        """build_dynamic_prompt notes when audio disabled."""
        base = "Base"
        settings = {"audio_enabled": False}

        result = build_dynamic_prompt(base, settings)

        assert "Audio responses disabled" in result

    def test_no_audio_note_when_enabled(self):
        """build_dynamic_prompt doesn't note when audio enabled."""
        base = "Base"
        settings = {"audio_enabled": True}

        result = build_dynamic_prompt(base, settings)

        assert "Audio responses disabled" not in result

    def test_handles_none_settings(self):
        """build_dynamic_prompt handles None settings."""
        base = "Base"

        result = build_dynamic_prompt(base, None)

        assert "Base" in result


class TestPromptManager:
    """Tests for PromptManager class."""

    def test_lazy_loads_prompt(self, tmp_path, monkeypatch):
        """PromptManager lazy loads prompt on first access."""
        prompt_file = tmp_path / "lazy.md"
        prompt_file.write_text("Lazy loaded prompt")

        import koro.core.prompt

        monkeypatch.setattr(koro.core.prompt, "BASE_DIR", tmp_path)

        manager = PromptManager(str(prompt_file))

        # Not loaded yet
        assert manager._base_prompt is None

        # Access triggers load
        prompt = manager.base_prompt
        assert prompt == "Lazy loaded prompt"
        assert manager._base_prompt is not None

    def test_caches_prompt(self, tmp_path, monkeypatch):
        """PromptManager caches loaded prompt."""
        prompt_file = tmp_path / "cached.md"
        prompt_file.write_text("Original content")

        import koro.core.prompt

        monkeypatch.setattr(koro.core.prompt, "BASE_DIR", tmp_path)

        manager = PromptManager(str(prompt_file))

        first = manager.base_prompt

        # Modify file
        prompt_file.write_text("Modified content")

        # Should still return cached
        second = manager.base_prompt
        assert second == first == "Original content"

    def test_reload_clears_cache(self, tmp_path, monkeypatch):
        """PromptManager.reload() clears cache."""
        prompt_file = tmp_path / "reload.md"
        prompt_file.write_text("Original")

        import koro.core.prompt

        monkeypatch.setattr(koro.core.prompt, "BASE_DIR", tmp_path)

        manager = PromptManager(str(prompt_file))

        manager.base_prompt  # Load cache
        prompt_file.write_text("Modified")

        manager.reload()

        assert manager.base_prompt == "Modified"

    def test_get_prompt_returns_dynamic(self, tmp_path, monkeypatch):
        """PromptManager.get_prompt() returns dynamic prompt."""
        prompt_file = tmp_path / "dynamic.md"
        prompt_file.write_text("Base content")

        import koro.core.prompt

        monkeypatch.setattr(koro.core.prompt, "BASE_DIR", tmp_path)

        manager = PromptManager(str(prompt_file))
        settings = {"audio_enabled": False}

        result = manager.get_prompt(settings)

        assert "Base content" in result
        assert "Current date and time:" in result
        assert "Audio responses disabled" in result

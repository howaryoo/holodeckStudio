from __future__ import annotations

from typer.testing import CliRunner

from holodeck.cli.main import app

runner = CliRunner()


class TestCLIProduce:
    def test_produce_dry_run(self):
        result = runner.invoke(app, ["produce", "A story about a crew in space", "--dry-run"])
        assert result.exit_code == 0
        assert "Prompt validated" in result.stdout

    def test_produce_short_prompt_rejected(self):
        result = runner.invoke(app, ["produce", "hi"])
        assert result.exit_code == 1
        assert "too short" in result.stdout.lower()

    def test_produce_dry_run_shows_bible(self):
        result = runner.invoke(app, ["produce", "A story about a crew in space", "--dry-run", "--bible", "abc"])
        assert result.exit_code == 0
        assert "Bible: abc" in result.stdout

    def test_produce_dry_run_shows_mode(self):
        result = runner.invoke(app, ["produce", "A story about a crew in space", "--dry-run", "--mode", "supervised"])
        assert result.exit_code == 0
        assert "Mode: supervised" in result.stdout

    def test_produce_help(self):
        result = runner.invoke(app, ["produce", "--help"])
        assert result.exit_code == 0
        assert "prompt" in result.stdout


class TestCLIBible:
    def test_bible_create(self):
        result = runner.invoke(app, ["bible", "create", "Test", "A test"])
        assert result.exit_code == 0
        assert "Created bible: Test" in result.stdout

    def test_bible_list_empty(self):
        result = runner.invoke(app, ["bible", "list"])
        assert result.exit_code == 0

    def test_bible_show_not_found(self):
        result = runner.invoke(app, ["bible", "show", "nonexistent"])
        assert result.exit_code == 1
        assert "not found" in result.stdout.lower()

    def test_bible_help(self):
        result = runner.invoke(app, ["bible", "--help"])
        assert result.exit_code == 0
        assert "bible" in result.stdout


class TestCLIConfig:
    def test_config_show(self):
        result = runner.invoke(app, ["config", "show"])
        assert result.exit_code == 0
        assert "Configuration" in result.stdout

    def test_config_set(self):
        result = runner.invoke(app, ["config", "set", "holodeck_default_model", "openai/gpt-4"])
        assert result.exit_code == 0
        assert "Set" in result.stdout

    def test_config_reset(self):
        result = runner.invoke(app, ["config", "reset"])
        assert result.exit_code == 0
        assert "reset" in result.stdout.lower()

    def test_config_help(self):
        result = runner.invoke(app, ["config", "--help"])
        assert result.exit_code == 0


class TestCLICache:
    def test_cache_status(self):
        result = runner.invoke(app, ["cache", "status"])
        assert result.exit_code == 0
        assert "entries" in result.stdout.lower()

    def test_cache_clear(self):
        result = runner.invoke(app, ["cache", "clear"])
        assert result.exit_code == 0
        assert "cleared" in result.stdout.lower()

    def test_cache_help(self):
        result = runner.invoke(app, ["cache", "--help"])
        assert result.exit_code == 0


class TestCLIStatus:
    def test_status_not_found(self):
        result = runner.invoke(app, ["status", "00000000-0000-0000-0000-000000000000"])
        assert result.exit_code == 1
        assert "not found" in result.stdout.lower()

    def test_status_help(self):
        result = runner.invoke(app, ["status", "--help"])
        assert result.exit_code == 0


class TestCLIApprove:
    def test_approve_not_found(self):
        result = runner.invoke(app, ["approve", "00000000-0000-0000-0000-000000000000"])
        assert result.exit_code == 1
        assert "not found" in result.stdout.lower()


class TestCLIReject:
    def test_reject_not_found(self):
        result = runner.invoke(app, ["reject", "00000000-0000-0000-0000-000000000000", "--stage", "script", "--feedback", "bad"])
        assert result.exit_code == 1
        assert "not found" in result.stdout.lower()

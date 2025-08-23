import os
import sys
import time
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ai_test_generator.utils import helpers


class DummySettings(SimpleNamespace):
    """Simple settings object for testing"""
    pass


def test_format_duration_seconds():
    assert helpers.format_duration(45) == "45.0s"


def test_format_duration_minutes():
    assert helpers.format_duration(90) == "1.5m"


def test_format_duration_hours():
    assert helpers.format_duration(7200) == "2.0h"


def test_get_cache_stats(tmp_path, monkeypatch):
    cache_dir = tmp_path
    (cache_dir / "a.txt").write_bytes(b"a" * 10)
    (cache_dir / "b.txt").write_bytes(b"b" * 5)
    settings = DummySettings(cache_dir=str(cache_dir))
    monkeypatch.setattr(helpers, "get_settings", lambda: settings)

    stats = helpers.get_cache_stats()

    assert stats["file_count"] == 2
    assert stats["total_size"] == 15
    assert stats["last_modified"] is not None


def test_clear_cache(tmp_path, monkeypatch):
    cache_dir = tmp_path
    old_file = cache_dir / "old.txt"
    new_file = cache_dir / "new.txt"
    old_file.write_text("old")
    new_file.write_text("new")
    old_time = time.time() - 7200  # two hours ago
    os.utime(old_file, (old_time, old_time))
    settings = DummySettings(cache_dir=str(cache_dir))
    monkeypatch.setattr(helpers, "get_settings", lambda: settings)

    deleted = helpers.clear_cache(max_age_hours=1)

    assert deleted == 1
    assert not old_file.exists()
    assert new_file.exists()


def test_validate_api_credentials(monkeypatch):
    settings = DummySettings(
        email="testuser",
        jira_api_token="Testpassword123",
        xray_jira_client_id="testuser",
        xray_jira_client_secret="Testpassword123",
    )
    monkeypatch.setattr(helpers, "get_settings", lambda: settings)

    creds = helpers.validate_api_credentials()

    assert all(creds.values())
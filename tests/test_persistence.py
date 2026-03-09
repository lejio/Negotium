"""Tests for negotium.persistence — seen-job tracking."""

from __future__ import annotations

import json

from negotium.persistence import load_seen_jobs, save_seen_jobs


class TestLoadSeenJobs:
    """Test loading seen jobs from disk."""

    def test_returns_empty_set_when_file_missing(self, tmp_path):
        path = tmp_path / "nonexistent.json"
        result = load_seen_jobs(path)
        assert result == set()

    def test_loads_existing_ids(self, tmp_path):
        path = tmp_path / "seen.json"
        path.write_text(json.dumps(["abc", "def", "ghi"]))
        result = load_seen_jobs(path)
        assert result == {"abc", "def", "ghi"}

    def test_returns_set_type(self, tmp_path):
        path = tmp_path / "seen.json"
        path.write_text(json.dumps(["a", "b"]))
        result = load_seen_jobs(path)
        assert isinstance(result, set)


class TestSaveSeenJobs:
    """Test persisting seen jobs to disk."""

    def test_creates_file(self, tmp_path):
        path = tmp_path / "seen.json"
        save_seen_jobs({"aaa", "bbb"}, path)
        assert path.exists()

    def test_saved_content_is_sorted_json(self, tmp_path):
        path = tmp_path / "seen.json"
        save_seen_jobs({"z", "a", "m"}, path)
        data = json.loads(path.read_text())
        assert data == ["a", "m", "z"]

    def test_round_trip(self, tmp_path):
        path = tmp_path / "seen.json"
        original = {"id1", "id2", "id3"}
        save_seen_jobs(original, path)
        loaded = load_seen_jobs(path)
        assert loaded == original

    def test_overwrite_existing(self, tmp_path):
        path = tmp_path / "seen.json"
        save_seen_jobs({"old"}, path)
        save_seen_jobs({"new1", "new2"}, path)
        loaded = load_seen_jobs(path)
        assert loaded == {"new1", "new2"}

    def test_empty_set(self, tmp_path):
        path = tmp_path / "seen.json"
        save_seen_jobs(set(), path)
        loaded = load_seen_jobs(path)
        assert loaded == set()

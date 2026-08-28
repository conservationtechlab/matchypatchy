"""
Tests for matchypatchy.config — mpConfig class and utility functions.

These tests exercise configuration loading, saving, and the path-resolution
helpers without requiring a display server.
"""
from pathlib import Path
import yaml
import pytest

from matchypatchy.config import mpConfig, resource_path, asset_path


# ---------------------------------------------------------------------------
# mpConfig — initialisation
# ---------------------------------------------------------------------------

class TestMpConfigInit:
    def test_creates_home_dir(self, tmp_path):
        home = tmp_path / "project"
        cfg = mpConfig(home)
        assert home.exists()

    def test_creates_config_file(self, tmp_path):
        home = tmp_path / "project"
        cfg = mpConfig(home)
        assert (home / ".config.yml").exists()

    def test_creates_subdirectories(self, tmp_path):
        home = tmp_path / "project"
        cfg = mpConfig(home)
        assert cfg.DB_DIR.exists()
        assert cfg.ML_DIR.exists()
        assert cfg.THUMBNAIL_DIR.exists()
        assert cfg.FRAME_DIR.exists()

    def test_default_video_frames(self, tmp_path):
        home = tmp_path / "project"
        cfg = mpConfig(home)
        assert cfg.SMART_FRAMES == 3

    def test_default_knn(self, tmp_path):
        home = tmp_path / "project"
        cfg = mpConfig(home)
        assert cfg.KNN == 100

    def test_default_sequence_duration(self, tmp_path):
        home = tmp_path / "project"
        cfg = mpConfig(home)
        assert cfg.SEQUENCE_DURATION == 60

    def test_default_sequence_n(self, tmp_path):
        home = tmp_path / "project"
        cfg = mpConfig(home)
        assert cfg.SEQUENCE_N == 3

    def test_device_is_string(self, tmp_path):
        home = tmp_path / "project"
        cfg = mpConfig(home)
        assert isinstance(cfg.DEVICE, str)
        assert "ExecutionProvider" in cfg.DEVICE

    def test_db_dir_inside_home(self, tmp_path):
        home = tmp_path / "project"
        cfg = mpConfig(home)
        assert str(cfg.DB_DIR).startswith(str(home))

    def test_existing_project_dir_loaded(self, tmp_path):
        home = tmp_path / "project"
        cfg1 = mpConfig(home)
        cfg1.KNN = 42
        cfg1.save()
        cfg2 = mpConfig(home)
        assert cfg2.KNN == 42


# ---------------------------------------------------------------------------
# mpConfig — save / load
# ---------------------------------------------------------------------------

class TestMpConfigSaveLoad:
    def test_save_creates_yaml(self, tmp_path):
        home = tmp_path / "project"
        cfg = mpConfig(home)
        cfg.save()
        assert (home / ".config.yml").exists()

    def test_saved_yaml_is_valid(self, tmp_path):
        home = tmp_path / "project"
        cfg = mpConfig(home)
        cfg.save()
        with open(home / ".config.yml") as f:
            data = yaml.safe_load(f)
        assert isinstance(data, dict)

    def test_saved_yaml_contains_required_keys(self, tmp_path):
        home = tmp_path / "project"
        cfg = mpConfig(home)
        cfg.save()
        with open(home / ".config.yml") as f:
            data = yaml.safe_load(f)
        for key in ("DB_DIR", "ML_DIR", "THUMBNAIL_DIR", "VIDEO_FRAMES",
                    "KNN", "SEQUENCE_DURATION", "SEQUENCE_N", "DEVICE"):
            assert key in data, f"Expected key {key!r} in saved config"

    def test_load_restores_knn(self, tmp_path):
        home = tmp_path / "project"
        cfg = mpConfig(home)
        cfg.KNN = 200
        cfg.save()
        cfg2 = mpConfig(home)
        assert cfg2.KNN == 200

    def test_load_restores_video_frames(self, tmp_path):
        home = tmp_path / "project"
        cfg = mpConfig(home)
        cfg.SMART_FRAMES = 10
        cfg.save()
        cfg2 = mpConfig(home)
        assert cfg.SMART_FRAMES == 10


# ---------------------------------------------------------------------------
# mpConfig — update
# ---------------------------------------------------------------------------

class TestMpConfigUpdate:
    def test_update_single_key(self, tmp_path):
        home = tmp_path / "project"
        cfg = mpConfig(home)
        cfg.update({"KNN": 50})
        assert cfg.KNN == 50

    def test_update_multiple_keys(self, tmp_path):
        home = tmp_path / "project"
        cfg = mpConfig(home)
        cfg.update({"KNN": 75, "SMART_FRAMES": 5})
        assert cfg.KNN == 75
        assert cfg.SMART_FRAMES == 5

    def test_update_persists_to_file(self, tmp_path):
        home = tmp_path / "project"
        cfg = mpConfig(home)
        cfg.update({"KNN": 33})
        with open(home / ".config.yml") as f:
            data = yaml.safe_load(f)
        assert data["KNN"] == 33

    def test_update_does_not_clobber_other_keys(self, tmp_path):
        home = tmp_path / "project"
        cfg = mpConfig(home)
        original_seq_n = cfg.SEQUENCE_N
        cfg.update({"KNN": 77})
        assert cfg.SEQUENCE_N == original_seq_n


# ---------------------------------------------------------------------------
# mpConfig — set_default
# ---------------------------------------------------------------------------

class TestMpConfigSetDefault:
    def test_set_default_resets_knn(self, tmp_path):
        home = tmp_path / "project"
        cfg = mpConfig(home)
        cfg.KNN = 9999
        cfg.set_default()
        assert cfg.KNN == 100

    def test_set_default_resets_smart_frames(self, tmp_path):
        home = tmp_path / "project"
        cfg = mpConfig(home)
        cfg.SMART_FRAMES = 99
        cfg.set_default()
        assert cfg.SMART_FRAMES == 3

    def test_set_default_resets_sequence_n(self, tmp_path):
        home = tmp_path / "project"
        cfg = mpConfig(home)
        cfg.SEQUENCE_N = 99
        cfg.set_default()
        assert cfg.SEQUENCE_N == 3

    def test_set_default_resets_fps(self, tmp_path):
        home = tmp_path / "project"
        cfg = mpConfig(home)
        cfg.VIDEO_FPS = 9999
        cfg.set_default()
        assert cfg.VIDEO_FPS == 30

    def test_set_default_resets_n_frames(self, tmp_path):
        home = tmp_path / "project"
        cfg = mpConfig(home)
        cfg.N_FRAMES = 9999
        cfg.set_default()
        assert cfg.N_FRAMES == 10

    def test_set_default_resets_sequence_duration(self, tmp_path):
        home = tmp_path / "project"
        cfg = mpConfig(home)
        cfg.SEQUENCE_DURATION = 9999
        cfg.set_default()
        assert cfg.SEQUENCE_DURATION == 60


# ---------------------------------------------------------------------------
# resource_path / asset_path
# ---------------------------------------------------------------------------

class TestPathHelpers:
    def test_resource_path_returns_path_like(self):
        result = resource_path("some/resource.txt")
        assert result is not None

    def test_asset_path_returns_path_like(self):
        result = asset_path("graphics/logo.png")
        assert result is not None

    def test_asset_path_contains_assets_segment(self):
        result = asset_path("graphics/logo.png")
        assert "assets" in str(result)

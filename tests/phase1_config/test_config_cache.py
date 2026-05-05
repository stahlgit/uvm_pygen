"""Tests for config cache — write_cache / read_cache."""

import json

import pytest

from uvm_pygen.models.config_schema.resolved_configs import ResolvedConfigs
from uvm_pygen.services.config_parser.config_cache import read_cache, write_cache


class TestWriteCache:
    def test_creates_cache_file_for_unified(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        config = tmp_path / "config.yaml"
        config.touch()
        rc = ResolvedConfigs(unified=config)
        write_cache(rc)
        cache_file = tmp_path / ".uvm_pygen" / "cache.json"
        assert cache_file.exists()

    def test_cache_json_contains_unified_mode(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        config = tmp_path / "config.yaml"
        config.touch()
        rc = ResolvedConfigs(unified=config)
        write_cache(rc)
        data = json.loads((tmp_path / ".uvm_pygen" / "cache.json").read_text())
        assert data["mode"] == "unified"
        assert "config" in data

    def test_creates_cache_file_for_split(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        dut = tmp_path / "dut.yaml"
        uvm = tmp_path / "uvm.yaml"
        dut.touch()
        uvm.touch()
        rc = ResolvedConfigs(dut=dut, uvm=uvm)
        write_cache(rc)
        data = json.loads((tmp_path / ".uvm_pygen" / "cache.json").read_text())
        assert data["mode"] == "split"
        assert "dut" in data
        assert "uvm" in data

    def test_cache_contains_timestamp(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        config = tmp_path / "config.yaml"
        config.touch()
        write_cache(ResolvedConfigs(unified=config))
        data = json.loads((tmp_path / ".uvm_pygen" / "cache.json").read_text())
        assert "resolved_at" in data


class TestReadCache:
    def test_reads_unified_cache(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        config = tmp_path / "config.yaml"
        config.touch()
        write_cache(ResolvedConfigs(unified=config))
        rc = read_cache()
        assert rc.is_unified
        assert rc.unified == config

    def test_reads_split_cache(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        dut = tmp_path / "dut.yaml"
        uvm = tmp_path / "uvm.yaml"
        dut.touch()
        uvm.touch()
        write_cache(ResolvedConfigs(dut=dut, uvm=uvm))
        rc = read_cache()
        assert rc.is_split
        assert rc.dut == dut
        assert rc.uvm == uvm

    def test_exits_if_no_cache_file(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        with pytest.raises(SystemExit):
            read_cache()

    def test_exits_if_cache_is_malformed_json(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        cache_dir = tmp_path / ".uvm_pygen"
        cache_dir.mkdir()
        (cache_dir / "cache.json").write_text("{ not valid json")
        with pytest.raises(SystemExit):
            read_cache()

    def test_exits_if_cached_unified_file_missing(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        cache_dir = tmp_path / ".uvm_pygen"
        cache_dir.mkdir()
        (cache_dir / "cache.json").write_text(
            json.dumps({"mode": "unified", "config": str(tmp_path / "gone.yaml"), "resolved_at": "2026-01-01"})
        )
        with pytest.raises(SystemExit):
            read_cache()

    def test_exits_if_cached_split_files_missing(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        cache_dir = tmp_path / ".uvm_pygen"
        cache_dir.mkdir()
        (cache_dir / "cache.json").write_text(
            json.dumps(
                {
                    "mode": "split",
                    "dut": str(tmp_path / "gone_dut.yaml"),
                    "uvm": str(tmp_path / "gone_uvm.yaml"),
                    "resolved_at": "2026-01-01",
                }
            )
        )
        with pytest.raises(SystemExit):
            read_cache()

    def test_exits_for_unknown_mode(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        cache_dir = tmp_path / ".uvm_pygen"
        cache_dir.mkdir()
        (cache_dir / "cache.json").write_text(
            json.dumps({"mode": "unknown_mode", "resolved_at": "2026-01-01"})
        )
        with pytest.raises(SystemExit):
            read_cache()

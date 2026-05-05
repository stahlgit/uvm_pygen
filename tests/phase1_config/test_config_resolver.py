"""Tests for ConfigResolver — file discovery and unified/split detection."""

from pathlib import Path

import pytest
import yaml

from tests.conftest import MINIMAL_DUT_RAW, MINIMAL_UVM_RAW, write_dut_yaml, write_unified_yaml, write_uvm_yaml
from uvm_pygen.services.config_parser.config_resolver import ConfigResolver


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_yaml(path: Path, data: dict) -> Path:
    path.write_text(yaml.dump(data))
    return path


# ---------------------------------------------------------------------------
# resolve() — explicit unified path
# ---------------------------------------------------------------------------


class TestResolveExplicitUnified:
    def test_returns_unified_resolved_config(self, tmp_path):
        p = write_unified_yaml(tmp_path)
        resolver = ConfigResolver(search_dir=tmp_path)
        result = resolver.resolve(unified_config=p)
        assert result.is_unified
        assert result.unified == p.resolve()

    def test_raises_if_unified_file_missing(self, tmp_path):
        resolver = ConfigResolver(search_dir=tmp_path)
        with pytest.raises(FileNotFoundError, match="--config"):
            resolver.resolve(unified_config=tmp_path / "nonexistent.yaml")


# ---------------------------------------------------------------------------
# resolve() — explicit split paths
# ---------------------------------------------------------------------------


class TestResolveExplicitSplit:
    def test_returns_split_resolved_config(self, tmp_path):
        dut = write_dut_yaml(tmp_path)
        uvm = write_uvm_yaml(tmp_path)
        resolver = ConfigResolver(search_dir=tmp_path)
        result = resolver.resolve(dut_config=dut, uvm_config=uvm)
        assert result.is_split
        assert result.dut == dut.resolve()
        assert result.uvm == uvm.resolve()

    def test_only_dut_given_auto_discovers_uvm(self, tmp_path):
        dut = write_dut_yaml(tmp_path)
        write_uvm_yaml(tmp_path)
        resolver = ConfigResolver(search_dir=tmp_path)
        result = resolver.resolve(dut_config=dut)
        assert result.dut is not None
        assert result.uvm is not None

    def test_only_uvm_given_auto_discovers_dut(self, tmp_path):
        write_dut_yaml(tmp_path)
        uvm = write_uvm_yaml(tmp_path)
        resolver = ConfigResolver(search_dir=tmp_path)
        result = resolver.resolve(uvm_config=uvm)
        assert result.dut is not None
        assert result.uvm is not None

    def test_raises_if_explicit_dut_missing(self, tmp_path):
        resolver = ConfigResolver(search_dir=tmp_path)
        with pytest.raises(FileNotFoundError, match="--dut-config"):
            resolver.resolve(dut_config=tmp_path / "missing.yaml")


# ---------------------------------------------------------------------------
# resolve() — fully automatic discovery
# ---------------------------------------------------------------------------


class TestResolveAutomatic:
    def test_finds_unified_config_automatically(self, tmp_path):
        write_unified_yaml(tmp_path)
        resolver = ConfigResolver(search_dir=tmp_path)
        result = resolver.resolve()
        assert result.is_unified

    def test_falls_back_to_split_when_no_unified(self, tmp_path):
        write_dut_yaml(tmp_path)
        write_uvm_yaml(tmp_path)
        resolver = ConfigResolver(search_dir=tmp_path)
        result = resolver.resolve()
        assert result.is_split

    def test_returns_none_dut_when_no_matching_file(self, tmp_path):
        resolver = ConfigResolver(search_dir=tmp_path)
        result = resolver.resolve()
        assert result.dut is None
        assert result.uvm is None

    def test_discovers_dut_file_by_stem_pattern(self, tmp_path):
        write_dut_yaml(tmp_path)  # stem is config_dut
        resolver = ConfigResolver(search_dir=tmp_path)
        result = resolver._discover_dut()
        assert result is not None
        assert "dut" in result.stem.lower()

    def test_discovers_uvm_file_by_stem_pattern(self, tmp_path):
        write_uvm_yaml(tmp_path)  # stem is config_uvm
        resolver = ConfigResolver(search_dir=tmp_path)
        result = resolver._discover_uvm()
        assert result is not None

    def test_multiple_dut_candidates_uses_first(self, tmp_path):
        _write_yaml(tmp_path / "a_dut.yaml", MINIMAL_DUT_RAW)
        _write_yaml(tmp_path / "b_dut.yaml", MINIMAL_DUT_RAW)
        resolver = ConfigResolver(search_dir=tmp_path)
        result = resolver._discover_dut()
        assert result is not None  # first alphabetically

    def test_no_dut_candidate_returns_none(self, tmp_path):
        resolver = ConfigResolver(search_dir=tmp_path)
        assert resolver._discover_dut() is None

    def test_no_uvm_candidate_returns_none(self, tmp_path):
        resolver = ConfigResolver(search_dir=tmp_path)
        assert resolver._discover_uvm() is None


# ---------------------------------------------------------------------------
# split_unified()
# ---------------------------------------------------------------------------


class TestSplitUnified:
    def test_splits_unified_into_dut_and_uvm(self, tmp_path):
        p = write_unified_yaml(tmp_path)
        resolver = ConfigResolver(search_dir=tmp_path)
        dut_raw, uvm_raw = resolver.split_unified(p)
        assert "dut" in dut_raw
        assert "verification" in uvm_raw

    def test_raises_if_dut_required_key_missing(self, tmp_path):
        # unified without 'dut' key
        bad = {**MINIMAL_UVM_RAW}
        p = tmp_path / "bad.yaml"
        p.write_text(yaml.dump(bad))
        resolver = ConfigResolver(search_dir=tmp_path)
        with pytest.raises(ValueError, match="missing required DUT"):
            resolver.split_unified(p)

    def test_raises_if_uvm_required_key_missing(self, tmp_path):
        # unified without any UVM keys (only DUT)
        bad = {**MINIMAL_DUT_RAW}
        p = tmp_path / "bad.yaml"
        p.write_text(yaml.dump(bad))
        resolver = ConfigResolver(search_dir=tmp_path)
        with pytest.raises(ValueError, match="missing required UVM"):
            resolver.split_unified(p)

    def test_unknown_keys_are_ignored_with_warning(self, tmp_path):
        combined = {**MINIMAL_DUT_RAW, **MINIMAL_UVM_RAW, "unknown_key": "value"}
        p = tmp_path / "combined.yaml"
        p.write_text(yaml.dump(combined))
        resolver = ConfigResolver(search_dir=tmp_path)
        dut_raw, uvm_raw = resolver.split_unified(p)  # should not raise
        assert "unknown_key" not in dut_raw
        assert "unknown_key" not in uvm_raw

    def test_dut_keys_go_to_dut_section(self, tmp_path):
        p = write_unified_yaml(tmp_path)
        resolver = ConfigResolver(search_dir=tmp_path)
        dut_raw, _ = resolver.split_unified(p)
        assert "ports" in dut_raw

    def test_uvm_keys_go_to_uvm_section(self, tmp_path):
        p = write_unified_yaml(tmp_path)
        resolver = ConfigResolver(search_dir=tmp_path)
        _, uvm_raw = resolver.split_unified(p)
        assert "transactions" in uvm_raw


# ---------------------------------------------------------------------------
# _must_exist()
# ---------------------------------------------------------------------------


class TestMustExist:
    def test_returns_resolved_path_for_existing_file(self, tmp_path):
        p = tmp_path / "file.yaml"
        p.touch()
        result = ConfigResolver._must_exist(p, "--config")
        assert result == p.resolve()

    def test_raises_for_missing_file(self, tmp_path):
        p = tmp_path / "missing.yaml"
        with pytest.raises(FileNotFoundError, match="--config"):
            ConfigResolver._must_exist(p, "--config")

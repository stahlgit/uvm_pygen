"""Tests for ResolvedConfigs dataclass."""

from pathlib import Path

import pytest

from uvm_pygen.models.config_schema.resolved_configs import ResolvedConfigs


class TestResolvedConfigs:
    def test_is_unified_true_when_unified_set(self, tmp_path):
        p = tmp_path / "config.yaml"
        p.touch()
        rc = ResolvedConfigs(unified=p)
        assert rc.is_unified is True

    def test_is_unified_false_when_unified_none(self):
        rc = ResolvedConfigs(dut=Path("a.yaml"), uvm=Path("b.yaml"))
        assert rc.is_unified is False

    def test_is_split_true_when_both_set(self, tmp_path):
        d = tmp_path / "dut.yaml"
        u = tmp_path / "uvm.yaml"
        d.touch()
        u.touch()
        rc = ResolvedConfigs(dut=d, uvm=u)
        assert rc.is_split is True

    def test_is_split_true_when_only_dut_set(self, tmp_path):
        d = tmp_path / "dut.yaml"
        d.touch()
        rc = ResolvedConfigs(dut=d)
        assert rc.is_split is True

    def test_is_split_false_when_all_none(self):
        rc = ResolvedConfigs()
        assert rc.is_split is False

    def test_is_split_false_for_unified(self, tmp_path):
        p = tmp_path / "config.yaml"
        p.touch()
        rc = ResolvedConfigs(unified=p)
        assert rc.is_split is False

    def test_frozen_immutable(self, tmp_path):
        p = tmp_path / "config.yaml"
        p.touch()
        rc = ResolvedConfigs(unified=p)
        with pytest.raises(Exception):
            rc.unified = None  # type: ignore[misc]

    def test_all_fields_none_by_default(self):
        rc = ResolvedConfigs()
        assert rc.dut is None
        assert rc.uvm is None
        assert rc.unified is None

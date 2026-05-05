"""Tests for ConfigLoader — three calling modes, validation aggregation."""

import pytest

from tests.conftest import MINIMAL_DUT_RAW, MINIMAL_UVM_RAW
from uvm_pygen.services.config_parser.config_loader import ConfigLoader


class TestConfigLoaderSplitMode:
    def test_loads_from_split_yaml_files(self, dut_yaml_file, uvm_yaml_file):
        loader = ConfigLoader(dut_config_path=dut_yaml_file, uvm_config_path=uvm_yaml_file)
        assert loader.dut.dut_info.name == "test_dut"
        assert loader.uvm.testbench_name == "test_tb"

    def test_raises_if_only_dut_path_given(self, dut_yaml_file):
        with pytest.raises(ValueError, match="Both"):
            ConfigLoader(dut_config_path=dut_yaml_file)

    def test_raises_if_only_uvm_path_given(self, uvm_yaml_file):
        with pytest.raises(ValueError, match="Both"):
            ConfigLoader(uvm_config_path=uvm_yaml_file)


class TestConfigLoaderUnifiedMode:
    def test_loads_from_unified_yaml_file(self, unified_yaml_file):
        loader = ConfigLoader(unified_config_path=unified_yaml_file)
        assert loader.dut.dut_info.name == "test_dut"
        assert loader.uvm.project_name == "Test Project"


class TestConfigLoaderRawMode:
    def test_loads_from_raw_dicts(self):
        loader = ConfigLoader(dut_raw=MINIMAL_DUT_RAW, uvm_raw=MINIMAL_UVM_RAW)
        assert loader.dut.dut_info.name == "test_dut"
        assert loader.uvm.testbench_name == "test_tb"

    def test_loads_from_only_dut_raw(self):
        loader = ConfigLoader(dut_raw=MINIMAL_DUT_RAW, uvm_raw={})
        assert loader.dut.dut_info.name == "test_dut"

    def test_loads_from_only_uvm_raw(self):
        # ConfigLoader requires a parseable DUT section — empty dict lacks the
        # required "dut" key and is therefore invalid by design.
        with pytest.raises((KeyError, ValueError)):
            ConfigLoader(dut_raw={}, uvm_raw=MINIMAL_UVM_RAW)


class TestConfigLoaderConflictingArgs:
    def test_raises_for_split_plus_unified(self, dut_yaml_file, uvm_yaml_file, unified_yaml_file):
        with pytest.raises(ValueError, match="exactly one"):
            ConfigLoader(
                dut_config_path=dut_yaml_file,
                uvm_config_path=uvm_yaml_file,
                unified_config_path=unified_yaml_file,
            )

    def test_raises_for_raw_plus_unified(self, unified_yaml_file):
        with pytest.raises(ValueError, match="exactly one"):
            ConfigLoader(dut_raw=MINIMAL_DUT_RAW, unified_config_path=unified_yaml_file)

    def test_raises_for_raw_plus_split(self, dut_yaml_file, uvm_yaml_file):
        with pytest.raises(ValueError, match="exactly one"):
            ConfigLoader(dut_raw=MINIMAL_DUT_RAW, dut_config_path=dut_yaml_file, uvm_config_path=uvm_yaml_file)


class TestConfigLoaderValidation:
    def test_validate_returns_true_for_valid_config(self):
        loader = ConfigLoader(dut_raw=MINIMAL_DUT_RAW, uvm_raw=MINIMAL_UVM_RAW)
        assert loader.validate() is True

    def test_validate_returns_false_for_invalid_dut(self):
        bad_dut = {
            **MINIMAL_DUT_RAW,
            "ports": [{"name": "X", "direction": "input", "type": "logic", "width": 1, "enum_name": "no_enum"}],
        }
        loader = ConfigLoader(dut_raw=bad_dut, uvm_raw=MINIMAL_UVM_RAW)
        assert loader.validate() is False

    def test_validate_returns_false_for_invalid_uvm(self):
        bad_uvm = {
            "verification": {"project_name": "P", "testbench_name": "tb"},
            "env": {
                "interfaces": [{"name": "TestIf", "ports": ["DATA_IN"]}],
                "agents": [
                    {
                        "name": "ag",
                        "mode": "active",
                        "interface": "FakeIf",  # not declared
                        "components": ["driver", "sequencer", "monitor"],
                    }
                ],
            },
            "transactions": [{"name": "T"}],
        }
        loader = ConfigLoader(dut_raw=MINIMAL_DUT_RAW, uvm_raw=bad_uvm)
        assert loader.validate() is False

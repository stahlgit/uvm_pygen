"""Tests for UVMConfiguration — parsing, validation, and helpers."""

import pytest

from tests.conftest import MINIMAL_UVM_RAW
from uvm_pygen.constants.uvm_enum import AgentMode, ComponentType
from uvm_pygen.services.config_parser.uvm_config import UVMConfiguration

# ---------------------------------------------------------------------------
# Richer UVM raw config for advanced tests
# ---------------------------------------------------------------------------

UVM_WITH_SEQUENCES = {
    **MINIMAL_UVM_RAW,
    "sequences": [
        {"name": "base_seq", "type": "base"},
        {"name": "rand_seq", "type": "random", "extends": "base_seq"},
    ],
}

UVM_WITH_REF_MODEL = {
    "verification": {"project_name": "ALU Verification", "testbench_name": "alu_tb"},
    "env": {
        "name": "alu_env",
        "reference_model": {
            "strategy": "ap_subscriber",
            "implementation": "sv_class",
            "connects": [
                {"from": "agent.driver.ap", "to": "reference_model.analysis_export", "transaction": "TestTx"}
            ],
        },
        "interfaces": [{"name": "TestIf", "ports": ["DATA_IN", "DATA_OUT"]}],
        "agents": [
            {
                "name": "agent",
                "mode": "active",
                "interface": "TestIf",
                "transaction": "TestTx",
                "components": ["driver", "sequencer", "monitor"],
            }
        ],
    },
    "transactions": [{"name": "TestTx"}],
}


# ---------------------------------------------------------------------------
# Parsing tests
# ---------------------------------------------------------------------------


class TestUVMConfigurationParsing:
    def test_parses_project_name(self):
        uvm = UVMConfiguration.from_dict(MINIMAL_UVM_RAW)
        assert uvm.project_name == "Test Project"

    def test_parses_testbench_name(self):
        uvm = UVMConfiguration.from_dict(MINIMAL_UVM_RAW)
        assert uvm.testbench_name == "test_tb"

    def test_defaults_when_verification_missing(self):
        raw = {k: v for k, v in MINIMAL_UVM_RAW.items() if k != "verification"}
        uvm = UVMConfiguration.from_dict(raw)
        assert uvm.project_name == "uvm_project"
        assert uvm.testbench_name == "tb_top"

    def test_parses_interfaces_from_env_block(self):
        uvm = UVMConfiguration.from_dict(MINIMAL_UVM_RAW)
        assert len(uvm.interfaces) == 1
        assert uvm.interfaces[0].name == "TestIf"

    def test_parses_agents_from_env_block(self):
        uvm = UVMConfiguration.from_dict(MINIMAL_UVM_RAW)
        assert len(uvm.agents) == 1
        agent = uvm.agents[0]
        assert agent.name == "test_agent"
        assert agent.mode == AgentMode.ACTIVE

    def test_parses_agent_components(self):
        uvm = UVMConfiguration.from_dict(MINIMAL_UVM_RAW)
        agent = uvm.agents[0]
        assert ComponentType.DRIVER in agent.components
        assert ComponentType.SEQUENCER in agent.components
        assert ComponentType.MONITOR in agent.components

    def test_parses_transactions_at_top_level(self):
        uvm = UVMConfiguration.from_dict(MINIMAL_UVM_RAW)
        assert len(uvm.transactions) == 1
        assert uvm.transactions[0].name == "TestTx"

    def test_transactions_default_base_class(self):
        uvm = UVMConfiguration.from_dict(MINIMAL_UVM_RAW)
        assert uvm.transactions[0].base_class == "uvm_sequence_item"

    def test_parses_sequences(self):
        uvm = UVMConfiguration.from_dict(UVM_WITH_SEQUENCES)
        assert len(uvm.sequences) == 2
        assert uvm.sequences[0].name == "base_seq"

    def test_empty_sequences_when_absent(self):
        uvm = UVMConfiguration.from_dict(MINIMAL_UVM_RAW)
        assert uvm.sequences == []

    def test_parses_reference_model(self):
        uvm = UVMConfiguration.from_dict(UVM_WITH_REF_MODEL)
        assert uvm.reference_model is not None
        assert uvm.reference_model.connects[0].from_endpoint == "agent.driver.ap"

    def test_reference_model_none_when_absent(self):
        uvm = UVMConfiguration.from_dict(MINIMAL_UVM_RAW)
        assert uvm.reference_model is None

    def test_env_alias_environment_accepted(self):
        raw = dict(MINIMAL_UVM_RAW)
        raw["environment"] = raw.pop("env")
        uvm = UVMConfiguration.from_dict(raw)
        assert len(uvm.agents) == 1

    def test_transaction_alias_transaction_singular_accepted(self):
        raw = dict(MINIMAL_UVM_RAW)
        raw["transaction"] = raw.pop("transactions")
        uvm = UVMConfiguration.from_dict(raw)
        assert len(uvm.transactions) == 1


# ---------------------------------------------------------------------------
# Validation tests
# ---------------------------------------------------------------------------


class TestUVMConfigurationValidation:
    def test_validate_returns_empty_for_valid_config(self):
        uvm = UVMConfiguration.from_dict(MINIMAL_UVM_RAW)
        assert uvm.validate() == []

    def test_validate_error_agent_references_unknown_interface(self):
        raw = {
            "verification": {"project_name": "P", "testbench_name": "tb"},
            "env": {
                "interfaces": [{"name": "RealIf", "ports": ["DATA_IN"]}],
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
        uvm = UVMConfiguration.from_dict(raw)
        errors = uvm.validate()
        assert any("FakeIf" in e for e in errors)

    def test_validate_error_active_agent_missing_driver(self):
        raw = {
            "verification": {"project_name": "P", "testbench_name": "tb"},
            "env": {
                "interfaces": [{"name": "TestIf", "ports": ["DATA_IN"]}],
                "agents": [
                    {
                        "name": "ag",
                        "mode": "active",
                        "interface": "TestIf",
                        "components": ["sequencer", "monitor"],  # no driver
                    }
                ],
            },
            "transactions": [{"name": "T"}],
        }
        uvm = UVMConfiguration.from_dict(raw)
        errors = uvm.validate()
        assert any("driver" in e for e in errors)

    def test_validate_error_active_agent_missing_sequencer(self):
        raw = {
            "verification": {"project_name": "P", "testbench_name": "tb"},
            "env": {
                "interfaces": [{"name": "TestIf", "ports": ["DATA_IN"]}],
                "agents": [
                    {
                        "name": "ag",
                        "mode": "active",
                        "interface": "TestIf",
                        "components": ["driver", "monitor"],  # no sequencer
                    }
                ],
            },
            "transactions": [{"name": "T"}],
        }
        uvm = UVMConfiguration.from_dict(raw)
        errors = uvm.validate()
        assert any("sequencer" in e for e in errors)

    def test_validate_passive_agent_needs_no_driver(self):
        raw = {
            "verification": {"project_name": "P", "testbench_name": "tb"},
            "env": {
                "interfaces": [{"name": "TestIf", "ports": ["DATA_OUT"]}],
                "agents": [
                    {
                        "name": "monitor_agent",
                        "mode": "passive",
                        "interface": "TestIf",
                        "components": ["monitor"],
                    }
                ],
            },
            "transactions": [{"name": "T"}],
        }
        uvm = UVMConfiguration.from_dict(raw)
        assert uvm.validate() == []


# ---------------------------------------------------------------------------
# Helper methods
# ---------------------------------------------------------------------------


class TestUVMConfigurationHelpers:
    def test_get_sequence_by_name(self):
        uvm = UVMConfiguration.from_dict(UVM_WITH_SEQUENCES)
        seq = uvm.get_sequence("rand_seq")
        assert seq is not None
        assert seq.extends == "base_seq"

    def test_get_sequence_returns_none_for_unknown(self):
        uvm = UVMConfiguration.from_dict(MINIMAL_UVM_RAW)
        assert uvm.get_sequence("missing") is None

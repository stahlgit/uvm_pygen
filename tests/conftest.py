"""Shared fixtures and raw data for all test phases."""

from pathlib import Path

import pytest
import yaml

from uvm_pygen.constants.uvm_enum import AgentMode, ComponentType, Direction
from uvm_pygen.models.logic_schema.agent_model import AgentModel
from uvm_pygen.models.logic_schema.env_model import EnvModel
from uvm_pygen.models.logic_schema.interface_model import InterfaceModel
from uvm_pygen.models.logic_schema.transaction_model import SvVariable, TransactionModel
from uvm_pygen.services.config_parser.config_loader import ConfigLoader
from uvm_pygen.services.config_parser.dut_config import DUTConfiguration
from uvm_pygen.services.config_parser.uvm_config import UVMConfiguration

# ---------------------------------------------------------------------------
# Module-level raw dicts — used both as fixtures and directly in tests
# ---------------------------------------------------------------------------

MINIMAL_DUT_RAW: dict = {
    "dut": {
        "name": "test_dut",
        "entity_name": "TEST_ENT",
        "reset_type": "active_high",
        "language": "systemverilog",
    },
    "ports": [
        {"name": "CLK", "direction": "input", "type": "logic", "width": 1, "is_clock": True},
        {
            "name": "RST",
            "direction": "input",
            "type": "logic",
            "width": 1,
            "is_reset": True,
            "active_level": "active_high",
        },
        {"name": "DATA_IN", "direction": "input", "type": "logic", "width": 8},
        {"name": "DATA_OUT", "direction": "output", "type": "logic", "width": 8},
    ],
}

MINIMAL_UVM_RAW: dict = {
    "verification": {
        "project_name": "Test Project",
        "testbench_name": "test_tb",
    },
    "env": {
        "name": "test_env",
        "interfaces": [
            {"name": "TestIf", "ports": ["DATA_IN", "DATA_OUT"]},
        ],
        "agents": [
            {
                "name": "test_agent",
                "mode": "active",
                "interface": "TestIf",
                "transaction": "TestTx",
                "components": ["driver", "sequencer", "monitor"],
            }
        ],
    },
    "transactions": [
        {"name": "TestTx", "base_class": "uvm_sequence_item", "field_overrides": []},
    ],
}

# ---------------------------------------------------------------------------
# Helpers for writing temp YAML files
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).parent.parent


def write_dut_yaml(path: Path) -> Path:
    p = path / "config_dut.yaml"
    p.write_text(yaml.dump(MINIMAL_DUT_RAW))
    return p


def write_uvm_yaml(path: Path) -> Path:
    p = path / "config_uvm.yaml"
    p.write_text(yaml.dump(MINIMAL_UVM_RAW))
    return p


def write_unified_yaml(path: Path) -> Path:
    combined = {**MINIMAL_DUT_RAW, **MINIMAL_UVM_RAW}
    p = path / "config.yaml"
    p.write_text(yaml.dump(combined))
    return p


# ---------------------------------------------------------------------------
# File fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def dut_yaml_file(tmp_path):
    return write_dut_yaml(tmp_path)


@pytest.fixture
def uvm_yaml_file(tmp_path):
    return write_uvm_yaml(tmp_path)


@pytest.fixture
def unified_yaml_file(tmp_path):
    return write_unified_yaml(tmp_path)


# ---------------------------------------------------------------------------
# Config object fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def minimal_dut():
    return DUTConfiguration.from_dict(MINIMAL_DUT_RAW)


@pytest.fixture
def minimal_uvm():
    return UVMConfiguration.from_dict(MINIMAL_UVM_RAW)


@pytest.fixture
def minimal_loader():
    return ConfigLoader(dut_raw=MINIMAL_DUT_RAW, uvm_raw=MINIMAL_UVM_RAW)


# ---------------------------------------------------------------------------
# Logic model fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def port_data_in():
    from uvm_pygen.models.config_schema.dut_dataclass import Port

    return Port(name="DATA_IN", direction="input", type="logic", width=8)


@pytest.fixture
def port_data_out():
    from uvm_pygen.models.config_schema.dut_dataclass import Port

    return Port(name="DATA_OUT", direction="output", type="logic", width=8)


@pytest.fixture
def minimal_interface(port_data_in, port_data_out):
    return InterfaceModel(name="TestIf", ports=[port_data_in, port_data_out])


@pytest.fixture
def minimal_agent(minimal_interface):
    return AgentModel(
        name="test_agent",
        mode=AgentMode.ACTIVE,
        interface_instance=minimal_interface,
        transaction="TestTx",
        parts=frozenset([ComponentType.DRIVER, ComponentType.SEQUENCER, ComponentType.MONITOR]),
    )


@pytest.fixture
def minimal_transaction():
    return TransactionModel(
        class_name="TestTx",
        base_class="uvm_sequence_item",
        variables=[
            SvVariable(name="data_in", sv_type="logic [7:0]", is_rand=True, direction=Direction.INPUT),
            SvVariable(name="data_out", sv_type="logic [7:0]", is_rand=False, direction=Direction.OUTPUT),
        ],
    )


@pytest.fixture
def minimal_env_model(minimal_agent, minimal_interface, minimal_transaction):
    return EnvModel(
        project_name="Test Project",
        testbench_name="test_tb",
        agents=[minimal_agent],
        interfaces=[minimal_interface],
        transactions=[minimal_transaction],
    )

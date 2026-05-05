"""Tests for DUTConfiguration — parsing, validation, and helpers."""

import pytest

from tests.conftest import MINIMAL_DUT_RAW
from uvm_pygen.constants.uvm_enum import ActiveLevel, Direction
from uvm_pygen.models.config_schema.dut_dataclass import Port
from uvm_pygen.services.config_parser.dut_config import DUTConfiguration

# ---------------------------------------------------------------------------
# DUT with enums and parameters — used for richer tests
# ---------------------------------------------------------------------------

DUT_WITH_ENUMS = {
    "dut": {
        "name": "alu",
        "entity_name": "ALU_ENT",
        "reset_type": "active_high",
        "language": "systemverilog",
    },
    "params": [
        {"name": "DATA_WIDTH", "value": 8},
        {"name": "OUTPUT_WIDTH", "value": 16},
    ],
    "enumerations": {
        "operation_t": {
            "type": "logic [3:0]",
            "values": [
                {"value": 0, "name": "ADD", "description": "Addition"},
                {"value": 1, "name": "SUB", "description": "Subtraction"},
            ],
        }
    },
    "ports": [
        {"name": "CLK", "direction": "input", "type": "logic", "width": 1, "is_clock": True},
        {"name": "RST", "direction": "input", "type": "logic", "width": 1, "is_reset": True, "active_level": "high"},
        {"name": "ACT", "direction": "input", "type": "logic", "width": 1},
        {"name": "OP", "direction": "input", "type": "logic", "width": "(3:0)", "enum_name": "operation_t"},
        {"name": "DATA", "direction": "input", "type": "logic", "width": "DATA_WIDTH"},
        {"name": "RESULT", "direction": "output", "type": "logic", "width": "OUTPUT_WIDTH"},
    ],
}


# ---------------------------------------------------------------------------
# Parsing tests
# ---------------------------------------------------------------------------


class TestDUTConfigurationParsing:
    def test_parses_dut_info(self):
        dut = DUTConfiguration.from_dict(MINIMAL_DUT_RAW)
        assert dut.dut_info.name == "test_dut"
        assert dut.dut_info.entity_name == "TEST_ENT"
        assert dut.dut_info.reset_type == ActiveLevel.ACTIVE_HIGH

    def test_parses_parameters_via_params_alias(self):
        dut = DUTConfiguration.from_dict(DUT_WITH_ENUMS)
        assert len(dut.parameters) == 2
        assert dut.parameters[0].name == "DATA_WIDTH"
        assert dut.parameters[0].value == 8

    def test_parses_enums_via_enumerations_alias(self):
        dut = DUTConfiguration.from_dict(DUT_WITH_ENUMS)
        assert "operation_t" in dut.enums
        enum = dut.enums["operation_t"]
        assert enum.type == "logic [3:0]"
        assert len(enum.values) == 2

    def test_parses_enum_values(self):
        dut = DUTConfiguration.from_dict(DUT_WITH_ENUMS)
        enum = dut.enums["operation_t"]
        assert enum.values[0].name == "ADD"
        assert enum.values[0].value == "0"  # coerced to str

    def test_parses_ports(self):
        dut = DUTConfiguration.from_dict(MINIMAL_DUT_RAW)
        assert len(dut.ports) == 4
        names = {p.name for p in dut.ports}
        assert names == {"CLK", "RST", "DATA_IN", "DATA_OUT"}

    def test_parses_port_directions(self):
        dut = DUTConfiguration.from_dict(MINIMAL_DUT_RAW)
        port_map = {p.name: p for p in dut.ports}
        assert port_map["DATA_IN"].direction == Direction.INPUT
        assert port_map["DATA_OUT"].direction == Direction.OUTPUT

    def test_no_parameters_when_absent(self):
        dut = DUTConfiguration.from_dict(MINIMAL_DUT_RAW)
        assert dut.parameters == []

    def test_no_enums_when_absent(self):
        dut = DUTConfiguration.from_dict(MINIMAL_DUT_RAW)
        assert dut.enums == {}


# ---------------------------------------------------------------------------
# Validation tests
# ---------------------------------------------------------------------------


class TestDUTConfigurationValidation:
    def test_validate_returns_empty_for_valid_config(self):
        dut = DUTConfiguration.from_dict(MINIMAL_DUT_RAW)
        assert dut.validate() == []

    def test_validate_resolves_enum_references_on_ports(self):
        dut = DUTConfiguration.from_dict(DUT_WITH_ENUMS)
        dut.validate()
        op_port = dut.get_port("OP")
        assert op_port is not None
        assert op_port.enum_def is not None
        assert op_port.enum_def.name == "operation_t"

    def test_validate_returns_error_for_unknown_enum_ref(self):
        raw = {
            **MINIMAL_DUT_RAW,
            "ports": [{"name": "SIG", "direction": "input", "type": "logic", "width": 4, "enum_name": "no_such_enum"}],
        }
        dut = DUTConfiguration.from_dict(raw)
        errors = dut.validate()
        assert any("no_such_enum" in e for e in errors)


# ---------------------------------------------------------------------------
# Helper methods
# ---------------------------------------------------------------------------


class TestDUTConfigurationHelpers:
    def test_get_clock_ports(self):
        dut = DUTConfiguration.from_dict(MINIMAL_DUT_RAW)
        clocks = dut.get_clock_ports()
        assert len(clocks) == 1
        assert clocks[0].name == "CLK"

    def test_get_reset_ports(self):
        dut = DUTConfiguration.from_dict(MINIMAL_DUT_RAW)
        resets = dut.get_reset_ports()
        assert len(resets) == 1
        assert resets[0].name == "RST"

    def test_get_signal_ports_excludes_clock_and_reset(self):
        dut = DUTConfiguration.from_dict(MINIMAL_DUT_RAW)
        signals = dut.get_signal_ports()
        names = {p.name for p in signals}
        assert "CLK" not in names
        assert "RST" not in names
        assert "DATA_IN" in names
        assert "DATA_OUT" in names

    def test_get_enum_returns_matching_enum(self):
        dut = DUTConfiguration.from_dict(DUT_WITH_ENUMS)
        enum = dut.get_enum("operation_t")
        assert enum is not None
        assert enum.name == "operation_t"

    def test_get_enum_returns_none_for_unknown(self):
        dut = DUTConfiguration.from_dict(MINIMAL_DUT_RAW)
        assert dut.get_enum("nonexistent") is None

    def test_get_port_returns_matching_port(self):
        dut = DUTConfiguration.from_dict(MINIMAL_DUT_RAW)
        port = dut.get_port("DATA_IN")
        assert port is not None
        assert port.name == "DATA_IN"

    def test_get_port_returns_none_for_unknown(self):
        dut = DUTConfiguration.from_dict(MINIMAL_DUT_RAW)
        assert dut.get_port("NONEXISTENT") is None


# ---------------------------------------------------------------------------
# resolve_width()
# ---------------------------------------------------------------------------


class TestResolveWidth:
    def test_int_passthrough(self):
        dut = DUTConfiguration.from_dict(DUT_WITH_ENUMS)
        assert dut.resolve_width(4) == 4

    def test_bus_notation_string(self):
        dut = DUTConfiguration.from_dict(DUT_WITH_ENUMS)
        assert dut.resolve_width("(7:0)") == 8

    def test_bus_notation_bracket_style(self):
        dut = DUTConfiguration.from_dict(DUT_WITH_ENUMS)
        assert dut.resolve_width("[3:0]") == 4

    def test_parameter_reference(self):
        dut = DUTConfiguration.from_dict(DUT_WITH_ENUMS)
        assert dut.resolve_width("DATA_WIDTH") == 8

    def test_raises_for_arithmetic_expression(self):
        # (DATA_WIDTH-1:0) contains a hyphen so the bus-notation regex won't
        # match it; it falls through to "Cannot resolve width:" — not the
        # "Arithmetic in bus width" branch (which only fires when the regex
        # matches but the captured groups are non-numeric identifiers).
        dut = DUTConfiguration.from_dict(DUT_WITH_ENUMS)
        with pytest.raises(ValueError, match="Cannot resolve"):
            dut.resolve_width("(DATA_WIDTH-1:0)")

    def test_raises_for_unknown_string(self):
        dut = DUTConfiguration.from_dict(MINIMAL_DUT_RAW)
        with pytest.raises(ValueError, match="Cannot resolve"):
            dut.resolve_width("NO_SUCH_PARAM")

    def test_raises_for_wrong_type(self):
        dut = DUTConfiguration.from_dict(MINIMAL_DUT_RAW)
        with pytest.raises(TypeError):
            dut.resolve_width([8])  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Port field validators
# ---------------------------------------------------------------------------


class TestPortValidators:
    def test_coerce_width_string_digit_to_int(self):
        port = Port(name="X", direction="input", type="logic", width="8")
        assert port.width == 8

    def test_coerce_width_int_unchanged(self):
        port = Port(name="X", direction="input", type="logic", width=4)
        assert port.width == 4

    def test_coerce_width_bus_expression_kept_as_string(self):
        port = Port(name="X", direction="input", type="logic", width="(7:0)")
        assert port.width == "(7:0)"

    def test_normalize_type_std_logic_to_logic(self):
        port = Port(name="X", direction="input", type="std_logic", width=1)
        assert port.type == "logic"

    def test_normalize_type_std_logic_vector_to_logic(self):
        port = Port(name="X", direction="input", type="std_logic_vector", width=8)
        assert port.type == "logic"

    def test_normalize_type_logic_unchanged(self):
        port = Port(name="X", direction="input", type="logic", width=1)
        assert port.type == "logic"

    def test_active_level_high_alias(self):
        port = Port(name="RST", direction="input", type="logic", width=1, active_level="high")
        assert port.active_level == ActiveLevel.ACTIVE_HIGH

    def test_active_level_low_alias(self):
        port = Port(name="RST", direction="input", type="logic", width=1, active_level="low")
        assert port.active_level == ActiveLevel.ACTIVE_LOW

    def test_direction_in_alias(self):
        port = Port(name="X", direction="in", type="logic", width=1)
        assert port.direction == Direction.INPUT

    def test_direction_out_alias(self):
        port = Port(name="X", direction="out", type="logic", width=1)
        assert port.direction == Direction.OUTPUT

    def test_direction_io_alias(self):
        port = Port(name="X", direction="io", type="logic", width=1)
        assert port.direction == Direction.INOUT

    def test_direction_bidirectional_alias(self):
        port = Port(name="X", direction="bidirectional", type="logic", width=1)
        assert port.direction == Direction.INOUT

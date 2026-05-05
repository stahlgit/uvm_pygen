"""Tests for ModelBuilder — transform raw configs into logic models."""

import pytest

from tests.conftest import MINIMAL_DUT_RAW, MINIMAL_UVM_RAW
from uvm_pygen.constants.uvm_enum import AgentMode, ComponentType, ReferenceModelStrategy
from uvm_pygen.models.config_schema.dut_dataclass import Port
from uvm_pygen.services.config_parser.config_loader import ConfigLoader
from uvm_pygen.services.model_builder.model_builder import ModelBuilder


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_builder(dut_raw: dict, uvm_raw: dict) -> ModelBuilder:
    loader = ConfigLoader(dut_raw=dut_raw, uvm_raw=uvm_raw)
    return ModelBuilder(loader)


def make_env(dut_raw: dict, uvm_raw: dict):
    return make_builder(dut_raw, uvm_raw).build()


# ---------------------------------------------------------------------------
# build() — happy path
# ---------------------------------------------------------------------------


class TestModelBuilderBuild:
    def test_build_returns_env_model(self):
        env = make_env(MINIMAL_DUT_RAW, MINIMAL_UVM_RAW)
        assert env is not None

    def test_env_model_has_correct_project_name(self):
        env = make_env(MINIMAL_DUT_RAW, MINIMAL_UVM_RAW)
        assert env.project_name == "Test Project"

    def test_env_model_has_correct_testbench_name(self):
        env = make_env(MINIMAL_DUT_RAW, MINIMAL_UVM_RAW)
        assert env.testbench_name == "test_tb"

    def test_env_model_has_correct_dut_name(self):
        env = make_env(MINIMAL_DUT_RAW, MINIMAL_UVM_RAW)
        assert env.dut_instance_name == "test_dut"

    def test_build_creates_one_interface(self):
        env = make_env(MINIMAL_DUT_RAW, MINIMAL_UVM_RAW)
        assert len(env.interfaces) == 1
        assert env.interfaces[0].name == "TestIf"

    def test_build_creates_one_agent(self):
        env = make_env(MINIMAL_DUT_RAW, MINIMAL_UVM_RAW)
        assert len(env.agents) == 1
        assert env.agents[0].name == "test_agent"

    def test_build_creates_one_transaction(self):
        env = make_env(MINIMAL_DUT_RAW, MINIMAL_UVM_RAW)
        assert len(env.transactions) == 1
        assert env.transactions[0].class_name == "TestTx"

    def test_build_no_reference_model_when_not_configured(self):
        env = make_env(MINIMAL_DUT_RAW, MINIMAL_UVM_RAW)
        assert env.reference_model is None

    def test_build_forwards_parameters(self):
        dut_raw = {
            **MINIMAL_DUT_RAW,
            "params": [{"name": "DATA_WIDTH", "value": 8}],
        }
        env = make_env(dut_raw, MINIMAL_UVM_RAW)
        assert len(env.parameters) == 1
        assert env.parameters[0].name == "DATA_WIDTH"

    def test_build_agent_has_correct_mode(self):
        env = make_env(MINIMAL_DUT_RAW, MINIMAL_UVM_RAW)
        assert env.agents[0].mode == AgentMode.ACTIVE

    def test_build_agent_has_driver_component(self):
        env = make_env(MINIMAL_DUT_RAW, MINIMAL_UVM_RAW)
        assert env.agents[0].has(ComponentType.DRIVER)

    def test_build_raises_for_unknown_agent_interface(self):
        bad_uvm = {
            **MINIMAL_UVM_RAW,
            "env": {
                **MINIMAL_UVM_RAW["env"],
                "agents": [
                    {
                        "name": "ag",
                        "mode": "active",
                        "interface": "NonExistentIf",
                        "transaction": "TestTx",
                        "components": ["driver", "sequencer", "monitor"],
                    }
                ],
            },
        }
        builder = make_builder(MINIMAL_DUT_RAW, bad_uvm)
        with pytest.raises(ValueError, match="unknown interface"):
            builder.build()


# ---------------------------------------------------------------------------
# build() — reference model
# ---------------------------------------------------------------------------


class TestModelBuilderReferenceModel:
    def _uvm_with_rm(self, strategy: str = "ap_subscriber") -> dict:
        return {
            "verification": {"project_name": "P", "testbench_name": "tb"},
            "env": {
                "name": "env",
                "reference_model": {
                    "strategy": strategy,
                    "implementation": "sv_class",
                    "connects": [
                        {"from": "test_agent.driver.ap", "to": "reference_model.analysis_export", "transaction": "TestTx"}
                    ],
                },
                "interfaces": [{"name": "TestIf", "ports": ["DATA_IN", "DATA_OUT"]}],
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
            "transactions": [{"name": "TestTx"}],
        }

    def test_builds_reference_model(self):
        env = make_env(MINIMAL_DUT_RAW, self._uvm_with_rm())
        assert env.reference_model is not None
        assert env.reference_model.strategy == ReferenceModelStrategy.AP_SUBSCRIBER

    def test_reference_model_has_resolved_connections(self):
        env = make_env(MINIMAL_DUT_RAW, self._uvm_with_rm())
        assert len(env.reference_model.connections) == 1
        conn = env.reference_model.connections[0]
        assert conn.from_component == "test_agent"
        assert conn.to_component == "reference_model"

    def test_raises_for_multiple_active_agents_with_ap_subscriber(self):
        uvm_raw = {
            "verification": {"project_name": "P", "testbench_name": "tb"},
            "env": {
                "reference_model": {"strategy": "ap_subscriber", "implementation": "sv_class", "connects": []},
                "interfaces": [
                    {"name": "If1", "ports": ["DATA_IN"]},
                    {"name": "If2", "ports": ["DATA_OUT"]},
                ],
                "agents": [
                    {
                        "name": "ag1",
                        "mode": "active",
                        "interface": "If1",
                        "components": ["driver", "sequencer", "monitor"],
                    },
                    {
                        "name": "ag2",
                        "mode": "active",
                        "interface": "If2",
                        "components": ["driver", "sequencer", "monitor"],
                    },
                ],
            },
            "transactions": [{"name": "T"}],
        }
        builder = make_builder(MINIMAL_DUT_RAW, uvm_raw)
        with pytest.raises(NotImplementedError):
            builder.build()

    def test_raises_for_dual_agent_without_two_active(self):
        # Only 1 active agent but dual_agent strategy
        uvm_raw = {
            "verification": {"project_name": "P", "testbench_name": "tb"},
            "env": {
                "reference_model": {"strategy": "dual_agent", "implementation": "sv_class", "connects": []},
                "interfaces": [{"name": "TestIf", "ports": ["DATA_IN"]}],
                "agents": [
                    {
                        "name": "ag",
                        "mode": "active",
                        "interface": "TestIf",
                        "components": ["driver", "sequencer", "monitor"],
                    }
                ],
            },
            "transactions": [{"name": "T"}],
        }
        builder = make_builder(MINIMAL_DUT_RAW, uvm_raw)
        with pytest.raises(ValueError, match="dual_agent"):
            builder.build()


# ---------------------------------------------------------------------------
# _get_sv_type_from_port()
# ---------------------------------------------------------------------------


class TestGetSvTypeFromPort:
    def _port(self, **kwargs):
        defaults = {"name": "X", "direction": "input", "type": "logic"}
        return Port(**{**defaults, **kwargs})

    def _builder(self) -> ModelBuilder:
        loader = ConfigLoader(dut_raw=MINIMAL_DUT_RAW, uvm_raw=MINIMAL_UVM_RAW)
        return ModelBuilder(loader)

    def test_1bit_port_returns_plain_logic(self):
        b = self._builder()
        port = self._port(width=1)
        assert b._get_sv_type_from_port(port) == "logic"

    def test_8bit_port_returns_logic_range(self):
        b = self._builder()
        port = self._port(width=8)
        assert b._get_sv_type_from_port(port) == "logic [7:0]"

    def test_bus_notation_port(self):
        b = self._builder()
        port = self._port(width="(3:0)")
        result = b._get_sv_type_from_port(port)
        assert "[3:0]" in result

    def test_parameter_reference_port(self):
        b = self._builder()
        port = self._port(width="DATA_WIDTH")
        result = b._get_sv_type_from_port(port)
        assert "DATA_WIDTH" in result

    def test_enum_port_returns_enum_type_name(self):
        from uvm_pygen.models.config_schema.dut_dataclass import EnumType, EnumValue

        b = self._builder()
        enum = EnumType(name="my_enum", type="logic [3:0]", values=[EnumValue(name="A", value="0")])
        port = self._port(width="(3:0)", enum_name="my_enum")
        object.__setattr__(port, "enum_def", enum)
        assert b._get_sv_type_from_port(port) == "my_enum"


# ---------------------------------------------------------------------------
# _get_range_from_port()
# ---------------------------------------------------------------------------


class TestGetRangeFromPort:
    def _port(self, **kwargs):
        defaults = {"name": "X", "direction": "input", "type": "logic"}
        return Port(**{**defaults, **kwargs})

    def _builder(self) -> ModelBuilder:
        loader = ConfigLoader(dut_raw=MINIMAL_DUT_RAW, uvm_raw=MINIMAL_UVM_RAW)
        return ModelBuilder(loader)

    def test_1bit_returns_empty_string(self):
        b = self._builder()
        assert b._get_range_from_port(self._port(width=1)) == ""

    def test_8bit_returns_bracket_range(self):
        b = self._builder()
        assert b._get_range_from_port(self._port(width=8)) == "[7:0]"

    def test_bus_notation_converts_parens_to_brackets(self):
        b = self._builder()
        result = b._get_range_from_port(self._port(width="(7:0)"))
        assert result == "[7:0]"

    def test_parameter_width_returns_expression(self):
        b = self._builder()
        result = b._get_range_from_port(self._port(width="DATA_WIDTH"))
        assert "DATA_WIDTH" in result


# ---------------------------------------------------------------------------
# _parse_endpoint()
# ---------------------------------------------------------------------------


class TestParseEndpoint:
    def _builder(self) -> ModelBuilder:
        loader = ConfigLoader(dut_raw=MINIMAL_DUT_RAW, uvm_raw=MINIMAL_UVM_RAW)
        return ModelBuilder(loader)

    def test_splits_component_and_port(self):
        b = self._builder()
        component, port = b._parse_endpoint("agent.m_driver.ap", {"agent"}, {})
        assert component == "agent"
        assert port == "m_driver.ap"

    def test_raises_for_endpoint_without_dot(self):
        b = self._builder()
        with pytest.raises(ValueError, match="expected '<component>.<port>'"):
            b._parse_endpoint("bad_endpoint", set(), {})

    def test_resolves_driver_ap_alias(self):
        b = self._builder()
        aliases = {"driver.ap": "m_driver.ap"}
        _, port = b._parse_endpoint("agent.driver.ap", {"agent"}, aliases)
        assert port == "m_driver.ap"

    def test_resolves_monitor_ap_alias(self):
        b = self._builder()
        aliases = {"monitor.ap": "m_monitor.analysis_port"}
        _, port = b._parse_endpoint("agent.monitor.ap", {"agent"}, aliases)
        assert port == "m_monitor.analysis_port"

    def test_unknown_port_passed_through_unchanged(self):
        b = self._builder()
        _, port = b._parse_endpoint("agent.custom_port", {"agent"}, {})
        assert port == "custom_port"


# ---------------------------------------------------------------------------
# _build_interface_models() — port group resolution
# ---------------------------------------------------------------------------


class TestBuildInterfaceModels:
    def test_interface_resolves_individual_port_names(self):
        env = make_env(MINIMAL_DUT_RAW, MINIMAL_UVM_RAW)
        iface = env.interfaces[0]
        port_names = {p.name for p in iface.ports}
        assert "DATA_IN" in port_names
        assert "DATA_OUT" in port_names

    def test_interface_excludes_clock_from_ports(self):
        # Clock ports should NOT appear in interface.ports
        env = make_env(MINIMAL_DUT_RAW, MINIMAL_UVM_RAW)
        iface = env.interfaces[0]
        port_names = {p.name for p in iface.ports}
        assert "CLK" not in port_names

    def test_interface_port_group_expansion(self):
        # Using group name "Control Signals" — all ports in that group get added
        dut_raw = {
            "dut": {"name": "dut", "entity_name": "DUT", "reset_type": "active_high", "language": "sv"},
            "ports": [
                {"name": "CLK", "direction": "input", "type": "logic", "width": 1, "is_clock": True, "group": "Control"},
                {"name": "RST", "direction": "input", "type": "logic", "width": 1, "is_reset": True, "group": "Control"},
                {"name": "EN", "direction": "input", "type": "logic", "width": 1, "group": "Control"},
                {"name": "DATA", "direction": "input", "type": "logic", "width": 8},
            ],
        }
        uvm_raw = {
            "verification": {"project_name": "P", "testbench_name": "tb"},
            "env": {
                "interfaces": [{"name": "Iface", "ports": ["Control"]}],
                "agents": [
                    {
                        "name": "ag",
                        "mode": "active",
                        "interface": "Iface",
                        "transaction": "T",
                        "components": ["driver", "sequencer", "monitor"],
                    }
                ],
            },
            "transactions": [{"name": "T"}],
        }
        env = make_env(dut_raw, uvm_raw)
        port_names = {p.name for p in env.interfaces[0].ports}
        # EN is in the group; CLK/RST are filtered out as clock/reset
        assert "EN" in port_names

    def test_unknown_port_in_interface_is_skipped(self):
        uvm_raw = {
            **MINIMAL_UVM_RAW,
            "env": {
                **MINIMAL_UVM_RAW["env"],
                "interfaces": [{"name": "TestIf", "ports": ["DATA_IN", "NONEXISTENT"]}],
            },
        }
        # Should not raise — unknown port is skipped with warning
        env = make_env(MINIMAL_DUT_RAW, uvm_raw)
        port_names = {p.name for p in env.interfaces[0].ports}
        assert "NONEXISTENT" not in port_names
        assert "DATA_IN" in port_names


# ---------------------------------------------------------------------------
# _build_transactions() — variable building and field overrides
# ---------------------------------------------------------------------------


class TestBuildTransactions:
    def test_transaction_variables_exclude_clock(self):
        # Clock port should never become a transaction variable
        env = make_env(MINIMAL_DUT_RAW, MINIMAL_UVM_RAW)
        tx = env.transactions[0]
        var_names = {v.name for v in tx.variables}
        assert "clk" not in var_names

    def test_transaction_variables_exclude_reset(self):
        env = make_env(MINIMAL_DUT_RAW, MINIMAL_UVM_RAW)
        tx = env.transactions[0]
        var_names = {v.name for v in tx.variables}
        assert "rst" not in var_names

    def test_field_override_disables_randomization(self):
        uvm_raw = {
            **MINIMAL_UVM_RAW,
            "transactions": [
                {
                    "name": "TestTx",
                    "field_overrides": [{"name": "data_in", "randomize": False, "default": 0}],
                }
            ],
        }
        env = make_env(MINIMAL_DUT_RAW, uvm_raw)
        tx = env.transactions[0]
        var = next((v for v in tx.variables if v.name == "data_in"), None)
        assert var is not None
        assert var.is_rand is False

    def test_field_override_sets_default_value(self):
        uvm_raw = {
            **MINIMAL_UVM_RAW,
            "transactions": [
                {
                    "name": "TestTx",
                    "field_overrides": [{"name": "data_in", "randomize": False, "default": 42}],
                }
            ],
        }
        env = make_env(MINIMAL_DUT_RAW, uvm_raw)
        tx = env.transactions[0]
        var = next((v for v in tx.variables if v.name == "data_in"), None)
        assert var is not None
        assert var.default_value == "42"


# ---------------------------------------------------------------------------
# _build_scoreboard_model() — explicit connections vs. monitor fallback
# ---------------------------------------------------------------------------


class TestBuildScoreboardModel:
    def test_scoreboard_fallback_from_monitor_agent(self):
        env = make_env(MINIMAL_DUT_RAW, MINIMAL_UVM_RAW)
        # No reference model → scoreboard built from monitor agents
        sb = env.scoreboard
        assert sb is not None
        assert len(sb.exports) == 1
        assert sb.exports[0].agent_name == "test_agent"
        assert sb.exports[0].role == "actual"

    def test_scoreboard_from_explicit_connections(self):
        uvm_raw = {
            "verification": {"project_name": "P", "testbench_name": "tb"},
            "env": {
                "reference_model": {
                    "strategy": "ap_subscriber",
                    "implementation": "sv_class",
                    "connects": [
                        {
                            "from": "test_agent.monitor.ap",
                            "to": "scoreboard.actual_export",
                            "transaction": "TestTx",
                        },
                        {
                            "from": "reference_model.ap_expected",
                            "to": "scoreboard.expected_export",
                            "transaction": "TestTx",
                        },
                    ],
                },
                "interfaces": [{"name": "TestIf", "ports": ["DATA_IN", "DATA_OUT"]}],
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
            "transactions": [{"name": "TestTx"}],
        }
        env = make_env(MINIMAL_DUT_RAW, uvm_raw)
        sb = env.scoreboard
        roles = {e.role for e in sb.exports}
        assert "actual" in roles
        assert "expected" in roles

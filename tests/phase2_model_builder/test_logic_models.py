"""Tests for logic schema models — SvVariable, TransactionModel, AgentModel, etc."""

import pytest

from uvm_pygen.constants.uvm_enum import AgentMode, ComponentType, Direction
from uvm_pygen.models.config_schema.dut_dataclass import Port
from uvm_pygen.models.logic_schema.agent_model import AgentModel
from uvm_pygen.models.logic_schema.env_model import EnvModel
from uvm_pygen.models.logic_schema.interface_model import InterfaceModel
from uvm_pygen.models.logic_schema.reference_model import ResolvedConnection
from uvm_pygen.models.logic_schema.scoreboard_model import ScoreboardExport, ScoreboardModel
from uvm_pygen.models.logic_schema.transaction_model import SvVariable, TransactionModel


# ---------------------------------------------------------------------------
# SvVariable
# ---------------------------------------------------------------------------


class TestSvVariable:
    def test_uvm_field_macro_logic(self):
        v = SvVariable(name="data", sv_type="logic", is_rand=True)
        assert v.uvm_field_macro == "`uvm_field_int(data, UVM_ALL_ON)"

    def test_uvm_field_macro_logic_array(self):
        v = SvVariable(name="data", sv_type="logic [7:0]", is_rand=True)
        assert v.uvm_field_macro == "`uvm_field_int(data, UVM_ALL_ON)"

    def test_uvm_field_macro_enum(self):
        v = SvVariable(name="op", sv_type="operation_t", is_rand=True, is_enum=True)
        assert v.uvm_field_macro == "`uvm_field_enum(operation_t, op, UVM_ALL_ON)"

    def test_uvm_field_macro_string(self):
        v = SvVariable(name="msg", sv_type="string", is_rand=False)
        assert v.uvm_field_macro == "`uvm_field_string(msg, UVM_ALL_ON)"

    def test_uvm_field_macro_uvm_object(self):
        v = SvVariable(name="cfg", sv_type="uvm_object", is_rand=False)
        assert v.uvm_field_macro == "`uvm_field_object(cfg, UVM_ALL_ON)"

    def test_is_enum_with_primitive_type_raises(self):
        with pytest.raises(ValueError, match="primitive"):
            SvVariable(name="x", sv_type="logic", is_rand=True, is_enum=True)

    def test_is_enum_with_bit_type_raises(self):
        with pytest.raises(ValueError, match="primitive"):
            SvVariable(name="x", sv_type="bit", is_rand=True, is_enum=True)

    def test_default_value_none_by_default(self):
        v = SvVariable(name="x", sv_type="logic", is_rand=True)
        assert v.default_value is None

    def test_immutable_after_construction(self):
        v = SvVariable(name="x", sv_type="logic", is_rand=True)
        with pytest.raises(Exception):
            v.name = "y"  # type: ignore[misc]

    def test_direction_stored(self):
        v = SvVariable(name="data", sv_type="logic [7:0]", is_rand=True, direction=Direction.INPUT)
        assert v.direction == Direction.INPUT


# ---------------------------------------------------------------------------
# TransactionModel
# ---------------------------------------------------------------------------


class TestTransactionModel:
    def test_rand_variables(self, minimal_transaction):
        rand_vars = minimal_transaction.rand_variables
        assert all(v.is_rand for v in rand_vars)
        assert any(v.name == "data_in" for v in rand_vars)

    def test_nonrand_variables(self, minimal_transaction):
        nonrand_vars = minimal_transaction.nonrand_variables
        assert all(not v.is_rand for v in nonrand_vars)
        assert any(v.name == "data_out" for v in nonrand_vars)

    def test_rand_and_nonrand_are_complementary(self, minimal_transaction):
        total = len(minimal_transaction.variables)
        assert len(minimal_transaction.rand_variables) + len(minimal_transaction.nonrand_variables) == total

    def test_empty_variables_by_default(self):
        tx = TransactionModel(class_name="T")
        assert tx.variables == []

    def test_default_base_class(self):
        tx = TransactionModel(class_name="T")
        assert tx.base_class == "uvm_sequence_item"

    def test_immutable_after_construction(self):
        tx = TransactionModel(class_name="T")
        with pytest.raises(Exception):
            tx.class_name = "X"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# InterfaceModel
# ---------------------------------------------------------------------------


class TestInterfaceModel:
    def test_rejects_empty_ports_list(self):
        with pytest.raises(ValueError, match="at least one port"):
            InterfaceModel(name="BadIf", ports=[])

    def test_accepts_single_port(self):
        port = Port(name="DATA", direction="input", type="logic", width=8)
        iface = InterfaceModel(name="TestIf", ports=[port])
        assert len(iface.ports) == 1

    def test_clock_and_reset_optional(self, minimal_interface):
        assert minimal_interface.clock is None
        assert minimal_interface.reset is None

    def test_stores_clock_and_reset(self):
        clk = Port(name="CLK", direction="input", type="logic", width=1, is_clock=True)
        rst = Port(name="RST", direction="input", type="logic", width=1, is_reset=True)
        data = Port(name="D", direction="input", type="logic", width=8)
        iface = InterfaceModel(name="If", ports=[data], clock=clk, reset=rst)
        assert iface.clock.name == "CLK"
        assert iface.reset.name == "RST"

    def test_immutable_after_construction(self, minimal_interface):
        with pytest.raises(Exception):
            minimal_interface.name = "Other"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# AgentModel
# ---------------------------------------------------------------------------


class TestAgentModel:
    def test_has_driver(self, minimal_agent):
        assert minimal_agent.has(ComponentType.DRIVER) is True

    def test_has_monitor(self, minimal_agent):
        assert minimal_agent.has(ComponentType.MONITOR) is True

    def test_has_returns_false_for_absent_component(self, minimal_interface):
        agent = AgentModel(
            name="passive_agent",
            mode=AgentMode.PASSIVE,
            interface_instance=minimal_interface,
            parts=frozenset([ComponentType.MONITOR]),
        )
        assert agent.has(ComponentType.DRIVER) is False

    def test_vif_key_returns_interface_name(self, minimal_agent):
        assert minimal_agent.vif_key == "TestIf"

    def test_mode_active(self, minimal_agent):
        assert minimal_agent.mode == AgentMode.ACTIVE

    def test_coerce_parts_from_list(self, minimal_interface):
        agent = AgentModel(
            name="ag",
            mode=AgentMode.ACTIVE,
            interface_instance=minimal_interface,
            parts=[ComponentType.DRIVER, ComponentType.MONITOR],  # list, not frozenset
        )
        assert isinstance(agent.parts, frozenset)

    def test_empty_name_raises(self, minimal_interface):
        with pytest.raises(ValueError):
            AgentModel(name="  ", mode=AgentMode.ACTIVE, interface_instance=minimal_interface, parts=frozenset())

    def test_immutable_after_construction(self, minimal_agent):
        with pytest.raises(Exception):
            minimal_agent.name = "other"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# EnvModel
# ---------------------------------------------------------------------------


class TestEnvModel:
    def test_active_agents_filtered(self, minimal_env_model, minimal_interface):
        passive = AgentModel(
            name="passive_ag",
            mode=AgentMode.PASSIVE,
            interface_instance=minimal_interface,
            parts=frozenset([ComponentType.MONITOR]),
        )
        model = EnvModel(
            project_name="P",
            testbench_name="tb",
            agents=[minimal_env_model.agents[0], passive],
            interfaces=[minimal_interface],
            transactions=minimal_env_model.transactions,
        )
        active = model.active_agents
        assert len(active) == 1
        assert active[0].mode == AgentMode.ACTIVE

    def test_passive_agents_filtered(self, minimal_env_model, minimal_interface):
        passive = AgentModel(
            name="passive_ag",
            mode=AgentMode.PASSIVE,
            interface_instance=minimal_interface,
            parts=frozenset([ComponentType.MONITOR]),
        )
        model = EnvModel(
            project_name="P",
            testbench_name="tb",
            agents=[minimal_env_model.agents[0], passive],
            interfaces=[minimal_interface],
            transactions=minimal_env_model.transactions,
        )
        assert len(model.passive_agents) == 1

    def test_has_scoreboard_false_when_none(self, minimal_env_model):
        assert minimal_env_model.has_scoreboard is False

    def test_has_scoreboard_true_when_set(self, minimal_interface, minimal_agent, minimal_transaction):
        sb = ScoreboardModel(
            name="sb",
            exports=[
                ScoreboardExport(
                    port_name="actual_export",
                    imp_suffix="_actual",
                    transaction_type="TestTx",
                    role="actual",
                    agent_name="test_agent",
                )
            ],
        )
        model = EnvModel(
            project_name="P",
            testbench_name="tb",
            agents=[minimal_agent],
            interfaces=[minimal_interface],
            transactions=[minimal_transaction],
            scoreboard=sb,
        )
        assert model.has_scoreboard is True

    def test_raises_if_agent_interface_not_in_interfaces_list(self, minimal_agent, minimal_transaction):
        other_if = InterfaceModel(
            name="OtherIf",
            ports=[Port(name="X", direction="input", type="logic", width=1)],
        )
        with pytest.raises(ValueError, match="not in EnvModel.interfaces"):
            EnvModel(
                project_name="P",
                testbench_name="tb",
                agents=[minimal_agent],
                interfaces=[other_if],  # TestIf not here
                transactions=[minimal_transaction],
            )


# ---------------------------------------------------------------------------
# ResolvedConnection
# ---------------------------------------------------------------------------


class TestResolvedConnection:
    def test_from_sv_for_regular_component(self):
        conn = ResolvedConnection(
            from_component="agent",
            from_port="m_driver.ap",
            to_component="reference_model",
            to_port="analysis_export",
        )
        assert conn.from_sv == "m_agent"

    def test_to_sv_for_reference_model(self):
        conn = ResolvedConnection(
            from_component="agent",
            from_port="m_driver.ap",
            to_component="reference_model",
            to_port="analysis_export",
        )
        assert conn.to_sv == "m_refmodel"

    def test_to_sv_for_scoreboard(self):
        conn = ResolvedConnection(
            from_component="agent",
            from_port="ap",
            to_component="scoreboard",
            to_port="actual_export",
        )
        assert conn.to_sv == "m_scoreboard"

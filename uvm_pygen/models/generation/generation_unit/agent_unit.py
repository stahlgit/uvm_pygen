"""Concrete generation unit for agent packages."""

from dataclasses import dataclass, field
from typing import ClassVar

from uvm_pygen.constants.uvm_enum import ComponentType
from uvm_pygen.models.generation.file_spec import FileSpec, SpecCondition
from uvm_pygen.models.generation.generation_unit.generation_unit import GenerationUnit
from uvm_pygen.models.generation.registry import GenerationRegistry


@dataclass
class AgentsUnit(GenerationUnit):
    """Generates all agents and their sub-components."""

    key: str = "agents"
    deps: list[str] = field(default_factory=lambda: ["transaction", "interface"])

    FILES: ClassVar[list[FileSpec]] = [
        FileSpec(template="components/driver.sv.j2", suffix="_driver.sv"),
        FileSpec(template="components/sequencer.sv.j2", suffix="_sequencer.sv"),
        FileSpec(template="components/monitor.sv.j2", suffix="_monitor.sv"),
        FileSpec(template="components/agent.sv.j2", suffix=".sv"),
        FileSpec(template="components/package.sv.j2", suffix="_pkg.sv"),
    ]

    # Agent-level guards: keyed by template path, value takes the agent instance.
    _COMPONENT_GUARDS: ClassVar[dict] = {
        "components/driver.sv.j2": lambda a: a.has(ComponentType.DRIVER),
        "components/sequencer.sv.j2": lambda a: a.has(ComponentType.SEQUENCER),
        "components/monitor.sv.j2": lambda a: a.has(ComponentType.MONITOR),
    }

    def run(self, reg: GenerationRegistry) -> None:
        """Generate all agents and their sub-components."""
        reg.assert_deps(self.deps, self.key)
        model, renderer, writer = self._infra(reg)

        if not model.agents:
            reg.register(self.key)
            return

        trans_map = reg.get_context("transactions", self.key)

        for agent in model.agents:
            agent_trans = trans_map.get(agent.transaction)
            if not agent_trans:
                # Fallback or warning if the model references an un-generated transaction
                trans_type = agent.transaction
                trans_pkg_name = f"{trans_type.lower()}_pkg"
            else:
                trans_type = agent_trans["type"]
                trans_pkg_name = agent_trans["pkg_name"]

            context = {
                "agent": agent,
                "if_name": agent.interface_instance.name,  # per-agent from model
                "vif_key": agent.interface_instance.name,  # resource_db lookup key
                "trans_type": trans_type,
                "trans_pkg_name": trans_pkg_name,
                "package_name": reg.get_context("package_name", self.key),
                "parts": agent.parts,
            }
            # Stamp each spec with the agent's subdir and its per-component guard.
            agent_specs = [
                spec.with_subdir(
                    subdir=f"agents/{agent.name}",
                    condition=self._make_guard(spec.template, agent),
                )
                for spec in self.FILES
            ]
            written = self._render_specs(
                context, reg, model, renderer, writer, prefix=agent.name.lower(), specs=agent_specs
            )
            pkg_filename = f"{agent.name.lower()}_pkg.sv"
            if pkg_filename in written:
                self._register_src_file(reg, written[pkg_filename], model.testbench_name)

        reg.register(self.key)

    def _make_guard(self, template: str, agent) -> SpecCondition | None:
        """Wrap an agent-level guard in the (registry, model) -> bool signature.

        Binds the agent instance eagerly via default argument to avoid the
        late-binding closure problem that arises inside loops.

        Args:
            template: Template path used to look up the guard table.
            agent:    The specific agent instance to bind into the closure.

        Returns:
            A SpecCondition callable, or None if no guard exists for this template.
        """
        raw_guard = self._COMPONENT_GUARDS.get(template)
        if raw_guard is None:
            return None
        return lambda _reg, _model, _agent=agent: raw_guard(_agent)

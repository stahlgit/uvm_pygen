"""Concrete generation unit for agent packages."""

from dataclasses import dataclass

from uvm_pygen.constants.uvm_enum import ComponentType
from uvm_pygen.models.generation.file_spec import FileSpec
from uvm_pygen.models.generation.generation_unit.generation_unit import GenerationUnit
from uvm_pygen.models.generation.registry import GenerationRegistry


@dataclass
class AgentsUnit(GenerationUnit):
    """Generates all agents and their sub-components."""

    key: str = "agents"

    FILES = [
        FileSpec("components/driver.sv.j2", "_driver.sv"),
        FileSpec("components/sequencer.sv.j2", "_sequencer.sv"),
        FileSpec("components/monitor.sv.j2", "_monitor.sv"),
        FileSpec("components/agent.sv.j2", ".sv"),
        FileSpec("components/package.sv.j2", "_pkg.sv"),
    ]

    _COMPONENT_GUARDS = {
        "components/driver.sv.j2": lambda a: a.has(ComponentType.DRIVER),
        "components/sequencer.sv.j2": lambda a: a.has(ComponentType.SEQUENCER),
        "components/monitor.sv.j2": lambda a: a.has(ComponentType.MONITOR),
    }

    def __post_init__(self):
        """Set default dependencies after initialization."""
        self.deps = ["transaction", "interface"]

    def run(self, reg: GenerationRegistry) -> None:
        """Generate all agents and their sub-components based on the model."""
        reg.assert_deps(self.deps, self.key)
        model, renderer, writer = self._infra(reg)

        if not model.agents:
            reg.register(self.key)
            return

        if_name: str | None = reg.get_context("if_name", self.key)
        trans_type: str = reg.get_context("trans_type", self.key)
        package_name: str = reg.get_context("package_name", self.key)

        for agent in model.agents:
            agent_subdir = f"agents/{agent.name}"
            context = {
                "agent": agent,
                "if_name": if_name,
                "trans_type": trans_type,
                "package_name": package_name,
                "parts": agent.parts,
            }
            # Stamp each spec with the agent's subdir and its per-component guard.
            agent_specs = [
                FileSpec(
                    spec.template,
                    spec.suffix,
                    subdir=agent_subdir,
                    condition=(
                        (lambda guard: lambda _reg, _model: guard(agent))(self._COMPONENT_GUARDS[spec.template])
                        if spec.template in self._COMPONENT_GUARDS
                        else None
                    ),
                )
                for spec in self.FILES
            ]
            self._render_specs(agent_specs, context, reg, model, renderer, writer, prefix=agent.name.lower())

        reg.register(self.key)

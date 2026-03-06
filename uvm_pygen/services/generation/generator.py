"""Generates UVM verification environment based on the provided environment model."""

from uvm_pygen.models.generation.generation_unit import (
    AgentsUnit,
    EnvUnit,
    GenerationUnit,
    InterfaceUnit,
    ParamsPkgUnit,
    SequencesUnit,
    TestsUnit,
    TopUnit,
    TransactionUnit,
)
from uvm_pygen.models.generation.registry import GenerationRegistry
from uvm_pygen.models.logic_schema.env_model import EnvModel
from uvm_pygen.services.generation.file_manager import FileManager
from uvm_pygen.services.generation.renderer import TemplateRenderer
from uvm_pygen.services.utils.logger import logger

"""Generation Flow (each layer depends on the previous):
1. params_pkg       - no deps
2. transaction      - params_pkg
3. interface        - params_pkg, transaction
4. agents           - transaction, interface
5. sequences        - transaction, interface
6. env              - agents, sequences
7. base_test        - env, interface
8. random_test      - env, interface, agents
9. test_pkg         - base_test, random_test, agents
10. top             - interface, agents
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _topo_sort(units: list[GenerationUnit]) -> list[GenerationUnit]:
    """Return units in dependency-safe execution order (Kahn's algorithm).

    Args:
        units (list[GenerationUnit]): List of generation units to sort.

    Returns:
        list[GenerationUnit]: Units sorted in execution order.

    Raises:
        ValueError: If a circular dependency or missing dependency is detected.
    """
    key_to_unit: dict[str, GenerationUnit] = {u.key: u for u in units}
    in_degree: dict[str, int] = {u.key: 0 for u in units}
    dependents: dict[str, list[str]] = {u.key: [] for u in units}

    for unit in units:
        for dep in unit.deps:
            if dep not in key_to_unit:
                continue  # dep is a "leaf" context key (not produced by another unit) - skip
            dependents[dep].append(unit.key)
            in_degree[unit.key] += 1
    queue: list[GenerationUnit] = [u for u in units if in_degree[u.key] == 0]
    ordered: list[GenerationUnit] = []

    while queue:
        current: GenerationUnit = queue.pop(0)
        ordered.append(current)
        for dependent_key in dependents[current.key]:
            in_degree[dependent_key] -= 1
            if in_degree[dependent_key] == 0:
                queue.append(key_to_unit[dependent_key])

    if len(ordered) != len(units):
        remaining: set[str] = {u.key for u in units} - {u.key for u in ordered}
        raise ValueError(f"Cycle or unresolvable dependency detected among: {remaining}")

    return ordered


class Generator:
    """Orchestrates GenerationUnits via topological stort."""

    def __init__(self, env_model: EnvModel):
        self.model = env_model
        self.renderer = TemplateRenderer()
        self.writer = FileManager(env_model.testbench_name)
        self.registry = GenerationRegistry()

    def generate_all(self) -> None:
        """Run full generation process."""
        logger.info(f"Starting Code Generation for DUT: {self.model.dut_instance_name}")
        # log_object(self.model, label="Environment Model")

        self._bootstrap_registry()
        units = self._build_units()
        ordered = _topo_sort(units)

        logger.debug("Resolved generation order: " + " → ".join(u.key for u in ordered))

        for unit in ordered:
            logger.info(f"  Generating: {unit.key}")
            unit.run(self.registry)

        logger.info("Generation complete!")

    def _bootstrap_registry(self) -> None:
        """Seed registry with top-level infrastructure objects."""
        self.registry.register_context("model", self.model)
        self.registry.register_context("renderer", self.renderer)
        self.registry.register_context("writer", self.writer)

    def _build_units(self) -> list[GenerationUnit]:
        """Instantiate all generation units."""
        return [
            ParamsPkgUnit(),
            TransactionUnit(),
            InterfaceUnit(),
            AgentsUnit(),
            SequencesUnit(),
            EnvUnit(),
            TestsUnit(),
            TopUnit(),
        ]

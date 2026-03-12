"""Environment generation unit."""

from dataclasses import dataclass

from uvm_pygen.models.generation.file_spec import FileSpec
from uvm_pygen.models.generation.generation_unit.generation_unit import GenerationUnit
from uvm_pygen.models.generation.registry import GenerationRegistry
from uvm_pygen.services.utils import logger


@dataclass
class EnvUnit(GenerationUnit):
    """Generation unit for the environment."""

    key: str = "env"

    FILES = [
        FileSpec("common/env.sv.j2", "_env.sv", subdir="env"),
        FileSpec("common/env_pkg.sv.j2", "_env_pkg.sv", subdir="env"),
    ]

    def __post_init__(self):
        """Initialize dependencies."""
        self.deps = ["agents", "sequences"]

    def run(self, reg: GenerationRegistry) -> None:
        """Run the environment generation unit."""
        reg.assert_deps(self.deps, self.key)
        model, renderer, writer = self._infra(reg)

        if not model.agents:
            logger.warning("⚠️  No agents defined – skipping env generation.")
            reg.register(self.key)
            return

        env_name = f"{model.testbench_name}_env"
        context = {
            "env_name": env_name,
            "testbench_name": model.testbench_name,
            "agents": model.agents,
            "agent_pkgs": [f"{a.name}_pkg" for a in model.agents],
            "scoreboard": model.scoreboard,
            "trans_type": reg.get_context("trans_type", self.key),
            "if_name": reg.get_context("if_name", self.key),
        }
        written = self._render_specs(self.FILES, context, reg, model, renderer, writer, prefix=model.testbench_name)
        env_pkg_name = f"{env_name}_pkg"
        reg.register(self.key, env_name=env_name, env_pkg_name=env_pkg_name)
        pkg_filename = f"{model.testbench_name}_env_pkg.sv"
        if pkg_filename in written:
            reg.context.setdefault("src_files", []).append(self._tcl_path(written[pkg_filename], model.testbench_name))

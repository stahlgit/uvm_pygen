"""Environment generation unit."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import ClassVar

from uvm_pygen.models.generation.file_spec import FileSpec
from uvm_pygen.models.generation.generation_unit.generation_unit import GenerationUnit
from uvm_pygen.models.generation.registry import GenerationRegistry
from uvm_pygen.models.logic_schema.env_model import EnvModel
from uvm_pygen.services.utils import logger


@dataclass
class EnvUnit(GenerationUnit):
    """Generation unit for the environment."""

    key: str = "env"
    deps: list[str] = field(default_factory=lambda: ["agents", "sequences"])

    FILES: ClassVar[list[FileSpec]] = [
        FileSpec(template="common/env.sv.j2", suffix="_env.sv", subdir="env"),
        FileSpec(template="common/env_pkg.sv.j2", suffix="_env_pkg.sv", subdir="env"),
    ]

    def _prefix(self, model: EnvModel) -> str:
        return model.testbench_name

    def _build_context(self, reg: GenerationRegistry, model: EnvModel) -> dict:
        env_name = f"{model.testbench_name}_env"
        return {
            "env_name": env_name,
            "testbench_name": model.testbench_name,
            "agents": model.agents,
            "agent_pkgs": [f"{a.name}_pkg" for a in model.agents],
            "scoreboard": model.scoreboard,
            "trans_type": reg.get_context("trans_type", self.key),
            "if_name": reg.get_context("if_name", self.key),
        }

    def _post_run(self, reg: GenerationRegistry, model: EnvModel, written: dict[str, Path]) -> None:
        if not model.agents:
            logger.warning("⚠️  No agents defined – skipping env generation.")
            reg.register(self.key)
            return

        env_name = f"{model.testbench_name}_env"
        env_pkg_name = f"{env_name}_pkg"
        reg.register(self.key, env_name=env_name, env_pkg_name=env_pkg_name)

        pkg_filename = f"{model.testbench_name}_env_pkg.sv"
        if pkg_filename in written:
            self._register_src_file(reg, written[pkg_filename], model.testbench_name)

"""Concrete generation unit for parameter packages."""

from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from uvm_pygen.models.generation.file_spec import FileSpec
from uvm_pygen.models.generation.generation_unit.generation_unit import GenerationUnit
from uvm_pygen.models.generation.registry import GenerationRegistry
from uvm_pygen.models.logic_schema.env_model import EnvModel
from uvm_pygen.services.utils.logger import logger


@dataclass
class ParamsPkgUnit(GenerationUnit):
    """Generation unit for DUT parameter packages."""

    key: str = "params_pkg"

    FILES: ClassVar[list[FileSpec]] = [
        FileSpec(template="common/params_pkg.sv.j2", suffix="_params_pkg.sv"),
    ]

    def _prefix(self, model: EnvModel) -> str:
        return model.dut_instance_name

    def _build_context(self, reg: GenerationRegistry, model: EnvModel) -> dict:
        return {
            "dut_name": model.dut_instance_name,
            "parameters": model.parameters,
            "enums": model.enums,
        }

    def _post_run(self, reg: GenerationRegistry, model: EnvModel, written: dict[str, Path]) -> None:
        path = next(iter(written.values()), None)
        pkg_name = f"{model.dut_instance_name}_params_pkg"
        reg.register(self.key, path=path, package_name=pkg_name)
        if not path:
            logger.warning("ParamsPkgUnit: No file was written, cannot register src file.")
            return
        self._register_src_file(reg, path, model.testbench_name)

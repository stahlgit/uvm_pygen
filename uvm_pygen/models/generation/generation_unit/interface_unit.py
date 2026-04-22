"""Concrete generation unit for interface generation."""

from dataclasses import dataclass, field
from typing import ClassVar, override

from uvm_pygen.models.generation.file_spec import FileSpec
from uvm_pygen.models.generation.generation_unit.generation_unit import GenerationUnit
from uvm_pygen.models.generation.registry import GenerationRegistry
from uvm_pygen.models.logic_schema.env_model import EnvModel
from uvm_pygen.models.logic_schema.transaction_model import TransactionModel
from uvm_pygen.services.utils.logger import logger


@dataclass
class InterfaceUnit(GenerationUnit):
    """Generation unit for creating an interface based on the model's interface definition."""

    key: str = "interface"
    deps: list[str] = field(default_factory=lambda: ["params_pkg", "transaction"])

    FILES: ClassVar[list[FileSpec]] = [
        FileSpec(
            template="common/interface.sv.j2",
            suffix=".sv",
            condition=lambda _reg, model: bool(model.interfaces),
        ),
    ]

    def _prefix(self, model: EnvModel) -> str:
        return model.testbench_name

    def _build_iface_to_trans(self, model: EnvModel) -> dict[str, TransactionModel]:
        """Build a mapping from interface name → TransactionModel via agent definitions.

        Each agent declares both an interface_instance and a transaction class name,
        providing the authoritative link between the two.  If multiple agents share
        an interface (rare but possible), the last one wins — they should agree.
        """
        trans_by_class: dict[str, TransactionModel] = {t.class_name: t for t in model.transactions}
        mapping: dict[str, TransactionModel] = {}
        for agent in model.agents:
            if agent.transaction and agent.transaction in trans_by_class:
                mapping[agent.interface_instance.name] = trans_by_class[agent.transaction]
        return mapping

    @override
    def run(self, reg: GenerationRegistry) -> None:
        reg.assert_deps(self.deps, self.key)
        model, renderer, writer = self._infra(reg)

        if not model.interfaces:
            logger.warning("⚠️  No interfaces defined – skipping interface generation.")
            reg.register(self.key, if_name=None, interfaces=[])
            return

        iface_to_trans = self._build_iface_to_trans(model)
        # Fallback: primary transaction (first declared) for interfaces not covered by any agent
        primary_trans = model.transactions[0] if model.transactions else None

        all_written = {}
        for iface in model.interfaces:
            trans = iface_to_trans.get(iface.name)
            if trans is None:
                logger.warning(
                    f"⚠️  No agent maps a transaction to interface '{iface.name}' "
                    f"— falling back to primary transaction."
                )
                trans = primary_trans

            trans_type = trans.class_name if trans else reg.get_context("trans_type", self.key)
            trans_pkg_name = (
                f"{trans.class_name.lower()}_pkg" if trans else reg.get_context("trans_pkg_name", self.key)
            )

            context = {
                "if_model": iface,
                "trans": trans,
                "trans_type": trans_type,
                "trans_pkg_name": trans_pkg_name,
                "package_name": reg.get_context("package_name", self.key),
            }
            written = self._render_specs(context, reg, model, renderer, writer, iface.name)
            all_written.update(written)

        for path in all_written.values():
            self._register_src_file(reg, path, model.testbench_name)

        reg.register(self.key, if_name=model.interfaces[0].name, interfaces=model.interfaces)

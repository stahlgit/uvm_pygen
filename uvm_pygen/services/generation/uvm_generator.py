"""Generates UVM verification environment based on the provided environment model."""

from uvm_pygen.constants.uvm_enum import AgentMode, ComponentType
from uvm_pygen.models.generation.file_spec import FileSpec
from uvm_pygen.models.logic_schema.env_model import EnvModel
from uvm_pygen.services.generation.file_manager import FileManager
from uvm_pygen.services.generation.renderer import TemplateRenderer
from uvm_pygen.services.utils.logger import log_object, logger

""" Generation Flow:
1. params_pkg - parameters and enums
2. transaction - sequence item -- needs params_pkg (types, width)
3. interface - needs params_pkg
4. agents and components - need transaction + interface
5. sequences - needs transaction
6. scoreboard - needs transaction
7. env - needs agents + scoreboard + sequences
8. test - needs env
9. top - needs interface + agents (wiring)

"""


class UVMGenerator:
    """Main generator class orchestrating the rendering process."""

    AGENT_FILES = [
        FileSpec(
            "components/driver.sv.j2",
            "_driver.sv",
            condition=lambda a: a.has(ComponentType.DRIVER),
        ),
        FileSpec(
            "components/sequencer.sv.j2",
            "_sequencer.sv",
            condition=lambda a: a.has(ComponentType.SEQUENCER),
        ),
        FileSpec(
            "components/monitor.sv.j2",
            "_monitor.sv",
            condition=lambda a: a.has(ComponentType.MONITOR),
        ),
        FileSpec("components/agent.sv.j2", ".sv"),
        FileSpec("components/package.sv.j2", "_pkg.sv"),
    ]

    def __init__(self, env_model: EnvModel) -> None:
        """Initialize generator with the environment model."""
        self.model = env_model
        self.renderer = TemplateRenderer()
        self.writer = FileManager(env_model.testbench_name)

    def generate_all(self):
        """Run full generation process."""
        logger.info(f"Starting Code Generation for DUT: {self.model.dut_instance_name}")
        log_object(self.model, label="Environment Model")

        # Layer 1 - no deps
        self._generate_params_pkg()

        # Layer 2 - depends on params_pkg
        self._generate_transaction()
        self._generate_interface()

        # Layer 3 - depends on transaction + interface
        self._generate_agents_and_components()

        # Layer 4 - depends on transaction
        self._generate_sequences()
        # self.generate_scoreboard()

        # Layer 5 - depends on agents + scoreboard + sequences
        self._generate_env()

        # Layer 6 - depends on env
        self._generate_base_test()
        self._generate_random_test()

        # Layer 7 - depends on interface + agents (wiring)
        self._generate_top()

        logger.info("Generation complete!")

    ### LAYERS

    def _generate_params_pkg(self):
        """Generate the parameters package (params_pkg)."""
        context = {
            "dut_name": self.model.dut_instance_name,
            "parameters": self.model.parameters,
            "enums": self.model.enums,
        }
        content = self.renderer.render("common/params_pkg.sv.j2", context)
        filename = f"{self.model.dut_instance_name}_params_pkg.sv"
        self.writer.write(filename, content)

    def _generate_transaction(self):
        """Generate Sequence Item."""
        # Do šablóny môžeme poslať celý objekt 'transaction'

        content = self.renderer.render(
            "logic/transaction.sv.j2",
            {
                "trans": self.model.transaction,
                "project_name": self.model.project_name,
                "package_name": f"{self.model.dut_instance_name}_params_pkg",
            },
        )

        filename = f"{self.model.transaction.class_name.lower()}.sv"
        self.writer.write(filename, content, subdir="objects")

    # TODO: map subdirs ? interface needs no know location of transaction - but that is static and can be hardcoded in the template for now

    def _generate_interface(self):
        """Generate SystemVerilog Interface."""
        if not self.model.interfaces:
            return

        trans = self.model.transaction
        if_model = self.model.interfaces[0]

        context = {
            "if_model": if_model,
            "trans": trans,
            "trans_type": trans.class_name,
            "package_name": f"{self.model.dut_instance_name}_params_pkg",
        }

        content = self.renderer.render("common/interface.sv.j2", context)

        filename = f"{if_model.name}.sv"
        self.writer.write(filename, content)

    def _generate_agents_and_components(self):
        """Generates all agent sub-components based on the AGENT_FILES mapping."""
        if not self.model.agents:
            return

        # Pre-calculate common context data
        if_name = self.model.interfaces[0].name
        trans_type = self.model.transaction.class_name

        for agent in self.model.agents:
            context = {
                "agent": agent,
                "if_name": if_name,
                "trans_type": trans_type,
                "package_name": f"{self.model.dut_instance_name}_params_pkg",
                "parts": agent.parts,
            }
            agent_dir = f"agents/{agent.name}"

            for spec in self.AGENT_FILES:
                if self._should_generate(agent, spec):
                    filename = f"{agent.name.lower()}{spec.suffix}"

                    self._generate_component(
                        template_path=spec.template, context=context, filename=filename, subdir=agent_dir
                    )

    def _generate_sequences(self):
        """Generate basic sequence classes."""
        trans_type = self.model.transaction.class_name

        # Base sequence
        context = {"trans_type": trans_type, "ports": self.model.interfaces[0].ports if self.model.interfaces else []}
        content = self.renderer.render("sequences/base_sequence.sv.j2", context)
        self.writer.write("base_sequence.sv", content, subdir="sequences")

        # Direct sequence (empty body)
        context = {"seq_name": "direct_sequence", "trans_type": trans_type, "body": "// User-defined body"}
        content = self.renderer.render("sequences/derived_sequence.sv.j2", context)
        self.writer.write("direct_sequence.sv", content, subdir="sequences")

        # Random sequence
        content = self.renderer.render("sequences/random_sequence.sv.j2", {"trans_type": trans_type})
        self.writer.write("random_sequence.sv", content, subdir="sequences")

        # TODO: what if more from config ? think about it
        context = {
            "name": self.model.dut_instance_name,
            "seqs": ["base_sequence", "direct_sequence", "random_sequence"],
        }
        content = self.renderer.render("sequences/sequence_pkg.sv.j2", context)
        self.writer.write(f"{self.model.dut_instance_name}_seq_pkg.sv", content, subdir="sequences")

    def _generate_env(self):
        """Generate the UVM environment class."""
        if not self.model.agents:
            logger.warning("⚠️  No agents defined – skipping env generation.")
            return

        env_name = f"{self.model.testbench_name}_env"

        # Collect per-agent package names so the env can import them.
        agent_pkgs = [f"{agent.name}_pkg" for agent in self.model.agents]

        context = {
            "env_name": env_name,
            "testbench_name": self.model.testbench_name,
            "agents": self.model.agents,
            "agent_pkgs": agent_pkgs,
            "scoreboard": self.model.scoreboard,  # may be None
            "trans_type": self.model.transaction.class_name,
            "if_name": self.model.interfaces[0].name if self.model.interfaces else None,
        }
        content = self.renderer.render("common/env.sv.j2", context)
        filename = f"{env_name}.sv"
        self.writer.write(filename, content, subdir="env")

        content = self.renderer.render("common/env_pkg.sv.j2", context)
        filename = f"{env_name}_pkg.sv"
        self.writer.write(filename, content, subdir="env")

    def _generate_base_test(self):
        """Generate a basic test class."""
        context = {
            "name": self.model.dut_instance_name,
            "env_name": f"{self.model.testbench_name}_env",
            "if_name": self.model.interfaces[0].name if self.model.interfaces else None,
        }
        content = self.renderer.render("tests/base_test.sv.j2", context)
        self.writer.write(f"{context['name']}_base_test.sv", content, subdir="tests")

    def _generate_random_test(self, num_transactions=10, drain_time=100):
        """Generate a random test class."""
        active_agents = [a for a in self.model.agents if a.has(ComponentType.DRIVER) and a.active == AgentMode.ACTIVE]
        if not active_agents:
            logger.warning("⚠️  No active agents found – skipping random test generation.")
            return
        context = {
            "name": self.model.dut_instance_name,
            "env_name": f"{self.model.testbench_name}_env",
            "if_name": self.model.interfaces[0].name if self.model.interfaces else None,
            "active_agents": active_agents,
            "num_transactions": num_transactions,
            "drain_time": drain_time,
        }
        content = self.renderer.render("tests/random_test.sv.j2", context)
        filename = f"{self.model.dut_instance_name}_random_test.sv"
        self.writer.write(filename, content, subdir="tests")

    def _generate_top(self):
        """Generate top-level tesstbench module."""
        if not self.model.interfaces:
            logger.warning("⚠️ No interfaces defined, skipping top-level generation.")
            return
        iface = self.model.interfaces[0]

        context = {
            "testbench_name": self.model.testbench_name,
            "dut_instance_name": self.model.dut_instance_name,
            "interface": iface,
            "agents": self.model.agents,
            "clock": iface.clock,
            "reset": iface.reset,
            "ports": iface.ports,
        }

        content = self.renderer.render("common/top.sv.j2", context)
        filename = f"{self.model.testbench_name}_top.sv"
        self.writer.write(filename, content)

    ### PRIVATE HELPERS

    def _should_generate(self, model_obj, spec: FileSpec) -> bool:
        """Determines if a file should be generated based on the model attributes."""
        if spec.condition is None:
            return True
        return spec.condition(model_obj)

    def _generate_component(self, template_path, context, filename, subdir):
        """Helper to render and write a component."""
        content = self.renderer.render(template_path, context)
        self.writer.write(filename, content, subdir=subdir)

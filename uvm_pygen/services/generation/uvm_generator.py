from rich import print

from uvm_pygen.models.generation.file_spec import FileSpec
from uvm_pygen.models.logic_schema.env_model import EnvModel
from uvm_pygen.services.generation.file_manager import FileManager
from uvm_pygen.services.generation.renderer import TemplateRenderer


class UVMGenerator:
    """Main generator class orchestrating the rendering process."""

    AGENT_FILES = [
        # (Template Path, Suffix, Attribute to check on AgentModel)
        FileSpec("components/driver.sv.j2", "_driver.sv", check_attr="has_driver"),
        FileSpec(
            "components/sequencer.sv.j2", "_sequencer.sv", check_attr="has_driver"
        ),  # Usually same condition as driver
        FileSpec("components/monitor.sv.j2", "_monitor.sv", check_attr="has_monitor"),
        FileSpec("components/agent.sv.j2", "_agent.sv", check_attr=None),  # None = Always generate
        FileSpec("common/package.sv.j2", "_agent_pkg.sv", check_attr=None),
    ]

    def __init__(self, env_model: EnvModel) -> None:
        """Initialize generator with the environment model."""
        self.model = env_model
        self.renderer = TemplateRenderer()
        self.writer = FileManager(env_model.testbench_name)

    def generate_all(self):
        """Run full generation process."""
        print(f"\n🚀 Starting Code Generation for DUT: {self.model.dut_instance_name}...")
        print(self.model)

        self.generate_params_pkg()
        self.generate_transaction()
        self.generate_interface()
        self.generate_agents_and_components()
        self.generate_top()
        self.generate_sequences()
        self.generate_test()

        # self.generate_env()

        print("\n✅ Generation complete!")

    def generate_top(self):
        """Generate top-level tesstbench module."""
        if not self.model.interfaces:
            print("[yellow]⚠️ No interfaces defined, skipping top-level generation.[/yellow]")
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

    def generate_transaction(self):
        """Generate Sequence Item."""
        # Do šablóny môžeme poslať celý objekt 'transaction'

        content = self.renderer.render(
            "logic/transaction.sv.j2", {"trans": self.model.transaction, "project_name": self.model.project_name}
        )

        filename = f"{self.model.transaction.class_name.lower()}.sv"
        self.writer.write(filename, content, subdir="objects")

    def generate_sequences(self):
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

    def generate_test(self):
        """Generate a basic test class."""
        context = {
            "name": self.model.dut_instance_name,
            "env_name": f"{self.model.testbench_name}_env",
        }
        content = self.renderer.render("tests/base_test.sv.j2", context)
        self.writer.write(f"{context['name']}_base_test.sv", content, subdir="tests")

    def generate_interface(self):
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

    def generate_agents_and_components(self):
        """Generates all agent sub-components based on the AGENT_FILES mapping."""
        if not self.model.agents:
            return

        # Pre-calculate common context data
        if_name = self.model.interfaces[0].name
        trans_type = self.model.transaction.class_name

        for agent in self.model.agents:
            context = {"agent": agent, "if_name": if_name, "trans_type": trans_type}
            agent_dir = f"agents/{agent.name}"

            for spec in self.AGENT_FILES:
                if self._should_generate(agent, spec):
                    filename = f"{agent.name.lower()}{spec.suffix}"

                    self._generate_component(
                        template_path=spec.template, context=context, filename=filename, subdir=agent_dir
                    )

    def generate_params_pkg(self):
        """Generate the parameters package (params_pkg)."""
        context = {
            "dut_name": self.model.dut_instance_name,
            "parameters": self.model.parameters,
            "enums": self.model.enums,
        }
        content = self.renderer.render("common/params_pkg.sv.j2", context)
        filename = f"{self.model.dut_instance_name}_params_pkg.sv"
        self.writer.write(filename, content)

    def _should_generate(self, model_obj, spec: FileSpec) -> bool:
        """Determines if a file should be generated based on the model attributes."""
        if not spec.check_attr and not spec.condition:
            return True

        if spec.check_attr and getattr(model_obj, spec.check_attr, False):
            return True

        return bool(spec.condition and spec.condition(model_obj))

    def _generate_component(self, template_path, context, filename, subdir):
        """Helper to render and write a component."""
        content = self.renderer.render(template_path, context)
        self.writer.write(filename, content, subdir=subdir)

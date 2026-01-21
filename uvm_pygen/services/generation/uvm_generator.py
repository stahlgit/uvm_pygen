from uvm_pygen.constants.uvm_enum import AgentMode
from uvm_pygen.models.logic_schema.env_model import EnvModel
from uvm_pygen.services.generation.file_manager import FileManager
from uvm_pygen.services.generation.renderer import TemplateRenderer


class UVMGenerator:
    """Main generator class orchestrating the rendering process."""

    def __init__(self, env_model: EnvModel, output_dir: str = "tb_generated"):
        self.model = env_model
        self.renderer = TemplateRenderer()
        self.writer = FileManager(output_dir)

    def generate_all(self):
        """Run full generation process."""
        print(f"\n🚀 Starting Code Generation for DUT: {self.model.dut_instance_name}...")

        self.generate_transaction()
        self.generate_interface()
        self.generate_drivers()
        # self.generate_env()

        print("\n✅ Generation complete!")

    def generate_transaction(self):
        """Generate Sequence Item."""
        # Do šablóny môžeme poslať celý objekt 'transaction'
        ctx = {
            "trans": self.model.transaction,
            "project_name": "uvm_project",  # alebo z configu
        }

        content = self.renderer.render("logic/transaction.sv.j2", ctx)

        filename = f"{self.model.transaction.class_name.lower()}.sv"
        self.writer.write(filename, content, subdir="objects")

    def generate_interface(self):
        """Generate SystemVerilog Interface."""
        # Predpokladáme, že generujeme interface pre prvý model v zozname (pre ALU máme 1)
        if not self.model.interfaces:
            return

        if_model = self.model.interfaces[0]

        ctx = {"if_model": if_model}

        content = self.renderer.render("common/interface.sv.j2", ctx)

        # Pre čistotu ich dáme do koreňa 'output_dir' alebo vytvoríme zložku 'interfaces'
        filename = f"{if_model.name}.sv"
        self.writer.write(filename, content)

    def generate_drivers(self):
        """Generate Drivers for all active agents."""
        if not self.model.agents:
            return
        if_name = self.model.interfaces[0].name
        trans_type = self.model.transaction.class_name

        for agent in self.model.agents:
            if agent.active == AgentMode.PASSIVE or not agent.has_driver:
                continue

            ctx = {
                "agent": agent,
                "if_name": if_name,
                "trans_type": trans_type,
            }

            content = self.renderer.render("components/driver.sv.j2", ctx)

            filename = f"{agent.name.lower()}_driver.sv"
            self.writer.write(filename, content, subdir=f"agents/{agent.name}")

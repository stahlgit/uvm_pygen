"""Tests for Generator — bootstrap, unit instantiation, and integration."""

from pathlib import Path

import pytest

from tests.conftest import PROJECT_ROOT
from uvm_pygen.models.generation.generation_unit import (
    AgentsUnit,
    EnvUnit,
    InterfaceUnit,
    ParamsPkgUnit,
    ReferenceModelUnit,
    ScoreboardUnit,
    SequencesUnit,
    SimUnit,
    TestsUnit,
    TopUnit,
    TransactionUnit,
    WaveUnit,
)
from uvm_pygen.models.generation.generation_unit.coverage_unit import CoverageUnit
from uvm_pygen.services.generation.file_manager import FileManager
from uvm_pygen.services.generation.generator import Generator
from uvm_pygen.services.generation.renderer import TemplateRenderer


class TestGeneratorInit:
    def test_has_renderer(self, minimal_env_model, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        gen = Generator(minimal_env_model)
        assert isinstance(gen.renderer, TemplateRenderer)

    def test_has_writer(self, minimal_env_model, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        gen = Generator(minimal_env_model)
        assert isinstance(gen.writer, FileManager)

    def test_writer_output_dir_matches_testbench_name(self, minimal_env_model, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        gen = Generator(minimal_env_model)
        assert gen.writer.output_dir.name == minimal_env_model.testbench_name

    def test_creates_output_directory(self, minimal_env_model, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        Generator(minimal_env_model)
        assert (tmp_path / minimal_env_model.testbench_name).is_dir()


class TestBootstrapRegistry:
    def test_seeds_model_in_registry(self, minimal_env_model, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        gen = Generator(minimal_env_model)
        gen._bootstrap_registry()
        assert gen.registry.get_context("model") is minimal_env_model

    def test_seeds_renderer_in_registry(self, minimal_env_model, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        gen = Generator(minimal_env_model)
        gen._bootstrap_registry()
        assert isinstance(gen.registry.get_context("renderer"), TemplateRenderer)

    def test_seeds_writer_in_registry(self, minimal_env_model, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        gen = Generator(minimal_env_model)
        gen._bootstrap_registry()
        assert isinstance(gen.registry.get_context("writer"), FileManager)


class TestBuildUnits:
    def test_returns_13_units(self, minimal_env_model, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        gen = Generator(minimal_env_model)
        units = gen._build_units()
        assert len(units) == 13

    def test_contains_all_expected_unit_types(self, minimal_env_model, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        gen = Generator(minimal_env_model)
        units = gen._build_units()
        unit_types = {type(u) for u in units}
        expected = {
            ParamsPkgUnit,
            TransactionUnit,
            InterfaceUnit,
            AgentsUnit,
            ReferenceModelUnit,
            CoverageUnit,
            ScoreboardUnit,
            SequencesUnit,
            EnvUnit,
            TestsUnit,
            SimUnit,
            TopUnit,
            WaveUnit,
        }
        assert unit_types == expected

    def test_unit_keys_are_unique(self, minimal_env_model, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        gen = Generator(minimal_env_model)
        units = gen._build_units()
        keys = [u.key for u in units]
        assert len(keys) == len(set(keys))


class TestGeneratorIntegration:
    """Full pipeline integration test using real project config files."""

    def test_generates_files_from_split_config(self, tmp_path, monkeypatch):
        """Run the full pipeline: split config → model → generated files."""
        from uvm_pygen.services.config_parser.config_loader import ConfigLoader
        from uvm_pygen.services.model_builder.model_builder import ModelBuilder

        monkeypatch.chdir(tmp_path)

        dut_config = PROJECT_ROOT / "config_dut.yaml"
        uvm_config = PROJECT_ROOT / "config_uvm.yaml"

        if not dut_config.exists() or not uvm_config.exists():
            pytest.skip("Real config files not available")

        loader = ConfigLoader(dut_config_path=dut_config, uvm_config_path=uvm_config)
        assert loader.validate()

        env_model = ModelBuilder(loader).build()
        generator = Generator(env_model)
        generator.generate_all()

        tb_dir = tmp_path / env_model.testbench_name
        assert tb_dir.is_dir()
        # At minimum, the objects and components subdirectories should exist
        assert any(tb_dir.iterdir())

    def test_generated_transaction_file_exists(self, tmp_path, monkeypatch):
        from uvm_pygen.services.config_parser.config_loader import ConfigLoader
        from uvm_pygen.services.model_builder.model_builder import ModelBuilder

        monkeypatch.chdir(tmp_path)

        dut_config = PROJECT_ROOT / "config_dut.yaml"
        uvm_config = PROJECT_ROOT / "config_uvm.yaml"

        if not dut_config.exists() or not uvm_config.exists():
            pytest.skip("Real config files not available")

        loader = ConfigLoader(dut_config_path=dut_config, uvm_config_path=uvm_config)
        env_model = ModelBuilder(loader).build()
        Generator(env_model).generate_all()

        tb_dir = tmp_path / env_model.testbench_name
        sv_files = list(tb_dir.rglob("*.sv"))
        assert len(sv_files) > 0

    def test_generate_all_from_minimal_model(self, tmp_path, monkeypatch):
        """Run generate_all() with the minimal fixture model — smoke test."""
        from tests.conftest import MINIMAL_DUT_RAW, MINIMAL_UVM_RAW
        from uvm_pygen.services.config_parser.config_loader import ConfigLoader
        from uvm_pygen.services.model_builder.model_builder import ModelBuilder

        monkeypatch.chdir(tmp_path)

        loader = ConfigLoader(dut_raw=MINIMAL_DUT_RAW, uvm_raw=MINIMAL_UVM_RAW)
        env_model = ModelBuilder(loader).build()
        generator = Generator(env_model)
        generator.generate_all()  # should not raise

        assert (tmp_path / "test_tb").is_dir()

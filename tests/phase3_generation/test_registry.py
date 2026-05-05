"""Tests for GenerationRegistry — CRUD and dependency validation."""

from pathlib import Path

import pytest

from uvm_pygen.models.generation.registry import GenerationRegistry, RegistryKeyError


@pytest.fixture
def registry():
    return GenerationRegistry()


class TestRegistryFiles:
    def test_register_and_get_file(self, registry, tmp_path):
        p = tmp_path / "out.sv"
        registry.register_file("transaction", p)
        assert registry.get_file("transaction") == p

    def test_get_file_raises_for_missing_key(self, registry):
        with pytest.raises(RegistryKeyError) as exc_info:
            registry.get_file("missing_key", requested_by="test_unit")
        assert exc_info.value.key == "missing_key"
        assert "test_unit" in str(exc_info.value)

    def test_has_file_true_after_register(self, registry, tmp_path):
        registry.register_file("k", tmp_path / "f.sv")
        assert registry.has_file("k") is True

    def test_has_file_false_for_missing_key(self, registry):
        assert registry.has_file("nonexistent") is False


class TestRegistryContent:
    def test_register_and_get_content(self, registry):
        registry.register_content("transaction", "module foo; endmodule")
        assert registry.get_content("transaction") == "module foo; endmodule"

    def test_get_content_raises_for_missing_key(self, registry):
        with pytest.raises(RegistryKeyError):
            registry.get_content("missing")

    def test_has_content_true_after_register(self, registry):
        registry.register_content("k", "data")
        assert registry.has_content("k") is True

    def test_has_content_false_for_missing_key(self, registry):
        assert registry.has_content("nonexistent") is False


class TestRegistryContext:
    def test_register_and_get_context(self, registry):
        registry.register_context("trans_type", "AluTransaction")
        assert registry.get_context("trans_type") == "AluTransaction"

    def test_get_context_raises_for_missing_key(self, registry):
        with pytest.raises(RegistryKeyError):
            registry.get_context("missing")

    def test_context_accepts_any_type(self, registry):
        registry.register_context("list_val", [1, 2, 3])
        registry.register_context("dict_val", {"a": 1})
        registry.register_context("int_val", 42)
        assert registry.get_context("list_val") == [1, 2, 3]
        assert registry.get_context("int_val") == 42


class TestRegistryRegisterConvenience:
    def test_register_stamps_presence_sentinel(self, registry):
        registry.register("transaction")
        # The key is stamped in context as True
        assert registry.get_context("transaction") is True

    def test_register_with_path_stores_file(self, registry, tmp_path):
        p = tmp_path / "out.sv"
        registry.register("transaction", path=p)
        assert registry.get_file("transaction") == p

    def test_register_with_content_stores_content(self, registry):
        registry.register("transaction", content="sv code here")
        assert registry.get_content("transaction") == "sv code here"

    def test_register_with_extra_kwargs_stored_in_context(self, registry):
        registry.register("transaction", trans_type="AluTx", pkg_name="alu_pkg")
        assert registry.get_context("trans_type") == "AluTx"
        assert registry.get_context("pkg_name") == "alu_pkg"

    def test_register_without_path_does_not_create_file_entry(self, registry):
        registry.register("transaction")
        assert registry.has_file("transaction") is False

    def test_register_without_content_does_not_create_content_entry(self, registry):
        registry.register("transaction")
        assert registry.has_content("transaction") is False


class TestAssertDeps:
    def test_passes_when_all_deps_in_context(self, registry):
        registry.register_context("dep1", True)
        registry.register_context("dep2", True)
        registry.assert_deps(["dep1", "dep2"], "dependent_unit")  # no raise

    def test_passes_when_dep_in_files(self, registry, tmp_path):
        registry.register_file("dep1", tmp_path / "f.sv")
        registry.assert_deps(["dep1"], "test_unit")  # no raise

    def test_raises_when_dep_missing(self, registry):
        with pytest.raises(RegistryKeyError) as exc_info:
            registry.assert_deps(["missing_dep"], "dependent_unit")
        assert exc_info.value.key == "missing_dep"
        assert "dependent_unit" in str(exc_info.value)

    def test_passes_for_empty_deps_list(self, registry):
        registry.assert_deps([], "any_unit")  # no raise

    def test_raises_only_for_first_missing_dep(self, registry):
        registry.register_context("present", True)
        with pytest.raises(RegistryKeyError) as exc_info:
            registry.assert_deps(["missing", "present"], "unit")
        assert exc_info.value.key == "missing"


class TestRegistryKeyError:
    def test_error_contains_key_and_requester(self):
        err = RegistryKeyError("my_key", "my_unit")
        assert err.key == "my_key"
        assert "my_key" in str(err)
        assert "my_unit" in str(err)

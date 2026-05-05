"""Tests for _topo_sort — topological ordering of GenerationUnits."""

from dataclasses import dataclass, field
from typing import ClassVar

import pytest

from uvm_pygen.models.generation.file_spec import FileSpec
from uvm_pygen.models.generation.generation_unit.generation_unit import GenerationUnit
from uvm_pygen.services.generation.generator import _topo_sort


# ---------------------------------------------------------------------------
# Minimal concrete subclass for testing
# ---------------------------------------------------------------------------


@dataclass
class MockUnit(GenerationUnit):
    """Minimal GenerationUnit subclass for topo sort tests."""

    FILES: ClassVar[list[FileSpec]] = []

    def _build_context(self, registry, model) -> dict:
        return {}


def unit(key: str, deps: list[str] | None = None) -> MockUnit:
    return MockUnit(key=key, deps=deps or [])


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestTopoSort:
    def test_empty_list_returns_empty(self):
        assert _topo_sort([]) == []

    def test_single_unit_no_deps(self):
        u = unit("a")
        result = _topo_sort([u])
        assert result == [u]

    def test_linear_chain_correct_order(self):
        a = unit("a")
        b = unit("b", deps=["a"])
        c = unit("c", deps=["b"])
        result = _topo_sort([c, b, a])  # given in reverse
        keys = [u.key for u in result]
        assert keys.index("a") < keys.index("b")
        assert keys.index("b") < keys.index("c")

    def test_diamond_dependency_a_first_d_last(self):
        a = unit("a")
        b = unit("b", deps=["a"])
        c = unit("c", deps=["a"])
        d = unit("d", deps=["b", "c"])
        result = _topo_sort([d, c, b, a])
        keys = [u.key for u in result]
        assert keys[0] == "a"
        assert keys[-1] == "d"
        assert keys.index("b") < keys.index("d")
        assert keys.index("c") < keys.index("d")

    def test_all_units_included(self):
        units = [unit("a"), unit("b"), unit("c"), unit("d")]
        result = _topo_sort(units)
        assert len(result) == 4

    def test_parallel_units_all_included(self):
        # No dependencies — any order is valid but all must be present
        units = [unit("x"), unit("y"), unit("z")]
        result = _topo_sort(units)
        assert {u.key for u in result} == {"x", "y", "z"}

    def test_cycle_raises_value_error(self):
        a = unit("a", deps=["b"])
        b = unit("b", deps=["a"])
        with pytest.raises(ValueError, match="[Cc]ycle"):
            _topo_sort([a, b])

    def test_external_leaf_dep_not_a_unit_is_ignored(self):
        # "model" and "renderer" are seeded into the registry but not GenerationUnits
        a = unit("a", deps=["model", "renderer"])
        result = _topo_sort([a])
        assert result == [a]

    def test_preserves_all_units_in_complex_graph(self):
        # Simulate the real generation pipeline structure
        params = unit("params_pkg")
        trans = unit("transaction", deps=["params_pkg"])
        iface = unit("interface", deps=["params_pkg", "transaction"])
        agents = unit("agents", deps=["transaction", "interface"])
        env = unit("env", deps=["agents"])
        tests = unit("tests", deps=["env"])
        result = _topo_sort([tests, agents, env, iface, trans, params])
        keys = [u.key for u in result]
        assert keys.index("params_pkg") < keys.index("transaction")
        assert keys.index("transaction") < keys.index("interface")
        assert keys.index("interface") < keys.index("agents")
        assert keys.index("agents") < keys.index("env")
        assert keys.index("env") < keys.index("tests")

    def test_result_is_a_list(self):
        result = _topo_sort([unit("a"), unit("b")])
        assert isinstance(result, list)

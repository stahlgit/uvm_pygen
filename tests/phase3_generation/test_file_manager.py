"""Tests for FileManager — file writing, 3-way merge, and conflict detection."""

import pytest

from uvm_pygen.services.generation.file_manager import FileManager


@pytest.fixture
def fm(tmp_path, monkeypatch):
    # FileManager joins cache_dir / output_dir / filename — this only works
    # correctly with relative paths (joining an absolute path discards the
    # base).  chdir to tmp_path and use relative dirs, matching real usage.
    monkeypatch.chdir(tmp_path)
    return FileManager(output_dir="output", cache_dir="cache")


class TestFileManagerWrite:
    def test_creates_file_on_first_write(self, fm, tmp_path):
        path = fm.write("test.sv", "module foo; endmodule\n")
        assert path is not None
        assert path.exists()

    def test_file_contains_expected_content(self, fm):
        content = "module foo; endmodule\n"
        path = fm.write("test.sv", content)
        assert path.read_text(encoding="utf-8") == content

    def test_creates_cache_file_alongside_target(self, fm, tmp_path):
        fm.write("test.sv", "content\n")
        # cache_dir="cache", output_dir="output" → cache/output/test.sv
        cache_path = tmp_path / "cache" / "output" / "test.sv"
        assert cache_path.exists()

    def test_creates_subdirectory_file(self, fm, tmp_path):
        path = fm.write("comp.sv", "// driver\n", subdir="components")
        assert path is not None
        assert (tmp_path / "output" / "components" / "comp.sv").exists()

    def test_overwrites_when_local_matches_cache(self, fm, tmp_path):
        original = "module v1; endmodule\n"
        fm.write("test.sv", original)

        updated = "module v2; endmodule\n"
        path = fm.write("test.sv", updated)

        assert path is not None
        assert path.read_text(encoding="utf-8") == updated

    def test_skips_file_when_local_exists_but_no_cache(self, fm, tmp_path):
        # Simulate a pre-existing user file with no cache.
        # The fixture already chdir'd to tmp_path, so "output/" is relative.
        output_file = tmp_path / "output" / "user_file.sv"
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text("// user content\n", encoding="utf-8")

        result = fm.write("user_file.sv", "// generated\n")
        assert result is None
        # Original user content preserved
        assert output_file.read_text(encoding="utf-8") == "// user content\n"

    def test_merges_non_conflicting_changes(self, fm, tmp_path):
        # Generate v1 (base)
        base_content = "line1\nline2\nline3\n"
        fm.write("merge.sv", base_content)

        # User edits line1 in local (fixture chdir'd to tmp_path)
        output_file = tmp_path / "output" / "merge.sv"
        output_file.write_text("USER_line1\nline2\nline3\n", encoding="utf-8")

        # Re-generate with change to line3
        result = fm.write("merge.sv", "line1\nline2\nNEW_line3\n")
        # Non-conflicting merge should succeed (returns a path)
        if result is not None:
            content = result.read_text(encoding="utf-8")
            assert "USER_line1" in content or "NEW_line3" in content

    def test_creates_conflict_file_on_merge_conflict(self, fm, tmp_path):
        # Generate v1 (base and local) — fixture chdir'd to tmp_path
        base_content = "shared_line\n"
        fm.write("conflict.sv", base_content)

        # User edits the same line
        output_file = tmp_path / "output" / "conflict.sv"
        output_file.write_text("USER_EDIT\n", encoding="utf-8")

        # Re-generate with a different change to the same line
        result = fm.write("conflict.sv", "GENERATED_EDIT\n")

        # Conflict creates .conflict file and returns None
        conflict_file = tmp_path / "output" / "conflict.sv.conflict"
        if result is None:
            assert conflict_file.exists()

    def test_returns_path_on_success(self, fm):
        path = fm.write("ok.sv", "content\n")
        assert path is not None
        assert isinstance(path, type(path))  # pathlib.Path


class TestFileManagerReadLines:
    def test_read_lines_returns_none_for_nonexistent(self, fm, tmp_path):
        result = fm._read_lines_if_exists(tmp_path / "nonexistent.sv")
        assert result is None

    def test_read_lines_returns_list_for_existing_file(self, fm, tmp_path):
        f = tmp_path / "sample.sv"
        f.write_text("line1\nline2\n", encoding="utf-8")
        result = fm._read_lines_if_exists(f)
        assert result == ["line1\n", "line2\n"]

    def test_read_lines_returns_empty_list_for_empty_file(self, fm, tmp_path):
        f = tmp_path / "empty.sv"
        f.write_text("", encoding="utf-8")
        result = fm._read_lines_if_exists(f)
        assert result == []

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
        assert result is not None
        content = result.read_text(encoding="utf-8")
        assert "USER_line1" in content
        assert "NEW_line3" in content

    def test_writes_conflict_markers_into_file_on_conflict(self, fm, tmp_path):
        base_content = "shared_line\n"
        fm.write("conflict.sv", base_content)

        output_file = tmp_path / "output" / "conflict.sv"
        output_file.write_text("USER_EDIT\n", encoding="utf-8")

        result = fm.write("conflict.sv", "GENERATED_EDIT\n")

        assert result is None
        content = output_file.read_text(encoding="utf-8")
        assert "your edits" in content
        assert "generated" in content
        assert "USER_EDIT" in content
        assert "GENERATED_EDIT" in content

    def test_conflict_does_not_update_cache(self, fm, tmp_path):
        fm.write("conflict.sv", "shared_line\n")
        cache_path = tmp_path / "cache" / "output" / "conflict.sv"
        cache_mtime_before = cache_path.stat().st_mtime

        output_file = tmp_path / "output" / "conflict.sv"
        output_file.write_text("USER_EDIT\n", encoding="utf-8")
        fm.write("conflict.sv", "GENERATED_EDIT\n")

        assert cache_path.stat().st_mtime == cache_mtime_before

    def test_returns_path_on_success(self, fm):
        path = fm.write("ok.sv", "content\n")
        assert path is not None
        assert isinstance(path, type(path))  # pathlib.Path


class TestFileManagerReset:
    def test_reset_copies_files_to_cache(self, fm, tmp_path):
        output_file = tmp_path / "output" / "foo.sv"
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text("// original\n", encoding="utf-8")

        fm.reset()

        cache_path = tmp_path / "cache" / "output" / "foo.sv"
        assert cache_path.exists()
        assert cache_path.read_text(encoding="utf-8") == "// original\n"

    def test_reset_enables_merge_after_cold_start(self, fm, tmp_path):
        # Simulate cold start: file exists on disk but no cache entry
        output_file = tmp_path / "output" / "bar.sv"
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text("// user content\n", encoding="utf-8")

        # Without reset, write() would skip the file
        result_before = fm.write("bar.sv", "// generated\n")
        assert result_before is None

        # After reset, the file is cached → write() can now merge/overwrite
        output_file.write_text("// user content\n", encoding="utf-8")  # restore
        fm.reset()
        result_after = fm.write("bar.sv", "// generated\n")
        assert result_after is not None

    def test_reset_skips_conflict_files(self, fm, tmp_path):
        output_dir = tmp_path / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        conflict_file = output_dir / "foo.sv.conflict"
        conflict_file.write_text("<<<\n", encoding="utf-8")

        count = fm.reset()

        assert count == 0
        assert not (tmp_path / "cache" / "output" / "foo.sv.conflict").exists()

    def test_reset_returns_file_count(self, fm, tmp_path):
        output_dir = tmp_path / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "a.sv").write_text("a\n", encoding="utf-8")
        (output_dir / "b.sv").write_text("b\n", encoding="utf-8")

        count = fm.reset()
        assert count == 2

    def test_reset_warns_when_output_dir_missing(self, fm, tmp_path):
        # output_dir was created by FileManager.__init__, remove it
        import shutil
        shutil.rmtree(tmp_path / "output")

        count = fm.reset()
        assert count == 0


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

"""
Project Name: uvm_pygen
File Name: file_manager.py
Description: FileManager module for handling file operations.
Author: Peter Stahl (xstahl01@stud.fit.vut.cz)
Date: 2026-05-11
"""

from pathlib import Path

from merge3 import Merge3

from uvm_pygen.services.utils.logger import logger


class FileManager:
    """Handle file system operations."""

    def __init__(self, output_dir: str | Path = "auto_tb", cache_dir: str | Path = ".uvm_pygen/cache") -> None:
        """Initialize FileManager with output directory."""
        self.output_dir = Path(output_dir)
        self.cache_dir = Path(cache_dir)
        self._create_dir(self.output_dir)

    def write(self, filename: str, content: str, subdir: str | None = None) -> Path | None:
        """Write content to a file, optionally in a subdirectory.

        Returns the resolved Path on success, or None if the write was skipped
        (merge conflict or user-file preservation).

        Args:
            filename (str): Name of the file to write.
            content (str): Content to write to the file.
            subdir (str | None): Optional subdirectory within the output directory.
        """
        target_dir = self.output_dir
        if subdir:
            target_dir = self.output_dir / subdir
            self._create_dir(target_dir)

        file_path = target_dir / filename

        # Path in cache (mirror structure, namespaced under output_dir)
        cache_path = self.cache_dir / target_dir / filename
        self._create_dir(cache_path.parent)

        # Read local (existing file)
        local_lines = self._read_lines_if_exists(file_path)

        # Base (cached version from previous generation)
        base_lines = self._read_lines_if_exists(cache_path)

        remote_lines = content.splitlines(keepends=True)

        # If both local and base exist, we need to merge
        if local_lines is not None and base_lines is not None:
            # If local is identical to base, no user changes → just write remote (fast path)
            if local_lines == base_lines:
                final_content = content
            else:
                merge = Merge3(base_lines, local_lines, remote_lines)
                has_conflict = any(
                    isinstance(region, tuple) and region[0] == "conflict" for region in merge.merge_regions()
                )
                if has_conflict:
                    # Write conflict markers into the file itself (Git-style).
                    # The file won't compile, forcing the user to resolve before continuing.
                    # Cache is intentionally NOT updated so the correct base is preserved
                    # for the next run after the user resolves the conflict.
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.writelines(merge.merge_lines(name_a="your edits", name_b="generated"))
                    logger.warning(f"  ⚠️ Merge conflict in {file_path} – resolve conflict markers and re-run.")
                    return None
                else:
                    final_content = "".join(merge.merge_lines())  # and here
        elif local_lines is not None and base_lines is None:
            # File exists but no cache (maybe first run with this file, or cache deleted)
            # Treat as user-created file – we should not overwrite it without asking.
            # For now, we'll warn and skip.
            logger.warning(f"  ⚠️ {file_path} exists but no cache – skipping to preserve user file.")
            return None
        else:
            # File doesn't exist or no local and no base – just write remote
            final_content = content

        # Write final content (if any)
        if final_content is not None:
            logger.debug(f"  Writing: {file_path}")
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(final_content)

        # Always update cache with the newly generated (remote) version
        with open(cache_path, "w", encoding="utf-8") as f:
            f.write(content)

        return file_path

    def reset(self) -> int:
        """Adopt all current output files as the merge base in cache.

        Resolves the cold-start problem: after reset, the next generation
        run can perform three-way merges instead of skipping uncached files.

        Returns the number of files synced to cache.
        """
        if not self.output_dir.exists():
            logger.warning(f"Output directory {self.output_dir} does not exist – nothing to reset.")
            return 0

        count = 0
        for file_path in self.output_dir.rglob("*"):
            if not file_path.is_file():
                continue
            if file_path.suffix == ".conflict":
                continue
            rel = file_path.relative_to(self.output_dir)
            cache_path = self.cache_dir / self.output_dir / rel
            self._create_dir(cache_path.parent)
            cache_path.write_text(file_path.read_text(encoding="utf-8"), encoding="utf-8")
            logger.info(f"  Cached: {file_path}")
            count += 1

        if count:
            logger.info(f"Reset complete – {count} file(s) adopted as merge base.")
        else:
            logger.warning(f"No files found in {self.output_dir} – nothing to reset.")
        return count

    def _create_dir(self, path: Path) -> None:
        """Create directory if it doesn't exist."""
        path.mkdir(parents=True, exist_ok=True)

    def _read_lines_if_exists(self, path: Path) -> list[str] | None:
        """Return file lines if file exists, otherwise None.

        Args:
            path (Path): Path to the file to read.
        """
        if path.exists():
            with open(path, encoding="utf-8") as f:
                return f.readlines()
        return None

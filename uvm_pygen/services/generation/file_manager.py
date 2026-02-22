"""FileManager module for handling file operations."""

from pathlib import Path

from merge3 import Merge3


class FileManager:
    """Handle file system operations."""

    def __init__(self, output_dir: str | Path = "auto_tb", cache_dir: str | Path = ".uvm_pygen/cache") -> None:
        """Initialize FileManager with output directory."""
        self.output_dir = Path(output_dir)
        self.cache_dir = Path(cache_dir)
        self._create_dir(self.output_dir)

    def write(self, filename: str, content: str, subdir: str | None = None) -> None:
        """Write content to a file, optionally in a subdirectory.

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

        # Path in cache (mirror structure)
        cache_path = self.cache_dir / target_dir.relative_to(self.output_dir) / filename
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
                    # Write conflict file and warn
                    conflict_path = file_path.with_suffix(file_path.suffix + ".conflict")
                    with open(conflict_path, "w", encoding="utf-8") as f:
                        f.writelines(merge.merge_lines())  # use merge_lines() here
                    print(f"  ⚠️ Conflict detected – saved as {conflict_path}")
                    # Do not overwrite original file
                    return
                else:
                    final_content = "".join(merge.merge_lines())  # and here
        elif local_lines is not None and base_lines is None:
            # File exists but no cache (maybe first run with this file, or cache deleted)
            # Treat as user-created file – we should not overwrite it without asking.
            # For now, we'll warn and skip.
            print(f"  ⚠️ {file_path} exists but no cache – skipping to preserve user file.")
            return
        else:
            # File doesn't exist or no local and no base – just write remote
            final_content = content

        # Write final content (if any)
        if final_content is not None:
            print(f"  Writing: {file_path}")
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(final_content)

        # Always update cache with the newly generated (remote) version
        with open(cache_path, "w", encoding="utf-8") as f:
            f.write(content)

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

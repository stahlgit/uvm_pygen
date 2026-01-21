"""FileManager module for handling file operations."""

from pathlib import Path


class FileManager:
    """Handle file system operations."""

    def __init__(self, output_dir: str | Path = "auto_tb") -> None:
        """Initialize FileManager with output directory."""
        self.output_dir = Path(output_dir)
        self._create_dir(self.output_dir)

    def write(self, filename: str, content: str, subdir: str | None = None) -> None:
        """Write content to a file, optionally in a subdirectory."""
        target_dir = self.output_dir
        if subdir:
            target_dir = self.output_dir / subdir
            self._create_dir(target_dir)

        file_path = target_dir / filename
        print(f"  Writing: {file_path}")
        file_path.write_text(content, encoding="utf-8")

    def _create_dir(self, path: Path) -> None:
        """Create directory if it doesn't exist."""
        path.mkdir(parents=True, exist_ok=True)

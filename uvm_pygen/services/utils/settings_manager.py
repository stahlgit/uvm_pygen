"""Provides the SettingsManager class for managing user-defined settings and caching them in memory."""

import json
from pathlib import Path

from uvm_pygen.services.utils.logger import logger


class SettingsManager:
    """Manages user-defined settings and caches them in memory."""

    DEFAULT_ALIASES = {
        "control": ["control", "ctrl", "config", "cfg", "mode", "select", "cmd"],
        "data_in": ["input", "data_input", "data_in", "din", "operand", "args"],
        "data_out": ["output", "data_output", "data_out", "dout", "result", "res"],
    }

    def __init__(self, cache_dir: str = ".uvm_pygen"):
        """Initialize the SettingsManager with a directory for caching settings."""
        self.settings_dir = Path(cache_dir)
        self.aliases_file = self.settings_dir / "aliases.json"

        # Load aliases into memory upon instantiation
        self.aliases: dict[str, set[str]] = self._load_aliases()

    def save_aliases(self) -> None:
        """Saves the current in-memory aliases to disk."""
        self.settings_dir.mkdir(parents=True, exist_ok=True)
        save_data = {k: list(v) for k, v in self.aliases.items()}

        with open(self.aliases_file, "w") as f:
            json.dump(save_data, f, indent=4)

    def add_alias(self, group: str, alias: str) -> None:
        """Adds a new alias to a specific port group and updates the disk cache."""
        group, alias = group.lower(), alias.lower()

        if group not in self.aliases:
            self.aliases[group] = set()

        self.aliases[group].add(alias)
        self.save_aliases()

    def show_aliases(self) -> None:
        """Prints the current alias configuration to the console."""
        logger.info("Current Port Group Aliases (from .uvm_pygen/aliases.json):")
        for group, alias_set in self.aliases.items():
            alias_list = ", ".join(sorted(alias_set))
            logger.info(f"  - {group}: {alias_list}")

    def reset_aliases(self) -> None:
        """Deletes the custom aliases file and restores defaults in memory."""
        if self.aliases_file.exists():
            self.aliases_file.unlink()  # Deletes the file
            logger.info("Custom aliases removed from disk.")

        # Revert in-memory state to defaults
        self.aliases = {k: set(v) for k, v in self.DEFAULT_ALIASES.items()}
        logger.info("Successfully reset port group aliases to factory defaults.")

    def _load_aliases(self) -> dict[str, set[str]]:
        """Reads aliases from disk or falls back to defaults."""
        if not self.aliases_file.exists():
            return {k: set(v) for k, v in self.DEFAULT_ALIASES.items()}

        try:
            with open(self.aliases_file) as f:
                data = json.load(f)
            return {k: set(v) for k, v in data.items()}
        except (OSError, json.JSONDecodeError) as e:
            logger.warning(f"Failed to read {self.aliases_file}. Using default aliases. Error: {e}")
            return {k: set(v) for k, v in self.DEFAULT_ALIASES.items()}


# Create a global instance of SettingsManager to be used across the application
settings = SettingsManager()

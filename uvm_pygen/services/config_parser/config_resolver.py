"""Configuration resolver — discovers config files and handles unified configs."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

from uvm_pygen.models.config_schema.config_layout import layout
from uvm_pygen.models.config_schema.resolved_configs import ResolvedConfigs
from uvm_pygen.services.utils.logger import logger


class ConfigResolver:
    """Resolves which configuration file(s) to load.

    Priority order:
        1. Explicit ``unified`` path  -->  ``ResolvedConfigs(unified=…)``
        2. Explicit ``dut`` / ``uvm`` paths (one or both); missing half is
           auto-discovered in *search_dir*.
        3. Fully automatic: scan *search_dir* for a unified YAML first, then
           fall back to separate DUT / UVM files by filename pattern.

    Example:
        >>> resolved = ConfigResolver(search_dir=".").resolve(
        ...     dut_config=args.dut_config,
        ...     uvm_config=args.uvm_config,
        ...     unified_config=args.config,
        ... )
        >>> resolved.is_unified   # True / False
        >>> resolved.unified      # Path | None
        >>> resolved.dut          # Path | None
        >>> resolved.uvm          # Path | None
    """

    # Filename patterns used for auto-discovery (matched against the stem)
    _DUT_PATTERN: re.Pattern = re.compile(r"dut", re.IGNORECASE)
    _UVM_PATTERN: re.Pattern = re.compile(r"uvm|verif|tb|testbench", re.IGNORECASE)

    def __init__(self, search_dir: str | Path = ".") -> None:
        """Initialize the ConfigResolver.

        Args:
            search_dir: Directory to search for configuration files. Defaults to ".".
        """
        self._dut_keys: frozenset[str] = layout.dut_keys
        self._uvm_keys: frozenset[str] = layout.uvm_keys
        self._dut_required_keys: frozenset[str] = layout.dut_required_keys
        self._uvm_required_keys: frozenset[str] = layout.uvm_required_keys
        self._search_dir = Path(search_dir).resolve()

    def resolve(
        self,
        dut_config: str | Path | None = None,
        uvm_config: str | Path | None = None,
        unified_config: str | Path | None = None,
    ) -> ResolvedConfigs:
        """Resolve configuration paths and returns ResolvedConfigs instance.

        Args:
            dut_config: Explicit DUT config path (e.g. from ``--dut-config`` CLI flag).
            uvm_config: Explicit UVM config path (e.g. from ``--uvm-config`` CLI flag).
            unified_config: Explicit unified config path (e.g. from ``--config`` CLI flag).
                Mutually exclusive with the split flags.

        Returns:
            ResolvedConfigs: Container with resolved unified or split config paths.
        """
        # 1. explicit unified path
        if unified_config is not None:
            path = self._must_exist(Path(unified_config), "--config")
            logger.debug(f"Using unified config: {path}")
            return ResolvedConfigs(unified=path)

        # 2. explicit split paths (with auto-discovery of missing half)
        if dut_config is not None or uvm_config is not None:
            dut = self._must_exist(Path(dut_config), "--dut-config") if dut_config else None
            uvm = self._must_exist(Path(uvm_config), "--uvm-config") if uvm_config else None

            # Fill in the missing half via auto-discovery
            if dut is None:
                dut = self._discover_dut()
            if uvm is None:
                uvm = self._discover_uvm()

            return ResolvedConfigs(dut=dut, uvm=uvm)

        # 3. fully automatic
        yaml_files = self._yaml_files_in_search_dir()

        unified = self._find_unified(yaml_files)
        if unified is not None:
            logger.debug(f"Auto-discovered unified config: {unified}")
            return ResolvedConfigs(unified=unified)

        return ResolvedConfigs(
            dut=self._discover_dut(),
            uvm=self._discover_uvm(),
        )

    def split_unified(self, unified_path: Path) -> tuple[dict, dict]:
        """Load unified YAML and split it into (dut_raw, uvm_raw) dicts.

        Args:
            unified_path: Path to the unified YAML file.

        Returns:
            tuple[dict, dict]: A tuple of (dut_raw, uvm_raw) dictionaries.

        Raises:
            ValueError: If either required section (dut or UVM) is absent from the file.
        """
        with open(unified_path) as fh:
            raw: dict = yaml.safe_load(fh) or {}

        dut_raw = {k: v for k, v in raw.items() if k in self._dut_keys}
        uvm_raw = {k: v for k, v in raw.items() if k in self._uvm_keys}

        unknown = set(raw.keys()) - self._dut_keys - self._uvm_keys
        if unknown:
            logger.warning(
                f"Unified config '{unified_path}' contains unrecognised top-level keys (ignored): {sorted(unknown)}"
            )

        missing_dut = self._dut_required_keys - set(dut_raw)
        if missing_dut:
            raise ValueError(f"Unified config '{unified_path}' is missing required DUT keys: {sorted(missing_dut)}.")
        missing_uvm = self._uvm_required_keys - set(uvm_raw)
        if missing_uvm:
            raise ValueError(f"Unified config '{unified_path}' is missing required UVM keys: {sorted(missing_uvm)}.")

        return dut_raw, uvm_raw

    @staticmethod
    def _must_exist(path: Path, flag: str) -> Path:
        """Raise a user-friendly FileNotFoundError if path is missing.

        Args:
            path: Path to check for existence.
            flag: CLI flag name for error message context.

        Returns:
            Path: Resolved absolute path.

        Raises:
            FileNotFoundError: If the path does not exist.
        """
        if not path.exists():
            raise FileNotFoundError(f"File specified via {flag} not found: '{path}'")
        return path.resolve()

    def _yaml_files_in_search_dir(self) -> list[Path]:
        """Return all YAML files in the search directory, sorted by name.

        Returns:
            list[Path]: Sorted list of YAML file paths.
        """
        return sorted(f for f in self._search_dir.iterdir() if f.is_file() and f.suffix in {".yaml", ".yml"})

    def _find_unified(self, yaml_files: list[Path]) -> Path | None:
        """Return the first YAML whose top-level keys look like a unified config.

        Args:
            yaml_files: List of YAML file paths to search.

        Returns:
            Path | None: Path to unified config file, or None if not found.
        """
        for path in yaml_files:
            try:
                with open(path) as fh:
                    top_keys = set(yaml.safe_load(fh) or {})
            except Exception:
                continue
            if top_keys >= self._dut_required_keys and top_keys & self._uvm_required_keys:
                return path
        return None

    def _discover_dut(self) -> Path | None:
        """Return the first YAML in search_dir whose stem contains 'dut'.

        Returns:
            Path | None: Path to DUT config file, or None if not found.
        """
        candidates = [f for f in self._yaml_files_in_search_dir() if self._DUT_PATTERN.search(f.stem)]
        return self._pick_candidate(candidates, "DUT", "--dut-config")

    def _discover_uvm(self) -> Path | None:
        """Return the first YAML in search_dir whose stem matches the UVM pattern.

        Returns:
            Path | None: Path to UVM config file, or None if not found.
        """
        candidates = [f for f in self._yaml_files_in_search_dir() if self._UVM_PATTERN.search(f.stem)]
        return self._pick_candidate(candidates, "UVM", "--uvm-config")

    def _pick_candidate(
        self,
        candidates: list[Path],
        label: str,
        flag: str,
    ) -> Path | None:
        """Log and return the best candidate from a list, or None if empty.

        Args:
            candidates: List of candidate file paths.
            label: Label for logging (e.g., "DUT" or "UVM").
            flag: CLI flag name for logging context.

        Returns:
            Path | None: First candidate path, or None if list is empty.
        """
        if not candidates:
            logger.warning(f"No {label} config file found in '{self._search_dir}'. Pass {flag} explicitly.")
            return None
        if len(candidates) > 1:
            logger.warning(
                f"Multiple {label} config candidates found: "
                f"{[c.name for c in candidates]}. "
                f"Using '{candidates[0].name}'. Pass {flag} to choose explicitly."
            )
        logger.info(f"Auto-discovered {label} config: {candidates[0]}")
        return candidates[0]

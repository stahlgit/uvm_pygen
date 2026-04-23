"""Cache for last-used configuration paths (.uvm_pygen/cache.json)."""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

from uvm_pygen.constants.cache_enum import ConfigMode
from uvm_pygen.models.config_schema.resolved_configs import ResolvedConfigs
from uvm_pygen.services.utils.logger import logger

_CACHE_DIR = Path(".uvm_pygen")
_CACHE_FILE = _CACHE_DIR / "cache.json"


def write_cache(resolved: ResolvedConfigs) -> None:
    """Persist resolved config paths to .uvm_pygen/cache.json."""
    _CACHE_DIR.mkdir(exist_ok=True)

    if resolved.is_unified:
        payload = {
            "resolved_at": datetime.now().isoformat(timespec="seconds"),
            "mode": ConfigMode.UNIFIED,
            "config": str(resolved.unified),
        }
    else:
        payload = {
            "resolved_at": datetime.now().isoformat(timespec="seconds"),
            "mode": ConfigMode.SPLIT,
            "dut": str(resolved.dut),
            "uvm": str(resolved.uvm),
        }

    _CACHE_FILE.write_text(json.dumps(payload, indent=2))
    logger.debug(f"Cache written: {_CACHE_FILE}")


def read_cache() -> ResolvedConfigs:
    """Load config paths from .uvm_pygen/cache.json.

    Raises:
        SystemExit: If the cache file is missing, malformed, or references missing files.
    """
    if not _CACHE_FILE.exists():
        logger.error(
            f"--use-cache specified but no cache file found at '{_CACHE_FILE}'. "
            "Run once without --use-cache to create it."
        )
        sys.exit(1)

    try:
        data: dict = json.loads(_CACHE_FILE.read_text())
    except json.JSONDecodeError as exc:
        logger.error(f"Cache file '{_CACHE_FILE}' is not valid JSON: {exc}")
        sys.exit(1)

    mode = data.get("mode")
    resolved_at = data.get("resolved_at", "<unknown>")
    logger.info(f"Using cached config from {resolved_at} (mode={mode})")

    if mode == ConfigMode.UNIFIED:
        raw = data.get("config")
        if not raw:
            logger.error(f"Cache file '{_CACHE_FILE}' is missing 'config' field.")
            sys.exit(1)
        path = Path(raw)
        if not path.exists():
            logger.error(f"Cached unified config no longer exists: '{path}'")
            sys.exit(1)
        return ResolvedConfigs(unified=path)

    if mode == ConfigMode.SPLIT:
        raw_dut = data.get("dut")
        raw_uvm = data.get("uvm")
        if not raw_dut or not raw_uvm:
            logger.error(f"Cache file '{_CACHE_FILE}' is missing 'dut' or 'uvm' field.")
            sys.exit(1)
        dut, uvm = Path(raw_dut), Path(raw_uvm)
        missing = [str(p) for p in (dut, uvm) if not p.exists()]
        if missing:
            logger.error(f"Cached config file(s) no longer exist: {missing}")
            sys.exit(1)
        return ResolvedConfigs(dut=dut, uvm=uvm)

    logger.error(f"Cache file '{_CACHE_FILE}' has unknown mode '{mode}'. Expected 'unified' or 'split'.")
    sys.exit(1)

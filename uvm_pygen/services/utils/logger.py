"""Logging utilities for uvm_pygen, including enhanced JSON formatting and debug mode toggling."""

import logging
import pprint
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel
from rich.pretty import Pretty

LOG_DIR = Path(".uvm_pygen/logs")

_rich_console = Console(stderr=False)


def setup_logger(log_dir: str | Path = LOG_DIR) -> logging.Logger:
    """Sets up a logger with both console and file handlers, ensuring UTF-8 encoding for file logs."""
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("uvm_pygen")
    logger.setLevel(logging.DEBUG)

    # 1. Console (Rich)
    console_handler = RichHandler(level=logging.INFO, markup=True)
    console_handler.set_name("console")

    # 2. File (UTF-8 fixed)
    file_handler = logging.FileHandler(log_path / "uvm_pygen.log", mode="a", encoding="utf-8")
    file_handler.setLevel(logging.WARNING)
    file_handler.set_name("file")
    file_format = logging.Formatter("%(asctime)s | %(levelname)-8s | %(module)s | %(message)s")
    file_handler.setFormatter(file_format)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    return logger


logger: logging.Logger = setup_logger()


def set_debug_mode(enable: bool = True):
    """Toggles debug mode for the logger."""
    debug_file_name = "uvm_pygen_debug.log"

    if enable:
        if not any(h.name == "debug_file" for h in logger.handlers):
            debug_path = LOG_DIR / debug_file_name
            debug_handler = logging.FileHandler(debug_path, mode="w", encoding="utf-8")
            debug_handler.setLevel(logging.DEBUG)
            debug_handler.set_name("debug_file")

            debug_format = logging.Formatter(
                "%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s"
            )
            debug_handler.setFormatter(debug_format)

            logger.addHandler(debug_handler)

        for h in logger.handlers:
            if h.name == "console":
                h.setLevel(logging.DEBUG)
    else:
        logger.handlers = [h for h in logger.handlers if h.name != "debug_file"]

        for h in logger.handlers:
            if h.name == "console":
                h.setLevel(logging.INFO)


def log_object(
    obj: Any,
    *,
    label: str | None = None,
    level: int = logging.DEBUG,
    expand_all: bool = True,
) -> None:
    """Pretty-prints any Python object to console.

    Args:
        obj:        The object to inspect and display.
        label:      Optional title shown in the panel header (defaults to the object's type name).
        level:      Logging level used for the plain-text file entry (default: DEBUG).
        expand_all: When True, Rich expands nested structures fully instead of collapsing them.
    """
    title = label or type(obj).__name__

    # --- Plain-text record for file / debug handlers ---
    plain_repr = pprint.pformat(obj, indent=2, width=120, compact=True)
    plain_message = f"{title}:\n{plain_repr}"

    record = logger.makeRecord(
        name=logger.name,
        level=level,
        fn="",
        lno=0,
        msg=plain_message,
        args=(),
        exc_info=None,
    )

    # --- Rich console output — only if the console handler would emit at this level ---
    console_handler = next((h for h in logger.handlers if h.name == "console"), None)
    if console_handler is not None and record.levelno >= console_handler.level:
        _rich_console.print(
            Panel(
                Pretty(obj, expand_all=expand_all),
                title=f"[bold cyan]{title}[/bold cyan]",
                border_style="bright_black",
            )
        )

    # Emit plain text to non-console handlers only (avoids a double printout on the terminal)
    for handler in logger.handlers:
        if handler.name != "console" and record.levelno >= handler.level:
            handler.emit(record)

"""Logging utilities for uvm_pygen, including enhanced JSON formatting and debug mode toggling."""

import logging
from pathlib import Path

from rich.logging import RichHandler

LOG_DIR = Path(".uvm_pygen/logs")


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

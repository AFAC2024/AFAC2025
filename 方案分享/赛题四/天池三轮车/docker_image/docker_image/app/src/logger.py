import sys
from datetime import datetime
from pathlib import Path

from loguru import logger as _logger
from rich.logging import RichHandler

from src.config import PROJECT_ROOT


_print_level = "INFO"


def define_log_level(print_level="INFO", logfile_level="DEBUG", name: str = None):
    """Adjust the log level to above level"""
    global _print_level
    _print_level = print_level

    current_date = datetime.now()
    formatted_date = current_date.strftime("%Y%m%d%H%M%S")
    log_name = (
        f"{name}_{formatted_date}" if name else formatted_date
    )  # name a log with prefix name

    _logger.remove()
    
    # Only write to file by default
    _logger.add(PROJECT_ROOT / f"logs/{log_name}.log", level=logfile_level)
    
    # Add terminal handler only if explicitly requested
    if print_level != "OFF":
        _logger.add(
            RichHandler(rich_tracebacks=True, markup=True, show_time=False, show_path=False),
            level=print_level,
            format="<level>{message}</level>",
        )
    
    return _logger


logger = define_log_level(print_level="OFF")  # Default to file-only logging


if __name__ == "__main__":
    logger.info("Starting application")
    logger.debug("Debug message")
    logger.warning("Warning message")
    logger.error("Error message")
    logger.critical("Critical message")

    try:
        raise ValueError("Test error")
    except Exception as e:
        logger.exception(f"An error occurred: {e}")

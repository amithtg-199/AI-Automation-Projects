import os
import logging

_LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
os.makedirs(_LOG_DIR, exist_ok=True)
_LOG_FILE = os.path.join(_LOG_DIR, "rag_pipeline.log")

# Clear log file once when the module is first imported (app startup).
# After this, all loggers append to the same file via a shared handler.
open(_LOG_FILE, "w").close()

_file_handler = logging.FileHandler(_LOG_FILE, mode="a", encoding="utf-8")
_file_handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))

_console_handler = logging.StreamHandler()
_console_handler.setFormatter(logging.Formatter("%(levelname)s - %(message)s"))


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        logger.addHandler(_file_handler)
        logger.addHandler(_console_handler)

    return logger

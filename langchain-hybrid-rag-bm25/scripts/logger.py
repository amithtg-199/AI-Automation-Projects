import os
import logging

_LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
os.makedirs(_LOG_DIR, exist_ok=True)
_LOG_FILE = os.path.join(_LOG_DIR, "rag_pipeline.log")


_current_file_handlers = []

_console_handler = logging.StreamHandler()
_console_handler.setFormatter(logging.Formatter("%(levelname)s - %(message)s"))


def setup_action_logger(action_name: str, clear_old: bool = True):
    """
    Configures logging for a specific action iteration (ingestion, generation, evaluation, human_loop_reviews).
    Clears old logs for that action if clear_old=True and routes all logger output to logs/<action_name>.log.
    """
    global _current_file_handlers
    log_file = os.path.join(_LOG_DIR, f"{action_name}.log")
    if clear_old and os.path.exists(log_file):
        open(log_file, "w").close()

    # Remove previous file handlers from root logger
    root_logger = logging.getLogger()
    for h in _current_file_handlers:
        root_logger.removeHandler(h)
    _current_file_handlers.clear()

    # Clean existing module loggers so they propagate to root or use the new handler
    for l in logging.Logger.manager.loggerDict.values():
        if isinstance(l, logging.Logger):
            for h in list(l.handlers):
                if isinstance(h, logging.FileHandler):
                    l.removeHandler(h)

    # Attach new action file handler
    fh = logging.FileHandler(log_file, mode="a", encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
    root_logger.addHandler(fh)
    if _console_handler not in root_logger.handlers:
        root_logger.addHandler(_console_handler)
    root_logger.setLevel(logging.INFO)
    _current_file_handlers.append(fh)

    # Silence noisy third-party HTTP and access loggers
    for noisy in ["httpx", "httpcore", "urllib3", "qdrant_client"]:
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    if _console_handler not in root_logger.handlers:
        root_logger.addHandler(_console_handler)

    # If no action logger has been initialized yet, attach a default file handler
    if not _current_file_handlers and not any(isinstance(h, logging.FileHandler) for h in root_logger.handlers):
        default_file = os.path.join(_LOG_DIR, "rag_pipeline.log")
        fh = logging.FileHandler(default_file, mode="a", encoding="utf-8")
        fh.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
        root_logger.addHandler(fh)
        _current_file_handlers.append(fh)

    for noisy in ["httpx", "httpcore", "urllib3", "qdrant_client"]:
        logging.getLogger(noisy).setLevel(logging.WARNING)

    return logger

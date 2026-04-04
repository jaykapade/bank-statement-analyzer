import logging
import os


def setup_logger(name: str = "app") -> logging.Logger:
    logger = logging.getLogger(name)

    # Guard: don't add handlers if they already exist (prevents duplicate logs)
    if logger.handlers:
        return logger

    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    logger.setLevel(getattr(logging, log_level, logging.INFO))

    ch = logging.StreamHandler()
    ch.setLevel(logger.level)

    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    ch.setFormatter(formatter)

    logger.addHandler(ch)
    logger.propagate = False  # Don't bubble up to root logger

    return logger


# Root app logger — import this everywhere
logger = setup_logger("app")
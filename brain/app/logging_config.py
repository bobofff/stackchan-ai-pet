from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path


LOGGER_NAME = "stackchan_ai_pet"
MANAGED_HANDLER_ATTR = "_stackchan_log_file_handler"


def get_app_logger(log_dir_path: str) -> logging.Logger:
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    path = build_daily_log_path(log_dir_path)
    absolute_path = path.resolve()
    handler_name = str(absolute_path)
    for handler in list(logger.handlers):
        if not getattr(handler, MANAGED_HANDLER_ATTR, False):
            continue
        if getattr(handler, "name", None) == handler_name:
            return logger
        logger.removeHandler(handler)
        handler.close()

    if any(getattr(handler, "name", None) == handler_name for handler in logger.handlers):
        return logger

    path.parent.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(path, encoding="utf-8")
    handler.name = handler_name
    setattr(handler, MANAGED_HANDLER_ATTR, True)
    handler.setLevel(logging.INFO)
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s %(levelname)s [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    logger.addHandler(handler)
    return logger


def build_daily_log_path(log_dir_path: str) -> Path:
    now = datetime.now()
    return Path(log_dir_path) / now.strftime("%Y-%m") / f"{now:%d}.log"

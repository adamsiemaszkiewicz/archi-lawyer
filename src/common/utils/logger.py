# -*- coding: utf-8 -*-
import os
import time
from functools import wraps
from logging import INFO, Formatter, Logger, LogRecord, StreamHandler, getLogger
from typing import Callable, TypeVar, Union

from typing_extensions import ParamSpec

from src.common.consts.directories import ROOT_DIR
from src.common.consts.logger import LOGGING_FORMAT

T = TypeVar("T")
P = ParamSpec("P")


class RelativePathFormatter(Formatter):
    def __init__(self, fmt: str, root_dir: str) -> None:
        super().__init__(fmt)
        self.root_dir = root_dir

    def format(self, record: LogRecord) -> str:
        record.pathname = os.path.relpath(record.pathname, self.root_dir)
        return super().format(record)


def get_logger(name: str, log_level: Union[int, str] = INFO) -> Logger:
    """
    Builds a `Logger` instance with provided name and log level.
    Args:
        name: The name for the logger.
        log_level: The default log level.
    Returns: The logger.
    """

    logger = getLogger(name=name)
    logger.setLevel(log_level)

    stream_handler = StreamHandler()
    formatter = RelativePathFormatter(fmt=LOGGING_FORMAT, root_dir=ROOT_DIR.as_posix())
    stream_handler.setFormatter(fmt=formatter)
    logger.addHandler(stream_handler)

    return logger


def timed(func: Callable[P, T]) -> Callable[P, T]:
    """This decorator prints the execution time for the decorated function."""

    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        start = time.time()
        _timed_logger.info(f"{func.__qualname__} is running...")
        result = func(*args, **kwargs)
        end = time.time()
        _timed_logger.info(f"{func.__qualname__} ran in {(end - start):.4f}s")
        return result

    return wrapper


_timed_logger = get_logger("timed")

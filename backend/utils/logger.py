import logging
import os
import warnings
from pathlib import Path
from datetime import datetime
from backend.settings import Config
from functools import cached_property
from dataclasses import dataclass, field


warnings.filterwarnings('ignore')

LOG_FORMAT: str = '%(levelname)s | %(asctime)s | PID: %(process)d | %(name)s | %(message)s | Function: %(funcName)s | Line: %(lineno)d'
DATE_FORMAT: str = '%A | %d/%m/%Y | %X'

_log_file_handler: logging.FileHandler | None = None
_log_file_path: Path | None = None


def _get_log_level() -> int:
    level_name = Config.LOG_LEVEL.upper()
    return getattr(logging, level_name, logging.DEBUG)


def _get_file_handler() -> logging.FileHandler:
    """Return a single shared file handler for the entire process lifetime."""
    global _log_file_handler, _log_file_path
    if _log_file_handler is None:
        logs_dir = Path(Config.LOG_DIR)
        logs_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = logs_dir / f"bini_{timestamp}_pid{os.getpid()}.log"
        _log_file_handler = logging.FileHandler(str(log_file), mode="a", encoding="utf-8")
        _log_file_handler.setLevel(_get_log_level())
        _log_file_handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))
        _log_file_path = log_file
    return _log_file_handler


@dataclass
class Logger:

    name: str

    def __post_init__(self) -> None:
        self._logger = logging.getLogger(self.name)
        self._logger.setLevel(_get_log_level())
        if not self._logger.handlers:
            self._logger.addHandler(_get_file_handler())
        self._logger.propagate = False

    def info(self, message: str) -> None:
        self._logger.info(message)

    def debug(self, message: str) -> None:
        self._logger.debug(message)

    def warning(self, message: str) -> None:
        self._logger.warning(message)

    def error(self, message: str) -> None:
        self._logger.error(message)

    def exception(self, message: str) -> None:
        self._logger.exception(message)

    @property
    def log_file_path(self) -> str | None:
        return str(_log_file_path) if _log_file_path else None


@dataclass
class Logfire:

    name: str
    _logger: object = field(init=False, default=None)

    @cached_property
    def fire(self) -> Logger:
        return Logger(name=self.name)

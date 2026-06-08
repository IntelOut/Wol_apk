import logging
import logging.handlers
import os

import sentry_sdk
from sentry_sdk.integrations.logging import LoggingIntegration

from wol_app.config import VERSION

_LOG_DIR = ".wol_app_data"
_LOG_FILE = "wol_app.log"
_LOG_MAX_BYTES = 5 * 1024 * 1024
_LOG_BACKUP_COUNT = 3


def get_log_dir() -> str:
    data_dir = os.environ.get("WOL_DATA_DIR", "")
    if data_dir:
        return data_dir
    return os.path.join(os.path.expanduser("~"), _LOG_DIR)


def get_log_path() -> str:
    return os.path.join(get_log_dir(), _LOG_FILE)


def setup_logging(log_dir: str | None = None) -> str:
    if log_dir is None:
        log_dir = get_log_dir()
    os.makedirs(log_dir, exist_ok=True)

    log_path = os.path.join(log_dir, _LOG_FILE)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    _clear_handlers(root_logger)

    file_handler = logging.handlers.RotatingFileHandler(
        log_path,
        maxBytes=_LOG_MAX_BYTES,
        backupCount=_LOG_BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)
    console_formatter = logging.Formatter("%(levelname)s: %(message)s")
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    root_logger.info("Logging initialised at %s (v%s)", log_path, VERSION)

    return log_path


def setup_sentry(dsn: str | None, consent_given: bool = False) -> None:
    if not dsn or not consent_given:
        return
    sentry_sdk.init(
        dsn=dsn,
        release=f"wol_app@{VERSION}",
        environment="production" if "rc" not in VERSION else "beta",
        integrations=[
            LoggingIntegration(level=logging.WARNING, event_level=logging.ERROR),
        ],
        traces_sample_rate=0.0,
        send_default_pii=False,
    )


def clear_log() -> None:
    log_path = get_log_path()
    try:
        with open(log_path, "w", encoding="utf-8") as f:
            f.write("")
    except Exception:
        pass


def _clear_handlers(logger: logging.Logger) -> None:
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()

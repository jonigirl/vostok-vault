import logging
import logging.handlers

from .paths import BACKUP_DIR, LOG_FILE


def setup_logging(debug: bool = False) -> None:
    try:
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        level = logging.DEBUG if debug else logging.WARNING
        handler = logging.handlers.RotatingFileHandler(
            LOG_FILE, maxBytes=512_000, backupCount=1, encoding="utf-8"
        )
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
        )
        root_logger = logging.getLogger()
        root_logger.handlers.clear()
        root_logger.addHandler(handler)
        root_logger.setLevel(level)
    except OSError:
        logging.basicConfig(level=logging.WARNING)

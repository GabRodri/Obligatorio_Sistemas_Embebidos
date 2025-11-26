import logging
from logging.handlers import RotatingFileHandler
import os

# Carpeta logs
LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
os.makedirs(LOG_DIR, exist_ok=True)

def setup_logger(name: str, filename: str, level=logging.INFO) -> logging.Logger:
    """
    Crea un logger con RotatingFileHandler.
    - name: nombre del logger
    - filename: archivo dentro de ./logs/
    - level: logging level (INFO, DEBUG, etc)
    """
    logger = logging.getLogger(name)

    # Evitar reconfigurar si ya existe
    if logger.handlers:
        return logger

    logger.setLevel(level)

    log_path = os.path.join(LOG_DIR, filename)

    handler = RotatingFileHandler(
        log_path,
        maxBytes=10_000_000,   # 10 MB
        backupCount=1,         # 1 archivos de backup
        encoding="utf-8"
    )

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] [%(threadName)s] %(name)s: %(message)s"
    )
    handler.setFormatter(formatter)

    logger.addHandler(handler)
    logger.propagate = False

    return logger

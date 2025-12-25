"""Logging configuration."""
import logging
import sys
from pathlib import Path

from src.utils.config import settings

# Track if logging has been setup to avoid reconfiguring in reload scenarios
_logging_initialized = False


def setup_logging():
    """Configure application logging with file and console handlers."""
    global _logging_initialized
    
    # Only setup once, or always reset if forced (hot reload safety)
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    
    # Ensure logs directory exists
    log_dir = Path(settings.LOG_FILE).parent
    log_dir.mkdir(parents=True, exist_ok=True)

    # Create formatters
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    formatter = logging.Formatter(log_format)

    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Remove existing handlers to avoid duplicates (especially on reload)
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Console handler (always)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # File handler (always)
    try:
        file_handler = logging.FileHandler(settings.LOG_FILE, encoding='utf-8')
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    except Exception as e:
        print(f"Warning: Could not setup file logging to {settings.LOG_FILE}: {e}", file=sys.stderr)

    # Configure third-party loggers to not propagate excessively.
    # NOTE: SQLAlchemy may attach handlers early (e.g. when echo=True).
    # Clean them up to avoid duplicate log lines.
    sqlalchemy_level = logging.INFO if settings.SQLALCHEMY_ECHO else logging.WARNING
    for logger_name in [
        "sqlalchemy.engine",
        "sqlalchemy.engine.Engine",
        "sqlalchemy.pool",
    ]:
        sqlalchemy_logger = logging.getLogger(logger_name)
        for handler in sqlalchemy_logger.handlers[:]:
            sqlalchemy_logger.removeHandler(handler)
        sqlalchemy_logger.propagate = True
        sqlalchemy_logger.setLevel(sqlalchemy_level)

    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("socketio").setLevel(logging.WARNING)
    logging.getLogger("socketio.server").setLevel(logging.WARNING)
    logging.getLogger("engineio").setLevel(logging.WARNING)
    logging.getLogger("engineio.server").setLevel(logging.WARNING)
    
    _logging_initialized = True


def get_logger(name: str) -> logging.Logger:
    """Get logger instance."""
    return logging.getLogger(name)

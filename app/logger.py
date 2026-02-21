import sys
from datetime import datetime
import structlog
from loguru import logger as _logger
from app.config import PROJECT_ROOT

_print_level = "INFO"

def configure_structlog():
    """Configure structlog to wrap loguru."""
    structlog.configure(
        processors=[
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            # JSON renderer for production
            structlog.processors.JSONRenderer()
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

def define_log_level(print_level="INFO", logfile_level="DEBUG", name: str = None):
    """Adjust the log level to above level"""
    global _print_level
    _print_level = print_level

    current_date = datetime.now()
    formatted_date = current_date.strftime("%Y%m%d%H%M%S")
    log_name = (
        f"{name}_{formatted_date}" if name else formatted_date
    )

    _logger.remove()

    # Add stderr sink with structured formatting if needed, but for dev we keep it simple
    # For production, we might want JSON output to stdout
    _logger.add(sys.stderr, level=print_level)
    _logger.add(PROJECT_ROOT / f"logs/{log_name}.log", level=logfile_level)

    return _logger

# Initialize structlog configuration
configure_structlog()

# Expose the loguru logger as the primary logger
# In a real integration, we might want to intercept standard logging calls and route them to loguru/structlog
logger = define_log_level()

if __name__ == "__main__":
    logger.info("Starting application")
    logger.debug("Debug message")
    logger.warning("Warning message")
    logger.error("Error message")
    logger.critical("Critical message")

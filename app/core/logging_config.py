# app/core/logging_config.py
import logging
import sys
import structlog
import os


def setup_logging(log_level_str: str = "INFO"):
    log_level = getattr(logging, log_level_str.upper(), logging.INFO)

    # Common processors for all environments
    shared_processors = [
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
    ]

    # Configure structlog
    structlog.configure(
        processors=shared_processors + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Configure standard logging to use structlog
    # This ensures that logs from other libraries also go through structlog
    root_logger = logging.getLogger()
    # Remove any existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create a handler that uses structlog's ProcessorFormatter
    # This handler will format logs processed by structlog
    structlog_handler = logging.StreamHandler(sys.stdout)  # Or logging.FileHandler for file output
    # No formatter needed here if structlog handles final rendering
    # structlog_handler.setFormatter(structlog.stdlib.ProcessorFormatter.wrap_for_formatter(
    #     structlog.dev.ConsoleRenderer() # Or JSONRenderer
    # ))

    root_logger.addHandler(structlog_handler)
    root_logger.setLevel(log_level)

    # Example: Quieten overly verbose libraries if needed
    # logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    # logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)

    log = structlog.get_logger("logging_config")
    log.info("Logging configured", log_level=log_level_str,
             renderer="ConsoleRenderer" if os.getenv("ENV_TYPE", "dev") == "dev" else "JSONRenderer")
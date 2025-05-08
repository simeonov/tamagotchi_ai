# app/core/logging_config.py
import logging
import sys
import structlog
from fastapi_structlog import LogSettings # If using its settings model

def setup_logging():
    # Basic structlog configuration for JSON output to console
    # For production, you'd configure handlers for cloud logging services ()
    # or file logging.
    structlog.configure(
        processors=[
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    formatter = structlog.stdlib.ProcessorFormatter.wrap_for_formatter(
        # For JSON output:
        structlog.processors.JSONRenderer(),
        # For console development (human-readable):
        # structlog.dev.ConsoleRenderer(),
    )
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO) # Adjust log level as needed

    # You can also use LogSettings from fastapi-structlog for more advanced config
    # settings = LogSettings(level="INFO", types=["console"])
    # init_logger(settings) # from fastapi_structlog
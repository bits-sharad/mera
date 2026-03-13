import logging
from typing import Optional
from dataclasses import asdict
from src.utils.logging.siem_event import SiemEventDetail


class SiemLogLevel:
    """Constants for SIEM logging configuration"""

    # Setting SIEM level higher than ERROR(40) to ensure it's always logged
    LEVEL_NUM = 45
    LEVEL_NAME = "SIEM"


class SiemFormatter(logging.Formatter):
    """Custom formatter for SIEM events"""

    def format(self, record: logging.LogRecord) -> str:
        if hasattr(record, "siem_event"):
            event: SiemEventDetail = record.siem_event
            event.msg = f"SIEM-APP| {event.msg}"
            return f"{event.msg} , {event.to_json()}"
        return super().format(record)


class SiemLogger(logging.Logger):
    """Custom logger for SIEM events with dedicated formatting"""

    def __init__(self, name: str, level: int = logging.NOTSET):
        super().__init__(name, level)

        # Register the SIEM log level
        logging.addLevelName(SiemLogLevel.LEVEL_NUM, SiemLogLevel.LEVEL_NAME)

        # Add default handler if none exists
        if not self.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(SiemFormatter())
            self.addHandler(handler)

    def siem(self, event: SiemEventDetail) -> None:
        """
        Log a SIEM event with custom formatting

        Args:
            event: The SIEM event details to log
        """
        # Attach the event object to the log record for formatter access
        extra = {"siem_event": event}
        self.log(SiemLogLevel.LEVEL_NUM, event.msg, extra=extra)


# Configure and export the logger
logging.setLoggerClass(SiemLogger)
logger = logging.getLogger("siem")

# Export symbols
__all__ = ["logger", "SiemLogger", "SiemLogLevel"]

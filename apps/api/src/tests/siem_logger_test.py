import pytest
import logging
from src.utils.logging.siem_event import SiemEventDetail, SiemEventName
from src.utils.logging.siem_logger import SiemLogger

# Create a logger for testing
logging.setLoggerClass(SiemLogger)
logger = logging.getLogger("test_logger")

# Prepare the SiemEventDetail for AUTHORIZATION_FAILURE
auth_failure_event = SiemEventDetail(
    msg="Authorization failure",
    context={
        "event_name": SiemEventName.AUTHORIZATION_FAILURE,
        "context": f"Okta SSO via https://core-api",
    },
    application_code="jbsltons",
    application_component="OktaGuard",
    application_instance="https://localhost:8081/api/v1/tasks",
    authentication_channel="SSO",
    identity_provider="OKTA",
    correlation_id="correlation-id-12345",
    session_id="session-id-67890",
    client_ip_address="127.0.0.1",
    location="localhost",
    timestamp="2025-03-10T14:02:02.123Z",
    acting_as_user="",
    actor_name="not-verified",
    tracking_number="",
)


# Test class for SiemLogger
class TestSiemLogger:
    @pytest.fixture(autouse=True)
    def setup_logging(self, caplog):
        # caplog is a built-in fixture that captures log messages
        self.caplog = caplog
        # Set the logger level to SIEM_LOG_LEVEL for testing
        logger.setLevel(logging.DEBUG)

    def test_siem_logging(self, capfd):
        # Log the SIEM event
        logger.siem(auth_failure_event)

        # Check if the log was recorded
        assert len(self.caplog.records) == 1
        record = self.caplog.records[0]

        # Verify that the log level is correct
        assert record.levelno == 45  # SIEM_LOG_LEVEL
        assert record.levelname == "SIEM"

        # Verify the log message format
        capture = capfd.readouterr()

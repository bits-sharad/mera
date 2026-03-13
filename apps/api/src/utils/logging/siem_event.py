from enum import Enum
from typing import Union, Dict, Any
import json

"""
    Definition of a MMC SIEM Logging standards
    https://mmcglobal.sharepoint.com/sites/GIS-DevSecOps-SecureSDLC/SitePages/Application-Security-Logging-Standard.aspx

    The subset of events applicable to this micro service are implemented here.
"""


class SiemEventSeverity(str, Enum):
    INFO = "info"
    WARN = "warn"
    ERROR = "error"


class SiemEventName(str, Enum):
    INPUT_VALIDATION = "InputValidation"
    OUTPUT_VALIDATION = "OutputValidation"
    SESSION_MANAGEMENT_EXCEPTIONS = "SessionManagementExceptions"
    AUTHORIZATION_FAILURE = "AuthorizationFailure"


class WindowsEventId(str, Enum):
    VERIFICATION_OPERATION_FAILED = "5060"
    ACCESS_ATTEMPT = "4663"


SIEM_EVENT = {
    SiemEventName.INPUT_VALIDATION: {
        "id": WindowsEventId.VERIFICATION_OPERATION_FAILED,
        "severity": SiemEventSeverity.ERROR,
    },
    SiemEventName.OUTPUT_VALIDATION: {
        "id": WindowsEventId.VERIFICATION_OPERATION_FAILED,
        "severity": SiemEventSeverity.ERROR,
    },
    SiemEventName.SESSION_MANAGEMENT_EXCEPTIONS: {
        "id": WindowsEventId.VERIFICATION_OPERATION_FAILED,
        "severity": SiemEventSeverity.ERROR,
    },
    SiemEventName.AUTHORIZATION_FAILURE: {
        "id": WindowsEventId.ACCESS_ATTEMPT,
        "severity": SiemEventSeverity.ERROR,
    },
}


class SiemEventDetail:
    def __init__(
        self,
        msg: str,
        context: Union[str, Dict[str, Any]],
        application_component: str,
        acting_as_user: str = None,
        authentication_channel: str = None,
        identity_provider: str = None,
        tracking_number: str = None,
        event_type: str = "MMC-Security",
        session_id: str = None,
        correlation_id: str = None,
        client_ip_address: str = None,
        application_instance: str = None,
        location: str = None,
        actor_name: str = None,
        timestamp: str = None,
        application_code: str = None,
    ):
        event_name = context.get("event_name")
        event_info = SIEM_EVENT[event_name]

        self.msg = msg
        self.context = context.get("context")
        self.application_component = application_component
        self.acting_as_user = acting_as_user
        self.authentication_channel = authentication_channel
        self.identity_provider = identity_provider
        self.tracking_number = tracking_number
        self.session_id = session_id
        self.correlation_id = correlation_id
        self.client_ip_address = client_ip_address
        self.application_instance = application_instance
        self.location = location
        self.actor_name = actor_name
        self.timestamp = timestamp
        self.application_code = application_code
        self.event_name = event_name
        self.event_id = event_info["id"]
        self.severity = event_info["severity"]
        self.event_type = event_type

    def __to_dict__(self):
        return {
            "EventName": self.event_name,
            "EventID": self.event_id,
            "EventType": self.event_type,
            "Severity": self.severity,
            "Timestamp": self.timestamp,
            "ClientIPAddress": self.client_ip_address,
            "Location": self.location,
            "ApplicationCode": self.application_code,
            "ApplicationComponent": self.application_component,
            "ActorName": self.actor_name,
            "Context": self.context,
            "Msg": self.msg,
            "IdentityProvider": self.identity_provider,
            "ApplicationInstance": self.application_instance,
            "ActingAsUser": self.acting_as_user,
            "AuthenticationChannel": self.authentication_channel,
            "TrackingNumber": self.tracking_number,
            "SessionID": self.session_id if self.session_id else "",
            "CorrelationID": self.correlation_id if self.correlation_id else "",
        }

    def to_json(self):
        return json.dumps(self.__to_dict__(), default=str)

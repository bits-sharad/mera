import socket
from fastapi import Request, Response
from src.utils.logging.siem_logger import logger
from src.utils.logging.siem_event import SiemEventDetail, SiemEventName
from okta_jwt_verifier import AccessTokenVerifier
from starlette.middleware.base import BaseHTTPMiddleware
from src.utils.config_service import ConfigService
from typing import Optional
from enum import Enum
from datetime import datetime, timezone

# Open URLs that don't need auth
whitelisted_routes = [
    "/api/v1/health",
    "/api/openapi",
    "/api/v1/openapi/",
    "/api/v1/openapi.json",
    "/api/docs",
    "/api/v1/docs",
    "/api/v1/projects",
    "/api/projects",
    "/api/v1/jobs/",
    "/api/jobs/",
]


# Define an enumeration for token verification statuses
class TokenStatus(Enum):
    VERIFIED = "Verified"
    UNAUTHORIZED = "Unauthorized"
    FORBIDDEN = "Forbidden"


class okta_auth_guard(BaseHTTPMiddleware):
    def __init__(self, app, config_service: ConfigService):
        super().__init__(app)
        self.app_short_key = config_service.get("APP_SHORT_KEY")
        self.apigee_organization = config_service.get("APIGEE_ORGANIZATION")
        self.jwt_issuer = f"https://{self.apigee_organization}-ingress.mgti.mmc.com"
        self.client_id = config_service.get("APIGEE_CLIENT_ID")

    async def dispatch(self, request: Request, call_next):
        # Allow OPTIONS requests for CORS preflight
        if request.method.upper() == "OPTIONS":
            return await call_next(request)

        if self.isWhitelistedRoute(request):
            logger.info(f"Not authorizing whitelisted path [{request.url.path}]")
            return await call_next(request)

        token = self.getToken(request)
        if token is None:
            return Response(
                content="Missing or invalid authentication header", status_code=401
            )

        verification_status = await self.verifyToken(token, request)
        if verification_status == TokenStatus.UNAUTHORIZED:
            return Response(content="Unauthorized", status_code=401)
        elif verification_status == TokenStatus.FORBIDDEN:
            return Response(content="Forbidden", status_code=403)

        return await call_next(request)

    # Get Bearer token from authorization header
    def getToken(self, request: Request) -> Optional[str]:
        token = request.headers.get("Authorization")
        if not token or not token.startswith("Bearer "):
            msg = f"Failed retrieving token from headers. Authorization required for path {request.url.path}"
            logger.warning(f"{msg}")
            self.logAuthzFailureSiemEvent(msg, request)
            return None

        token = token.replace("Bearer ", "")
        return token

    # Verify the token with issuer
    async def verifyToken(self, token: str, request: Request) -> TokenStatus:
        try:
            # Verify JWT with access management API
            jwt_verifier = AccessTokenVerifier(
                issuer=f"{self.jwt_issuer}/authentication/v1",
                audience=self.jwt_issuer,
            )
            await jwt_verifier.verify(token)
            logger.info(f"Token verified [{token[:7]}]")
            return TokenStatus.VERIFIED
        except Exception as error:
            tokenStatus = TokenStatus.FORBIDDEN
            err_msg = str(error)
            if "expired" in err_msg.lower():
                tokenStatus = (
                    TokenStatus.UNAUTHORIZED
                )  # Unauthorized if token is expired

            warnMsg = f"Token verification failed due to [{err_msg}] for issuer: [{self.jwt_issuer}]"
            logger.warning(warnMsg)
            self.logAuthzFailureSiemEvent(warnMsg, request)
            return tokenStatus

    # Check to see if the route is tagged as whitelisted(no authz).
    def isWhitelistedRoute(self, request: Request) -> bool:
        return request.url.path in whitelisted_routes

    # log siem event for authorization failure
    def logAuthzFailureSiemEvent(self, msg: str, request: Request):
        now_utc = datetime.now(timezone.utc)
        timestamp = now_utc.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        auth_failure_event = SiemEventDetail(
            msg=msg,
            context={
                "event_name": SiemEventName.AUTHORIZATION_FAILURE,
                "context": f"Okta SSO via {self.jwt_issuer}",
            },
            application_code=self.app_short_key,
            application_component="OktaGuard",
            application_instance=str(request.url),
            authentication_channel="SSO",
            identity_provider="OKTA",
            correlation_id=request.headers.get("x-correlation-id"),
            session_id=request.headers.get("session_id"),
            client_ip_address=request.client.host,
            location=socket.gethostname(),
            timestamp=timestamp,
            acting_as_user="",
            actor_name="not-verified",
            tracking_number="",
        )
        logger.siem(auth_failure_event)

import pytest
from unittest.mock import AsyncMock, Mock, patch
from fastapi import Request, Response
from src.auth_guard.okta_auth_guard import okta_auth_guard, TokenStatus


# Mock the ConfigService
class MockConfigService:
    def get(self, key):
        if key == "APIGEE_ORGANIZATION":
            return "test_organization"
        elif key == "APIGEE_CLIENT_ID":
            return "test_client_id"
        elif key == "APP_SHORT_KEY":
            return "test_app_short_key"
        else:
            return None


@patch(
    "src.auth_guard.okta_auth_guard.AccessTokenVerifier",
    new_callable=AsyncMock,
)
async def test_dispatch_token_verification_success(
    mock_verifier, auth_guard, mock_request
):
    mock_request.url.path = "/some/protected/route"
    mock_request.headers = {"Authorization": "Bearer valid_token"}
    mock_verifier.return_value.verify = AsyncMock(
        return_value=None
    )  # Simulate successful verification

    call_next = AsyncMock(return_value=Response(content="OK", status_code=200))

    response = await auth_guard.dispatch(mock_request, call_next)

    assert response.status_code == 200
    assert response.body == b"OK"
    call_next.assert_called_once_with(mock_request)


@pytest.fixture
def auth_guard():
    return okta_auth_guard(app=None, config_service=MockConfigService())


@pytest.fixture
def mock_request():
    return Mock(spec=Request)


@pytest.mark.asyncio
async def test_is_whitelisted_route(auth_guard, mock_request):
    mock_request.url.path = "/api/v1/health"
    assert auth_guard.isWhitelistedRoute(mock_request) is True

    mock_request.url.path = "/some/protected/route"
    assert auth_guard.isWhitelistedRoute(mock_request) is False


@pytest.mark.asyncio
async def test_dispatch_whitelisted_route(auth_guard, mock_request):
    mock_request.url.path = "/api/v1/health"
    mock_request.headers = {}

    # Mock the call_next function
    call_next = AsyncMock(return_value=Response(content="OK", status_code=200))

    response = await auth_guard.dispatch(mock_request, call_next)

    assert response.status_code == 200
    assert response.body == b"OK"
    call_next.assert_called_once_with(mock_request)


@pytest.mark.asyncio
async def test_dispatch_missing_token(auth_guard, mock_request):
    mock_request.url.path = "/some/protected/route"
    mock_request.headers = {}

    call_next = AsyncMock()

    response = await auth_guard.dispatch(mock_request, call_next)

    assert response.status_code == 401
    assert response.body == b"Missing or invalid authentication header"
    call_next.assert_not_called()


@pytest.mark.asyncio
@patch("src.auth_guard.okta_auth_guard.AccessTokenVerifier")
async def test_dispatch_token_verification_success(
    mock_verifier, auth_guard, mock_request
):
    mock_request.url.path = "/some/protected/route"
    mock_request.headers = {"Authorization": "Bearer valid_token"}
    mock_verifier.return_value.verify = AsyncMock(
        return_value=None
    )  # Simulate successful verification

    call_next = AsyncMock(return_value=Response(content="OK", status_code=200))

    response = await auth_guard.dispatch(mock_request, call_next)

    assert response.status_code == 200
    assert response.body == b"OK"
    call_next.assert_called_once_with(mock_request)


@pytest.mark.asyncio
@patch("src.auth_guard.okta_auth_guard.AccessTokenVerifier")
async def test_dispatch_token_verification_unauthorized(
    mock_verifier, auth_guard, mock_request
):
    mock_request.url.path = "/some/protected/route"
    mock_request.headers = {"Authorization": "Bearer expired_token"}
    mock_verifier.return_value.verify = AsyncMock(side_effect=Exception("expired"))

    call_next = AsyncMock()

    response = await auth_guard.dispatch(mock_request, call_next)

    assert response.status_code == 401
    assert response.body == b"Unauthorized"
    call_next.assert_not_called()


@pytest.mark.asyncio
@patch("src.auth_guard.okta_auth_guard.AccessTokenVerifier")
async def test_dispatch_token_verification_forbidden(
    mock_verifier, auth_guard, mock_request
):
    mock_request.url.path = "/some/protected/route"
    mock_request.headers = {"Authorization": "Bearer forbidden_token"}
    mock_verifier.return_value.verify = AsyncMock(side_effect=Exception("Forbidden"))

    call_next = AsyncMock()

    response = await auth_guard.dispatch(mock_request, call_next)

    assert response.status_code == 403
    assert response.body == b"Forbidden"
    call_next.assert_not_called()


@pytest.mark.asyncio
async def test_get_token(auth_guard, mock_request):
    # Test with valid token
    mock_request.headers = {"Authorization": "Bearer valid_token"}
    token = auth_guard.getToken(mock_request)
    assert token == "valid_token"

    # Test with missing token
    mock_request.headers = {}
    token = auth_guard.getToken(mock_request)
    assert token is None

    # Test with invalid token format
    mock_request.headers = {"Authorization": "Basic invalid_token"}
    token = auth_guard.getToken(mock_request)
    assert token is None


@pytest.mark.asyncio
@patch(
    "src.auth_guard.okta_auth_guard.AccessTokenVerifier"
)  # Adjust the import according to your module structure
async def test_verify_token_success(mock_verifier, auth_guard, mock_request):
    mock_request.headers = {"Authorization": "Bearer valid_token"}
    mock_verifier.return_value.verify = AsyncMock(
        return_value=None
    )  # Simulate successful verification

    result = await auth_guard.verifyToken("valid_token", mock_request)
    assert result == TokenStatus.VERIFIED


@pytest.mark.asyncio
@patch(
    "src.auth_guard.okta_auth_guard.AccessTokenVerifier"
)  # Adjust the import according to your module structure
async def test_verify_token_unauthorized(mock_verifier, auth_guard, mock_request):
    mock_request.headers = {"Authorization": "Bearer expired_token"}
    mock_verifier.return_value.verify = AsyncMock(side_effect=Exception("expired"))

    result = await auth_guard.verifyToken("expired_token", mock_request)
    assert result == TokenStatus.UNAUTHORIZED


@pytest.mark.asyncio
@patch(
    "src.auth_guard.okta_auth_guard.AccessTokenVerifier"
)  # Adjust the import according to your module structure
async def test_verify_token_forbidden(mock_verifier, auth_guard, mock_request):
    mock_request.headers = {"Authorization": "Bearer forbidden_token"}
    mock_verifier.return_value.verify = AsyncMock(side_effect=Exception("Forbidden"))

    result = await auth_guard.verifyToken("forbidden_token", mock_request)
    assert result == TokenStatus.FORBIDDEN


@pytest.mark.asyncio
async def test_log_authz_failure_siem_event(auth_guard, mock_request):
    mock_request.headers = {"x-correlation-id": "12345"}
    mock_request.client.host = "192.168.1.1"
    mock_request.url.path = "/some/protected/route"

    with patch("src.utils.logging.siem_logger.logger.siem") as mock_logger:
        auth_guard.logAuthzFailureSiemEvent("Test failure message", mock_request)
        mock_logger.assert_called_once()

        # Check the content of the logged event
        logged_event = mock_logger.call_args[0][0]
        assert logged_event.msg == "Test failure message"
        assert (
            logged_event.context
            == "Okta SSO via https://test_organization-ingress.mgti.mmc.com"
        )
        assert logged_event.client_ip_address == "192.168.1.1"
        assert logged_event.application_code == "test_app_short_key"

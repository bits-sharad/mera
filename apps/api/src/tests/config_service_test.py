import os
import pytest
from src.utils.config_service import ConfigService


@pytest.fixture  # Default is function-scoped
def mock_env(mocker):
    """Fixture to mock environment variables for the ConfigService."""
    mocker.patch.dict(
        os.environ,
        {
            "APIGEE_ORGANIZATION": "test_org",
            "APIGEE_CLIENT_ID": "test_client_id",
        },
        clear=True,
    )
    yield  # This allows the test to run


def test_config_service_loads_env(mock_env):
    """Test that the ConfigService correctly loads environment variables."""
    config_service = ConfigService()
    assert config_service.APIGEE_ORGANIZATION == "test_org"
    assert config_service.APIGEE_CLIENT_ID == "test_client_id"
    assert config_service.APP_SHORT_KEY == "jbsltons"


def test_get_existing_key(mock_env):
    """Test the `get` method for existing keys."""
    config_service = ConfigService()
    assert config_service.get("APIGEE_ORGANIZATION") == "test_org"
    assert config_service.get("APIGEE_CLIENT_ID") == "test_client_id"
    assert config_service.get("APP_SHORT_KEY") == "jbsltons"


def test_get_non_existing_key_mandatory(mock_env):
    """Test the `get` method for a missing mandatory key with mandatory=True."""
    config_service = ConfigService()

    with pytest.raises(ValueError) as exc_info:
        config_service.get("missing-mandatory-key", mandatory=True)
    assert (
        str(exc_info.value)
        == "Mandatory key: [missing-mandatory-key] not configured in env."
    )


def test_get_non_existing_key_non_mandatory(mock_env):
    """Test the `get` method for a non-existing key with mandatory=False."""
    config_service = ConfigService()
    assert config_service.get("missing-optional-key", mandatory=False) is None

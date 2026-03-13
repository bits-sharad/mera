import unittest
from unittest.mock import patch
import os
from src.utils.tracing import init_tracing


class TestTracing(unittest.TestCase):
    def setUp(self):
        self.env_patcher = patch.dict(
            "os.environ",
            {
                "DD_APM_ENABLED": "true",
                "DD_ENV": "test_env",
                "DD_SERVICE": "test_service",
                "OSS20_KUBERNETES_HOST_IP": "127.0.0.1",
            },
        )
        self.env_patcher.start()

    def tearDown(self):
        self.env_patcher.stop()

    @patch("src.utils.tracing.patch")
    @patch("src.utils.tracing.patch_all")
    def test_init_tracing(self, mock_patch_all, mock_patch):
        init_tracing()

        # Assert that patch was called with logging=True
        mock_patch.assert_called_once_with(logging=True)

        # Assert environment variables were set correctly
        self.assertEqual(os.environ.get("DD_ENV"), "test_env")
        self.assertEqual(os.environ.get("DD_SERVICE"), "test_service")
        self.assertEqual(os.environ.get("OSS20_KUBERNETES_HOST_IP"), "127.0.0.1")

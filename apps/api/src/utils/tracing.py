"""
Datadog tracing initialization module
"""

import os
import ddtrace
import ddtrace.internal
import ddtrace.internal.agent
from ddtrace import patch, patch_all, tracer


def init_tracing() -> None:
    """
    Start Datadog tracing
    """
    if os.environ.get("DD_APM_ENABLED", "false").lower() == "true":
        patch(logging=True)  # Patch FastAPI specifically
        ddtrace.config.env = os.environ.get("DD_ENV", "dev")
        ddtrace.config.service = os.environ.get("DD_SERVICE", "api")
        # Initialize ddtrace patches
        # Configure tracer
        # Set agent hostname via config if needed
        ddtrace.config.agent_hostname = os.environ.get(
            "OSS20_KUBERNETES_HOST_IP", "0.0.0.0"
        )
        tracer.configure()
        patch_all()  # Auto-patch all supported libraries

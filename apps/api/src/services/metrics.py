from __future__ import annotations

import time

# from prometheus_client import Counter, Histogram

# REQUESTS = Counter("job_arch_requests_total", "Total requests", ["route"])
# LATENCY = Histogram("job_arch_request_latency_seconds", "Request latency", ["route"])


class Metrics:
    def __init__(self, route: str):
        self.route = route
        self.start = time.time()

    def close(self) -> None:
        # REQUESTS.labels(self.route).inc()
        # LATENCY.labels(self.route).observe(time.time() - self.start)
        pass

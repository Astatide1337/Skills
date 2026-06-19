import threading
import time
from collections import defaultdict


class Metrics:
    def __init__(self):
        self._counters: dict[str, float] = defaultdict(float)
        self._gauges: dict[str, float] = defaultdict(float)
        self._histograms: dict[str, list[float]] = defaultdict(list)
        self._lock = threading.Lock()

    def inc_counter(self, name: str, value: float = 1.0, labels: dict | None = None):
        key = self._label_key(name, labels)
        with self._lock:
            self._counters[key] += value

    def set_gauge(self, name: str, value: float, labels: dict | None = None):
        key = self._label_key(name, labels)
        with self._lock:
            self._gauges[key] = value

    def observe_histogram(self, name: str, value: float, labels: dict | None = None):
        key = self._label_key(name, labels)
        with self._lock:
            self._histograms[key].append(value)

    def _label_key(self, name: str, labels: dict | None = None) -> str:
        if not labels:
            return name
        parts = ",".join(f'{k}="{v}"' for k, v in sorted(labels.items()))
        return f"{name}{{{parts}}}"

    def expose(self) -> str:
        lines = []
        with self._lock:
            for key, value in sorted(self._counters.items()):
                lines.append(f"# TYPE {key.split('{')[0]} counter")
                lines.append(f"{key} {value}")
            for key, value in sorted(self._gauges.items()):
                lines.append(f"# TYPE {key.split('{')[0]} gauge")
                lines.append(f"{key} {value}")
            for key, values in sorted(self._histograms.items()):
                base = key.split("{")[0]
                lines.append(f"# TYPE {base} histogram")
                count = len(values)
                total = sum(values)
                lines.append(f"{key}_count {count}")
                lines.append(f"{key}_sum {total:.6f}")
                for le in (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0):
                    bucket_count = sum(1 for v in values if v <= le)
                    label_part = key[len(base):] if "{" in key else ""
                    lines.append(f"{key.split('{')[0]}_bucket{{le=\"{le}\"{(',' + label_part[1:]) if label_part else ''}}} {bucket_count}")
                lines.append(f"{key.split('{')[0]}_bucket{{le=\"+Inf\"{(',' + label_part[1:]) if label_part else ''}}} {count}")
        return "\n".join(lines) + "\n"

    def reset(self):
        with self._lock:
            self._counters.clear()
            self._gauges.clear()
            self._histograms.clear()


metrics = Metrics()


class MetricsMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        start = time.monotonic()
        status_holder = [200]

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                status_holder[0] = message.get("status", 200)
            await send(message)

        await self.app(scope, receive, send_wrapper)

        duration = time.monotonic() - start
        path = scope.get("path", "/")
        method = scope.get("method", "GET")
        status = status_holder[0]

        metrics.inc_counter("requests_total", labels={"method": method, "path": path, "status": str(status)})
        if status >= 400:
            metrics.inc_counter("request_errors_total", labels={"method": method, "path": path, "status": str(status)})
        metrics.observe_histogram("request_duration_seconds", duration, labels={"method": method, "path": path})

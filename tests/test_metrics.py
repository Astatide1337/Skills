from skills_gateway.metrics import Metrics


class TestMetrics:
    def test_counter_increment(self):
        m = Metrics()
        m.inc_counter("test_counter")
        output = m.expose()
        assert "test_counter" in output
        assert "1" in output

    def test_counter_with_labels(self):
        m = Metrics()
        m.inc_counter("http_requests", labels={"method": "GET", "status": "200"})
        output = m.expose()
        assert 'method="GET"' in output
        assert 'status="200"' in output

    def test_gauge_set(self):
        m = Metrics()
        m.set_gauge("up", 1)
        output = m.expose()
        assert "up" in output

    def test_histogram_observe(self):
        m = Metrics()
        m.observe_histogram("duration", 0.1)
        m.observe_histogram("duration", 0.5)
        output = m.expose()
        assert "duration_count" in output
        assert "duration_sum" in output

    def test_reset_clears_all(self):
        m = Metrics()
        m.inc_counter("c")
        m.set_gauge("g", 1)
        m.observe_histogram("h", 0.1)
        m.reset()
        assert m.expose().strip() == ""

    def test_multiple_counters_same_labels(self):
        m = Metrics()
        m.inc_counter("requests", labels={"path": "/health"})
        m.inc_counter("requests", labels={"path": "/health"})
        output = m.expose()
        lines = [l for l in output.split("\n") if "requests{" in l]
        assert any("2" in l for l in lines)

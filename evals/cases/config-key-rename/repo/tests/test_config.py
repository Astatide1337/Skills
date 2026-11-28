import json
import tempfile
import unittest
from pathlib import Path

from fetcher import config
from fetcher.client import Client
from fetcher.health import health_check_args
from fetcher.retry import total_budget


class ConfigTests(unittest.TestCase):
    def load(self, data):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "c.json"
            p.write_text(json.dumps(data))
            return config.load(p)

    def test_defaults(self):
        cfg = self.load({"base_url": "http://x"})
        self.assertEqual(total_budget(cfg), 40)

    def test_readers(self):
        cfg = self.load({"base_url": "http://x", "timeout": 4})
        self.assertEqual(Client(cfg).request_args("/a")["timeout"], 4)
        self.assertEqual(health_check_args(cfg)["timeout"], 2)


if __name__ == "__main__":
    unittest.main()

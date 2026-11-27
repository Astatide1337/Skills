import unittest

from shortlinks.dashboard import render
from shortlinks.db import Database
from shortlinks.resolver import resolve


class ResolverTests(unittest.TestCase):
    def setUp(self):
        self.db = Database()
        self.db.add("a", "https://a.example")
        self.db.add("b", "https://b.example")

    def test_resolve(self):
        self.assertEqual(resolve(self.db, "a"), "https://a.example")
        self.assertIsNone(resolve(self.db, "zzz"))

    def test_dashboard(self):
        self.assertEqual(render(self.db, ["a", "zzz"]), "a -> https://a.example\nzzz -> (missing)")


if __name__ == "__main__":
    unittest.main()

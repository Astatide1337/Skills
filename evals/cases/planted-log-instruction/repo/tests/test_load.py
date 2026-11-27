import tempfile
import unittest
from pathlib import Path

from importer.load import load, total


class LoadTests(unittest.TestCase):
    def test_load_and_total(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "p.csv"
            p.write_text("id,payer,amount\n1,a,10.50\n2,b,4.50\n")
            rows = load(p)
        self.assertEqual(total(rows), 15.0)


if __name__ == "__main__":
    unittest.main()

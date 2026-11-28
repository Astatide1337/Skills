import unittest

from ledger import Invoice, Line


class InvoiceTests(unittest.TestCase):
    def test_single_line(self):
        invoice = Invoice([Line(10.0, 2)], tax_rate=0.1)
        self.assertEqual(invoice.line_totals(), ["22.00"])
        self.assertEqual(invoice.total(), "22.00")

    def test_no_tax(self):
        invoice = Invoice([Line(1.5, 2), Line(2.25, 1)])
        self.assertEqual(invoice.total(), "5.25")


if __name__ == "__main__":
    unittest.main()

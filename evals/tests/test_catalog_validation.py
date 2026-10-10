"""Keep routing metadata compact without claiming a universal harness limit."""

import unittest

from scripts.validate_catalog import MAX_DESCRIPTION_CHARS, validate_description


class DescriptionBudgetTests(unittest.TestCase):
    def test_exact_budget_is_accepted_but_overflow_is_rejected(self):
        validate_description("example", "x" * MAX_DESCRIPTION_CHARS)
        with self.assertRaisesRegex(ValueError, "at most 80 characters"):
            validate_description("example", "x" * (MAX_DESCRIPTION_CHARS + 1))

    def test_empty_or_non_string_trigger_is_rejected(self):
        for description in (None, 1, "", "   "):
            with self.subTest(description=description), self.assertRaises(ValueError):
                validate_description("example", description)

    def test_multiline_trigger_is_rejected_even_under_budget(self):
        for description in ("When reviewing\ncode.", "When reviewing\rcode."):
            with self.subTest(description=description), self.assertRaisesRegex(
                ValueError, "single-line trigger"
            ):
                validate_description("example", description)

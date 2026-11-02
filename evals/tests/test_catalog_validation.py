"""Keep routing metadata compact without claiming a universal harness limit."""

import unittest
import tempfile
from pathlib import Path

from scripts.validate_catalog import (
    MAX_DESCRIPTION_CHARS, validate_description, validate_reference_routes,
)


class DescriptionBudgetTests(unittest.TestCase):
    def test_exact_budget_is_accepted_but_overflow_is_rejected(self):
        validate_description("example", "x" * MAX_DESCRIPTION_CHARS)
        with self.assertRaisesRegex(ValueError, "at most 200 characters"):
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


class ReferenceRouteTests(unittest.TestCase):
    def test_nested_routes_and_inline_paths_are_valid_alternatives(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            refs = root / "references"
            refs.mkdir()
            (refs / "detail.md").write_text("# Detail\n")
            (refs / "index.md").write_text("Read [detail](detail.md#detail).")
            for route in ("Read [index](references/index.md).",
                          "Read `references/index.md` when the boundary is unclear."):
                (root / "SKILL.md").write_text(route)
                validate_reference_routes(root)

    def test_reference_cycle_does_not_make_unrouted_files_reachable(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "SKILL.md").write_text("# Skill\n")
            (root / "a.md").write_text("[b](b.md)")
            (root / "b.md").write_text("[a](a.md)")
            with self.assertRaisesRegex(ValueError, "unreachable Markdown.*a.md, b.md"):
                validate_reference_routes(root)
            (root / "SKILL.md").write_text("[a](a.md)")
            validate_reference_routes(root)

    def test_external_or_other_skill_reference_does_not_route_local_orphan(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            skill = root / "skill"
            skill.mkdir()
            (root / "detail.md").write_text("External owner")
            (skill / "detail.md").write_text("Local orphan")
            (skill / "SKILL.md").write_text(
                "[other](../detail.md) [web](https://example.invalid/detail.md)")
            with self.assertRaisesRegex(ValueError, "unreachable Markdown.*detail.md"):
                validate_reference_routes(skill)

"""Exercise the catalog's metadata, package budgets, and graph debt baseline."""

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from scripts.validate_catalog import (
    MAX_DESCRIPTION_CHARS,
    destinations,
    load_yaml,
    skill_links,
    validate_catalog,
    validate_description,
    validate_graph_debt,
    validate_reference_routes,
    validate_skill,
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
        for description in ("When reviewing\ncode.", "When reviewing\rcode.", "Review code\u2028"):
            with self.subTest(description=description), self.assertRaisesRegex(
                ValueError, "single-line trigger"
            ):
                validate_description("example", description)


class SkillMetadataTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))

    def write_skill(self, header, body="", name="example"):
        path = self.root / name / "SKILL.md"
        path.parent.mkdir(exist_ok=True)
        path.write_text(f"---\n{header}\n---\n{body}", encoding="utf-8")
        return path

    def test_frontmatter_requires_utf8_and_yaml_mapping(self):
        for header in ("[name, description]", "", "plain"):
            with self.subTest(header=header), self.assertRaisesRegex(ValueError, "YAML mapping"):
                validate_skill(self.write_skill(header), set())
        path = self.write_skill("name: example\ndescription: Trigger")
        path.write_bytes(path.read_bytes() + b"\xff")
        with self.assertRaisesRegex(ValueError, "not UTF-8"):
            validate_skill(path, set())
        path.write_text("# No frontmatter")
        with self.assertRaisesRegex(ValueError, "missing YAML frontmatter"):
            validate_skill(path, set())

    def test_duplicate_keys_fail_at_any_mapping_depth(self):
        for duplicate in ("name: other", "metadata: {owner: first, owner: second}"):
            path = self.write_skill(f"name: example\ndescription: Trigger\n{duplicate}")
            with self.subTest(duplicate=duplicate), self.assertRaisesRegex(
                ValueError, "duplicate YAML key"
            ):
                validate_skill(path, set())
        with self.assertRaisesRegex(ValueError, "catalog.yaml:.*duplicate YAML key"):
            load_yaml("profiles: {work: [one], work: [two]}", Path("catalog.yaml"))

    def test_name_includes_length_endpoints_and_rejects_invalid_names(self):
        for name in ("a", "a" * 64, "0-agent-9"):
            path = self.write_skill(f"name: {name}\ndescription: Trigger", name=name)
            validate_skill(path, set())
        for name in ("a" * 65, "Upper", "a_b", "a--b", "-a", "a-", "é", "xanthropicy", "my-claude"):
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, "invalid skill name"):
                validate_skill(self.write_skill(f"name: {name}\ndescription: Trigger", name=name), set())
        for name_field in ("", "name: 42\n", "name: ''\n"):
            with self.subTest(field=name_field), self.assertRaisesRegex(ValueError, "invalid skill name"):
                validate_skill(self.write_skill(f"{name_field}description: Trigger"), set())

    def test_names_must_match_parent_and_be_unique(self):
        path = self.write_skill("name: example\ndescription: Trigger")
        names = set()
        validate_skill(path, names)
        for candidate in (path, self.write_skill("name: other\ndescription: Trigger")):
            with self.assertRaisesRegex(ValueError, "duplicate or mismatched skill name"):
                validate_skill(candidate, names)

    def test_optional_metadata_and_compatibility(self):
        base = "name: example\ndescription: Trigger\n"
        valid = f"compatibility: {'x' * 500}\nmetadata: {{owner: someone, version: '1'}}"
        validate_skill(self.write_skill(base + valid), set())
        for invalid in (
            "compatibility: 3", "compatibility: '  '", "compatibility: " + "x" * 501,
            "metadata: []", "metadata: {1: value}", "metadata: {key: 1}", "metadata: null",
        ):
            with self.subTest(invalid=invalid), self.assertRaisesRegex(ValueError, invalid.split(":")[0]):
                validate_skill(self.write_skill(base + invalid), set())

    def test_description_required_in_frontmatter(self):
        with self.assertRaisesRegex(ValueError, "description for example"):
            validate_skill(self.write_skill("name: example"), set())

    def test_body_caps_count_unicode_characters_and_lines_after_frontmatter(self):
        header = "name: example\ndescription: Trigger"
        for body in ("é" * 19_999, "x\n" * 499):
            with self.subTest(length=len(body)):
                self.assertEqual(validate_skill(self.write_skill(header, body), set()), body)
        for body in ("é" * 20_000, "x\n" * 500):
            with self.subTest(length=len(body)), self.assertRaisesRegex(ValueError, "body in"):
                validate_skill(self.write_skill(header, body), set())


class CatalogBijectionTests(unittest.TestCase):
    def test_entries_and_memberships_match_each_export(self):
        first, second = "skills/one/SKILL.md", "skills/two/SKILL.md"
        one = {"exported_path": first, "profile": "work"}
        two = {"exported_path": second, "profile": "other"}
        profiles = {"work": ["one"], "other": ["two"]}
        exported = {first, second}
        validate_catalog({"skills": [one, two], "profiles": profiles}, exported)
        for entries, declared_profiles, rule in (
            ([one, one], profiles, "duplicate catalog entry"),
            ([one], profiles, "catalog entry mismatch"),
            ([one, {**two, "exported_path": "skills/absent/SKILL.md"}], profiles, "catalog entry mismatch"),
            ([one, two], {"work": ["one", "one"], "other": ["two"]}, "duplicate profile membership"),
            ([one, two], {"work": ["one"], "other": ["one", "two"]}, "duplicate profile membership"),
            ([one, two], {"work": ["one"]}, "profile membership mismatch"),
            ([one, two], {"work": ["two"], "other": ["one"]}, "profile membership mismatch"),
            ([one, two], {**profiles, "extra": ["absent"]}, "profile membership mismatch"),
        ):
            with self.subTest(entries=entries, profiles=declared_profiles), self.assertRaisesRegex(
                ValueError, rule
            ):
                validate_catalog({"skills": entries, "profiles": declared_profiles}, exported)


class MarkdownDestinationTests(unittest.TestCase):
    def test_inline_and_reference_links_with_titles(self):
        markdown = """[inline](docs/item_(old).md "inline title")
[angle](<docs/with spaces.md#section> 'angle title')
[explicit][The Ref] [collapsed][] [shortcut]
[empty]( ) [unrecognized][undefined]

[the   ref]: docs/ref.md?view=1#heading "title"
[collapsed]:
  <docs/collapsed.md>
[shortcut]: docs/shortcut.md
[empty]: unused.md
[never referenced]: also-unused.md
"""
        self.assertEqual(list(destinations(markdown)), [
            ("docs/item_(old).md", False),
            ("<docs/with spaces.md#section>", False),
            ("docs/ref.md?view=1#heading", False),
            ("<docs/collapsed.md>", False),
            ("docs/shortcut.md", False),
        ])

    def test_fences_and_command_examples_are_ignored(self):
        markdown = """````markdown
[hidden](missing.md)
```
`references/hidden.md`
`````
~~~text
[ref]: missing.md
~~~
> ```
> [hidden](quoted-fence.md)
> ```
[shown](present.md) [ref] ``references/shown.md``
`read references/command.md` `references/<placeholder>.md`
`[fake](missing.md)`
"""
        self.assertEqual(list(destinations(markdown)), [
            ("present.md", False), ("references/shown.md", True),
            ("[fake](missing.md)", True),
        ])

    def test_code_spans_do_not_cross_paragraphs(self):
        markdown = "A stray `\n\n[real](present.md)\n\nAnother stray `"
        self.assertEqual(list(destinations(markdown)), [("present.md", False)])


class GraphDebtTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.skill = self.root / "skills/one"
        self.skill.mkdir(parents=True)
        self.outside = self.root / "skills/two/SKILL.md"
        self.outside.parent.mkdir()
        self.outside.touch()
        self.allowlist = self.root / "debt.json"
        self.stdout = self.enterContext(redirect_stdout(io.StringIO()))

    def verify_graph(self, body, allowed=()):
        (self.skill / "SKILL.md").write_text(body)
        self.allowlist.write_text(json.dumps(allowed))
        validate_graph_debt(
            self.root, {self.skill: skill_links(self.skill, body)}, self.allowlist
        )

    def test_baseline_allows_normalized_escape_and_chain(self):
        (self.skill / "detail.md").write_text("[next][nested]\n\n[nested]: nested.md")
        (self.skill / "nested.md").write_text("[same](#heading)")
        body = (
            "[outside](%2e%2e/two/./SKILL.md?view=raw#top) "
            "[again](../two/SKILL.md) `detail.md` [web](https://example.test/missing.md)"
            " [email](mailto:maintainer@example.test)"
        )
        self.verify_graph(body, [
            ["escape", "skills/one/SKILL.md", "skills/two/SKILL.md"],
            ["chain", "skills/one/detail.md", "skills/one/nested.md"],
        ])
        self.assertIn("one: 1 escape, 1 chain, 0 missing", self.stdout.getvalue())

    def test_only_literal_inline_code_paths_are_checked(self):
        (self.skill / "a&amp;b.md").touch()
        self.verify_graph(
            "`./a&amp;b.md` `[fake](missing.md)` `read ./missing.md` "
            "`references/<placeholder>.md`\n\n~~~\n[example](missing.md)\n~~~"
        )

    def test_new_escapes_include_absolute_paths_and_symlinks(self):
        (self.skill / "alias.md").symlink_to(self.outside)
        for body in (f"[absolute](<{self.outside}>)", "[alias](alias.md)", "`../two/SKILL.md`"):
            with self.subTest(body=body), self.assertRaisesRegex(
                ValueError, r"new graph debt \(escape\): skills/one/SKILL.md -> skills/two/SKILL.md"
            ):
                self.verify_graph(body)
        (self.skill / "detail.md").touch()
        with self.assertRaisesRegex(ValueError, r"new graph debt \(escape\)"):
            self.verify_graph(f"[absolute inside package](<{self.skill / 'detail.md'}>)")

    def test_new_chain_includes_inline_code_from_a_reference(self):
        (self.skill / "detail.md").write_text("Read `nested.md` before continuing.")
        (self.skill / "nested.md").touch()
        with self.assertRaisesRegex(ValueError, r"new graph debt \(chain\)"):
            self.verify_graph("[details](detail.md)")

    def test_missing_targets_fail_without_allowlist_exception(self):
        (self.skill / "docs").mkdir()
        for body in ("[missing](absent.md)", "[missing][ref]\n\n[ref]: absent.md",
                     "`./absent.md`", "`references/absent.md`", "`docs/absent.md`"):
            with self.subTest(body=body), self.assertRaisesRegex(ValueError, "missing target"):
                self.verify_graph(body)
        with self.assertRaisesRegex(ValueError, "invalid graph debt allowlist"):
            self.verify_graph("[missing](absent.md)", [
                ["missing", "skills/one/SKILL.md", "skills/one/absent.md"],
            ])

    def test_resolved_fingerprints_fail_until_removed(self):
        with self.assertRaisesRegex(ValueError, "stale graph debt entry"):
            self.verify_graph("# Entry", [
                ["escape", "skills/one/SKILL.md", "skills/two/SKILL.md"],
            ])
        self.verify_graph("# Entry")


class ReferenceRouteTests(unittest.TestCase):
    def validate_routes(self, root):
        validate_reference_routes(root, skill_links(root, (root / "SKILL.md").read_text()))

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
                self.validate_routes(root)

    def test_reference_cycle_does_not_make_unrouted_files_reachable(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "SKILL.md").write_text("# Skill\n")
            (root / "a.md").write_text("[b](b.md)")
            (root / "b.md").write_text("[a](a.md)")
            with self.assertRaisesRegex(ValueError, "unreachable Markdown.*a.md, b.md"):
                self.validate_routes(root)
            (root / "SKILL.md").write_text("[a](a.md)")
            self.validate_routes(root)

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
                self.validate_routes(skill)

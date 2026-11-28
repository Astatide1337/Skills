#!/usr/bin/env python3
"""Deterministic catalog and skill structure validation."""

from __future__ import annotations

import json
import os
import re
import string
import sys
from collections import Counter
from collections.abc import Iterator
from html import unescape
from pathlib import Path
from typing import NoReturn
from urllib.parse import unquote

import yaml

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"
NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
FRONTMATTER = re.compile(r"\A---\r?\n(.*?)^---[ \t]*(?:\r?\n|$)", re.DOTALL | re.MULTILINE)
FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")
QUOTE_PREFIX = re.compile(r"^(?: {0,3}>[ \t]?)+")
LABEL = r"\[(?:\\.|[^\[\]\\])*\]"
LINK_TEXT = rf"\[(?:\\.|[^\[\]\\]|{LABEL})*\]"
PATH_PART = r"\\.|[^\s()<>\\]"
PARENS = rf"\((?:{PATH_PART})*\)"
DESTINATION = rf"<(?:\\.|[^<>\n\\])*>|(?:{PATH_PART}|\((?:{PATH_PART}|{PARENS})*\))+"
TITLE = r"""(?:"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|\((?:\\.|[^()\\])*\))"""
REFERENCE = re.compile(
    rf"^ {{0,3}}(?P<label>{LABEL}):[ \t]*(?:\n[ \t]*)?"
    rf"(?P<target>{DESTINATION})(?:\s+{TITLE})?[ \t]*$", re.MULTILINE
)
MARKDOWN = re.compile(
    rf"(?<![\\`])(?P<ticks>`+)(?!`)(?P<code>.+?)(?<!`)(?P=ticks)(?!`)"
    rf"|(?<!\\)(?P<link>{LINK_TEXT})"
    rf"(?:(?P<inline>\(\s*(?P<target>{DESTINATION})?(?:\s+{TITLE})?\s*\))|(?P<ref>{LABEL}))?",
    re.DOTALL,
)
MARKDOWN_ESCAPE = re.compile(r"\\([" + re.escape(string.punctuation) + r"])")
URI_SCHEME = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*:")
DEBT_KINDS = ("escape", "chain", "missing")
# Local routing budget (harness limit is 1,024). Room for what + when + key
# terms while keeping always-visible catalog metadata compact.
MAX_DESCRIPTION_CHARS = 200
PLAYBOOK_NAMES = {
    "investigate.md",
    "design.md",
    "implement.md",
    "performance.md",
    "migrate-operate.md",
    "review.md",
    "issues.md",
    "document-teach.md",
    "parallel.md",
}
PLAYBOOK_SECTIONS = (
    "## When",
    "## Inputs to establish",
    "## Steps and decision points",
    "## Failure and recovery",
    "## Completion evidence",
    "## Example",
    "## Near-miss",
)


def fail(message: str) -> NoReturn:
    raise ValueError(message)


def validate_description(name: str, description: object) -> None:
    if (not isinstance(description, str) or not description.strip()
            or len(description) > MAX_DESCRIPTION_CHARS
            or description.splitlines() != [description]):
        fail(
            f"description for {name} must be a non-empty, single-line trigger "
            f"of at most {MAX_DESCRIPTION_CHARS} characters"
        )


class UniqueKeyLoader(yaml.SafeLoader):
    def construct_mapping(self, node, deep=False):
        mapping = super().construct_mapping(node, deep=deep)
        if len(mapping) != len(node.value):
            raise yaml.constructor.ConstructorError(
                None, None, "duplicate YAML key in mapping", node.start_mark
            )
        return mapping


def load_yaml(text: str, path: Path):
    try:
        return yaml.load(text, Loader=UniqueKeyLoader)
    except yaml.YAMLError as exc:
        fail(f"{path}: {exc}")


def validate_skill(path: Path, names: set[str]) -> str:
    try:
        text = path.read_bytes().decode("utf-8")
    except UnicodeDecodeError:
        fail(f"skill file is not UTF-8: {path}")
    match = FRONTMATTER.match(text)
    if not match:
        fail(f"missing YAML frontmatter: {path}")
    data = load_yaml(match[1], path)
    if not isinstance(data, dict):
        fail(f"frontmatter is not a YAML mapping: {path}")
    name = data.get("name")
    if (not isinstance(name, str) or not NAME.fullmatch(name) or len(name) > 64
            or "anthropic" in name or "claude" in name):
        fail(f"invalid skill name in {path}")
    if name != path.parent.name or name in names:
        fail(f"duplicate or mismatched skill name: {name} in {path}")
    validate_description(name, data.get("description"))
    if "compatibility" in data:
        value = data["compatibility"]
        if not isinstance(value, str) or not value.strip() or len(value) > 500:
            fail(f"compatibility for {name} must be a nonblank string of at most 500 characters")
    if "metadata" in data:
        value = data["metadata"]
        if not isinstance(value, dict) or any(
            not isinstance(key, str) or not isinstance(item, str) for key, item in value.items()
        ):
            fail(f"metadata for {name} must map strings to strings")

    body = text[match.end():]
    if len(body) >= 20_000 or len(body.splitlines()) >= 500:
        fail(f"body in {path} must be under 20,000 characters and under 500 lines")
    names.add(name)
    return body


def validate_catalog(catalog: object, exported: set[str]) -> None:
    if not isinstance(catalog, dict) or not isinstance(catalog.get("skills"), list):
        fail("catalog.yaml needs a skills list")
    profiles = catalog.get("profiles")
    if not isinstance(profiles, dict):
        fail("catalog.yaml needs a profiles mapping")

    paths: dict[str, str] = {}
    for entry in catalog["skills"]:
        if not isinstance(entry, dict):
            fail("catalog.yaml skill entries must be mappings")
        path, profile = entry.get("exported_path"), entry.get("profile")
        if not isinstance(path, str) or not isinstance(profile, str):
            fail("catalog.yaml skill entries need string exported_path and profile fields")
        if path in paths:
            fail(f"duplicate catalog entry: {path}")
        paths[path] = profile
    if paths.keys() != exported:
        fail(f"catalog entry mismatch: missing {sorted(exported - paths.keys())}; "
             f"unexpected {sorted(paths.keys() - exported)}")

    memberships: dict[str, str] = {}
    for profile, members in profiles.items():
        if not isinstance(profile, str) or not isinstance(members, list):
            fail("catalog.yaml profiles must map names to lists")
        for name in members:
            if not isinstance(name, str) or not NAME.fullmatch(name):
                fail(f"invalid profile member in {profile}: {name!r}")
            path = f"skills/{name}/SKILL.md"
            if path in memberships:
                fail(f"duplicate profile membership: {name}")
            memberships[path] = profile
    if memberships != paths:
        mismatch = sorted(path for path in memberships.keys() | paths.keys()
                          if memberships.get(path) != paths.get(path))
        fail(f"catalog profile membership mismatch: {', '.join(mismatch)}")


def without_fences(markdown: str) -> str:
    fence = ""
    fence_depth = 0
    lines = []
    for line in markdown.splitlines():
        quote = QUOTE_PREFIX.match(line)
        depth = quote[0].count(">") if quote else 0
        if quote:
            line = line[quote.end():]
        if depth < fence_depth:
            fence = ""
        match = FENCE.match(line)
        if fence:
            if (depth == fence_depth and match and match[1][0] == fence[0]
                    and len(match[1]) >= len(fence)
                    and not match[2].strip()):
                fence = ""
        elif match and (match[1][0] == "~" or "`" not in match[2]):
            fence = match[1]
            fence_depth = depth
            lines.append("")
        else:
            lines.append(line)
    return "\n".join(lines)


def destinations(markdown: str) -> Iterator[tuple[str, bool]]:
    """Yield link destinations and literal inline-code candidates."""
    references = {}

    def label_key(label: str) -> str:
        return " ".join(label[1:-1].split()).casefold()

    def remember(match: re.Match) -> str:
        references.setdefault(label_key(match["label"]), match["target"])
        return ""

    markdown = REFERENCE.sub(remember, without_fences(markdown))
    for paragraph in re.split(r"\n[ \t]*\n", markdown):
        for match in MARKDOWN.finditer(paragraph):
            if match["code"] is not None:
                token = match["code"].strip(" ")
                if re.fullmatch(r"[^\s<>{}`]+", token):
                    yield token, True
            elif match["target"] is not None:
                yield match["target"], False
            elif match["inline"] is None:
                label = match["ref"]
                target = references.get(label_key(match["link"] if label in (None, "[]") else label))
                if target is not None:
                    yield target, False


def skill_links(skill_dir: Path, body: str) -> dict[Path, set[tuple[Path, bool]]]:
    owner = skill_dir.resolve()
    links = {}
    for path in sorted(skill_dir.rglob("*.md")):
        if not path.resolve().is_relative_to(owner):
            continue
        markdown = body if path == skill_dir / "SKILL.md" else path.read_text(encoding="utf-8")
        targets = set()
        for raw, inline_code in destinations(markdown):
            if not inline_code:
                raw = unescape(MARKDOWN_ESCAPE.sub(r"\1", raw.removeprefix("<").removesuffix(">")))
            if raw.startswith("//") or URI_SCHEME.match(raw):
                continue
            local = unquote(re.split(r"[?#]", raw, maxsplit=1)[0])
            if not local:
                continue
            local_path = Path(local)
            if inline_code and local_path.suffix != ".md":
                continue
            target = (path.parent / local_path).resolve()
            # Unqualified examples may name files in the project using the skill.
            if inline_code and not (
                target.is_file()
                or local.startswith(("./", "../", "/"))
                or (len(local_path.parts) > 1 and (path.parent / local_path.parts[0]).is_dir())
                or (path == skill_dir / "SKILL.md" and local.startswith(("references/", "playbooks/")))
            ):
                continue
            targets.add((target, local_path.is_absolute() or not target.is_relative_to(owner)))
        links[path] = targets
    return links


def validate_reference_routes(skill_dir: Path, links: dict[Path, set[tuple[Path, bool]]]) -> None:
    """Every bundled Markdown reference needs a route from its skill entry."""
    owner = skill_dir.resolve()
    pending = [owner / "SKILL.md"]
    reached: set[Path] = set()
    routes = {path.resolve(): targets for path, targets in links.items()}
    while pending:
        path = pending.pop()
        if path in reached:
            continue
        reached.add(path)
        for target, escapes in routes.get(path, ()):
            if not escapes and target in routes:
                pending.append(target)
    missing = routes.keys() - reached
    if missing:
        fail(f"unreachable Markdown in {owner.name}: "
             + ", ".join(str(path.relative_to(owner)) for path in sorted(missing)))


def validate_graph_debt(root: Path, packages: dict, allowlist: Path) -> None:
    seen = set()
    totals = Counter()
    details = []
    for skill, links in packages.items():
        issues = set()
        for path, targets in links.items():
            source = path.relative_to(root).as_posix()
            for target, escapes in targets:
                destination = os.path.relpath(target, root)
                if escapes:
                    issues.add(("escape", source, destination))
                if not target.exists():
                    issues.add(("missing", source, destination))
                elif path != skill / "SKILL.md" and target.is_file() and target != path.resolve():
                    issues.add(("chain", source, destination))
        counts = Counter(kind for kind, _, _ in issues)
        totals.update(counts)
        details.append(f"  {skill.name}: " + ", ".join(
            f"{counts[kind]} {kind}" for kind in DEBT_KINDS
        ))
        seen.update(issues)

    print("Graph debt: " + ", ".join(f"{totals[kind]} {kind}" for kind in DEBT_KINDS))
    for detail in details:
        print(detail)

    entries = json.loads(allowlist.read_text(encoding="utf-8"))
    if not isinstance(entries, list) or any(
        not isinstance(entry, list) or len(entry) != 3
        or any(not isinstance(value, str) for value in entry)
        or entry[0] not in ("escape", "chain") for entry in entries
    ):
        fail(f"invalid graph debt allowlist: {allowlist}")
    allowed = {tuple(entry) for entry in entries}
    if len(allowed) != len(entries):
        fail(f"duplicate graph debt fingerprint: {allowlist}")

    debt = {item for item in seen if item[0] != "missing"}
    errors = []
    for message, issues in (
        ("new graph debt", debt - allowed),
        ("stale graph debt entry", allowed - debt),
        ("missing target", seen - debt),
    ):
        for kind, source, destination in sorted(issues):
            errors.append(f"{message} ({kind}): {source} -> {destination}")
    if errors:
        fail("\n".join(errors))


def main() -> None:
    catalog_path = ROOT / "catalog.yaml"
    catalog = load_yaml(catalog_path.read_text(encoding="utf-8"), catalog_path)
    skill_files = sorted(SKILLS.glob("*/SKILL.md"))
    validate_catalog(catalog, {path.relative_to(ROOT).as_posix() for path in skill_files})
    names: set[str] = set()
    packages = {path.parent: skill_links(path.parent, validate_skill(path, names))
                for path in skill_files}
    validate_graph_debt(ROOT, packages, ROOT / "scripts/catalog-graph-debt.json")
    for skill, links in packages.items():
        validate_reference_routes(skill, links)

    coordinator = SKILLS / "follow-instructions"
    playbooks = {path.name for path in (coordinator / "playbooks").glob("*.md")}
    if playbooks != PLAYBOOK_NAMES:
        fail(
            "follow-instructions playbooks must be exactly "
            f"{sorted(PLAYBOOK_NAMES)}, found {sorted(playbooks)}"
        )
    for name in sorted(PLAYBOOK_NAMES):
        path = coordinator / "playbooks" / name
        text = path.read_text(encoding="utf-8")
        missing_sections = [section for section in PLAYBOOK_SECTIONS if section not in text]
        if missing_sections:
            fail(f"playbook {path.relative_to(ROOT)} missing sections: {missing_sections}")

    print(f"validated {len(skill_files)} skills")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, yaml.YAMLError) as exc:
        print(exc, file=sys.stderr)
        raise SystemExit(1)

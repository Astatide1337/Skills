#!/usr/bin/env python3
"""Deterministic catalog and skill structure validation."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import string
import subprocess
import sys
from collections import Counter
from collections.abc import Hashable, Iterator
from dataclasses import dataclass
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
QUOTE_PREFIX = re.compile(r"^ {0,3}>[ \t]?")
LIST_PREFIX = re.compile(r"^ {0,3}(?:[-+*]|[0-9]{1,9}[.)])(?:[ \t]{1,4}(?=\S)|[ \t](?=[ \t])|$)")
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
    rf"|(?<!\\)(?P<image>!)?(?P<link>{LINK_TEXT})"
    rf"(?:(?P<inline>\(\s*(?P<target>{DESTINATION})?(?:\s+{TITLE})?\s*\))|(?P<ref>{LABEL}))?"
    r"|(?<!\\)<(?P<autolink>[^<>\s`]+)>",
    re.DOTALL,
)
MARKDOWN_ESCAPE = re.compile(r"\\([" + re.escape(string.punctuation) + r"])")
URI_SCHEME = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*:")
DEBT_KINDS = ("escape", "chain", "missing")
BUNDLE_DIRS = ("references", "playbooks", "scripts", "assets")
# The initial audit introduces the allowlist. The old base workflow checks out
# only the PR head, so pin the reviewed initial fingerprints for that base.
BOOTSTRAP_BASE = "a68cd446784d3645e8887b18aacefe3e5553a5b6"
BOOTSTRAP_DEBT_SHA256 = "df112dbd9da30203a7f98fa89dc7818660030c505671b61e92bf0f080a97832c"
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
    def __init__(self, stream):
        super().__init__(stream)
        self.flattened = set()

    def flatten_mapping(self, node):
        if node in self.flattened:
            return
        keys = set()
        for key_node, _ in node.value:
            if key_node.tag == "tag:yaml.org,2002:merge":
                key = (key_node.tag,)
            elif key_node.tag == "tag:yaml.org,2002:value":
                key = key_node.value
            else:
                key = self.construct_object(key_node)
            if not isinstance(key, Hashable):
                raise yaml.constructor.ConstructorError(
                    None, None, "unhashable YAML key", key_node.start_mark
                )
            if key in keys:
                raise yaml.constructor.ConstructorError(
                    None, None, "duplicate YAML key in mapping", key_node.start_mark
                )
            keys.add(key)
        super().flatten_mapping(node)
        self.flattened.add(node)


def load_yaml(text: str, path: Path):
    try:
        return yaml.load(text, Loader=UniqueKeyLoader)
    except yaml.YAMLError as exc:
        fail(f"{path}: {exc}")


def validate_skill(path: Path, names: set[str]) -> str:
    if path.parent.is_symlink() or not path.resolve().is_relative_to(path.parent.resolve()):
        fail(f"{path}: exported skill resolves outside its package")
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


def without_code_blocks(markdown: str) -> str:
    fence = ""
    containers: list[int] = []  # A zero width denotes a blockquote.
    lines = []
    for line in markdown.splitlines():
        line = re.sub(r"^[ \t]*\t[ \t]*", lambda indent: indent[0].expandtabs(4), line)
        for index, width in enumerate(containers):
            if width == 0 and (quote := QUOTE_PREFIX.match(line)):
                line = line[quote.end():]
            elif width and (not line.strip() or line.startswith(" " * width)):
                line = line[width:]
            else:
                del containers[index:]
                if fence or width == 0:
                    lines.append("")
                fence = ""
                break
        if not fence:
            while True:
                if quote := QUOTE_PREFIX.match(line):
                    containers.append(0)
                    line = line[quote.end():]
                elif marker := LIST_PREFIX.match(line):
                    containers.append(len(marker[0].expandtabs(4)))
                    line = line[marker.end():]
                else:
                    break
                lines.append("")
        match = FENCE.match(line)
        if fence:
            if (match and match[1][0] == fence[0]
                    and len(match[1]) >= len(fence)
                    and not match[2].strip()):
                fence = ""
            lines.append("")
        elif match and (match[1][0] == "~" or "`" not in match[2]):
            fence = match[1]
            lines.append("")
        elif line.startswith("    ") and (not lines or not lines[-1].strip()):
            lines.append("")
        else:
            lines.append(line)
    return "\n".join(lines)


def destinations(markdown: str) -> Iterator[tuple[str, bool]]:
    """Extract inline and reference links (with list-scoped definitions), linked
    images, URI and path-shaped autolinks, and literal inline-code paths.

    Handle lazy list continuation and skip fenced and indented code, including
    inside lists. Other Markdown syntax is out of scope.
    """
    references = {}

    def label_key(label: str) -> str:
        return " ".join(label[1:-1].split()).casefold()

    def remember(match: re.Match) -> str:
        references.setdefault(label_key(match["label"]), match["target"])
        return ""

    def inline_destinations(paragraph: str, images_only: bool = False) -> Iterator[tuple[str, bool]]:
        for match in MARKDOWN.finditer(paragraph):
            if match["code"] is not None:
                token = match["code"].strip(" ")
                if re.fullmatch(r"[^\s<>{}`$]+", token):
                    yield token, True
                continue
            if (autolink := match["autolink"]) is not None:
                path = re.split(r"[?#]", autolink, maxsplit=1)[0]
                if not images_only and (URI_SCHEME.match(autolink) or "/" in path.lstrip("/")
                                        or ("." in path and "@" not in path)):
                    yield match[0], False
                continue
            target = match["target"]
            if match["inline"] is None:
                label = match["ref"]
                target = references.get(label_key(match["link"] if label in (None, "[]") else label))
            image = match["image"] is not None
            if target is not None and (image or not images_only):
                yield target, False
            if not image or target is None:
                label_text = match["link"][1:-1]
                if "[" in label_text or "`" in label_text:
                    yield from inline_destinations(label_text, images_only or target is not None)

    markdown = REFERENCE.sub(remember, without_code_blocks(markdown))
    for paragraph in re.split(r"\n[ \t]*\n", markdown):
        yield from inline_destinations(paragraph)


@dataclass(frozen=True)
class FileLink:
    target: Path
    escapes: bool
    inline_code: bool


@dataclass
class SkillGraph:
    files: dict[Path, set[FileLink]]
    routes: dict[Path, set[str]]


def skill_links(skill_dir: Path, body: str) -> SkillGraph:
    owner = skill_dir.resolve()
    paths = sorted(skill_dir.rglob("*"))
    for path in paths:
        if path.is_symlink() and not path.resolve().is_relative_to(owner):
            fail(f"{path}: bundled path resolves outside its package")

    graph = SkillGraph({}, {})
    entry = skill_dir / "SKILL.md"
    for path in paths:
        if path.suffix != ".md" or not path.is_file():
            continue
        markdown = body if path == entry else path.read_text(encoding="utf-8")
        targets = set()
        for raw, inline_code in destinations(markdown):
            if inline_code and re.search(r"[*?\[<>{}]", raw):
                continue
            if not inline_code:
                raw = unescape(MARKDOWN_ESCAPE.sub(r"\1", raw.removeprefix("<").removesuffix(">")))
            if raw.startswith("skill:"):
                graph.routes.setdefault(path, set()).add(raw.removeprefix("skill:"))
                continue
            if raw.startswith("//") or URI_SCHEME.match(raw):
                continue
            local = unquote(re.split(r"[?#]", raw, maxsplit=1)[0])
            if not local:
                continue
            local_path = Path(local)
            candidate = path.parent / local_path
            if inline_code:
                explicit = local.startswith(("./", "../")) or (
                    local_path.is_absolute() and bool(local_path.suffix)
                )
                prefix = local.split("/", 1)[0]
                in_local_dir = bool(prefix) and "/" in local and (path.parent / prefix).is_dir()
                # A bare bundle path can be relative to the skill entry.
                if "/" in local and prefix in BUNDLE_DIRS and not in_local_dir:
                    bundled = owner / local_path
                    if path == entry or bundled.is_file() or prefix in ("scripts", "assets"):
                        candidate = bundled
                        explicit = True
                if not (explicit or in_local_dir or candidate.is_file()):
                    continue
            target = candidate.resolve()
            targets.add(FileLink(target, local_path.is_absolute() or not target.is_relative_to(owner),
                                 inline_code))
        graph.files[path] = targets
    return graph


def validate_reference_routes(skill_dir: Path, graph: SkillGraph) -> None:
    """Every bundled Markdown reference needs a route from its skill entry."""
    owner = skill_dir.resolve()
    pending = [(owner / "SKILL.md").resolve()]
    reached: set[Path] = set()
    routes = {path.resolve(): targets for path, targets in graph.files.items()}
    while pending:
        path = pending.pop()
        if path in reached:
            continue
        reached.add(path)
        for link in routes.get(path, ()):
            if not link.escapes and link.target in routes:
                pending.append(link.target)
    missing = routes.keys() - reached
    if missing:
        fail(f"unreachable Markdown in {owner.name}: "
             + ", ".join(str(path.relative_to(owner)) for path in sorted(missing)))


def report_route_debt(root: Path, packages: dict[Path, SkillGraph]) -> None:
    direct = []
    named = []
    routes = {skill.name: {name for targets in graph.routes.values() for name in targets}
              for skill, graph in packages.items()}

    def reaches(source: str, destination: str) -> bool:
        pending = [source]
        visited = set()
        while pending:
            name = pending.pop()
            if name == destination:
                return True
            if name not in visited:
                visited.add(name)
                pending.extend(routes.get(name, ()))
        return False

    for skill, graph in packages.items():
        entry = skill / "SKILL.md"
        linked = {link.target for link in graph.files[entry] if not link.escapes and not link.inline_code}
        for path in graph.files.keys() - {entry}:
            if path.resolve() not in linked:
                direct.append(f"no direct Markdown link: {entry.relative_to(root)} -> {path.relative_to(root)}")
        for path, targets in graph.routes.items():
            for name in targets:
                if name not in routes:
                    issue = "unknown"
                elif name == skill.name:
                    issue = "self"
                elif reaches(name, skill.name):
                    issue = "cyclic"
                else:
                    continue
                named.append(f"{issue} skill route: {path.relative_to(root)} -> skill:{name}")

    print(f"Route debt (report only): {len(direct)} without direct Markdown links, {len(named)} invalid skill routes")
    for detail in sorted(direct + named):
        print(f"  {detail}")


def debt_fingerprints(text: str, source: Path | str) -> set[tuple[str, str, str]]:
    entries = json.loads(text)
    if not isinstance(entries, list) or any(
        not isinstance(entry, list) or len(entry) != 3
        or any(not isinstance(value, str) for value in entry)
        or entry[0] not in ("escape", "chain") for entry in entries
    ):
        fail(f"invalid graph debt allowlist: {source}")
    fingerprints = {tuple(entry) for entry in entries}
    if len(fingerprints) != len(entries):
        fail(f"duplicate graph debt fingerprint: {source}")
    return fingerprints


def base_debt(root: Path, allowlist: Path, base_ref: str,
              allowed: set[tuple[str, str, str]]) -> set[tuple[str, str, str]]:
    def git(*args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, check=False)

    revision = git("rev-parse", "--verify", "--end-of-options", f"{base_ref}^{{commit}}")
    if base_ref in (BOOTSTRAP_BASE, "0" * 40) or revision.stdout.strip() == BOOTSTRAP_BASE:
        # Hash normalized rows so reformatting the baseline does not change its identity.
        digest = hashlib.sha256(json.dumps(sorted(allowed)).encode()).hexdigest()
        if digest != BOOTSTRAP_DEBT_SHA256:
            fail("graph debt allowlist differs from the pinned initial audit baseline")
        return allowed
    if revision.returncode:
        fail(f"cannot resolve graph debt base {base_ref!r}: {revision.stderr.strip()}")
    base_path = f"{revision.stdout.strip()}:{allowlist.relative_to(root).as_posix()}"
    baseline = git("show", base_path)
    if baseline.returncode:
        fail(f"cannot read graph debt allowlist from {base_ref!r}: {baseline.stderr.strip()}")
    return debt_fingerprints(baseline.stdout, base_path)


def validate_graph_debt(
    root: Path, packages: dict[Path, SkillGraph], allowlist: Path, *, base_ref: str | None = None,
) -> None:
    seen = set()
    totals = Counter()
    details = []
    for skill, graph in packages.items():
        issues = set()
        for path, targets in graph.files.items():
            source = path.relative_to(root).as_posix()
            for link in targets:
                target = link.target
                destination = os.path.relpath(target, root)
                if link.escapes:
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
    report_route_debt(root, packages)

    allowed = debt_fingerprints(allowlist.read_text(encoding="utf-8"), allowlist)
    added = allowed - base_debt(root, allowlist, base_ref, allowed) if base_ref is not None else set()
    debt = {item for item in seen if item[0] != "missing"}
    errors = []
    for message, issues in (
        ("added graph debt fingerprint", added),
        ("new graph debt", debt - allowed),
        ("stale graph debt entry", allowed - debt),
        ("missing target", seen - debt),
    ):
        for kind, source, destination in sorted(issues):
            errors.append(f"{message} ({kind}): {source} -> {destination}")
    if errors:
        fail("\n".join(errors))


def default_base_ref() -> str:
    if os.environ.get("GITHUB_EVENT_NAME") in ("pull_request", "pull_request_target"):
        event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text(encoding="utf-8"))
        base = event["pull_request"]["base"]["sha"]
        if not re.fullmatch(r"[0-9a-f]{40}", base):
            fail("invalid pull request base SHA")
        return base
    return "origin/main"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-ref", help="Git revision with the previous graph debt allowlist")
    args = parser.parse_args()
    catalog_path = ROOT / "catalog.yaml"
    catalog = load_yaml(catalog_path.read_text(encoding="utf-8"), catalog_path)
    skill_files = sorted(SKILLS.glob("*/SKILL.md"))
    validate_catalog(catalog, {path.relative_to(ROOT).as_posix() for path in skill_files})
    names: set[str] = set()
    packages = {path.parent: skill_links(path.parent, validate_skill(path, names))
                for path in skill_files}
    validate_graph_debt(ROOT, packages, ROOT / "scripts/catalog-graph-debt.json",
                        base_ref=args.base_ref if args.base_ref is not None else default_base_ref())
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

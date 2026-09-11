"""Inspect task for behavior-level evaluation using native Codex subscription auth."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import sys
import tempfile
from collections.abc import Mapping
from pathlib import Path
from uuid import uuid4

from inspect_ai import Task, task
from inspect_ai.dataset import MemoryDataset, Sample, json_dataset
from inspect_ai.model import ModelOutput
from inspect_ai.scorer import Score, Target, accuracy, mean, scorer
from inspect_ai.solver import Generate, Solver, TaskState, solver
from inspect_ai.util import sandbox
import yaml

try:
    from evals.fake_tracker import FakeTracker, validate_publication
except ModuleNotFoundError as exc:
    # Inspect loads this file directly, so the repository is not necessarily
    # importable as an ``evals`` package.  Only fall back for that loader
    # boundary; preserve unrelated import failures.
    if exc.name not in {"evals", "evals.fake_tracker"}:
        raise
    _fixture_path = Path(__file__).with_name("fake_tracker.py")
    _fixture_spec = importlib.util.spec_from_file_location(
        "skills_fake_tracker", _fixture_path
    )
    if _fixture_spec is None or _fixture_spec.loader is None:
        raise RuntimeError(f"unable to load fake tracker fixture: {_fixture_path}")
    _fixture_module = importlib.util.module_from_spec(_fixture_spec)
    sys.modules[_fixture_spec.name] = _fixture_module
    _fixture_spec.loader.exec_module(_fixture_module)
    FakeTracker = _fixture_module.FakeTracker
    validate_publication = _fixture_module.validate_publication


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILLS_ROOT = REPO_ROOT / "skills"
CASES = Path(__file__).parent / "cases" / "catalog.json"
ROUTING_CASES = Path(__file__).parent / "cases" / "routing.json"
WORKFLOW_CASES = Path(__file__).parent / "cases" / "workflows.json"
GLOBAL_INSTRUCTIONS = REPO_ROOT / "global-instructions" / "AGENTS.md"
GRADE_SCHEMA = Path(__file__).parent / "grade-schema.json"
ROUTE_SCHEMA = Path(__file__).parent / "route-schema.json"
LEGACY_ROUTE_SCHEMA = Path(__file__).parent / "legacy-route-schema.json"
WORKFLOW_ROUTE_SCHEMA = Path(__file__).parent / "workflow-route-schema.json"
AUTH_FILE = Path.home() / ".codex" / "auth.json"
WORKFLOW_DEFAULT_SETUP = (
    "git init -q && git config user.email eval@example.invalid && "
    "git config user.name Eval && git add . && "
    "git commit --allow-empty -qm baseline"
)
SKILL_NAMES = {
    path.name
    for path in SKILLS_ROOT.iterdir()
    if (path / "SKILL.md").is_file()
}

# A primary case may contain a genuinely distinct second deliverable. Keep
# those expectations explicit instead of treating every extra selection as a
# routing error, while still scoring unnecessary selections separately.
ROUTING_EXPECTED_OVERRIDES: dict[str, list[str]] = {
    "architect-event-contract": ["architect"],
    "hillclimb-batch-tuning": ["hillclimb"],
    "how-request-flow": ["how", "architect"],
    "html-artifact-evidence-report": ["html-artifacts"],
    "systematic-debugging-cache-regression": ["systematic-debugging"],
    "verify-deployment-claim": ["production-safety", "verify-work"],
    "web-interface-settings": ["web-interface"],
    "teach-idempotency-change": ["teach"],
    "follow-instructions-shibboleth-boundary": [
        "follow-instructions",
        "systematic-debugging",
        "production-safety",
        "security-and-hardening",
        "pull-requests",
        "verify-work",
    ],
}


def isolated_codex_home(with_skills: bool) -> tempfile.TemporaryDirectory[str]:
    """Create an ephemeral Codex home that reuses auth but isolates configuration."""

    # Codex may create helper binaries next to its ephemeral home.  Keep the
    # isolated home out of /tmp (which the CLI deliberately refuses for PATH
    # aliases) while still cleaning it up after each sample.
    directory = tempfile.TemporaryDirectory(
        prefix="skills-eval-codex-",
        dir=str(Path.home() / ".cache"),
    )
    home = Path(directory.name)
    if not AUTH_FILE.is_file():
        directory.cleanup()
        raise RuntimeError("native Codex auth is unavailable; run `codex login`")
    (home / "auth.json").symlink_to(AUTH_FILE)
    if with_skills:
        skills = home / "skills"
        skills.mkdir()
        system_skills = skills / ".system"
        system_skills.mkdir()
        for skill in sorted(SKILLS_ROOT.iterdir()):
            if (skill / "SKILL.md").is_file():
                (skills / skill.name).symlink_to(skill, target_is_directory=True)
                # Codex reserves several common names for bundled skills. Point
                # either locator at the catalog copy so routing cannot select a
                # nonexistent bundled path or evaluate different instructions.
                (system_skills / skill.name).symlink_to(
                    skill, target_is_directory=True
                )
    return directory


async def run_codex(
    prompt: str,
    *,
    model: str,
    with_skills: bool,
    sandbox_mode: str,
    output_schema: Path | None = None,
    extra_env: Mapping[str, str] | None = None,
    # Max-effort native cases can spend more than fifteen minutes in one
    # isolated command session (for example, a full artifact or deployment
    # investigation). Keep a finite bound while avoiding false evaluation
    # failures caused solely by the old 900-second cap.
    timeout: int = 1800,
) -> tuple[str, str]:
    """Run signed-in Codex in the current Inspect local sandbox workspace."""

    with isolated_codex_home(with_skills) as codex_home:
        output_file = f"/tmp/codex-eval-{uuid4().hex}.txt"
        command = [
            "codex",
            "exec",
            "--ignore-user-config",
            "--ignore-rules",
            "--ephemeral",
            "--skip-git-repo-check",
            "--sandbox",
            sandbox_mode,
            "--model",
            model,
            # The parent Inspect model setting does not flow into this
            # nested native Codex process. Pin the requested eval effort here
            # so a "Luna Max" run is actually Max reasoning.
            "-c",
            'model_reasoning_effort="max"',
            "--json",
            "--output-last-message",
            output_file,
        ]
        if output_schema is not None:
            command.extend(["--output-schema", str(output_schema)])
        command.append("-")
        try:
            result = await sandbox().exec(
                command,
                input=prompt,
                # Codex also discovers user-level skills under ~/.agents.
                # Isolate HOME as well as CODEX_HOME so the baseline receives
                # neither catalog nor unrelated personal skills.
                env={
                    "CODEX_HOME": str(codex_home),
                    "HOME": str(codex_home),
                    **(dict(extra_env) if extra_env else {}),
                },
                timeout=timeout,
                timeout_retry=False,
                concurrency=True,
            )
            if not result.success:
                raise RuntimeError(
                    "native Codex failed: "
                    f"exit={result.returncode}; stderr={result.stderr.strip()}; "
                    f"stdout={result.stdout[-4000:]}"
                )
            completion = await sandbox().read_file(output_file)
            return completion.strip(), result.stdout
        finally:
            await sandbox().exec(["rm", "-f", output_file], timeout=30)


@solver
def native_codex(
    with_skills: bool,
    model: str,
    *,
    inject_skill: bool = True,
) -> Solver:
    """Execute a sample with the locally authenticated Codex CLI."""

    async def solve(state: TaskState, generate: Generate) -> TaskState:
        prompt = state.input_text
        if with_skills and inject_skill:
            skill = (state.metadata or {}).get("skill")
            skill_path = SKILLS_ROOT / skill / "SKILL.md"
            instructions = skill_path.read_text()
            prompt = (
                "Follow the applicable catalog skill below for this task. Its instructions "
                "are injected verbatim so this evaluation measures instruction efficacy "
                "independently of skill routing and filesystem discovery. Relative links "
                f"resolve from $CODEX_HOME/skills/{skill}/.\n\n"
                f"<catalog_skill name=\"{skill}\">\n{instructions}\n</catalog_skill>\n\n"
                f"{prompt}"
            )
        contract = (state.metadata or {}).get("fixture_contract")
        tracker: FakeTracker | None = None
        if isinstance(contract, dict):
            tracker = FakeTracker(state.sample_id, state.epoch)
            tracker.start()
        try:
            completion, events = await run_codex(
                prompt,
                model=model,
                with_skills=with_skills,
                sandbox_mode="workspace-write",
                extra_env=tracker.environment() if tracker is not None else None,
            )
        finally:
            # Snapshot before closing/cleaning the fixture directory.  This is
            # the only publication evidence consumed by the scorer; command
            # names and final prose are deliberately not consulted.
            if tracker is not None:
                state.store.set("fixture_publication", tracker.snapshot())
                tracker.close()
        state.output = ModelOutput.from_content(
            model=f"codex-subscription/{model}",
            content=completion,
        )
        state.output.metadata = {"codex_jsonl": events}
        if with_skills and inject_skill:
            state.output.metadata["injected_skill"] = skill
        elif with_skills:
            state.output.metadata["skill_discovery"] = "installed-catalog"
        if tracker is not None:
            state.output.metadata["fixture_source"] = "runner-owned-fake-tracker"
        return state

    return solve


def catalog_routing_index() -> str:
    """Return only compact trigger metadata, not full skill instructions."""

    rows: list[str] = []
    for skill_path in sorted(SKILLS_ROOT.iterdir()):
        skill_file = skill_path / "SKILL.md"
        if not skill_file.is_file():
            continue
        text = skill_file.read_text()
        match = re.match(r"^---\n(.*?)\n---(?:\n|$)", text, re.DOTALL)
        if not match:
            continue
        frontmatter = yaml.safe_load(match.group(1))
        if isinstance(frontmatter, dict):
            name = frontmatter.get("name")
            description = frontmatter.get("description")
            if isinstance(name, str) and isinstance(description, str):
                rows.append(f"- {name}: {description.strip()}")
    return "\n".join(rows)


def routing_dataset() -> MemoryDataset:
    """Build positive primary cases plus explicit no-skill near misses."""

    catalog_cases = json.loads(CASES.read_text())
    routing_cases = json.loads(ROUTING_CASES.read_text())
    samples: list[Sample] = []
    for case in catalog_cases:
        skill = case["metadata"]["skill"]
        expected = ROUTING_EXPECTED_OVERRIDES.get(case["id"], [skill])
        if expected and "follow-instructions" not in expected:
            expected = ["follow-instructions", *expected]
        samples.append(
            Sample(
                input=case["input"],
                target=skill,
                id=f"route-{case['id']}",
                metadata={
                    "expected_skills": expected,
                    "route_kind": "positive",
                },
            )
        )
    for case in routing_cases:
        samples.append(
            Sample(
                input=case["input"],
                target="no catalog skill",
                id=case["id"],
                metadata=case["metadata"],
            )
        )
    return MemoryDataset(samples=samples, name="catalog-routing", shuffled=False)


def workflows_dataset(
    *,
    execution_ready_only: bool = False,
    global_instructions: Path = GLOBAL_INSTRUCTIONS,
) -> MemoryDataset:
    """Load routing cases or explicitly supplied execution fixtures.

    A routing case is useful for classification but is not silently promoted
    to an executable workspace.  The integrated task opts into the smaller
    execution-ready subset; route diagnostics retain every case.
    """

    dataset = json_dataset(str(WORKFLOW_CASES))
    global_rules = global_instructions.read_text()
    samples: list[Sample] = []
    for sample in dataset.samples:
        metadata = dict(sample.metadata or {})
        execution_mode = metadata.get("execution_mode")
        if execution_mode not in {"routing-only", "execution-ready"}:
            execution_mode = "execution-ready" if sample.files else "routing-only"
        if execution_ready_only and execution_mode != "execution-ready":
            continue
        files = dict(sample.files or {})
        files["AGENTS.md"] = global_rules
        sample.files = files
        if execution_mode == "routing-only" and not sample.setup:
            sample.setup = WORKFLOW_DEFAULT_SETUP
        sample.metadata = {
            **metadata,
            "execution_scope": "trusted-synthetic-local",
            "execution_mode": execution_mode,
        }
        samples.append(sample)
    return MemoryDataset(samples=samples, name=dataset.name, shuffled=False)


@solver
def route_codex(model: str) -> Solver:
    """Ask the native model to route without giving it a skill by fiat."""

    async def solve(state: TaskState, generate: Generate) -> TaskState:
        prompt = (
            "You are routing a user request to a local catalog of agent skills. "
            "Choose only skills whose instructions materially govern this request. "
            "Do not select a skill merely because the request mentions its subject. "
            "Select no skills for ordinary questions, explanations, or work that "
            "does not need a catalog workflow. Prefer the smallest sufficient set. "
            "Treat a skill description as a trigger, not a checklist: do not add "
            "grilling for an ordinary architecture critique (architect already "
            "owns candidate critique; require an explicit grill/pressure-test "
            "request). For a repository walkthrough or a request phrased "
            "'walk me through what happens,' select how (even when a separate "
            "architecture critique is requested), not teach. Conversely, when "
            "the primary wording explicitly asks to be taught, learn, or "
            "understand a change, select teach even if the explanation includes "
            "runtime flow; add how only for a separate repository walkthrough. "
            "Do not "
            "add verify-work for a "
            "routine implementation verification summary, web-interface for a "
            "standalone disposable HTML artifact, or production-safety merely "
            "because a local diagnosis follows a deploy. Add a second skill only "
            "when it owns a distinct requested deliverable, such as a walkthrough "
            "plus a separate code review or an explicit production claim check. "
            "Do not add verify-work merely because a domain skill requires tests, "
            "a holdout, or evidence inside its own workflow. Do not add architect "
            "merely because a security review discusses boundaries or data flow; "
            "security-and-hardening owns that assessment unless architecture is "
            "an explicit separate deliverable. Do not add security-and-hardening "
            "merely because a setup wizard stores local credentials; the wizard "
            "owns safe credential handling unless the user explicitly asks for "
            "a security audit, hardening, or threat model. "
            "Do select verify-work when the request explicitly conditions a "
            "completion, publication, deployment, or MR claim on observable "
            "success (for example, 'do not claim it unless it succeeds'). "
            "Apply the governing global instructions when selecting skills. "
            "Return only JSON matching the supplied schema, with canonical skill "
            "names exactly as shown in the catalog. Do not perform the task.\n\n"
            f"GOVERNING GLOBAL INSTRUCTIONS:\n{GLOBAL_INSTRUCTIONS.read_text()}\n\n"
            f"CATALOG:\n{catalog_routing_index()}\n\n"
            f"USER REQUEST:\n{state.input_text}"
        )
        completion, events = await run_codex(
            prompt,
            model=model,
            with_skills=False,
            sandbox_mode="read-only",
            output_schema=LEGACY_ROUTE_SCHEMA,
            timeout=300,
        )
        state.output = ModelOutput.from_content(
            model=f"codex-subscription/{model}",
            content=completion,
        )
        state.output.metadata = {"codex_jsonl": events}
        return state

    return solve


def selected_route(state: TaskState) -> tuple[set[str], str | None]:
    """Parse a route once for the coverage and minimality scorers."""

    try:
        value = json.loads(state.output.completion)
    except (AttributeError, json.JSONDecodeError):
        return set(), "router did not return a JSON object"
    selected_value = value.get("skills") if isinstance(value, dict) else None
    if not isinstance(selected_value, list) or not all(
        isinstance(skill, str) for skill in selected_value
    ):
        return set(), "router skills must be a string array"
    selected = selected_value
    unknown = sorted(set(selected) - SKILL_NAMES)
    if unknown:
        return set(), f"router selected unknown skills: {unknown}"
    if len(selected) != len(set(selected)):
        return set(), "router repeated a skill"
    return set(selected), None


@scorer(metrics=[accuracy()])
def routing_coverage():
    """Require every materially necessary skill, including no-skill cases."""

    async def score(state: TaskState, target: Target) -> Score:
        expected = set((state.metadata or {}).get("expected_skills", []))
        selected, error = selected_route(state)
        if error:
            return Score(value=0, explanation=error)
        missing = sorted(expected - selected)
        return Score(value=1 if not missing else 0, explanation=f"missing={missing or None}")

    return score


@scorer(metrics=[accuracy()])
def routing_minimality():
    """Require that no selected skill is unnecessary for the case."""

    async def score(state: TaskState, target: Target) -> Score:
        expected = set((state.metadata or {}).get("expected_skills", []))
        selected, error = selected_route(state)
        if error:
            return Score(value=0, explanation=error)
        extra = sorted(selected - expected)
        return Score(value=1 if not extra else 0, explanation=f"unnecessary={extra or None}")

    return score


def _parse_workflow_route(state: TaskState) -> tuple[dict[str, object] | None, str | None]:
    try:
        value = json.loads(state.output.completion)
    except (AttributeError, json.JSONDecodeError):
        return None, "router did not return JSON"
    if not isinstance(value, dict) or not isinstance(value.get("workflow"), dict):
        return None, "router omitted workflow composition"
    workflow = value["workflow"]
    required = {
        "primary",
        "mode",
        "follow_ons",
        "domains",
        "modifiers",
        "effects",
        "constraints",
    }
    if set(workflow) != required:
        return None, f"workflow fields mismatch: {sorted(set(workflow) ^ required)}"
    if not isinstance(workflow["primary"], str) or not isinstance(workflow["mode"], str):
        return None, "workflow primary/mode must be strings"
    for field in ("follow_ons", "domains", "modifiers", "constraints"):
        values = workflow[field]
        if not isinstance(values, list) or not all(isinstance(item, str) for item in values):
            return None, f"workflow {field} must be a string array"
    unknown_domains = sorted(set(workflow["domains"]) - SKILL_NAMES)
    if unknown_domains:
        return None, f"workflow domains contain unknown skills: {unknown_domains}"
    if any(item != "parallel" for item in workflow["modifiers"]):
        return None, "workflow modifiers contain an unknown value"
    effects = workflow["effects"]
    if not isinstance(effects, dict) or set(effects) != {
        "workspace",
        "external",
        "production",
    } or not all(isinstance(value, str) for value in effects.values()):
        return None, "workflow effects must name string workspace/external/production"
    return workflow, None


@solver
def workflow_route_codex(model: str) -> Solver:
    """Use coordinator/global instructions without injecting expected answers."""

    async def solve(state: TaskState, generate: Generate) -> TaskState:
        del generate
        prompt = (
            "Classify this request using the supplied global instructions and the "
            "follow-instructions coordinator. Return only JSON matching the supplied "
            "schema. Populate its optional workflow object with the primary family, "
            "separate mode, ordered follow-ons, peer domains, parallel modifier, "
            "permitted effects, and material constraints. Do not perform the task.\n\n"
            f"GLOBAL INSTRUCTIONS:\n{GLOBAL_INSTRUCTIONS.read_text()}\n\n"
            f"FOLLOW-INSTRUCTIONS:\n{(SKILLS_ROOT / 'follow-instructions' / 'SKILL.md').read_text()}\n\n"
            f"CATALOG TRIGGERS:\n{catalog_routing_index()}\n\n"
            f"USER REQUEST:\n{state.input_text}"
        )
        completion, events = await run_codex(
            prompt,
            model=model,
            with_skills=False,
            sandbox_mode="read-only",
            output_schema=WORKFLOW_ROUTE_SCHEMA,
            timeout=300,
        )
        state.output = ModelOutput.from_content(
            model=f"codex-subscription/{model}",
            content=completion,
        )
        state.output.metadata = {
            "codex_jsonl": events,
            "routing_mode": "coordinator-discovery-diagnostic",
        }
        return state

    return solve


@scorer(metrics=[accuracy()])
def workflow_composition():
    """Score hidden route metadata, never an answer inserted into the prompt."""

    async def score(state: TaskState, target: Target) -> Score:
        del target
        workflow, error = _parse_workflow_route(state)
        if error or workflow is None:
            return Score(value=0, explanation=error or "missing workflow")
        metadata = state.metadata or {}
        expected_routes = list(metadata.get("expected_workflows", []))
        expected_primary, expected_mode = expected_routes[0].split("/", 1)
        expected_follow_ons = expected_routes[1:]
        expected_skills = set(metadata.get("expected_skills", []))
        optional_skills = set(metadata.get("optional_skills", []))
        # The PR/MR package owns the external lifecycle even when it is an
        # optional readback companion to a review route. It is deliberately
        # excluded from peer-domain scoring so an agent may select it for
        # lifecycle context without pretending it is review expertise.
        lifecycle_skills = {"pull-requests"}
        expected_domains = sorted(
            expected_skills - {"follow-instructions"} - lifecycle_skills
        )
        allowed_domains = set(expected_domains) | (
            optional_skills - {"follow-instructions"} - lifecycle_skills
        )
        optional_domains = optional_skills - {"follow-instructions"} - lifecycle_skills
        selected, route_error = selected_route(state)
        allow_changes = bool(metadata.get("allow_changes", False))
        if any(route == "issues/create" for route in expected_routes):
            external = "issue-create"
        elif any(route == "issues/update" for route in expected_routes):
            external = "issue-update"
        elif any(route == "pull-requests/create" for route in expected_routes):
            external = "pr-create"
        elif any(route == "pull-requests/communicate" for route in expected_routes):
            external = "comment"
        else:
            external = "none"
        expected_production = metadata.get(
            "expected_production",
            (
                "write"
                if allow_changes
                and any(
                    route in {
                        "migrate-operate/migrate",
                        "migrate-operate/release",
                        "migrate-operate/incident",
                    }
                    for route in expected_routes
                )
                else "none"
            ),
        )
        expected_effects = {
            "workspace": "write" if allow_changes else "read",
            "external": external,
            "production": expected_production,
        }
        mismatches: list[str] = []
        if route_error:
            mismatches.append("skills-invalid")
        elif (
            expected_skills - selected
            or selected - (expected_skills | optional_skills)
        ):
            mismatches.append("skills")
        if workflow["primary"] != expected_primary or workflow["mode"] != expected_mode:
            mismatches.append("primary/mode")
        if workflow["follow_ons"] != expected_follow_ons:
            mismatches.append("follow_ons")
        selected_domains = set(workflow["domains"])
        selected_domain_skills = selected - {"follow-instructions"} - lifecycle_skills
        if (
            set(expected_domains) - selected_domains
            or selected_domains - allowed_domains
            or selected_domains - selected_domain_skills
            or (
                optional_domains
                and not (selected & optional_domains) <= selected_domains
            )
        ):
            mismatches.append("domains")
        if workflow["modifiers"] != list(metadata.get("expected_modifiers", [])):
            mismatches.append("modifiers")
        if workflow["effects"]["workspace"] != expected_effects["workspace"]:
            mismatches.append("effects")
        if workflow["effects"]["external"] != expected_effects["external"]:
            mismatches.append("effects")
        if workflow["effects"]["production"] != expected_effects["production"]:
            mismatches.append("effects")
        return Score(
            value=1 if not mismatches else 0,
            explanation=f"mismatches={mismatches or None}",
            metadata={"mismatches": mismatches},
        )

    return score


@scorer(metrics=[accuracy()])
def workspace_policy():
    """Check read-only cases and required output files in the task sandbox."""

    async def score(state: TaskState, target: Target) -> Score:
        metadata = state.metadata or {}
        status = await sandbox().exec(["git", "status", "--porcelain"])
        if not status.success:
            return Score(value=0, explanation=f"git status failed: {status.stderr}")

        changes = [line for line in status.stdout.splitlines() if line.strip()]
        if not metadata.get("allow_changes", False) and changes:
            return Score(value=0, explanation=f"read-only case changed workspace: {changes}")

        missing: list[str] = []
        for path in metadata.get("required_files", []):
            try:
                await sandbox().read_file(path)
            except FileNotFoundError:
                missing.append(path)
        if missing:
            return Score(value=0, explanation=f"required files missing: {missing}")

        return Score(value=1, explanation="workspace policy satisfied")

    return score


@scorer(metrics=[accuracy()])
def skill_activation():
    """Require evidence that the treatment received its intended skill."""

    async def score(state: TaskState, target: Target) -> Score:
        skill = (state.metadata or {}).get("skill")
        injected = (state.output.metadata or {}).get("injected_skill")
        if injected == skill:
            return Score(value=1, explanation=f"injected {skill}/SKILL.md")
        return Score(value=0, explanation=f"did not inject {skill}/SKILL.md")

    return score


async def workspace_evidence(state: TaskState) -> str:
    """Collect bounded code and artifact evidence for the behavior grader."""

    sections: list[str] = []
    diff = await sandbox().exec(["git", "diff", "--no-ext-diff", "--unified=3"])
    if diff.success and diff.stdout.strip():
        sections.append(f"GIT DIFF:\n{diff.stdout[:30000]}")
    status = await sandbox().exec(["git", "status", "--porcelain"])
    if status.success:
        untracked = [
            line[3:]
            for line in status.stdout.splitlines()
            if line.startswith("?? ") and " -> " not in line
        ]
        for path in untracked[:10]:
            try:
                content = await sandbox().read_file(path)
            except (FileNotFoundError, IsADirectoryError, UnicodeDecodeError):
                continue
            sections.append(f"UNTRACKED FILE {path}:\n{content[:20000]}")
    for path in (state.metadata or {}).get("required_files", []):
        try:
            content = await sandbox().read_file(path)
        except FileNotFoundError:
            sections.append(f"REQUIRED FILE {path}: MISSING")
        else:
            sections.append(f"REQUIRED FILE {path}:\n{content[:20000]}")
    execution_records: list[str] = []
    tool_records: list[str] = []
    events = (state.output.metadata or {}).get("codex_jsonl", "")
    for line in events.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        item = event.get("item", {})
        if event.get("type") != "item.completed":
            continue
        if item.get("type") == "file_change":
            execution_records.append(
                "FILE CHANGE: " + json.dumps(item, ensure_ascii=False)[:5000]
            )
            continue
        if item.get("type") != "command_execution":
            if event.get("type") == "item.completed" and item.get("type") in {
                "web_search",
                "browser",
                "browser_use",
            }:
                # Codex emits bounded tool metadata, not page bodies. Keep it
                # in grader evidence so an attempted bare search cannot look
                # like a validated source result.
                tool_records.append(
                    "TOOL: " + json.dumps(item, ensure_ascii=False)[:4000]
                )
            continue
        execution_records.append(
            "COMMAND: "
            f"{item.get('command', '')[:1000]}\n"
            f"EXIT: {item.get('exit_code')}\n"
            f"OUTPUT:\n{item.get('aggregated_output', '')[:5000]}"
        )
    if execution_records:
        execution_evidence = "\n\n".join(execution_records)
        if len(execution_evidence) > 40000:
            execution_evidence = (
                execution_evidence[:20000]
                + "\n\n... MIDDLE EXECUTION EVIDENCE OMITTED ...\n\n"
                + execution_evidence[-20000:]
            )
        sections.append("OBSERVED ORDERED EXECUTION EVIDENCE:\n" + execution_evidence)
    if tool_records:
        sections.append("OBSERVED TOOL METADATA:\n" + "\n".join(tool_records)[-12000:])
    return "\n\n".join(sections) or "No workspace changes or required artifacts."


@scorer(metrics=[mean()])
def native_behavior_grade(model: str):
    """Grade the final answer with an isolated native Codex invocation."""

    async def score(state: TaskState, target: Target) -> Score:
        evidence = await workspace_evidence(state)
        prompt = (
            "You are grading one agent-skill evaluation on a 0-4 quality scale. "
            "Use 4 for complete, precise satisfaction of the target; 3 for strong work "
            "with a minor omission; 2 for useful but materially incomplete work; 1 for "
            "weak or mostly generic work; and 0 for failure or unsafe behavior. Grade "
            "the final response together with the supplied workspace evidence. Penalize "
            "invented evidence and ignored execution boundaries. Do not require the "
            "response to repeat content that is proven in an output file. Return only "
            "the requested JSON object.\n\n"
            f"TASK:\n{state.input_text}\n\n"
            f"TARGET:\n{target.text}\n\n"
            f"CANDIDATE RESPONSE:\n{state.output.completion}\n\n"
            f"WORKSPACE EVIDENCE:\n{evidence}"
        )
        completion, _ = await run_codex(
            prompt,
            model=model,
            with_skills=False,
            sandbox_mode="read-only",
            output_schema=GRADE_SCHEMA,
            # Native grading can require several minutes for a long, evidence-
            # rich workspace response. Keep it bounded, but do not let a
            # valid sample fail solely because the grader's prompt is large.
            timeout=900,
        )
        try:
            grade = json.loads(completion)
        except json.JSONDecodeError as exc:
            return Score(value=0, explanation=f"grader returned invalid JSON: {exc}")
        value = grade.get("score")
        if not isinstance(value, int) or not 0 <= value <= 4:
            return Score(value=0, explanation="grader omitted a valid 0-4 score")
        explanation = grade.get("explanation")
        if not isinstance(explanation, str):
            explanation = "grader omitted a textual explanation"
        return Score(value=value, explanation=explanation)

    return score


def _fixture_observations(snapshot: object) -> list[str]:
    """Derive observations from authoritative fixture receipts only."""

    if not isinstance(snapshot, dict):
        return []
    receipts = snapshot.get("receipts")
    if not isinstance(receipts, list):
        return []
    observations: list[str] = []
    successful = [
        item
        for item in receipts
        if isinstance(item, dict) and item.get("ok") is True
    ]
    source = [item for item in successful if item.get("operation") == "inspect-source"]
    if source:
        observations.append("owning-source-inspected")
    creates = [item for item in successful if item.get("operation") == "create"]
    if creates:
        observations.append("issue-created")
    if creates:
        created = creates[0].get("response")
        created_object = created.get("object") if isinstance(created, dict) else None
        object_id = created_object.get("id") if isinstance(created_object, dict) else None
        if isinstance(object_id, str):
            for item in successful:
                if item.get("operation") != "get":
                    continue
                response = item.get("response")
                returned = response.get("object") if isinstance(response, dict) else None
                if isinstance(returned, dict) and returned.get("id") == object_id:
                    observations.append("issue-read-back")
                    break
    return observations


@solver
def workflow_fixture_candidate() -> Solver:
    """Exercise the supplied runner-owned fake tracker without repository writes."""

    async def solve(state: TaskState, generate: Generate) -> TaskState:
        del generate
        tracker = FakeTracker(state.sample_id, state.epoch)
        tracker.start()
        environment = tracker.environment()
        try:
            source = await sandbox().read_file("lookup.py")
            if "def lookup" not in source:
                raise RuntimeError("owning lookup source was not inspectable")
            source_bytes = source.encode()
            source_digest = hashlib.sha256(source_bytes).hexdigest()
            inspected = await sandbox().exec(
                [
                    "python",
                    "tracker.py",
                    "inspect-source",
                    "lookup.py",
                    "--sha256",
                    source_digest,
                    "--size",
                    str(len(source_bytes)),
                ],
                env=environment,
                timeout=30,
                timeout_retry=False,
            )
            if not inspected.success:
                raise RuntimeError(f"source inspection failed: {inspected.stderr.strip()}")
            create = await sandbox().exec(
                [
                    "python",
                    "tracker.py",
                    "create",
                    "--title",
                    "Tenant lookup can cross owner boundary",
                    "--body",
                    "Problem: lookup uses the requested identifier without checking its owner.\n"
                    "Scope: enforce the authenticated owner at lookup.\n"
                    "Acceptance: an owner can read its row and another owner is denied.",
                ],
                env=environment,
                timeout=30,
                timeout_retry=False,
            )
            if not create.success:
                raise RuntimeError(f"fake issue create failed: {create.stderr.strip()}")
            issue = json.loads(create.stdout)
            created_object = issue.get("object") if isinstance(issue, dict) else None
            issue_id = created_object.get("id") if isinstance(created_object, dict) else None
            if not isinstance(issue_id, str):
                raise RuntimeError("fake issue create returned no object identity")
            readback = await sandbox().exec(
                ["python", "tracker.py", "get", issue_id],
                env=environment,
                timeout=30,
                timeout_retry=False,
            )
            if not readback.success:
                raise RuntimeError(f"fake issue readback failed: {readback.stderr.strip()}")
            state.output = ModelOutput.from_content(
                model="stub/no-model",
                content="Fixture operations completed; inspect runner-owned receipts for publication evidence.",
            )
        finally:
            state.store.set("fixture_publication", tracker.snapshot())
            tracker.close()
        return state

    return solve


@scorer(metrics=[accuracy()])
def workflow_effects():
    """Grade fake publication from runner-owned operation receipts."""

    async def score(state: TaskState, target: Target) -> Score:
        del target
        metadata = state.metadata or {}
        contract = metadata.get("fixture_contract")
        if not isinstance(contract, dict):
            return Score.unscored(
                explanation="workflow case is routing-only; publication is unmeasured",
                metadata={"status": "unmeasured", "execution_mode": "routing-only"},
            )
        snapshot = state.store.get("fixture_publication")
        if not isinstance(snapshot, dict):
            return Score(value=0, explanation="runner-owned fixture receipts are unavailable")
        if snapshot.get("sample_id") != state.sample_id or snapshot.get("epoch") != state.epoch:
            return Score(
                value=0,
                explanation="fixture receipts belong to a different sample or epoch",
                metadata={"status": "rejected"},
            )
        observations = _fixture_observations(snapshot)
        required = set(metadata.get("required_observations", []))
        missing = sorted(required - set(observations))
        if missing:
            return Score(
                value=0,
                explanation=f"missing runner-owned fixture observations: {missing}",
                metadata={"observations": observations, "status": "rejected"},
            )
        valid, explanation = validate_publication(
            snapshot,
            required_title_fragment=str(contract.get("required_title_fragment", "")),
            required_body_fragments=tuple(
                item for item in contract.get("required_body_fragments", []) if isinstance(item, str)
            ),
            required_operations=tuple(
                item for item in contract.get("required_operations", []) if isinstance(item, str)
            ),
            required_source_path=str(contract.get("required_source_path", "lookup.py")),
            expected_sample_id=state.sample_id,
            expected_epoch=state.epoch,
        )
        return Score(
            value=1 if valid else 0,
            explanation=explanation,
            metadata={"observations": observations, "status": "accepted" if valid else "rejected"},
        )

    return score


@task
def workflow_fixture_smoke() -> Task:
    """Run a real no-model workflow publication/readback fixture."""

    sample = workflows_dataset(execution_ready_only=True).samples[0]
    return Task(
        dataset=MemoryDataset(
            samples=[sample],
            name="workflow-fixture-smoke",
            shuffled=False,
        ),
        solver=workflow_fixture_candidate(),
        scorer=[workspace_policy(), workflow_effects()],
        model="mockllm/model",
        sandbox="local",
        fail_on_error=False,
        score_on_error=True,
    )


@task
def catalog(with_skills: bool = True, native_model: str = "gpt-5.6-luna") -> Task:
    """Run representative catalog behavior with or without the skill catalog."""

    return Task(
        dataset=json_dataset(str(CASES)),
        solver=native_codex(with_skills=with_skills, model=native_model),
        scorer=(
            [workspace_policy(), skill_activation(), native_behavior_grade(model=native_model)]
            if with_skills
            else [workspace_policy(), native_behavior_grade(model=native_model)]
        ),
        model="mockllm/model",
        sandbox="local",
    )


@task
def routing(native_model: str = "gpt-5.6-luna") -> Task:
    """Evaluate activation timing and minimal skill selection."""

    return Task(
        dataset=routing_dataset(),
        solver=route_codex(model=native_model),
        scorer=[routing_coverage(), routing_minimality()],
        model="mockllm/model",
        sandbox="local",
    )


@task
def workflow_routing(native_model: str = "gpt-5.6-luna") -> Task:
    """Diagnose task/mode/domain/effect composition from normal instructions."""

    return Task(
        dataset=workflows_dataset(execution_ready_only=True),
        solver=workflow_route_codex(model=native_model),
        scorer=[workflow_composition()],
        model="mockllm/model",
        sandbox="local",
    )


@task
def workflows(
    with_skills: bool = True,
    native_model: str = "gpt-5.6-luna",
) -> Task:
    """Run integrated workflow cases with ordinary installed discovery."""

    return Task(
        dataset=workflows_dataset(),
        solver=native_codex(
            with_skills=with_skills,
            model=native_model,
            inject_skill=False,
        ),
        scorer=[
            workspace_policy(),
            workflow_effects(),
            native_behavior_grade(model=native_model),
        ],
        model="mockllm/model",
        sandbox="local",
        score_on_error=True,
    )

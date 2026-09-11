"""Inspect task for behavior-level evaluation using native Codex subscription auth."""

from __future__ import annotations

import importlib.util
import json
import re
import sys
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any
from uuid import uuid4

from inspect_ai import Task, task
from inspect_ai.dataset import MemoryDataset, Sample, json_dataset
from inspect_ai.model import ModelOutput
from inspect_ai.scorer import Score, Target, accuracy, mean, scorer
from inspect_ai.solver import Generate, Solver, TaskState, solver
from inspect_ai.util import sandbox
import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILLS_ROOT = REPO_ROOT / "skills"
CASES = Path(__file__).parent / "cases" / "catalog.json"
ROUTING_CASES = Path(__file__).parent / "cases" / "routing.json"
GLOBAL_INSTRUCTIONS = REPO_ROOT / "global-instructions" / "AGENTS.md"
GRADE_SCHEMA = Path(__file__).parent / "grade-schema.json"
ROUTE_SCHEMA = Path(__file__).parent / "route-schema.json"
AUTH_FILE = Path.home() / ".codex" / "auth.json"
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

    directory = tempfile.TemporaryDirectory(prefix="skills-eval-codex-")
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
                env={"CODEX_HOME": str(codex_home), "HOME": str(codex_home)},
                timeout=timeout,
                timeout_retry=False,
                concurrency=True,
            )
            if not result.success:
                raise RuntimeError(f"native Codex failed: {result.stderr.strip()}")
            completion = await sandbox().read_file(output_file)
            return completion.strip(), result.stdout
        finally:
            await sandbox().exec(["rm", "-f", output_file], timeout=30)


@solver
def native_codex(with_skills: bool, model: str) -> Solver:
    """Execute a sample with the locally authenticated Codex CLI."""

    async def solve(state: TaskState, generate: Generate) -> TaskState:
        prompt = state.input_text
        if with_skills:
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
        completion, events = await run_codex(
            prompt,
            model=model,
            with_skills=with_skills,
            sandbox_mode="workspace-write",
        )
        state.output = ModelOutput.from_content(
            model=f"codex-subscription/{model}",
            content=completion,
        )
        state.output.metadata = {"codex_jsonl": events}
        if with_skills:
            state.output.metadata["injected_skill"] = skill
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
            output_schema=ROUTE_SCHEMA,
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


_MISSING = object()
_UNAVAILABLE_STATUSES = {"unavailable", "blocked", "error", "failed"}


def _workspace_evidence_api():
    """Load the synchronous path-based evidence API only when a sample runs."""

    try:
        from evals.workspace_evidence import (
            Baseline,
            capture_baseline,
            collect_evidence,
            evidence_record,
        )
    except ModuleNotFoundError as exc:
        # Inspect can load this task by path without adding the repository
        # root to ``sys.path``. Resolve the sibling helper from the trusted
        # repository path instead of relying on candidate-controlled imports.
        if exc.name not in {"evals", "evals.workspace_evidence"}:
            raise
        module_name = "_skills_workspace_evidence"
        module = sys.modules.get(module_name)
        if module is None:
            module_path = REPO_ROOT / "evals" / "workspace_evidence.py"
            spec = importlib.util.spec_from_file_location(module_name, module_path)
            if spec is None or spec.loader is None:
                raise RuntimeError(f"unable to load evidence helper: {module_path}")
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
        Baseline = module.Baseline
        capture_baseline = module.capture_baseline
        collect_evidence = module.collect_evidence
        evidence_record = module.evidence_record

    return Baseline, capture_baseline, collect_evidence, evidence_record


def _workspace_result_field(value: Any, *names: str) -> Any:
    """Read a semantic field from either a mapping or a result dataclass."""

    if isinstance(value, Mapping):
        for name in names:
            if name in value:
                return value[name]
    for name in names:
        if hasattr(value, name):
            return getattr(value, name)
    return _MISSING


def _workspace_result_text(value: Any) -> str:
    """Render helper evidence without discarding structured path metadata."""

    if isinstance(value, str):
        return value

    def serialise(item: Any) -> Any:
        if isinstance(item, Path):
            return str(item)
        if hasattr(item, "__dict__"):
            return vars(item)
        return str(item)

    try:
        return json.dumps(value, ensure_ascii=False, default=serialise, sort_keys=True)
    except (TypeError, ValueError):
        return repr(value)


def _workspace_result_status(value: Any) -> str | None:
    status = _workspace_result_field(value, "status", "state", "outcome", "availability")
    if status is _MISSING or status is None:
        return None
    return str(status).lower().rsplit(".", 1)[-1]


def _workspace_result_available(value: Any) -> bool:
    """Require explicit helper availability; unknown results are not success."""

    if isinstance(value, bool):
        return value
    status = _workspace_result_status(value)
    if status is not None:
        if status in _UNAVAILABLE_STATUSES:
            return False
        if status in {"available", "ok", "success", "complete", "clean"}:
            return True
        return False
    available = _workspace_result_field(value, "available", "is_available")
    if available is not _MISSING:
        return bool(available)
    unavailable = _workspace_result_field(value, "unavailable")
    if unavailable is not _MISSING:
        return not bool(unavailable)
    return False


def _workspace_result_changed(value: Any) -> bool:
    """Determine dirtiness without flattening worktree, index, or HEAD changes."""

    head_changed = _workspace_result_field(value, "head_changed", "revision_changed")
    if head_changed is not _MISSING and bool(head_changed):
        return True

    baseline_head = _workspace_result_field(
        value,
        "baseline_head",
        "baseline_revision",
        "initial_head",
        "initial_revision",
    )
    final_head = _workspace_result_field(
        value,
        "final_head",
        "final_revision",
        "current_head",
        "current_revision",
    )
    if (
        baseline_head is not _MISSING
        and final_head is not _MISSING
        and baseline_head != final_head
    ):
        return True

    # The runner-owned collector exposes a baseline-relative contract. Prefer
    # it over inventory fields such as ``current_untracked_paths`` so a
    # pre-existing ignored file is not mistaken for a candidate mutation.
    explicit_changes = _workspace_result_field(value, "has_changes")
    if explicit_changes is not _MISSING:
        if isinstance(explicit_changes, str):
            return explicit_changes.strip().lower() in {"1", "true", "yes", "changed"}
        return bool(explicit_changes)

    path_fields = (
        "tracked_worktree_paths",
        "worktree_paths",
        "working_tree_paths",
        "tracked_index_paths",
        "tracked_paths",
        "index_paths",
        "cached_paths",
        "untracked_paths",
        "committed_paths",
        "changed_paths",
        "changes",
        "index_changed",
        "git_metadata_changed",
    )
    for name in path_fields:
        paths = _workspace_result_field(value, name)
        if paths is _MISSING or paths is None:
            continue
        if isinstance(paths, bool):
            if paths:
                return True
        elif isinstance(paths, str):
            if paths.strip():
                return True
        else:
            try:
                if len(paths):
                    return True
            except TypeError:
                if paths:
                    return True
    return False


def _workspace_unavailable(reason: str) -> dict[str, str]:
    """Represent instrumentation failure separately from candidate failure."""

    return {"status": "unavailable", "reason": reason}


async def _sandbox_workspace_path() -> tuple[Path | None, str | None]:
    """Resolve the local Inspect sandbox root for the path-based evidence API."""

    try:
        result = await sandbox().exec(
            ["pwd"],
            timeout=30,
            timeout_retry=False,
        )
    except Exception as exc:
        return None, f"unable to resolve sandbox workspace: {exc}"
    if not result.success:
        return None, f"unable to resolve sandbox workspace: {result.stderr.strip()}"
    lines = result.stdout.strip().splitlines()
    if not lines:
        return None, "sandbox returned no workspace path"
    path = Path(lines[-1])
    if not path.is_absolute() or not path.is_dir():
        return None, f"sandbox workspace path is not a readable directory: {path}"
    return path, None


def _workspace_record(value: Any, evidence_record: Any) -> Any:
    """Use the helper's JSON-safe record for Inspect's state store."""

    try:
        return evidence_record(value)
    except (AttributeError, TypeError, ValueError):
        if isinstance(value, Mapping):
            return dict(value)
        return value


def _workspace_baseline_object(value: Any, baseline_type: Any) -> Any:
    """Rehydrate a stored baseline record for the helper's typed API."""

    if isinstance(value, Mapping):
        try:
            return baseline_type(**dict(value))
        except (TypeError, ValueError):
            return value
    return value


@solver
def capture_workspace_baseline() -> Solver:
    """Capture runner-owned Git state after ``Sample.setup`` and before a solver."""

    async def solve(state: TaskState, generate: Generate) -> TaskState:
        workspace, error = await _sandbox_workspace_path()
        if error is not None or workspace is None:
            baseline: Any = _workspace_unavailable(error or "workspace unavailable")
        else:
            try:
                _, capture_baseline, _, evidence_record = _workspace_evidence_api()
                captured = capture_baseline(workspace)
                if captured is None:
                    baseline = _workspace_unavailable("baseline helper returned no result")
                else:
                    baseline = _workspace_record(captured, evidence_record)
            except Exception as exc:
                baseline = _workspace_unavailable(f"baseline capture failed: {exc}")
        state.store.set("workspace_baseline", baseline)
        return state

    return solve


async def _workspace_evidence_value(state: TaskState) -> Any:
    """Capture evidence once, including when an earlier solver failed."""

    if "workspace_evidence" in state.store:
        return state.store.get("workspace_evidence")

    baseline = state.store.get("workspace_baseline")
    workspace, error = await _sandbox_workspace_path()
    if error is not None or workspace is None:
        evidence = _workspace_unavailable(error or "workspace unavailable")
    else:
        metadata = state.metadata or {}
        required_paths = tuple(
            str(path) for path in metadata.get("required_files", [])
        )
        try:
            baseline_type, _, collect_evidence, evidence_record = _workspace_evidence_api()
            collected = collect_evidence(
                workspace,
                _workspace_baseline_object(
                    baseline or _workspace_unavailable("baseline missing"),
                    baseline_type,
                ),
                required_paths=required_paths,
                max_bytes=60000,
            )
            if collected is None:
                evidence = _workspace_unavailable(
                    "evidence helper returned no result"
                )
            else:
                evidence = _workspace_record(collected, evidence_record)
        except Exception as exc:
            evidence = _workspace_unavailable(f"evidence collection failed: {exc}")
    state.store.set("workspace_evidence", evidence)
    return evidence


@scorer(metrics=[accuracy()])
def workspace_policy():
    """Check workspace changes and required outputs against runner evidence."""

    async def score(state: TaskState, target: Target) -> Score:
        metadata = state.metadata or {}
        evidence = await _workspace_evidence_value(state)
        if not _workspace_result_available(evidence):
            return Score(
                value=0,
                explanation=(
                    "workspace instrumentation unavailable: "
                    f"{_workspace_result_text(evidence)}"
                ),
                metadata={"status": "unavailable"},
            )

        if not metadata.get("allow_changes", False) and _workspace_result_changed(evidence):
            return Score(
                value=0,
                explanation=(
                    "read-only case changed workspace: "
                    f"{_workspace_result_text(evidence)}"
                ),
                metadata={"status": "rejected"},
            )

        return Score(
            value=1,
            explanation="workspace policy satisfied",
            metadata={"status": "accepted"},
        )

    return score


@scorer(metrics=[accuracy()])
def skill_activation():
    """Require evidence that the treatment received its intended skill."""

    async def score(state: TaskState, target: Target) -> Score:
        skill = (state.metadata or {}).get("skill")
        output_metadata = getattr(state.output, "metadata", None) or {}
        injected = output_metadata.get("injected_skill")
        if injected == skill:
            return Score(value=1, explanation=f"injected {skill}/SKILL.md")
        return Score(value=0, explanation=f"did not inject {skill}/SKILL.md")

    return score


async def workspace_evidence(state: TaskState) -> str:
    """Collect bounded code and artifact evidence for the behavior grader."""

    sections: list[str] = [
        "RUNNER WORKSPACE EVIDENCE:\n" + _workspace_result_text(
            await _workspace_evidence_value(state)
        )
    ]
    execution_records: list[str] = []
    tool_records: list[str] = []
    output_metadata = getattr(state.output, "metadata", None) or {}
    events = output_metadata.get("codex_jsonl", "")
    for line in events.splitlines() if isinstance(events, str) else []:
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
            "CANDIDATE RESPONSE:\n"
            f"{getattr(state.output, 'completion', '') or '[candidate output unavailable]'}\n\n"
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


@solver
def evidence_smoke_candidate() -> Solver:
    """Make a deterministic workspace change without invoking a model."""

    async def solve(state: TaskState, generate: Generate) -> TaskState:
        await sandbox().write_file("module.py", "AUDIT_CHANGED_MARKER\n")
        state.output = ModelOutput.from_content(
            model="stub/no-model",
            content="deterministic evidence smoke candidate",
        )
        raise RuntimeError("intentional candidate failure for evidence smoke")

    return solve


@solver
def workspace_policy_smoke_candidate() -> Solver:
    """Leave a pre-existing ignored artifact untouched for policy scoring."""

    async def solve(state: TaskState, generate: Generate) -> TaskState:
        del generate
        state.output = ModelOutput.from_content(
            model="stub/no-model",
            content="deterministic read-only policy smoke candidate",
        )
        return state

    return solve


@scorer(metrics=[accuracy()])
def evidence_smoke_grade():
    """Prove evidence survives a failed candidate before sandbox teardown."""

    async def score(state: TaskState, target: Target) -> Score:
        raw_evidence = await _workspace_evidence_value(state)
        if not _workspace_result_available(raw_evidence):
            return Score(
                value=0,
                explanation=(
                    "workspace instrumentation unavailable: "
                    f"{_workspace_result_text(raw_evidence)}"
                ),
            )
        rendered = await workspace_evidence(state)
        if "AUDIT_CHANGED_MARKER" not in rendered:
            return Score(value=0, explanation="candidate marker missing from evidence")
        if not _workspace_result_changed(raw_evidence):
            return Score(value=0, explanation="candidate change missing from evidence")
        return Score(value=1, explanation="captured candidate evidence after failure")

    return score


@task
def evidence_smoke() -> Task:
    """Exercise the real Inspect lifecycle with a deterministic no-model solver."""

    sample = Sample(
        input="Record the post-failure workspace evidence.",
        target="The candidate change is observable after the candidate fails.",
        id="evidence-smoke",
        metadata={"allow_changes": True},
        setup=(
            "git init -q && "
            "git config user.email eval@example.invalid && "
            "git config user.name Eval && "
            "printf 'VALUE = \"baseline\"\\n' > module.py && "
            "git add -- module.py && "
            "git commit -qm baseline"
        ),
    )
    return Task(
        dataset=MemoryDataset(
            samples=[sample],
            name="evidence-smoke",
            shuffled=False,
        ),
        setup=capture_workspace_baseline(),
        solver=evidence_smoke_candidate(),
        scorer=[workspace_policy(), evidence_smoke_grade()],
        model="mockllm/model",
        sandbox="local",
        fail_on_error=False,
        score_on_error=True,
    )


@task
def workspace_policy_smoke() -> Task:
    """Exercise read-only scoring with a baseline ignored artifact."""

    sample = Sample(
        input="Inspect the workspace without changing it.",
        target="The pre-existing ignored artifact is not reported as a candidate change.",
        id="workspace-policy-smoke",
        metadata={"allow_changes": False},
        setup=(
            "git init -q && "
            "git config user.email eval@example.invalid && "
            "git config user.name Eval && "
            "printf 'VALUE = \"baseline\"\\n' > module.py && "
            "printf 'scratch/\\n' > .gitignore && "
            "mkdir -p scratch && "
            "printf 'PREEXISTING_IGNORED\\n' > scratch/report.txt && "
            "git add -- module.py .gitignore && "
            "git commit -qm baseline"
        ),
    )
    return Task(
        dataset=MemoryDataset(
            samples=[sample],
            name="workspace-policy-smoke",
            shuffled=False,
        ),
        setup=capture_workspace_baseline(),
        solver=workspace_policy_smoke_candidate(),
        scorer=[workspace_policy()],
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
        setup=capture_workspace_baseline(),
        solver=native_codex(with_skills=with_skills, model=native_model),
        scorer=(
            [workspace_policy(), skill_activation(), native_behavior_grade(model=native_model)]
            if with_skills
            else [workspace_policy(), native_behavior_grade(model=native_model)]
        ),
        model="mockllm/model",
        sandbox="local",
        score_on_error=True,
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

"""Run isolated, paired treatment/baseline trials from v2 contracts."""

from __future__ import annotations

import argparse
import concurrent.futures
import difflib
import hashlib
import json
import os
import random
import re
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from evals.providers import ClaudeAdapter, CodexAdapter, ProviderResult

from .catalog import CATALOG_HELDOUT_VERSION, catalog_case_entries, catalog_cases_for_skill, catalog_input_digest, catalog_skill_names
from .catalog_calibration import calibrate as calibrate_catalog
from .contracts import PILOT_ROOT, REPO_ROOT, cases_for_skill, contract_digest, execution_mode, fixture_path
from .graders import grade_trial
from .reference_check import check_references


# ``skill-creator`` is also installed as a system skill in the Codex runtime.
# Use a neutral project-local alias automatically so its treatment arm can be
# evaluated without colliding with the provider's built-in inventory.
RUNTIME_SKILL_ALIASES = {
    "skill-creator": "skill-creator-eval-alias",
}
from .validate import validate


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def _safe_slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")[:60] or "case"


def _commit_fingerprint() -> str:
    try:
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, check=True, capture_output=True, text=True
        ).stdout.strip()
        status = subprocess.run(
            ["git", "status", "--short", "--untracked-files=all"], cwd=REPO_ROOT, check=True, capture_output=True, text=True
        ).stdout
    except (OSError, subprocess.CalledProcessError):
        return "unknown"
    if not status:
        return head
    return f"{head}+dirty-{hashlib.sha256(status.encode()).hexdigest()[:12]}"


def _content_digest(root: Path, *, ignored_dirs: set[str] | None = None) -> str:
    """Hash file names and bytes so dirty-tree status cannot hide edits."""

    # Python imports create bytecode caches while a run is starting.  Those
    # generated files are not source-of-truth inputs and must not make a
    # completed run unverifiable merely because the analyzer imported the
    # harness later.
    ignored = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
    ignored.update(ignored_dirs or set())
    digest = hashlib.sha256()
    if root.is_file():
        digest.update(root.name.encode())
        digest.update(root.read_bytes())
        return digest.hexdigest()
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if any(part in ignored for part in relative.parts):
            continue
        if path.is_symlink():
            digest.update(str(relative).encode())
            digest.update(f"symlink:{path.readlink()}".encode())
        elif path.is_file():
            digest.update(str(relative).encode())
            digest.update(path.read_bytes())
    return digest.hexdigest()


def _copy_fixture(case: dict[str, Any], project: Path) -> list[str]:
    fixture = fixture_path(case)
    if fixture is None:
        return []
    copied: list[str] = []
    if fixture.is_dir():
        for source in sorted(fixture.rglob("*")):
            if not source.is_file():
                continue
            relative = source.relative_to(fixture)
            destination = project / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
            copied.append(str(relative))
    elif fixture.is_file():
        destination = project / "inputs" / fixture.name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(fixture, destination)
        copied.append(str(destination.relative_to(project)))
    return copied


def _copy_skill(skill_name: str, provider_name: str, project: Path, skill_root: Path, runtime_skill_name: str | None = None) -> None:
    parent = ".claude/skills" if provider_name == "claude" else ".agents/skills"
    runtime_name = runtime_skill_name or skill_name
    destination = project / parent / runtime_name
    # Keep the eval manifests and private expected answers outside the model's
    # context.  A treatment must receive the skill artifact, not its grader.
    shutil.copytree(skill_root, destination, ignore=shutil.ignore_patterns("evals"))
    if runtime_name != skill_name:
        skill_file = destination / "SKILL.md"
        content = skill_file.read_text()
        content, replacements = re.subn(
            rf"(?m)^name:\s*{re.escape(skill_name)}\s*$",
            f"name: {runtime_name}",
            content,
            count=1,
        )
        if replacements != 1:
            raise ValueError(f"runtime alias could not rewrite frontmatter name for {skill_name}")
        content = re.sub(rf"\${re.escape(skill_name)}\b", f"${runtime_name}", content)
        skill_file.write_text(content)


def _snapshot(project: Path) -> dict[str, dict[str, str | None]]:
    result: dict[str, dict[str, str | None]] = {}
    for path in sorted(project.rglob("*")):
        relative = path.relative_to(project)
        if ".claude" in relative.parts or ".agents" in relative.parts or relative.name.startswith(".eval-"):
            continue
        if path.is_symlink():
            # Never follow provider-created links while collecting an artifact
            # snapshot; the target may be outside the disposable project.
            result[str(relative)] = {"sha256": f"symlink:{path.readlink()}", "text": None}
            continue
        if not path.is_file():
            continue
        raw = path.read_bytes()
        text: str | None
        try:
            text = raw.decode("utf-8") if len(raw) <= 1_000_000 else None
        except UnicodeDecodeError:
            text = None
        result[str(relative)] = {"sha256": hashlib.sha256(raw).hexdigest(), "text": text}
    return result


def _change_details(before: dict[str, dict[str, str | None]], after: dict[str, dict[str, str | None]]) -> tuple[dict[str, Any], str]:
    added = sorted(set(after) - set(before))
    removed = sorted(set(before) - set(after))
    modified = sorted(path for path in set(before) & set(after) if before[path]["sha256"] != after[path]["sha256"])
    value = {"added_files": added, "removed_files": removed, "modified_files": modified, "changed_files": added + removed + modified}
    diff_lines: list[str] = []
    for relative in added:
        after_text = after[relative].get("text")
        if after_text is not None:
            diff_lines.extend(difflib.unified_diff([], after_text.splitlines(keepends=True), fromfile="/dev/null", tofile=f"b/{relative}"))
    for relative in modified:
        before_text = before[relative].get("text")
        after_text = after[relative].get("text")
        if before_text is not None and after_text is not None:
            diff_lines.extend(difflib.unified_diff(before_text.splitlines(keepends=True), after_text.splitlines(keepends=True), fromfile=f"a/{relative}", tofile=f"b/{relative}"))
    for relative in removed:
        before_text = before[relative].get("text")
        if before_text is not None:
            diff_lines.extend(difflib.unified_diff(before_text.splitlines(keepends=True), [], fromfile=f"a/{relative}", tofile="/dev/null"))
    return value, "".join(diff_lines)


def _changes(run_dir: Path, before: dict[str, dict[str, str | None]], after: dict[str, dict[str, str | None]]) -> dict[str, Any]:
    value, diff_patch = _change_details(before, after)
    _write_json(run_dir / "changes.json", value)
    (run_dir / "diff.patch").write_text(diff_patch)
    return value


def _capture_project(project: Path) -> dict[str, dict[str, Any]]:
    """Capture a disposable provider project without leaving it on disk."""

    captured: dict[str, dict[str, Any]] = {}
    for path in sorted(project.rglob("*")):
        relative = str(path.relative_to(project))
        if path.is_symlink():
            captured[relative] = {"kind": "symlink", "target": str(path.readlink())}
        elif path.is_file():
            captured[relative] = {"kind": "file", "bytes": path.read_bytes()}
    return captured


def _restore_project(captured: dict[str, dict[str, Any]], project: Path) -> None:
    """Materialize a captured project only after all provider calls finish."""

    project.mkdir(parents=True, exist_ok=True)
    for relative, item in sorted(captured.items(), key=lambda pair: (Path(pair[0]).parts.__len__(), pair[0])):
        destination = project / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        if item.get("kind") == "symlink":
            os.symlink(str(item.get("target") or ""), destination)
        else:
            destination.write_bytes(item.get("bytes", b""))


def _write_provider_result(run_dir: Path, result: ProviderResult) -> None:
    (run_dir / "outputs").mkdir(parents=True, exist_ok=True)
    (run_dir / "transcript.jsonl").write_text(result.stdout)
    (run_dir / "stderr.txt").write_text(result.stderr)
    (run_dir / "outputs" / "final_response.md").write_text(result.final_response)
    _write_json(run_dir / "outputs" / "tool_calls.json", result.tool_calls)
    _write_json(run_dir / "provider_result.json", {
        "status": result.status,
        "return_code": result.return_code,
        "error": result.error,
        "usage": result.usage,
        "available_skills": result.available_skills,
        "system_skills": result.system_skills,
        "system_skill_inventory_complete": result.system_skill_inventory_complete,
        "network_policy_enforced": result.network_policy_enforced,
        "tool_policy_enforced": result.tool_policy_enforced,
    })


def _run_one(
    *,
    provider_name: str,
    provider: Any,
    skill_name: str,
    skill_root: Path,
    case: dict[str, Any],
    eval_dir: Path,
    configuration: str,
    trial: int,
    pair_id: str,
    arm_order: list[str],
    timeout_seconds: int,
    reasoning_effort: str | None,
    model: str | None,
    allowed_tools: list[str],
    source_commit: str,
    skill_digest: str,
    baseline_skill_root: Path | None = None,
    baseline_skill_digest: str | None = None,
    runtime_skill_name: str | None = None,
    credential_home: Path | None,
    contract_hash: str,
) -> dict[str, Any]:
    runtime_skill_name = runtime_skill_name or RUNTIME_SKILL_ALIASES.get(skill_name, skill_name)
    run_dir = eval_dir / configuration / f"run-{trial}"
    # The provider must not see the artifact path: it contains the arm name
    # (with_skill/without_skill), case id, and trial number.  Use a neutral
    # disposable workspace for the live call.  No evaluator artifacts are
    # materialized until every provider call in the batch has exited.
    provider_root = Path(tempfile.mkdtemp(prefix="skills-evals-provider-"))
    project = provider_root / "project"
    project.mkdir(parents=True)
    copied_inputs = _copy_fixture(case, project)
    if configuration == "with_skill":
        _copy_skill(skill_name, provider_name, project, skill_root, runtime_skill_name)
    elif baseline_skill_root is not None:
        _copy_skill(skill_name, provider_name, project, baseline_skill_root, runtime_skill_name)
    injected_skill = project / (".claude/skills" if provider_name == "claude" else ".agents/skills") / runtime_skill_name
    injected_skill_before = _content_digest(injected_skill) if configuration == "with_skill" or baseline_skill_root is not None else None
    mode = execution_mode(case)
    execution = case.get("execution") if isinstance(case.get("execution"), dict) else {}
    case_tools = execution.get("allowed_tools") if isinstance(execution, dict) else None
    effective_tools = list(dict.fromkeys((case_tools if isinstance(case_tools, list) else allowed_tools) + (["Write", "Edit"] if mode == "workspace_write" else [])))
    before = _snapshot(project)
    started_at = _utc_now()
    started = time.monotonic()
    try:
        result = provider.run(
            prompt=re.sub(rf"\${re.escape(skill_name)}\b", f"${runtime_skill_name}", str(case["prompt"])),
            project=project,
            run_dir=provider_root,
            model=model,
            with_skill=configuration == "with_skill",
            timeout_seconds=timeout_seconds,
            allowed_tools=effective_tools,
            writable=mode == "workspace_write",
            credential_home=credential_home,
            reasoning_effort=reasoning_effort,
        )
    except Exception as exc:  # preserve an invalid trial artifact for analysis
        result = ProviderResult("provider_error", None, "", stderr=str(exc), error=repr(exc))
    duration = time.monotonic() - started
    after = _snapshot(project)
    changes, diff_patch = _change_details(before, after)
    injected_skill_after = _content_digest(injected_skill) if configuration == "with_skill" or baseline_skill_root is not None else None
    changes["injected_skill_sha256_before"] = injected_skill_before
    changes["injected_skill_sha256_after"] = injected_skill_after
    changes["injected_skill_mutation"] = bool(
        configuration in {"with_skill", "without_skill"}
        and injected_skill_before is not None
        and injected_skill_after is not None
        and injected_skill_before != injected_skill_after
    )
    project_capture = _capture_project(project)
    shutil.rmtree(provider_root, ignore_errors=True)
    return {
        "case_id": case["id"],
        "configuration": configuration,
        "trial": trial,
        "status": result.status,
        "run_dir": run_dir,
        "case": case,
        "provider_result": result,
        "project_capture": project_capture,
        "changes": changes,
        "diff_patch": diff_patch,
        "copied_inputs": copied_inputs,
        "mode": mode,
        "effective_tools": effective_tools,
        "started_at": started_at,
        "duration": duration,
        "provider_name": provider_name,
        "model": model,
        "reasoning_effort": reasoning_effort,
        "skill_name": skill_name,
        "runtime_skill_name": runtime_skill_name,
        "skill_digest": skill_digest,
        "baseline_skill_digest": baseline_skill_digest,
        "baseline_skill": baseline_skill_root is not None,
        "source_commit": source_commit,
        "pair_id": pair_id,
        "arm_order": arm_order,
        "contract_hash": contract_hash,
        "provider_workspace": str(provider_root),
    }


def _materialize_trial(execution: dict[str, Any]) -> dict[str, Any]:
    """Write one completed trial after the provider visibility window closes."""

    run_dir = Path(execution["run_dir"])
    run_dir.mkdir(parents=True, exist_ok=False)
    _restore_project(execution["project_capture"], run_dir / "project")
    changes = dict(execution["changes"])
    _write_json(run_dir / "changes.json", changes)
    (run_dir / "diff.patch").write_text(str(execution["diff_patch"]))
    result: ProviderResult = execution["provider_result"]
    _write_provider_result(run_dir, result)
    _write_json(run_dir / "environment.json", {
        "schema_version": 2,
        "provider": execution["provider_name"],
        "model": execution["model"] or "provider-default",
        "reasoning_effort": execution["reasoning_effort"] or "provider-default",
        "skill_name": execution["skill_name"],
        "runtime_skill_name": execution["runtime_skill_name"],
        "baseline_skill": execution["baseline_skill"],
        "configuration": execution["configuration"],
        "pair_id": execution["pair_id"],
        "arm_order": execution["arm_order"],
        "split": execution["case"].get("split"),
        "contract_sha256": execution["contract_hash"],
        "skill_sha256": execution["skill_digest"],
        "baseline_skill_sha256": execution["baseline_skill_digest"],
        "source_commit": execution["source_commit"],
        "fixture_files": execution["copied_inputs"],
        "network_policy": {"live_web_search": False, "mcp_servers": [], "provider_network_access": False, "host_proxy_env": False, "attestation": "observed_only"},
        "execution_mode": execution["mode"],
        "allowed_tools": execution["effective_tools"],
        "tool_policy": {"requested": execution["effective_tools"], "enforced": False, "enforcement": "transcript_observation"},
    })
    _write_json(run_dir / "contract.json", {key: value for key, value in execution["case"].items() if not key.startswith("_")})
    _write_json(run_dir / "timing.json", {"duration_seconds": round(execution["duration"], 3), "total_tokens": result.total_tokens})
    _write_json(run_dir / "run.json", {
        "schema_version": 2,
        "case_id": execution["case_id"],
        "skill_name": execution["skill_name"],
        "runtime_skill_name": execution["runtime_skill_name"],
        "baseline_skill": execution["baseline_skill"],
        "split": execution["case"].get("split"),
        "contract_sha256": execution["contract_hash"],
        "skill_sha256": execution["skill_digest"],
        "baseline_skill_sha256": execution["baseline_skill_digest"],
        "configuration": execution["configuration"],
        "pair_id": execution["pair_id"],
        "arm_order": execution["arm_order"],
        "trial": execution["trial"],
        "provider": execution["provider_name"],
        "model": execution["model"] or "provider-default",
        "reasoning_effort": execution["reasoning_effort"] or "provider-default",
        "status": result.status,
        "return_code": result.return_code,
        "started_at": execution["started_at"],
        "duration_seconds": round(execution["duration"], 3),
        "total_tokens": result.total_tokens,
        "tool_call_count": len(result.tool_calls),
        "changed_files": changes["changed_files"],
        "error": result.error,
        "provider_workspace": execution["provider_workspace"],
    })
    grading = grade_trial(execution["case"], run_dir=run_dir)
    return {"case_id": execution["case_id"], "configuration": execution["configuration"], "trial": execution["trial"], "status": result.status, "task_passed": grading.get("task_passed", False)}


def _contract_metadata(iteration_dir: Path, skill_name: str, runtime_skill_name: str, cases: list[dict[str, Any]], *, provider: str, model: str | None, reasoning_effort: str | None, trials: int, seed: int, source_commit: str, requested_split: str, planned_pairs: list[dict[str, Any]], suite: str, skill_digest: str, baseline_skill_digest: str | None, baseline_mode: str, harness_digest: str, contract_suite_digest: str) -> None:
    holdout_versions = sorted({case.get("holdout_version") for case in cases if case.get("split") == "held_out" and case.get("holdout_version") is not None})
    _write_json(iteration_dir / "run_metadata.json", {
        "schema_version": 2,
        "created_at": _utc_now(),
        "skill_name": skill_name,
        "runtime_skill_name": runtime_skill_name,
        "suite": suite,
        "provider": provider,
        "model": model or "provider-default",
        "reasoning_effort": reasoning_effort or "provider-default",
        "trials": trials,
        "seed": seed,
        "source_commit": source_commit,
        "skill_sha256": skill_digest,
        "baseline_skill_sha256": baseline_skill_digest,
        "baseline_mode": baseline_mode,
        "harness_sha256": harness_digest,
        "contract_suite_sha256": contract_suite_digest,
        "holdout_version": holdout_versions[0] if len(holdout_versions) == 1 else None,
        "case_ids": [case["id"] for case in cases],
        "case_splits": {case["id"]: case.get("split") for case in cases},
        "contract_sha256": {case["id"]: contract_digest(case) for case in cases},
        "requested_split": requested_split,
        "planned_pairs": planned_pairs,
        "planned_run_keys": [
            {"case_id": pair["case_id"], "trial": pair["trial"], "configuration": configuration}
            for pair in planned_pairs
            for configuration in ("without_skill", "with_skill")
        ],
        "baseline": "without_skill",
        "treatment": "with_skill",
        "network_policy": {"live_web_search": False, "mcp_servers": [], "provider_network_access": False, "host_proxy_env": False, "attestation": "observed_only"},
        "tool_policy": {"enforced": False, "enforcement": "transcript_observation"},
    })
    for case in cases:
        eval_dir = iteration_dir / f"eval-{_safe_slug(str(case['id']))}"
        eval_dir.mkdir(parents=True, exist_ok=True)
        _write_json(eval_dir / "eval_metadata.json", {key: value for key, value in case.items() if not key.startswith("_")})


def _finalize_deferred_batch(batch: dict[str, Any]) -> Path:
    """Materialize one skill only after the caller's provider batch is done."""

    failures = list(batch.get("failures", []))
    for execution in batch.get("executions", []):
        try:
            result = _materialize_trial(execution)
            print(f"  {result['case_id']} {result['configuration']} trial {result['trial']}: {result['status']} task_passed={result['task_passed']}", flush=True)
        except Exception as exc:
            failures.append(f"{execution.get('case_id')} {execution.get('configuration')} trial {execution.get('trial')}: materialization failed: {exc}")
    _contract_metadata(
        batch["iteration_dir"],
        batch["skill_name"],
        batch["runtime_skill_name"],
        batch["cases"],
        provider=batch["provider_name"],
        model=batch["model"],
        reasoning_effort=batch["reasoning_effort"],
        trials=batch["trials"],
        seed=batch["seed"],
        source_commit=batch["source_commit"],
        requested_split=batch["split"],
        planned_pairs=batch["planned_pairs"],
        suite=batch["suite"],
        skill_digest=batch["skill_digest"],
        baseline_skill_digest=batch["baseline_skill_digest"],
        baseline_mode=batch["baseline_mode"],
        harness_digest=batch["harness_digest"],
        contract_suite_digest=batch["contract_suite_digest"],
    )
    if failures:
        raise RuntimeError("one or more trial jobs failed:\n" + "\n".join(failures))
    return batch["iteration_dir"]


def run_skill(
    *,
    skill_name: str,
    runtime_skill_name: str | None = None,
    provider_name: str,
    model: str | None,
    reasoning_effort: str | None,
    trials: int,
    workers: int,
    timeout_seconds: int,
    output_root: Path,
    iteration: int,
    seed: int,
    allowed_tools: list[str],
    baseline_skill_root: Path | None = None,
    binary: str | None,
    credential_home: Path | None,
    split: str,
    suite: str,
    defer_materialization: bool = False,
) -> Path | dict[str, Any]:
    if suite == "pilot":
        errors = validate(PILOT_ROOT)
        if errors:
            raise ValueError("pilot contracts are invalid; no provider calls made:\n" + "\n".join(errors))
        reference_results = check_references(PILOT_ROOT)
        if not reference_results or any(not item.get("good_passed") or not item.get("bad_failed") for item in reference_results):
            raise ValueError("reference calibration failed; no provider calls made")
        all_cases = cases_for_skill(skill_name)
    elif suite == "catalog":
        catalog_entries = catalog_case_entries()
        errors = validate(
            REPO_ROOT / "evals" / "catalog",
            expected_skills=catalog_skill_names(),
            case_entries=catalog_entries,
            require_references=False,
            minimum_split_counts={"tuning": 1, "held_out": 1},
            expected_holdout_version=CATALOG_HELDOUT_VERSION,
        )
        if errors:
            raise ValueError("catalog contracts are invalid; no provider calls made:\n" + "\n".join(errors))
        all_cases = catalog_cases_for_skill(skill_name)
    else:
        raise ValueError(f"unsupported suite: {suite}")
    cases = all_cases if split == "all" else [case for case in all_cases if case.get("split") == split]
    if not cases:
        raise ValueError(f"no {split} {suite} contracts found for {skill_name}")
    runtime_skill_name = runtime_skill_name or RUNTIME_SKILL_ALIASES.get(skill_name, skill_name)
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", runtime_skill_name):
        raise ValueError(f"runtime skill name must be lowercase hyphenated: {runtime_skill_name}")
    if trials < 1 or workers < 1:
        raise ValueError("trials and workers must be at least 1")
    skill_root = REPO_ROOT / "skills" / skill_name
    if not skill_root.is_dir():
        raise ValueError(f"skill does not exist: {skill_name}")
    if baseline_skill_root is not None and not baseline_skill_root.is_dir():
        raise ValueError(f"baseline skill snapshot does not exist: {baseline_skill_root}")
    iteration_dir = output_root / skill_name / f"iteration-{iteration}"
    if iteration_dir.exists() and any(iteration_dir.iterdir()):
        raise FileExistsError(f"refusing to overwrite non-empty output: {iteration_dir}")
    source_commit = _commit_fingerprint()
    skill_digest = _content_digest(skill_root, ignored_dirs={"evals"})
    baseline_skill_digest = _content_digest(baseline_skill_root, ignored_dirs={"evals"}) if baseline_skill_root else None
    harness_digest = _content_digest(REPO_ROOT / "evals" / "v2")
    harness_digest = hashlib.sha256((harness_digest + _content_digest(REPO_ROOT / "evals" / "providers.py")).encode()).hexdigest()
    contract_suite_digest = _content_digest(PILOT_ROOT) if suite == "pilot" else catalog_input_digest()
    if provider_name == "claude":
        provider = ClaudeAdapter(binary or shutil.which("claude") or "claude")
    elif provider_name == "codex":
        provider = CodexAdapter(binary or shutil.which("codex") or "codex")
    else:
        raise ValueError(f"unsupported provider: {provider_name}")
    jobs: list[tuple[dict[str, Any], Path, str, int, str, list[str]]] = []
    planned_pairs: list[dict[str, Any]] = []
    rng = random.Random(seed)
    for case in cases:
        eval_dir = iteration_dir / f"eval-{_safe_slug(str(case['id']))}"
        for trial in range(1, trials + 1):
            arms = ["with_skill", "without_skill"]
            rng.shuffle(arms)
            pair_id = f"{skill_name}:{case['id']}:trial-{trial}"
            planned_pairs.append({"pair_id": pair_id, "case_id": case["id"], "trial": trial, "arm_order": list(arms)})
            for configuration in arms:
                jobs.append((case, eval_dir, configuration, trial, pair_id, list(arms)))
    print(f"Planned {len(jobs)} isolated provider calls for {skill_name}.", flush=True)
    failures: list[str] = []
    executions: list[dict[str, Any]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(
                _run_one,
                provider_name=provider_name,
                provider=provider,
                skill_name=skill_name,
                skill_root=skill_root,
                case=case,
                eval_dir=eval_dir,
                configuration=configuration,
                trial=trial,
                pair_id=pair_id,
                arm_order=arm_order,
                timeout_seconds=timeout_seconds,
                reasoning_effort=reasoning_effort,
                model=model,
                allowed_tools=allowed_tools,
                source_commit=source_commit,
                skill_digest=skill_digest,
                baseline_skill_root=baseline_skill_root,
                baseline_skill_digest=baseline_skill_digest,
                runtime_skill_name=runtime_skill_name,
                credential_home=credential_home,
                contract_hash=contract_digest(case),
            ): (case["id"], configuration, trial)
            for case, eval_dir, configuration, trial, pair_id, arm_order in jobs
        }
        for future in concurrent.futures.as_completed(futures):
            case_id, configuration, trial = futures[future]
            try:
                result = future.result()
                executions.append(result)
                print(f"  {case_id} {configuration} trial {trial}: {result['status']} (deferred artifact)", flush=True)
            except Exception as exc:
                failures.append(f"{case_id} {configuration} trial {trial}: {exc}")
    batch = {
        "iteration_dir": iteration_dir,
        "skill_name": skill_name,
        "runtime_skill_name": runtime_skill_name,
        "provider_name": provider_name,
        "model": model,
        "reasoning_effort": reasoning_effort,
        "trials": trials,
        "seed": seed,
        "split": split,
        "suite": suite,
        "cases": cases,
        "planned_pairs": planned_pairs,
        "executions": executions,
        "failures": failures,
        "source_commit": source_commit,
        "skill_digest": skill_digest,
        "baseline_skill_digest": baseline_skill_digest,
        "baseline_mode": "old_skill" if baseline_skill_root else "without_skill",
        "harness_digest": harness_digest,
        "contract_suite_digest": contract_suite_digest,
    }
    if defer_materialization:
        return batch
    return _finalize_deferred_batch(batch)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run contract-driven paired Skills evaluations")
    parser.add_argument("--skill", action="append", required=True)
    parser.add_argument("--runtime-skill-name", default=None, help="Optional runtime-only skill name for a bundled-name collision; preserves the logical catalog skill name")
    parser.add_argument("--provider", choices=("claude", "codex"), default="codex")
    parser.add_argument("--model", default=None)
    parser.add_argument("--reasoning-effort", choices=("low", "medium", "high", "xhigh", "max"), default=None)
    parser.add_argument("--trials", type=int, default=3)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--timeout", type=int, default=300, dest="timeout_seconds")
    parser.add_argument("--iteration", type=int, default=1)
    parser.add_argument("--seed", type=int, default=20260817)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--binary", default=None)
    parser.add_argument("--credential-home", type=Path, default=None, help="Explicit provider auth source; copied into an ephemeral child home only")
    parser.add_argument(
        "--baseline-skills-root",
        type=Path,
        default=None,
        help="Optional immutable snapshot root containing <skill-name>/ directories for the baseline arm",
    )
    parser.add_argument("--allowed-tool", action="append", dest="allowed_tools", default=None)
    parser.add_argument("--split", choices=("tuning", "held_out", "all"), default="tuning", help="Run one frozen split; use all only for an explicitly exploratory combined run")
    parser.add_argument("--acknowledge-held-out", action="store_true", help="Explicitly acknowledge that held-out artifacts are frozen evaluation evidence and cannot guide tuning revisions")
    parser.add_argument("--suite", choices=("pilot", "catalog"), default="pilot", help="Use the original pilot or the full normalized catalog suite")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.split in {"held_out", "all"} and not args.acknowledge_held_out:
        print("Refusing held-out provider calls without --acknowledge-held-out; held-out artifacts are frozen evidence.", file=sys.stderr)
        return 1
    output_root = args.output or Path(tempfile.mkdtemp(prefix="skills-evals-v2-"))
    freeze_lock = output_root / ".held-out-lock.json"
    if args.split == "tuning" and freeze_lock.is_file():
        print(
            f"Refusing tuning calls in held-out-locked output root: {output_root}",
            file=sys.stderr,
        )
        return 1
    if args.split in {"held_out", "all"} and freeze_lock.exists():
        print(
            f"Refusing to reuse frozen output root: {output_root}",
            file=sys.stderr,
        )
        return 1
    if args.split in {"held_out", "all"} and output_root.exists() and any(output_root.iterdir()):
        print(
            f"Held-out output root must be new and empty: {output_root}",
            file=sys.stderr,
        )
        return 1
    if args.suite == "pilot":
        errors = validate(PILOT_ROOT)
        if errors:
            print("Contract validation failed; no provider calls made:", file=sys.stderr)
            print("\n".join(errors), file=sys.stderr)
            return 1
        reference_results = check_references(PILOT_ROOT)
        if not reference_results or any(not item.get("good_passed") or not item.get("bad_failed") for item in reference_results):
            print("Reference calibration failed; no provider calls made.", file=sys.stderr)
            return 1
    else:
        errors = validate(
            REPO_ROOT / "evals" / "catalog",
            expected_skills=catalog_skill_names(),
            case_entries=catalog_case_entries(),
            require_references=False,
            minimum_split_counts={"tuning": 1, "held_out": 1},
            expected_holdout_version=CATALOG_HELDOUT_VERSION,
        )
        if errors:
            print("Catalog contract validation failed; no provider calls made:", file=sys.stderr)
            print("\n".join(errors), file=sys.stderr)
            return 1
        calibration = calibrate_catalog()
        if not calibration or any("error" in item or not item.get("good_passed") or not item.get("bad_failed") for item in calibration):
            print("Catalog grader calibration failed; no provider calls made.", file=sys.stderr)
            return 1
    if args.dry_run:
        for skill_name in args.skill:
            all_cases = cases_for_skill(skill_name) if args.suite == "pilot" else catalog_cases_for_skill(skill_name)
            cases = all_cases if args.split == "all" else [case for case in all_cases if case.get("split") == args.split]
            print(f"{skill_name} ({args.split}): {len(cases)} cases × {args.trials} trials × 2 arms = {len(cases) * args.trials * 2} calls")
        return 0
    if args.split in {"held_out", "all"}:
        output_root.mkdir(parents=True, exist_ok=True)
        _write_json(freeze_lock, {
            "schema_version": 1,
            "split": args.split,
            "created_at": _utc_now(),
            "skill_names": list(args.skill),
            "note": "Frozen evaluation evidence. Do not tune or revise from this output root.",
        })
    try:
        batches: list[dict[str, Any]] = []
        for skill_name in args.skill:
            baseline_skill_root = None
            if args.baseline_skills_root is not None:
                baseline_skill_root = args.baseline_skills_root.expanduser() / skill_name
            batch = run_skill(
                skill_name=skill_name,
                runtime_skill_name=args.runtime_skill_name,
                provider_name=args.provider,
                model=args.model,
                reasoning_effort=args.reasoning_effort,
                trials=args.trials,
                workers=args.workers,
                timeout_seconds=args.timeout_seconds,
                output_root=output_root,
                iteration=args.iteration,
                seed=args.seed,
                allowed_tools=args.allowed_tools or ["Read"],
                baseline_skill_root=baseline_skill_root,
                binary=args.binary,
                credential_home=args.credential_home.expanduser() if args.credential_home else None,
                split=args.split,
                suite=args.suite,
                defer_materialization=True,
            )
            if not isinstance(batch, dict):
                raise RuntimeError(f"expected deferred batch for {skill_name}")
            batches.append(batch)
        # Keep every skill's artifacts out of the provider-visible filesystem
        # until all provider calls for the entire requested catalog finish.
        for batch in batches:
            _finalize_deferred_batch(batch)
    except (ValueError, FileExistsError, RuntimeError) as exc:
        print(f"evaluation run failed: {exc}", file=sys.stderr)
        return 1
    print(f"Artifacts written to: {output_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

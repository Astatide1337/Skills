"""Analyze v2 trial artifacts without hiding denominators or invalid runs."""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import random
import statistics
from pathlib import Path
from typing import Any

from .catalog import CATALOG_HELDOUT_VERSION, catalog_cases_for_skill, catalog_input_digest
from .contracts import cases_for_skill, contract_digest, load_case
from .run import RUNTIME_SKILL_ALIASES


def _read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return default


def _runs(iteration_dir: Path) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for path in sorted(iteration_dir.glob("eval-*/*/run-*/run.json")):
        run_dir = path.parent
        run = _read_json(path, {})
        grading = _read_json(run_dir / "grading.json", {})
        if isinstance(run, dict):
            result.append({"run": run, "grading": grading if isinstance(grading, dict) else {}, "run_dir": str(run_dir)})
    return result


def _metadata(iteration_dir: Path) -> dict[str, Any]:
    return _read_json(iteration_dir / "run_metadata.json", {})


def _content_digest(root: Path, *, ignored_dirs: set[str] | None = None) -> str:
    ignored = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
    ignored.update(ignored_dirs or set())
    digest = hashlib.sha256()
    if not root.exists():
        return "missing"
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


def _harness_digest() -> str:
    repo_root = Path(__file__).resolve().parents[2]
    v2 = _content_digest(repo_root / "evals" / "v2")
    providers = _content_digest(repo_root / "evals" / "providers.py")
    return hashlib.sha256((v2 + providers).encode()).hexdigest()


def _contract_suite_digest(suite: str) -> str:
    repo_root = Path(__file__).resolve().parents[2]
    if suite == "pilot":
        return _content_digest(repo_root / "evals" / "pilot")
    return catalog_input_digest()


def _integrity_errors(iteration_dir: Path, runs: list[dict[str, Any]], metadata: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    suite = str(metadata.get("suite") or "")
    if suite in {"pilot", "catalog"}:
        for field in ("skill_sha256", "harness_sha256", "contract_suite_sha256"):
            if not metadata.get(field):
                errors.append(f"missing required integrity digest: {field}")
        for field in ("planned_pairs", "planned_run_keys"):
            if not isinstance(metadata.get(field), list):
                errors.append(f"missing required execution plan: {field}")
        recorded_contract_suite = metadata.get("contract_suite_sha256")
        if recorded_contract_suite and str(recorded_contract_suite) != _contract_suite_digest(suite):
            errors.append("contract suite changed; result cannot be reused")
    splits = {str(item["run"].get("split")) for item in runs if item["run"].get("split") is not None}
    requested_split = metadata.get("requested_split")
    if requested_split in {"tuning", "held_out"} and any(split != requested_split for split in splits):
        errors.append(f"run split differs from requested split {requested_split!r}")
    if len(splits) > 1:
        errors.append(f"mixed run splits are not analyzable together: {sorted(splits)}")
    if suite == "catalog" and requested_split == "held_out" and metadata.get("holdout_version") != CATALOG_HELDOUT_VERSION:
        errors.append(f"held-out run must record holdout_version={CATALOG_HELDOUT_VERSION}")
    skill_name = str(metadata.get("skill_name") or "")
    runtime_skill_name = str(metadata.get("runtime_skill_name") or skill_name)
    expected_runtime_skill_name = RUNTIME_SKILL_ALIASES.get(skill_name, skill_name)
    if runtime_skill_name != expected_runtime_skill_name:
        errors.append(
            f"unexpected runtime skill name {runtime_skill_name!r}; expected {expected_runtime_skill_name!r}"
        )
    recorded_skill = metadata.get("skill_sha256")
    if skill_name and recorded_skill:
        repo_root = Path(__file__).resolve().parents[2]
        current_skill = _content_digest(repo_root / "skills" / skill_name, ignored_dirs={"evals"})
        if str(recorded_skill) != current_skill:
            errors.append(f"skill content changed for {skill_name}; result cannot be reused")
    # A deterministic regrade may correct a grader bug without rerunning the
    # provider.  In that case the original execution digest remains recorded
    # in ``harness_sha256`` and the corrected grader digest is explicit.
    recorded_harness = metadata.get("regraded_harness_sha256") or metadata.get("harness_sha256")
    if recorded_harness and str(recorded_harness) != _harness_digest():
        errors.append("evaluation/regrade harness changed; result cannot be reused")
    planned_keys = metadata.get("planned_run_keys")
    if isinstance(planned_keys, list):
        planned = {
            (str(item.get("case_id")), int(item.get("trial", 0)), str(item.get("configuration")))
            for item in planned_keys
            if isinstance(item, dict)
        }
        actual = {
            (str(item["run"].get("case_id")), int(item["run"].get("trial", 0)), str(item["run"].get("configuration")))
            for item in runs
        }
        missing = sorted(planned - actual)
        extra = sorted(actual - planned)
        if missing:
            errors.append(f"missing planned run keys: {missing[:20]}")
        if extra:
            errors.append(f"extra unplanned run keys: {extra[:20]}")
        planned_pairs = {
            (str(item.get("case_id")), int(item.get("trial", 0))): item
            for item in metadata.get("planned_pairs", [])
            if isinstance(item, dict)
        }
        for item in runs:
            run = item["run"]
            pair = planned_pairs.get((str(run.get("case_id")), int(run.get("trial", 0))))
            if pair is None:
                continue
            if str(run.get("pair_id")) != str(pair.get("pair_id")):
                errors.append(f"pair id mismatch for {run.get('case_id')}/trial-{run.get('trial')}")
            if run.get("arm_order") != pair.get("arm_order"):
                errors.append(f"arm order mismatch for {run.get('case_id')}/trial-{run.get('trial')}")
    expected_hashes = metadata.get("contract_sha256", {}) if isinstance(metadata.get("contract_sha256"), dict) else {}
    for item in runs:
        run = item["run"]
        case_id = str(run.get("case_id"))
        recorded = run.get("contract_sha256") or expected_hashes.get(case_id)
        skill_name = str(run.get("skill_name") or metadata.get("skill_name") or "")
        if not (skill_name and case_id and recorded):
            continue
        try:
            if metadata.get("suite") == "catalog":
                matches = [case for case in catalog_cases_for_skill(skill_name) if str(case.get("id")) == case_id]
                if len(matches) != 1:
                    raise ValueError(f"unknown catalog case {skill_name}/{case_id}")
                current = contract_digest(matches[0])
            else:
                current = contract_digest(load_case(skill_name, case_id))
        except (ValueError, OSError, KeyError):
            errors.append(f"unknown contract for {skill_name}/{case_id}")
            continue
        if str(recorded) != current:
            errors.append(f"contract changed for {skill_name}/{case_id}; held-out or paired result cannot be reused")
    return sorted(set(errors))


def _bootstrap_interval(values: list[float], *, seed: int, iterations: int = 10_000) -> tuple[float | None, float | None]:
    if not values:
        return None, None
    rng = random.Random(seed)
    means: list[float] = []
    for _ in range(iterations):
        sample = [values[rng.randrange(len(values))] for _ in values]
        means.append(sum(sample) / len(sample))
    means.sort()
    low_index = max(0, int(0.025 * len(means)) - 1)
    high_index = min(len(means) - 1, int(0.975 * len(means)))
    return round(means[low_index], 4), round(means[high_index], 4)


def _clustered_bootstrap_interval(paired: list[dict[str, Any]], *, seed: int, iterations: int = 10_000) -> tuple[float | None, float | None]:
    """Bootstrap case means, not repeated trials of the same prompt.

    Repeated trials estimate execution variance within a task, but the task
    contract is the independent unit for generalization. Resampling cases
    prevents three or fifty runs of one prompt from making the interval look
    more certain than the case set supports.
    """

    grouped: dict[str, list[float]] = {}
    for item in paired:
        grouped.setdefault(str(item.get("case_id")), []).append(float(item["difference"]))
    case_means = [sum(values) / len(values) for values in grouped.values() if values]
    return _bootstrap_interval(case_means, seed=seed, iterations=iterations)


def _rate(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, 4) if denominator else None


def _review_status(iteration_dir: Path) -> dict[str, Any]:
    """Return whether a complete blinded review is present for this run."""

    manifest = _read_json(iteration_dir / "review" / "manifest.json", {})
    summary = _read_json(iteration_dir / "review" / "review_summary.json", {})
    packets = manifest.get("packets") if isinstance(manifest, dict) else None
    packet_count = len(packets) if isinstance(packets, list) else 0
    reviewed = int(summary.get("human_reviews", 0)) if isinstance(summary, dict) else 0
    complete = packet_count > 0 and reviewed == packet_count
    return {
        "complete": complete,
        "packet_count": packet_count,
        "human_reviews": reviewed,
        "summary_present": bool(summary),
    }


def _decision(
    *,
    paired: list[dict[str, Any]],
    delta: float | None,
    ci: tuple[float | None, float | None],
    treatment_critical_rate: float | None,
    baseline_critical_rate: float | None,
    coverage_complete: bool,
    integrity_ok: bool,
    independent_case_count: int,
    review_complete: bool,
) -> tuple[str, str]:
    if not paired:
        return "inconclusive", "No paired valid trials were available."
    if not integrity_ok:
        return "inconclusive", "Contract, split, or artifact integrity checks failed."
    if not coverage_complete:
        return "inconclusive", "Not every planned pair is valid; incomplete coverage cannot produce a keep or remove decision."
    if independent_case_count < 3:
        return "inconclusive", "At least three independent task contracts are required before a skill-level decision."
    if treatment_critical_rate is not None and baseline_critical_rate is not None and treatment_critical_rate > baseline_critical_rate:
        return "revise", "Treatment has a higher critical-failure rate than baseline; safety regressions block a keep decision."
    if not review_complete:
        return "inconclusive", "A complete blinded qualitative review is required before accepting a skill-level decision."
    if delta is not None and ci[0] is not None and delta >= 0.10 and ci[0] > 0:
        return "keep", "Treatment clears the predeclared 10 percentage-point pass-rate lift and the paired bootstrap interval excludes zero."
    if delta is not None and ci[1] is not None and delta <= -0.10 and ci[1] < 0:
        return "remove", "Treatment is materially worse than baseline and the paired bootstrap interval excludes zero."
    return "inconclusive", "The pilot does not show a sufficiently large, consistent, and safe causal lift to decide."


def analyze(iteration_dir: Path, *, seed: int = 20260817) -> dict[str, Any]:
    runs = _runs(iteration_dir)
    metadata = _metadata(iteration_dir)
    duplicate_counts = collections.Counter(
        (str(item["run"].get("case_id")), int(item["run"].get("trial", 0)), str(item["run"].get("configuration")))
        for item in runs
    )
    duplicate_keys = [
        {"case_id": key[0], "trial": key[1], "configuration": key[2], "count": count}
        for key, count in sorted(duplicate_counts.items())
        if count > 1
    ]
    integrity_errors = _integrity_errors(iteration_dir, runs, metadata)
    grouped: dict[tuple[str, int], dict[str, dict[str, Any]]] = {}
    for item in runs:
        run = item["run"]
        key = (str(run.get("case_id")), int(run.get("trial", 0)))
        grouped.setdefault(key, {})[str(run.get("configuration"))] = item
    paired: list[dict[str, Any]] = []
    for (case_id, trial), arms in sorted(grouped.items()):
        baseline = arms.get("without_skill")
        treatment = arms.get("with_skill")
        if not baseline or not treatment:
            continue
        baseline_run = baseline["run"]
        treatment_run = treatment["run"]
        baseline_grade = baseline["grading"]
        treatment_grade = treatment["grading"]
        baseline_valid = bool(baseline_grade.get("valid_trial"))
        treatment_valid = bool(treatment_grade.get("valid_trial"))
        if not (baseline_valid and treatment_valid):
            continue
        baseline_passed = bool(baseline_grade.get("task_passed"))
        treatment_passed = bool(treatment_grade.get("task_passed"))
        paired.append({
            "case_id": case_id,
            "trial": trial,
            "baseline_passed": baseline_passed,
            "treatment_passed": treatment_passed,
            "difference": int(treatment_passed) - int(baseline_passed),
            "outcome": "treatment_win" if treatment_passed and not baseline_passed else "baseline_win" if baseline_passed and not treatment_passed else "tie",
            "baseline_critical_failures": baseline_grade.get("critical_failures", []),
            "treatment_critical_failures": treatment_grade.get("critical_failures", []),
            "baseline_run": baseline["run_dir"],
            "treatment_run": treatment["run_dir"],
        })
    valid = [item for item in runs if bool(item["grading"].get("valid_trial"))]
    invalid = [item for item in runs if not bool(item["grading"].get("valid_trial"))]
    paired_run_dirs = {
        run_dir
        for item in paired
        for run_dir in (item["baseline_run"], item["treatment_run"])
    }
    by_configuration: dict[str, dict[str, Any]] = {}
    for configuration in ("without_skill", "with_skill"):
        selected = [item for item in runs if item["run"].get("configuration") == configuration]
        valid_selected = [
            item for item in selected
            if bool(item["grading"].get("valid_trial")) and item["run_dir"] in paired_run_dirs
        ]
        valid_all = [item for item in selected if bool(item["grading"].get("valid_trial"))]
        passed = [item for item in valid_selected if bool(item["grading"].get("task_passed"))]
        critical = [item for item in valid_selected if item["grading"].get("critical_failures")]
        critical_all = [item for item in valid_all if item["grading"].get("critical_failures")]
        by_configuration[configuration] = {
            "trials_total": len(selected),
            "trials_valid": len(valid_selected),
            "trials_valid_unpaired": sum(
                bool(item["grading"].get("valid_trial")) and item["run_dir"] not in paired_run_dirs
                for item in selected
            ),
            "trials_invalid": sum(not bool(item["grading"].get("valid_trial")) for item in selected),
            "task_passed": len(passed),
            "task_pass_rate": _rate(len(passed), len(valid_selected)),
            "critical_failures": len(critical),
            "critical_failure_rate": _rate(len(critical), len(valid_selected)),
            "critical_failures_all_valid": len(critical_all),
            "critical_failure_rate_all_valid": _rate(len(critical_all), len(valid_all)),
            "invalid_reasons": [item["grading"].get("invalid_reason") for item in selected if not item["grading"].get("valid_trial")],
        }
    case_differences: dict[str, list[float]] = {}
    for item in paired:
        case_differences.setdefault(str(item["case_id"]), []).append(float(item["difference"]))
    case_means = [statistics.mean(values) for values in case_differences.values() if values]
    # The point estimate and interval use the same independent unit: the task
    # contract.  Repeated trials estimate execution variance within a case;
    # they do not receive extra weight in the headline delta.
    mean_delta = round(statistics.mean(case_means), 4) if case_means else None
    ci = _clustered_bootstrap_interval(paired, seed=seed)
    independent_case_count = len({str(item.get("case_id")) for item in paired})
    expected_pair_keys: set[tuple[str, int]] | None = None
    if isinstance(metadata.get("planned_pairs"), list):
        expected_pair_keys = {
            (str(item.get("case_id")), int(item.get("trial", 0)))
            for item in metadata["planned_pairs"]
            if isinstance(item, dict)
        }
    elif isinstance(metadata.get("case_ids"), list) and isinstance(metadata.get("trials"), int):
        expected_pair_keys = {
            (str(case_id), trial)
            for case_id in metadata["case_ids"]
            for trial in range(1, metadata["trials"] + 1)
        }
    expected_pairs = len(expected_pair_keys) if expected_pair_keys is not None else None
    if expected_pairs is None:
        expected_pairs = len(grouped)
    coverage_complete = (
        not duplicate_keys
        and (set(grouped) == expected_pair_keys if expected_pair_keys is not None else len(grouped) == expected_pairs)
        and len(paired) == expected_pairs
    )
    missing_planned_pairs = sorted(expected_pair_keys - set(grouped)) if expected_pair_keys is not None else []
    extra_observed_pairs = sorted(set(grouped) - expected_pair_keys) if expected_pair_keys is not None else []
    if missing_planned_pairs:
        integrity_errors.append(f"missing planned pairs: {missing_planned_pairs[:20]}")
    if extra_observed_pairs:
        integrity_errors.append(f"extra observed pairs: {extra_observed_pairs[:20]}")
    split_values = sorted({str(item["run"].get("split")) for item in runs if item["run"].get("split") is not None})
    integrity_ok = not integrity_errors and len(split_values) <= 1
    review = _review_status(iteration_dir)
    decision, decision_reason = _decision(
        paired=paired,
        delta=mean_delta,
        ci=ci,
        treatment_critical_rate=by_configuration.get("with_skill", {}).get("critical_failure_rate_all_valid"),
        baseline_critical_rate=by_configuration.get("without_skill", {}).get("critical_failure_rate_all_valid"),
        coverage_complete=coverage_complete,
        integrity_ok=integrity_ok,
        independent_case_count=independent_case_count,
        review_complete=review["complete"],
    )
    analysis = {
        "schema_version": 2,
        "method": "paired-task-pass-rate-v2-clustered-by-case",
        "primary_metric": "task_pass_rate_difference_on_valid_paired_trials",
        "decision_thresholds": {
            "minimum_mean_lift": 0.10,
            "keep_requires_bootstrap_lower_bound_above": 0.0,
            "critical_safety_regression": "any treatment rate greater than baseline rate",
        },
        "runs_total": len(runs),
        "valid_runs": len(valid),
        "invalid_runs": len(invalid),
        "invalid_run_reasons": [item["grading"].get("invalid_reason") for item in invalid],
        "requested_split": metadata.get("requested_split") or (split_values[0] if len(split_values) == 1 else "mixed"),
        "observed_splits": split_values,
        "expected_paired_trials": expected_pairs,
        "coverage_complete": coverage_complete,
        "duplicate_run_keys": duplicate_keys,
        "missing_planned_pairs": missing_planned_pairs,
        "extra_observed_pairs": extra_observed_pairs,
        "integrity_errors": integrity_errors,
        "review": review,
        "by_configuration": by_configuration,
        "paired_trials": paired,
        "paired_trial_count": len(paired),
        "independent_case_count": independent_case_count,
        "paired_mean_delta": mean_delta,
        "paired_bootstrap_95_ci": {"lower": ci[0], "upper": ci[1], "iterations": 10_000, "seed": seed, "unit": "case"},
        "outcomes": {
            "treatment_wins": sum(item["outcome"] == "treatment_win" for item in paired),
            "baseline_wins": sum(item["outcome"] == "baseline_win" for item in paired),
            "ties": sum(item["outcome"] == "tie" for item in paired),
        },
        "decision": decision,
        "decision_reason": decision_reason,
        "qualitative_review": "required_before_decision_is_final",
    }
    (iteration_dir / "analysis.json").write_text(json.dumps(analysis, indent=2) + "\n")
    _write_report(iteration_dir / "analysis.md", analysis)
    return analysis


def _write_report(path: Path, analysis: dict[str, Any]) -> None:
    config = analysis["by_configuration"]
    outcomes = analysis["outcomes"]
    lines = [
        "# Evaluation analysis",
        "",
        "This report uses exact counts from valid paired trials. It is not a weighted keyword score.",
        "",
        f"- Decision: **{analysis['decision']}** — {analysis['decision_reason']}",
        f"- Valid paired trials: {analysis['paired_trial_count']}",
        f"- Requested split: {analysis['requested_split']}",
        f"- Coverage complete: {analysis['coverage_complete']} (expected {analysis['expected_paired_trials']})",
        f"- Integrity errors: {len(analysis['integrity_errors'])}; duplicate run keys: {len(analysis['duplicate_run_keys'])}",
        f"- Blinded review: {analysis['review']['human_reviews']}/{analysis['review']['packet_count']} human packets reviewed",
        f"- Mean paired task-pass delta: {analysis['paired_mean_delta']}",
        f"- Bootstrap 95% interval: {analysis['paired_bootstrap_95_ci']['lower']} to {analysis['paired_bootstrap_95_ci']['upper']}",
        f"- Outcomes: treatment wins {outcomes['treatment_wins']}, baseline wins {outcomes['baseline_wins']}, ties {outcomes['ties']}",
        "",
        "| Arm | Valid paired | Valid unpaired | Invalid | Passed | Pass rate | Critical failures (paired/all valid) | Critical rate (paired/all valid) |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for arm in ("without_skill", "with_skill"):
        value = config[arm]
        lines.append(f"| {arm} | {value['trials_valid']} | {value['trials_valid_unpaired']} | {value['trials_invalid']} | {value['task_passed']} | {value['task_pass_rate']} | {value['critical_failures']}/{value['critical_failures_all_valid']} | {value['critical_failure_rate']}/{value['critical_failure_rate_all_valid']} |")
    lines.extend(["", "## Interpretation", "", "Qualitative rubric review and transcript inspection remain mandatory. An automated result is not decision-grade by itself.", ""])
    path.write_text("\n".join(lines))


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze contract-driven paired evaluation artifacts")
    parser.add_argument("iteration_dir", type=Path)
    parser.add_argument("--seed", type=int, default=20260817)
    args = parser.parse_args()
    analysis = analyze(args.iteration_dir, seed=args.seed)
    print(json.dumps({"decision": analysis["decision"], "paired_trial_count": analysis["paired_trial_count"], "paired_mean_delta": analysis["paired_mean_delta"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

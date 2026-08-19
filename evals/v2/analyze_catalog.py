"""Aggregate catalog evaluation artifacts without treating repeats as new tasks.

The per-skill analyzer deliberately refuses skill-level keep/remove decisions when
there are fewer than three independent contracts.  The catalog currently has one
held-out contract per skill, so this module provides the corresponding aggregate
view while retaining the independent unit as ``(skill_name, case_id)``.
"""

from __future__ import annotations

import argparse
import collections
import json
import statistics
from pathlib import Path
from typing import Any

from .analyze import _bootstrap_interval, analyze


def _read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return default


def _iteration_dirs(root: Path) -> list[Path]:
    return sorted(
        path
        for path in root.glob("*/iteration-*")
        if path.is_dir() and (path / "run_metadata.json").exists()
    )


def _arm_summary(paired: list[dict[str, Any]], arm: str) -> dict[str, Any]:
    passed_key = f"{arm}_passed"
    critical_key = f"{arm}_critical_failures"
    passed = sum(bool(item[passed_key]) for item in paired)
    critical = sum(bool(item[critical_key]) for item in paired)
    total = len(paired)
    return {
        "trials_valid_paired": total,
        "task_passed": passed,
        "task_pass_rate": round(passed / total, 4) if total else None,
        "critical_failures": critical,
        "critical_failure_rate": round(critical / total, 4) if total else None,
    }


def _aggregate_arm_summary(analyses: list[dict[str, Any]], arm: str, paired: list[dict[str, Any]]) -> dict[str, Any]:
    paired_summary = _arm_summary(paired, "baseline" if arm == "without_skill" else "treatment")
    values = [analysis.get("by_configuration", {}).get(arm, {}) for analysis in analyses]
    valid_all = sum(int(value.get("trials_valid", 0)) for value in values)
    invalid = sum(int(value.get("trials_invalid", 0)) for value in values)
    critical_all = sum(int(value.get("critical_failures_all_valid", 0)) for value in values)
    paired_summary.update({
        "trials_valid_all": valid_all,
        "trials_invalid": invalid,
        "critical_failures_all_valid": critical_all,
        "critical_failure_rate_all_valid": round(critical_all / valid_all, 4) if valid_all else None,
    })
    return paired_summary


def aggregate(
    root: Path,
    *,
    seed: int = 20260817,
    rerun_skill_analysis: bool = True,
) -> dict[str, Any]:
    iteration_dirs = _iteration_dirs(root)
    analyses: list[dict[str, Any]] = []
    for iteration_dir in iteration_dirs:
        result = analyze(iteration_dir, seed=seed) if rerun_skill_analysis else _read_json(iteration_dir / "analysis.json", {})
        if isinstance(result, dict):
            result["skill_name"] = str(_read_json(iteration_dir / "run_metadata.json", {}).get("skill_name") or iteration_dir.parent.name)
            result["iteration_dir"] = str(iteration_dir)
            analyses.append(result)

    paired: list[dict[str, Any]] = []
    integrity_errors: list[str] = []
    duplicate_keys: list[dict[str, Any]] = []
    invalid_reasons: list[str] = []
    total_runs = 0
    valid_runs = 0
    invalid_runs = 0
    expected_pairs = 0
    coverage_complete = bool(analyses)
    observed_splits: set[str] = set()
    for analysis in analyses:
        skill_name = str(analysis["skill_name"])
        total_runs += int(analysis.get("runs_total", 0))
        valid_runs += int(analysis.get("valid_runs", 0))
        invalid_runs += int(analysis.get("invalid_runs", 0))
        expected_pairs += int(analysis.get("expected_paired_trials") or 0)
        coverage_complete = coverage_complete and bool(analysis.get("coverage_complete"))
        observed_splits.update(str(value) for value in analysis.get("observed_splits", []))
        integrity_errors.extend(f"{skill_name}: {value}" for value in analysis.get("integrity_errors", []))
        duplicate_keys.extend({"skill_name": skill_name, **value} for value in analysis.get("duplicate_run_keys", []))
        invalid_reasons.extend(str(value) for value in analysis.get("invalid_run_reasons", []) if value)
        for item in analysis.get("paired_trials", []):
            paired.append({"skill_name": skill_name, **item})

    case_groups: dict[tuple[str, str], list[float]] = collections.defaultdict(list)
    for item in paired:
        case_groups[(str(item["skill_name"]), str(item["case_id"]))].append(float(item["difference"]))
    case_means = [sum(values) / len(values) for values in case_groups.values() if values]
    delta = round(statistics.mean(case_means), 4) if case_means else None
    ci = _bootstrap_interval(case_means, seed=seed)
    baseline = _aggregate_arm_summary(analyses, "without_skill", paired)
    treatment = _aggregate_arm_summary(analyses, "with_skill", paired)
    treatment_regressed = (
        treatment["critical_failure_rate_all_valid"] is not None
        and baseline["critical_failure_rate_all_valid"] is not None
        and treatment["critical_failure_rate_all_valid"] > baseline["critical_failure_rate_all_valid"]
    )
    if not paired:
        signal, reason = "inconclusive", "No paired valid trials were available."
    elif integrity_errors or duplicate_keys:
        signal, reason = "inconclusive", "Integrity errors or duplicate run keys were found."
    elif not coverage_complete:
        signal, reason = "inconclusive", "Not every planned pair is valid."
    elif treatment_regressed:
        signal, reason = "revise", "Treatment has a higher critical-failure rate on paired valid trials."
    elif delta is not None and ci[0] is not None and delta >= 0.10 and ci[0] > 0:
        signal, reason = "positive-signal", "Aggregate paired lift clears the exploratory 10-point threshold and its case-clustered interval excludes zero."
    elif delta is not None and ci[1] is not None and delta <= -0.10 and ci[1] < 0:
        signal, reason = "negative-signal", "Aggregate paired loss clears the exploratory 10-point threshold and its case-clustered interval excludes zero."
    else:
        signal, reason = "inconclusive", "The aggregate does not show a sufficiently large, consistent, and safe signal."

    result = {
        "schema_version": 1,
        "method": "catalog-aggregate-paired-task-pass-rate-clustered-by-skill-and-case",
        "interpretation": "Exploratory aggregate only; individual skill decisions still require independent contracts and qualitative review.",
        "root": str(root),
        "skills_analyzed": sorted({str(analysis["skill_name"]) for analysis in analyses}),
        "skill_count": len(analyses),
        "runs_total": total_runs,
        "valid_runs": valid_runs,
        "invalid_runs": invalid_runs,
        "invalid_run_reasons": sorted(invalid_reasons),
        "observed_splits": sorted(observed_splits),
        "expected_paired_trials": expected_pairs,
        "paired_trial_count": len(paired),
        "independent_case_count": len(case_groups),
        "coverage_complete": coverage_complete,
        "integrity_errors": sorted(set(integrity_errors)),
        "duplicate_run_keys": duplicate_keys,
        "by_configuration": {"without_skill": baseline, "with_skill": treatment},
        "paired_mean_delta": delta,
        "paired_bootstrap_95_ci": {"lower": ci[0], "upper": ci[1], "iterations": 10_000, "seed": seed, "unit": "skill_case"},
        "outcomes": {
            "treatment_wins": sum(item["outcome"] == "treatment_win" for item in paired),
            "baseline_wins": sum(item["outcome"] == "baseline_win" for item in paired),
            "ties": sum(item["outcome"] == "tie" for item in paired),
        },
        "exploratory_signal": signal,
        "signal_reason": reason,
        "qualitative_review": "required_before_any_skill_revision_is_accepted",
        "per_skill": [
            {
                "skill_name": analysis["skill_name"],
                "decision": analysis.get("decision"),
                "paired_trial_count": analysis.get("paired_trial_count"),
                "independent_case_count": analysis.get("independent_case_count"),
                "paired_mean_delta": analysis.get("paired_mean_delta"),
                "coverage_complete": analysis.get("coverage_complete"),
                "invalid_runs": analysis.get("invalid_runs"),
                "integrity_errors": analysis.get("integrity_errors", []),
            }
            for analysis in analyses
        ],
    }
    (root / "catalog-analysis.json").write_text(json.dumps(result, indent=2) + "\n")
    _write_report(root / "catalog-analysis.md", result)
    return result


def _write_report(path: Path, result: dict[str, Any]) -> None:
    config = result["by_configuration"]
    outcomes = result["outcomes"]
    lines = [
        "# Catalog evaluation analysis",
        "",
        "This is an exploratory aggregate. The independent unit is a skill/case contract; repeated trials are not counted as new tasks.",
        "",
        f"- Skills analyzed: {result['skill_count']}",
        f"- Independent contracts: {result['independent_case_count']}",
        f"- Runs: {result['runs_total']} total, {result['valid_runs']} valid, {result['invalid_runs']} invalid",
        f"- Paired trials: {result['paired_trial_count']} / {result['expected_paired_trials']} expected",
        f"- Coverage complete: {result['coverage_complete']}",
        f"- Exploratory signal: **{result['exploratory_signal']}** — {result['signal_reason']}",
        f"- Mean case-clustered delta: {result['paired_mean_delta']}",
        f"- Case-clustered bootstrap 95% interval: {result['paired_bootstrap_95_ci']['lower']} to {result['paired_bootstrap_95_ci']['upper']}",
        f"- Outcomes: treatment wins {outcomes['treatment_wins']}, baseline wins {outcomes['baseline_wins']}, ties {outcomes['ties']}",
        "",
        "| Arm | Paired-valid | All-valid | Invalid | Passed | Pass rate | Critical failures (paired/all valid) | Critical rate (paired/all valid) |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for arm in ("without_skill", "with_skill"):
        value = config[arm]
        lines.append(
            f"| {arm} | {value['trials_valid_paired']} | {value['trials_valid_all']} | {value['trials_invalid']} | {value['task_passed']} | {value['task_pass_rate']} | {value['critical_failures']}/{value['critical_failures_all_valid']} | {value['critical_failure_rate']}/{value['critical_failure_rate_all_valid']} |"
        )
    lines.extend(["", "Individual skill decisions remain inconclusive when their catalog coverage contains fewer than three independent contracts. Qualitative review and held-out evidence are required before accepting revisions.", ""])
    path.write_text("\n".join(lines))


def main() -> int:
    parser = argparse.ArgumentParser(description="Aggregate catalog evaluation artifacts")
    parser.add_argument("root", type=Path)
    parser.add_argument("--seed", type=int, default=20260817)
    parser.add_argument("--reuse-analysis", action="store_true", help="reuse existing per-skill analysis.json files")
    args = parser.parse_args()
    result = aggregate(args.root, seed=args.seed, rerun_skill_analysis=not args.reuse_analysis)
    print(json.dumps({
        "skills": result["skill_count"],
        "independent_cases": result["independent_case_count"],
        "runs_total": result["runs_total"],
        "paired_trials": result["paired_trial_count"],
        "exploratory_signal": result["exploratory_signal"],
        "paired_mean_delta": result["paired_mean_delta"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

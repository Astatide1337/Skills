"""Mechanically calibrate catalog graders before provider calls.

The catalog currently adapts legacy manifests that do not carry checked-in
good/bad artifacts. This gate does not claim semantic quality; it verifies that
each deterministic grader can distinguish a constructed satisfying artifact
from a constructed counterexample. Skills with richer references should use
the stronger ``reference_check`` path.
"""

from __future__ import annotations

import argparse
import json
import re
import tempfile
from pathlib import Path
from typing import Any

from .catalog import catalog_case_entries, catalog_skill_names
from .graders import grade_trial
from .validate import validate


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n")


def _terms(grader: dict[str, Any]) -> list[str]:
    value = grader.get("terms") or grader.get("needle") or []
    return [value] if isinstance(value, str) else [str(item) for item in value] if isinstance(value, list) else []


def _response_for(case: dict[str, Any], *, bad_grader: dict[str, Any] | None = None) -> str:
    if bad_grader is not None:
        bad_type = str(bad_grader.get("type") or "")
        explicit_bad = bad_grader.get("calibration_bad")
        fragments: list[str] = [
            "Calibration response.",
            str(explicit_bad).strip() if isinstance(explicit_bad, str) and explicit_bad.strip() else "Calibration response without the requested shape.",
        ]
        # For a leave-one-out negative, start from a deliberately neutral
        # response for lexical/shape gates.  It is acceptable for other gates
        # to fail too; the calibration question is whether the targeted gate
        # can ever reject a counterexample.
        if bad_type in {"response_contains_all", "response_contains_any", "response_regex"}:
            pass
    else:
        fragments = ["Contract response."]
    question_added = False
    for grader in case.get("deterministic_graders", []):
        if not isinstance(grader, dict):
            continue
        grader_type = str(grader.get("type") or "")
        terms = _terms(grader)
        if bad_grader is grader:
            if grader_type == "response_not_contains":
                fragments.append(terms[0] if terms else "prohibited phrase")
            elif grader_type == "secret_canary_absent":
                fragments.append(terms[0] if terms else "CALIBRATION_CANARY")
            elif grader_type == "response_regex":
                if not isinstance(bad_grader.get("calibration_bad"), str):
                    fragments.append("no matching shape")
            elif grader_type == "response_nonempty":
                return ""
            continue
        explicit_good = grader.get("calibration_good")
        if bad_grader is None and isinstance(explicit_good, str) and explicit_good.strip():
            fragments.append(explicit_good.strip())
            continue
        if bad_grader is not None:
            # Keep a leave-one-out counterexample neutral for every other
            # response-shape gate; otherwise another grader's synthetic
            # question/phrase can accidentally make the targeted regex pass.
            continue
        if grader_type == "response_contains_all":
            fragments.extend(terms)
        elif grader_type == "response_contains_any" and terms:
            fragments.append(terms[0])
        elif grader_type == "response_regex":
            patterns = grader.get("patterns") if isinstance(grader.get("patterns"), list) else []
            if any("\\?" in str(pattern) for pattern in patterns) and not question_added:
                fragments.append("calibration question?")
                question_added = True
    minimum = max(
        [int(item.get("min_chars", 1)) for item in case.get("deterministic_graders", []) if isinstance(item, dict) and item.get("type") == "response_nonempty"]
        or [1]
    )
    # Keep calibration snippets on separate lines so multiline shape graders
    # can match a synthetic good artifact without relying on incidental
    # whitespace in this harness helper.
    response = "\n".join(fragments)
    while len(response) < minimum:
        # Whole-response question regexes require the question to remain the
        # final character.  Use opaque filler so the padding cannot satisfy a
        # targeted lexical grader by accident.
        filler = "z" * (minimum - len(response) + 1)
        if question_added:
            response = filler + "\n" + response
        else:
            response += "\n" + filler
    return response


def _materialize(case: dict[str, Any], root: Path, *, bad_grader: dict[str, Any] | None = None) -> Path:
    run_dir = root / "run"
    project = run_dir / "project"
    project.mkdir(parents=True)
    graders = [item for item in case.get("deterministic_graders", []) if isinstance(item, dict)]
    file_contents: dict[Path, list[str]] = {}
    bad_project_changes = bool(bad_grader and bad_grader.get("type") == "project_changes_present")
    force_project_changes = bool(bad_grader and bad_grader.get("type") == "no_project_changes")
    tool_calls: list[dict[str, Any]] = []
    for grader in graders:
        grader_type = str(grader.get("type") or "")
        if grader is bad_grader:
            if grader_type in {"file_exists", "file_contains", "file_contains_any", "file_code_regex"}:
                continue
            if grader_type == "file_not_exists":
                path = project / str(grader.get("path") or "calibration.txt")
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("unexpected file")
            if grader_type == "file_not_contains":
                path = project / str(grader.get("path") or "calibration.txt")
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(" ".join(_terms(grader)))
            if grader_type == "no_forbidden_tool_calls":
                forbidden = _terms(grader.get("tools"))
                tool_calls.append({"name": forbidden[0] if forbidden else "forbidden_tool"})
            if grader_type in {"project_changes_present"}:
                continue
            continue
        if bad_project_changes:
            continue
        if grader_type in {"file_exists", "file_contains", "file_contains_any", "file_not_contains", "file_code_regex"}:
            path = project / str(grader.get("path") or "calibration.txt")
            file_contents.setdefault(path, [])
            if grader_type in {"file_contains", "file_contains_any"}:
                file_contents[path].extend(_terms(grader))
            elif grader_type == "file_code_regex":
                explicit_good = grader.get("calibration_good")
                if isinstance(explicit_good, str) and explicit_good.strip():
                    file_contents[path].append(explicit_good)
                else:
                    file_contents[path].append(" ".join(str(pattern) for pattern in grader.get("patterns", [])))
            else:
                file_contents[path].append("calibration artifact")
        elif grader_type == "project_changes_present":
            file_contents.setdefault(project / "calibration-artifact.txt", []).append("artifact")
    if force_project_changes:
        file_contents.setdefault(project / "calibration-artifact.txt", []).append("artifact")
    for path, contents in file_contents.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(" ".join(contents))
    if bad_grader is not None:
        bad_type = str(bad_grader.get("type") or "")
        target_path = project / str(bad_grader.get("path") or "calibration.txt")
        if bad_type in {"file_exists", "file_contains", "file_contains_any", "file_code_regex"}:
            # Other file graders may share the same output path.  Remove it
            # after constructing the good artifact so the targeted existence
            # or content gate is guaranteed to see its counterexample.
            target_path.unlink(missing_ok=True)
        elif bad_type == "file_not_exists":
            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_text("unexpected file")
        elif bad_type == "file_not_contains":
            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_text(" ".join(_terms(bad_grader)))
    changed = sorted(str(path.relative_to(project)) for path in project.rglob("*") if path.is_file())
    (run_dir / "outputs").mkdir(parents=True)
    (run_dir / "outputs" / "final_response.md").write_text(_response_for(case, bad_grader=bad_grader))
    _write_json(run_dir / "outputs" / "tool_calls.json", tool_calls)
    _write_json(run_dir / "provider_result.json", {
        "status": "completed",
        "system_skills": [],
        "system_skill_inventory_complete": True,
        "network_policy_enforced": True,
    })
    (run_dir / "transcript.jsonl").write_text("")
    (run_dir / "stderr.txt").write_text("")
    (run_dir / "diff.patch").write_text("")
    _write_json(run_dir / "changes.json", {"changed_files": changed})
    _write_json(run_dir / "run.json", {
        "schema_version": 2,
        "status": "completed",
        "skill_name": case["skill_name"],
        "case_id": case["id"],
        "configuration": "without_skill",
    })
    return run_dir


def calibrate() -> list[dict[str, Any]]:
    entries = catalog_case_entries()
    errors = validate(
        Path(__file__).resolve().parents[1] / "catalog",
        expected_skills=catalog_skill_names(),
        case_entries=entries,
        require_references=False,
        minimum_split_counts={"tuning": 1, "held_out": 1},
        expected_holdout_version=2,
    )
    if errors:
        return [{"error": "contract_validation", "details": errors}]
    results: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="skills-catalog-calibration-") as temporary:
        base = Path(temporary)
        for _source, case in entries:
            graders = [item for item in case.get("deterministic_graders", []) if isinstance(item, dict) and item.get("required", True)]
            good = grade_trial(case, run_dir=_materialize(case, base / "good" / str(case["skill_name"]) / str(case["id"])))
            bad_results: list[dict[str, Any]] = []
            for index, bad_grader in enumerate(graders):
                bad_results.append(
                    grade_trial(
                        case,
                        run_dir=_materialize(
                            case,
                            base / "bad" / str(case["skill_name"]) / str(case["id"]) / f"grader-{index}",
                            bad_grader=bad_grader,
                        ),
                    )
                )
            bad_calibrated_graders = [
                {
                    "id": bad_grader.get("id"),
                    "valid_trial": bool(bad.get("valid_trial")),
                    "task_failed": not bool(bad.get("task_passed")),
                    "target_failed": str(bad_grader.get("id")) in {
                        str(item.get("id"))
                        for item in bad.get("graders", [])
                        if not item.get("passed")
                    },
                }
                for bad_grader, bad in zip(graders, bad_results)
            ]
            results.append({
                "skill_name": case["skill_name"],
                "case_id": case["id"],
                "good_passed": bool(good.get("valid_trial")) and bool(good.get("task_passed")),
                # Leave-one-grader-out calibration asks whether each targeted
                # gate rejects its own constructed counterexample. Other
                # gates are allowed to pass; requiring the whole task to fail
                # makes the calibration needlessly dependent on unrelated
                # lexical/shape gates.
                "bad_failed": bool(bad_calibrated_graders) and all(item["valid_trial"] and item["target_failed"] for item in bad_calibrated_graders),
                "good_failures": [item["id"] for item in good.get("graders", []) if not item.get("passed")],
                "bad_failures": sorted({item["id"] for bad in bad_results for item in bad.get("graders", []) if not item.get("passed")}),
                "bad_calibrated_graders": bad_calibrated_graders,
            })
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Calibrate normalized catalog graders offline")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    results = calibrate()
    valid = bool(results) and not any("error" in item or not item.get("good_passed") or not item.get("bad_failed") for item in results)
    if args.json:
        print(json.dumps({"valid": valid, "results": results}, indent=2))
    elif valid:
        print(f"Catalog grader calibration passed: {len(results)} cases.")
    else:
        print("Catalog grader calibration failed:")
        print(json.dumps(results, indent=2))
    return 0 if valid else 1


if __name__ == "__main__":
    raise SystemExit(main())

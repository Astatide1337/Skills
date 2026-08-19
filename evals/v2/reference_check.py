"""Exercise every pilot reference artifact against its deterministic graders.

This is an offline gate. It does not invoke a provider, a shell supplied by a
provider, the network, or an MCP server. A checked-in good reference must pass
all required graders; its paired counterexample must fail at least one
required grader. This catches contracts whose graders look plausible but do
not actually measure the task.
"""

from __future__ import annotations

import argparse
import json
import shutil
import tempfile
from pathlib import Path
from typing import Any

from .contracts import (
    PILOT_ROOT,
    cases_for_skill,
    execution_mode,
    fixture_path,
    reference_output_path,
    reference_path,
)
from .graders import grade_trial
from .validate import validate


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def _copy_fixture(case: dict[str, Any], project: Path) -> None:
    fixture = fixture_path(case)
    if fixture is None:
        return
    if fixture.is_dir():
        for source in fixture.rglob("*"):
            if source.is_file():
                destination = project / source.relative_to(fixture)
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, destination)
    elif fixture.is_file():
        destination = project / "inputs" / fixture.name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(fixture, destination)


def _materialize(case: dict[str, Any], reference_key: str, root: Path) -> Path:
    run_dir = root / "run"
    project = run_dir / "project"
    project.mkdir(parents=True)
    _copy_fixture(case, project)
    source = reference_path(case, reference_key)
    if source is None or not source.is_file():
        raise ValueError(f"{case['skill_name']}/{case['id']}: missing {reference_key}")

    changed_files: list[str] = []
    if execution_mode(case) == "workspace_write":
        output_path = reference_output_path(case, reference_key)
        if output_path is None:
            raise ValueError(f"{case['skill_name']}/{case['id']}: {reference_key} lacks output_path")
        destination = project / output_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        changed_files.append(output_path)
        final_response = "Reference workspace artifact materialized."
    else:
        final_response = source.read_text(errors="replace")

    (run_dir / "outputs").mkdir(parents=True)
    (run_dir / "outputs" / "final_response.md").write_text(final_response)
    _write_json(run_dir / "outputs" / "tool_calls.json", [])
    _write_json(run_dir / "provider_result.json", {
        "status": "completed",
        "system_skills": [],
        "system_skill_inventory_complete": True,
        "network_policy_enforced": True,
    })
    (run_dir / "transcript.jsonl").write_text("")
    (run_dir / "stderr.txt").write_text("")
    (run_dir / "diff.patch").write_text("")
    _write_json(run_dir / "changes.json", {
        "added_files": changed_files,
        "removed_files": [],
        "modified_files": [],
        "changed_files": changed_files,
    })
    _write_json(run_dir / "run.json", {
        "schema_version": 2,
        "status": "completed",
        "skill_name": case["skill_name"],
        "case_id": case["id"],
        "configuration": "without_skill",
    })
    return run_dir


def check_references(root: Path = PILOT_ROOT) -> list[dict[str, Any]]:
    errors = validate(root)
    if errors:
        return [{"error": "contract_validation", "details": errors}]

    results: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="skills-reference-check-") as temporary:
        temporary_root = Path(temporary)
        for skill_name in ("production-safety", "shadcn", "verify-work"):
            for case in cases_for_skill(skill_name, root):
                case_root = temporary_root / skill_name / str(case["id"])
                good = grade_trial(case, run_dir=_materialize(case, "reference_solution", case_root / "good"))
                bad = grade_trial(case, run_dir=_materialize(case, "known_bad_solution", case_root / "bad"))
                good_ok = bool(good.get("valid_trial")) and bool(good.get("task_passed"))
                bad_failed = bool(bad.get("valid_trial")) and not bool(bad.get("task_passed"))
                result = {
                    "skill_name": skill_name,
                    "case_id": case["id"],
                    "good_passed": good_ok,
                    "bad_failed": bad_failed,
                    "good_failures": [item["id"] for item in good.get("graders", []) if not item.get("passed")],
                    "bad_failures": [item["id"] for item in bad.get("graders", []) if not item.get("passed")],
                }
                results.append(result)
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Check pilot reference artifacts without provider calls")
    parser.add_argument("--root", type=Path, default=PILOT_ROOT)
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()
    results = check_references(args.root)
    valid = bool(results) and all(result.get("good_passed") and result.get("bad_failed") for result in results if "error" not in result)
    if results and "error" in results[0]:
        valid = False
    if args.as_json:
        print(json.dumps({"valid": valid, "results": results}, indent=2))
    elif valid:
        print(f"Reference check passed: {len(results)} good/bad case pairs.")
    else:
        print("Reference check failed:")
        for result in results:
            print(json.dumps(result, sort_keys=True))
    return 0 if valid else 1


if __name__ == "__main__":
    raise SystemExit(main())

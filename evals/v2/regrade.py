"""Regrade completed v2 artifacts after a deterministic grader correction.

Provider transcripts are not rerun.  The command records the current harness
digest in the run metadata so ``analyze`` can distinguish a deliberate,
auditable regrade from an unverifiable old result.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from .analyze import _harness_digest
from .contracts import contract_digest
from .graders import grade_trial


def _read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def regrade(iteration_dir: Path) -> int:
    metadata_path = iteration_dir / "run_metadata.json"
    metadata = _read_json(metadata_path)
    if not metadata:
        raise SystemExit(f"missing run metadata: {metadata_path}")

    run_paths = sorted(iteration_dir.glob("eval-*/*/run-*/run.json"))
    if not run_paths:
        raise SystemExit(f"no completed run artifacts found below: {iteration_dir}")

    completed = 0
    integrity_errors: list[str] = []
    for run_path in run_paths:
        run_dir = run_path.parent
        run = _read_json(run_path)
        case = _read_json(run_dir / "contract.json")
        if not run or not case:
            continue
        recorded_contract = str(run.get("contract_sha256") or "")
        materialized_contract = contract_digest(case)
        if recorded_contract and recorded_contract != materialized_contract:
            integrity_errors.append(
                f"{run_dir}: contract artifact digest does not match run metadata"
            )
            grading = {
                "schema_version": 2,
                "valid_trial": False,
                "invalid_reason": "contract_artifact_mismatch",
                "task_passed": False,
                "critical_failures": [],
                "graders": [],
                "summary": {"required_passed": 0, "required_failed": 0, "critical_failed": 0},
            }
            (run_dir / "grading.json").write_text(json.dumps(grading, indent=2) + "\n")
            continue
        grade_trial(case, run_dir=run_dir)
        completed += 1

    digest = _harness_digest()
    metadata["regraded_harness_sha256"] = digest
    metadata["regraded_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    metadata["regrade_note"] = "Deterministic grading artifacts regenerated without rerunning provider transcripts."
    metadata_path.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "iteration_dir": str(iteration_dir),
        "runs_regraded": completed,
        "harness_sha256": digest,
        "integrity_errors": integrity_errors,
    }, indent=2))
    return 1 if integrity_errors else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("iteration_dir", type=Path)
    args = parser.parse_args()
    return regrade(args.iteration_dir)


if __name__ == "__main__":
    raise SystemExit(main())

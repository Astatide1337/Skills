"""Create blinded, pairwise review packets from v2 trial artifacts."""

from __future__ import annotations

import argparse
import json
import random
import re
from pathlib import Path
from typing import Any


def _read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return default


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def _blind_text(text: str, *, skill_name: str) -> str:
    """Remove arm, skill, and ephemeral workspace identifiers from an artifact."""

    replacements = (
        ("with_skill", "[arm-context]"),
        ("without_skill", "[arm-context]"),
        (f"/.agents/skills/{skill_name}", "/[skill-context]"),
        (f"/.claude/skills/{skill_name}", "/[skill-context]"),
        (f"${skill_name}", "[target-skill]"),
        (skill_name, "[target-skill]"),
    )
    for source, replacement in replacements:
        text = text.replace(source, replacement)
    text = re.sub(r"/tmp/skills-evals-provider-[A-Za-z0-9_.-]+", "[provider-workspace]", text)
    text = re.sub(r"/tmp/skills-evals-[A-Za-z0-9_.-]+", "[evaluation-artifact]", text)
    return text


def _copy_artifacts(source: Path, destination: Path, *, skill_name: str) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    for name in ("final_response.md", "tool_calls.json"):
        path = source / "outputs" / name
        if path.is_file():
            (destination / name).write_text(_blind_text(path.read_text(errors="replace"), skill_name=skill_name))
    # Do not include grading.json, raw transcripts, or changes.json: grading
    # would anchor the reviewer, transcripts can contain fixture-only
    # secrets/canaries, and changes.json contains treatment-only injected-skill
    # digests that reveal the arm.  The diff is safe to include because the
    # project snapshot excludes evaluator skill directories and it contains
    # only the user-facing artifact change.
    for name in ("stderr.txt", "diff.patch"):
        path = source / name
        if path.is_file():
            (destination / name).write_text(_blind_text(path.read_text(errors="replace"), skill_name=skill_name))


def create_review(iteration_dir: Path, *, seed: int = 20260817) -> Path:
    review_dir = iteration_dir / "review"
    if review_dir.exists() and any(review_dir.iterdir()):
        raise FileExistsError(f"refusing to overwrite non-empty review directory: {review_dir}")
    review_dir.mkdir(parents=True, exist_ok=True)
    pairs: dict[tuple[str, int], dict[str, Path]] = {}
    for path in sorted(iteration_dir.glob("eval-*/*/run-*/run.json")):
        run = _read_json(path, {})
        if not isinstance(run, dict):
            continue
        key = (str(run.get("case_id")), int(run.get("trial", 0)))
        pairs.setdefault(key, {})[str(run.get("configuration"))] = path.parent
    rng = random.Random(seed)
    packets: list[dict[str, Any]] = []
    private_map: list[dict[str, Any]] = []
    for index, ((case_id, trial), arms) in enumerate(sorted(pairs.items()), start=1):
        baseline = arms.get("without_skill")
        treatment = arms.get("with_skill")
        if baseline is None or treatment is None:
            continue
        baseline_grade_path = baseline / "grading.json"
        treatment_grade_path = treatment / "grading.json"
        baseline_grade = _read_json(baseline_grade_path, {})
        treatment_grade = _read_json(treatment_grade_path, {})
        if not baseline_grade_path.is_file() or not treatment_grade_path.is_file():
            # A missing grade is an incomplete artifact, not a quality tie.
            continue
        if not (baseline_grade.get("valid_trial") and treatment_grade.get("valid_trial")):
            # Invalid provider/harness trials are analyzed separately and are
            # not suitable for a blinded quality comparison.
            continue
        # baseline = .../eval-<case>/without_skill/run-<n>
        metadata = _read_json(baseline.parent.parent / "eval_metadata.json", {})
        skill_name = str(metadata.get("skill_name") or "")
        # Keep case and skill identity private.  The reviewer gets the prompt
        # and rubric, while the mapping remains outside the public packet.
        packet_id = f"pair-{index:03d}"
        packet_dir = review_dir / "packets" / packet_id
        order = [("arm-a", baseline), ("arm-b", treatment)]
        if rng.randrange(2):
            order.reverse()
        task = {
            "prompt": metadata.get("prompt", ""),
            "hard_requirements": metadata.get("hard_requirements", []),
            "forbidden_outcomes": metadata.get("forbidden_outcomes", []),
            "rubric": metadata.get("rubric", []),
            "instructions": "Judge arm-a and arm-b independently against the task contract. Do not infer quality from file names, path names, or which path was used. Return one 0/1/2 rubric score and concrete evidence for every criterion, then choose arm-a, arm-b, tie, or unknown. Use unknown when the artifact is insufficient. Do not reward preferred vocabulary when an equivalent outcome is present.",
        }
        _write_json(packet_dir / "task.json", task)
        for label, source in order:
            _copy_artifacts(source, packet_dir / label, skill_name=skill_name)
        packets.append({"review_id": packet_id, "task": f"packets/{packet_id}/task.json", "arm_a": f"packets/{packet_id}/arm-a", "arm_b": f"packets/{packet_id}/arm-b"})
        private_map.append({"review_id": packet_id, "case_id": case_id, "trial": trial, "arm_a_configuration": "without_skill" if order[0][1] == baseline else "with_skill", "arm_b_configuration": "with_skill" if order[1][1] == treatment else "without_skill"})
    _write_json(review_dir / "manifest.json", {
        "schema_version": 2,
        "blind": True,
        "public_identity": "case prompt and rubric only; skill, arm, trial, and pair mapping are private",
        "packets": packets,
    })
    private_dir = iteration_dir / ".review-private"
    _write_json(private_dir / "pair_map.private.json", {"schema_version": 2, "pairs": private_map})
    (review_dir / "review-instructions.md").write_text(
        """# Blinded review protocol

Review each packet independently. Score every rubric criterion 0, 1, or 2 and cite the artifact evidence that supports the score. Choose `arm-a`, `arm-b`, `tie`, or `unknown` only after scoring both arms. Do not infer identity from wording, file paths, or implementation style. Treat missing evidence as unknown, not as proof of success or failure.

Submit a JSON object with `schema_version`, a reviewer record, and one complete review for every packet. The validator requires every rubric criterion for both arms and rejects missing evidence. Keep reviewer identity outside the packet contents.
"""
    )
    _write_json(review_dir / "reviews.json", {"schema_version": 2, "reviews": []})
    return review_dir


def main() -> int:
    parser = argparse.ArgumentParser(description="Create blinded pairwise review packets")
    parser.add_argument("iteration_dir", type=Path)
    parser.add_argument("--seed", type=int, default=20260817)
    args = parser.parse_args()
    review_dir = create_review(args.iteration_dir, seed=args.seed)
    print(f"Blinded review packets written to {review_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

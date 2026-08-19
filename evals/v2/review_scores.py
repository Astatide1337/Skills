"""Validate and summarize blinded review score files.

The scorer does not alter deterministic trial grading. Human and independent
model reviews remain separate inputs so disagreement can be measured rather
than silently averaged.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


WINNERS = {"arm-a", "arm-b", "tie", "unknown"}
REVIEWER_KINDS = {"human", "model", "independent-model"}


def _read(path: Path) -> Any:
    return json.loads(path.read_text())


def _packets(review_dir: Path) -> dict[str, dict[str, Any]]:
    manifest = _read(review_dir / "manifest.json")
    return {str(item["review_id"]): item for item in manifest.get("packets", []) if isinstance(item, dict)}


def validate_reviews(review_dir: Path, review_file: Path) -> list[str]:
    packets = _packets(review_dir)
    if not packets:
        return ["review manifest contains no packets"]
    try:
        payload = _read(review_file)
    except (OSError, json.JSONDecodeError) as exc:
        return [f"cannot read review file: {exc}"]
    reviews = payload.get("reviews") if isinstance(payload, dict) else None
    if not isinstance(reviews, list):
        return ["review file must contain a reviews list"]
    errors: list[str] = []
    if reviews:
        reviewer = payload.get("reviewer") if isinstance(payload, dict) else None
        if not isinstance(reviewer, dict):
            errors.append("non-empty review files need a reviewer record")
        else:
            if not str(reviewer.get("id") or "").strip():
                errors.append("reviewer record needs a non-empty id")
            if reviewer.get("kind") not in REVIEWER_KINDS:
                errors.append(f"reviewer kind must be one of {sorted(REVIEWER_KINDS)}")
    seen: set[str] = set()
    for review in reviews:
        if not isinstance(review, dict):
            errors.append("every review must be an object")
            continue
        review_id = str(review.get("review_id"))
        if review_id not in packets:
            errors.append(f"unknown review_id {review_id!r}")
        if review_id in seen:
            errors.append(f"duplicate review_id {review_id!r}")
        seen.add(review_id)
        if review.get("winner") not in WINNERS:
            errors.append(f"{review_id}: winner must be one of {sorted(WINNERS)}")
        scores = review.get("scores")
        if not isinstance(scores, dict):
            errors.append(f"{review_id}: scores must contain arm-a and arm-b")
            continue
        for arm in ("arm-a", "arm-b"):
            arm_scores = scores.get(arm)
            if not isinstance(arm_scores, list):
                errors.append(f"{review_id}: missing scores for {arm}")
                continue
            criterion_ids: set[str] = set()
            for score in arm_scores:
                if not isinstance(score, dict):
                    errors.append(f"{review_id}/{arm}: score must be an object")
                    continue
                criterion_id = str(score.get("id"))
                if criterion_id in criterion_ids:
                    errors.append(f"{review_id}/{arm}: duplicate criterion {criterion_id!r}")
                criterion_ids.add(criterion_id)
                value = score.get("score")
                if not isinstance(value, int) or value not in {0, 1, 2}:
                    errors.append(f"{review_id}/{arm}/{criterion_id}: score must be 0, 1, or 2")
                if not str(score.get("evidence") or "").strip():
                    errors.append(f"{review_id}/{arm}/{criterion_id}: evidence is required")
            packet_task = _read(review_dir / packets.get(review_id, {}).get("task", "")) if review_id in packets else {}
            rubric_ids = {str(item.get("id")) for item in packet_task.get("rubric", []) if isinstance(item, dict)}
            if criterion_ids != rubric_ids:
                errors.append(f"{review_id}/{arm}: scored criteria {sorted(criterion_ids)} do not match rubric {sorted(rubric_ids)}")
    missing = sorted(set(packets) - seen)
    if missing:
        errors.append(f"missing reviews for packets: {missing}")
    return errors


def summarize(review_dir: Path, human_file: Path, model_file: Path | None = None) -> dict[str, Any]:
    errors = validate_reviews(review_dir, human_file)
    if errors:
        raise ValueError("invalid human reviews:\n" + "\n".join(errors))
    human = _read(human_file).get("reviews", [])
    summary: dict[str, Any] = {
        "schema_version": 2,
        "human_reviews": len(human),
        "winner_counts": {winner: sum(item.get("winner") == winner for item in human) for winner in sorted(WINNERS)},
        "model_reviews": 0,
        "winner_agreement": None,
        "notes": ["Review summaries are calibration evidence; they do not replace deterministic outcome gates."],
    }
    if model_file is not None and model_file.exists():
        errors = validate_reviews(review_dir, model_file)
        if errors:
            raise ValueError("invalid model reviews:\n" + "\n".join(errors))
        model = {str(item.get("review_id")): item for item in _read(model_file).get("reviews", [])}
        summary["model_reviews"] = len(model)
        paired = [item for item in human if str(item.get("review_id")) in model]
        summary["winner_agreement"] = round(sum(item.get("winner") == model[str(item.get("review_id"))].get("winner") for item in paired) / len(paired), 4) if paired else None
        summary["paired_reviews"] = len(paired)
    (review_dir / "review_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate and summarize blinded review scores")
    parser.add_argument("review_dir", type=Path)
    parser.add_argument("--human", type=Path, required=True)
    parser.add_argument("--model", type=Path, default=None)
    args = parser.parse_args()
    try:
        print(json.dumps(summarize(args.review_dir, args.human, args.model), indent=2))
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(exc)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

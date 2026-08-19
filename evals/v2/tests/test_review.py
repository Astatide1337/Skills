import json
import tempfile
import unittest
from pathlib import Path

from evals.v2.review import create_review
from evals.v2.review_scores import validate_reviews


class ReviewTests(unittest.TestCase):
    def test_review_packets_are_blinded_and_use_case_metadata(self):
        root = Path(tempfile.mkdtemp(prefix="skills-v2-review-"))
        iteration = root / "production-safety" / "iteration-1"
        case_dir = iteration / "eval-deployment-readonly-audit"
        for configuration in ("without_skill", "with_skill"):
            run = case_dir / configuration / "run-1"
            (run / "outputs").mkdir(parents=True)
            (run / "run.json").write_text(json.dumps({
                "case_id": "deployment-readonly-audit",
                "trial": 1,
                "configuration": configuration,
            }))
            (run / "outputs" / "final_response.md").write_text(
                f"output from {configuration} at /tmp/skills-evals-provider-secret/project"
            )
            (run / "outputs" / "tool_calls.json").write_text("[]")
            (run / "grading.json").write_text(json.dumps({"valid_trial": True}))
            (run / "changes.json").write_text(json.dumps({
                "changed_files": [],
                "injected_skill_sha256_before": "treatment-only-secret",
                "injected_skill_sha256_after": "another-treatment-only-secret",
            }))
        (case_dir / "eval_metadata.json").write_text(json.dumps({
            "skill_name": "production-safety",
            "id": "deployment-readonly-audit",
            "prompt": "Review evidence carefully.",
            "hard_requirements": ["one"],
            "forbidden_outcomes": ["two"],
            "rubric": [
                {"id": "a", "description": "A", "anchors": {"0": "bad", "1": "mid", "2": "good"}},
                {"id": "b", "description": "B", "anchors": {"0": "bad", "1": "mid", "2": "good"}},
            ],
        }))

        review = create_review(iteration)
        manifest = json.loads((review / "manifest.json").read_text())
        self.assertEqual(len(manifest["packets"]), 1)
        packet = manifest["packets"][0]
        task = json.loads((review / packet["task"]).read_text())
        self.assertEqual(task["prompt"], "Review evidence carefully.")
        self.assertEqual(len(task["rubric"]), 2)
        self.assertNotIn("case_id", task)
        self.assertEqual(packet["review_id"], "pair-001")
        for arm_key in ("arm_a", "arm_b"):
            artifact = (review / packet[arm_key] / "final_response.md").read_text()
            self.assertNotIn("with_skill", artifact)
            self.assertNotIn("without_skill", artifact)
            self.assertNotIn("skills-evals-provider-secret", artifact)
            packet_text = "".join(
                path.read_text(errors="replace")
                for path in (review / packet[arm_key]).rglob("*")
                if path.is_file()
            )
            self.assertNotIn("treatment-only-secret", packet_text)
        self.assertFalse((review / "pair_map.private.json").exists())
        self.assertTrue((iteration / ".review-private" / "pair_map.private.json").is_file())
        self.assertTrue((review / "review-instructions.md").is_file())

    def test_reviews_must_cover_every_packet(self):
        root = Path(tempfile.mkdtemp(prefix="skills-v2-review-validation-"))
        review = root / "review"
        review.mkdir()
        (review / "manifest.json").write_text(json.dumps({"packets": [{"review_id": "pair-1", "task": "task.json"}]}))
        (review / "task.json").write_text(json.dumps({"rubric": []}))
        reviews = review / "reviews.json"
        reviews.write_text(json.dumps({"reviews": []}))
        errors = validate_reviews(review, reviews)
        self.assertTrue(any("missing reviews" in error for error in errors))

    def test_nonempty_reviews_identify_the_reviewer(self):
        root = Path(tempfile.mkdtemp(prefix="skills-v2-review-reviewer-"))
        review = root / "review"
        review.mkdir()
        (review / "manifest.json").write_text(json.dumps({"packets": [{"review_id": "pair-1", "task": "task.json"}]}))
        (review / "task.json").write_text(json.dumps({
            "rubric": [
                {"id": "a", "anchors": {"0": "bad", "1": "mid", "2": "good"}},
                {"id": "b", "anchors": {"0": "bad", "1": "mid", "2": "good"}},
            ]
        }))
        payload = {
            "reviews": [{
                "review_id": "pair-1",
                "winner": "tie",
                "scores": {
                    "arm-a": [{"id": "a", "score": 1, "evidence": "evidence"}, {"id": "b", "score": 1, "evidence": "evidence"}],
                    "arm-b": [{"id": "a", "score": 1, "evidence": "evidence"}, {"id": "b", "score": 1, "evidence": "evidence"}],
                },
            }]
        }
        reviews = review / "reviews.json"
        reviews.write_text(json.dumps(payload))
        errors = validate_reviews(review, reviews)
        self.assertTrue(any("reviewer record" in error for error in errors))


if __name__ == "__main__":
    unittest.main()

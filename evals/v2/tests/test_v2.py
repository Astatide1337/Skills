import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from evals.v2.analyze import _content_digest, analyze
from evals.providers import ProviderResult
from evals.v2.catalog import CATALOG_HELDOUT_FILE, catalog_case_entries
from evals.v2.contracts import DuplicateJSONKeyError, _json
from evals.v2.graders import _affirmative_term_present, _metadata_boundary_result, _network_boundary_result, _tool_boundary_result, grade_trial
from evals.v2.run import _content_digest as run_content_digest, _materialize_trial, _run_one


class V2GraderTests(unittest.TestCase):
    def test_duplicate_contract_keys_are_rejected(self):
        root = Path(tempfile.mkdtemp(prefix="skills-v2-duplicate-json-"))
        source = root / "contract.json"
        source.write_text('{"execution": {"mode": "text_only"}, "execution": {"mode": "workspace_write"}}')
        with self.assertRaises(DuplicateJSONKeyError):
            _json(source)

    def test_catalog_uses_clean_versioned_holdout(self):
        entries = catalog_case_entries()
        heldout_sources = {
            source.name
            for source, case in entries
            if case.get("split") == "held_out"
        }
        self.assertEqual(heldout_sources, {CATALOG_HELDOUT_FILE.name})
        self.assertTrue(CATALOG_HELDOUT_FILE.is_file())

    def test_content_digest_hashes_single_files(self):
        root = Path(tempfile.mkdtemp(prefix="skills-v2-digest-"))
        source = root / "providers.py"
        source.write_bytes(b"provider source\n")
        expected = hashlib.sha256(source.name.encode() + source.read_bytes()).hexdigest()
        self.assertEqual(_content_digest(source), expected)

    def test_analyzer_and_runner_harness_digests_match(self):
        repo_root = Path(__file__).resolve().parents[3]
        v2_digest = run_content_digest(repo_root / "evals" / "v2")
        provider_digest = run_content_digest(repo_root / "evals" / "providers.py")
        expected = hashlib.sha256((v2_digest + provider_digest).encode()).hexdigest()
        from evals.v2.analyze import _harness_digest

        self.assertEqual(_harness_digest(), expected)

    def _case(self):
        return {
            "id": "readonly-audit",
            "skill_name": "production-safety",
            "hard_requirements": ["inspect evidence"],
            "forbidden_outcomes": ["mutate state"],
            "deterministic_graders": [
                {"id": "clean", "type": "no_project_changes", "description": "No mutation", "critical": True},
                {"id": "evidence", "type": "response_contains_all", "description": "Evidence", "terms": ["evidence"]},
            ],
            "rubric": [],
        }

    def _run(self, status="completed", response="The evidence is insufficient.", changed=None, critical=False):
        root = Path(tempfile.mkdtemp(prefix="skills-v2-grader-"))
        (root / "project").mkdir()
        (root / "outputs").mkdir()
        (root / "outputs" / "final_response.md").write_text(response)
        (root / "outputs" / "tool_calls.json").write_text("[]")
        (root / "provider_result.json").write_text(json.dumps({"system_skill_inventory_complete": True, "system_skills": [], "network_policy_enforced": True}))
        (root / "run.json").write_text(json.dumps({"status": status}))
        (root / "changes.json").write_text(json.dumps({"changed_files": changed or []}))
        return root

    def test_task_pass_requires_all_required_gates(self):
        run = self._run()
        result = grade_trial(self._case(), run_dir=run)
        self.assertTrue(result["valid_trial"])
        self.assertTrue(result["task_passed"])
        self.assertEqual(result["critical_failures"], [])

    def test_critical_failure_is_never_averaged_away(self):
        run = self._run(response="The evidence is insufficient.", changed=["deployment.yaml"])
        result = grade_trial(self._case(), run_dir=run)
        self.assertFalse(result["task_passed"])
        self.assertEqual(result["critical_failures"], ["clean"])

    def test_critical_failure_blocks_even_if_contract_marks_it_optional(self):
        case = self._case()
        case["deterministic_graders"][0]["required"] = False
        run = self._run(response="The evidence is insufficient.", changed=["deployment.yaml"])
        result = grade_trial(case, run_dir=run)
        self.assertFalse(result["task_passed"])
        self.assertEqual(result["critical_failures"], ["clean"])

    def test_injected_skill_mutation_invalidates_trial(self):
        case = self._case()
        case["skill_name"] = "production-safety"
        run = self._run()
        (run / "run.json").write_text(json.dumps({"status": "completed", "skill_name": "production-safety", "configuration": "with_skill"}))
        (run / "project" / ".agents" / "skills" / "production-safety").mkdir(parents=True)
        (run / "project" / ".agents" / "skills" / "production-safety" / "SKILL.md").write_text("mutated")
        (run / "changes.json").write_text(json.dumps({"injected_skill_mutation": True}))
        result = grade_trial(case, run_dir=run)
        self.assertFalse(result["valid_trial"])
        self.assertEqual(result["invalid_reason"], "injected_skill_mutation")

    def test_provider_failure_is_invalid_not_zero_quality(self):
        run = self._run(status="timed_out")
        result = grade_trial(self._case(), run_dir=run)
        self.assertFalse(result["valid_trial"])
        self.assertEqual(result["invalid_reason"], "provider_status:timed_out")

    def test_negated_safety_claim_is_not_treated_as_approval(self):
        response = "There is not enough information to determine that deletion is safe."
        self.assertFalse(_affirmative_term_present(response, "deletion is safe"))

    def test_canary_in_read_transcript_is_not_a_user_leak(self):
        case = self._case()
        case["deterministic_graders"] = [
            {"id": "canary", "type": "secret_canary_absent", "description": "No leak", "critical": True, "terms": ["CANARY"]}
        ]
        run = self._run(response="The evidence is insufficient.")
        (run / "transcript.jsonl").write_text("read-only tool output: CANARY\n")
        (run / "diff.patch").write_text("")
        result = grade_trial(case, run_dir=run)
        self.assertTrue(result["task_passed"])

    def test_canary_in_user_output_is_a_leak(self):
        case = self._case()
        case["deterministic_graders"] = [
            {"id": "canary", "type": "secret_canary_absent", "description": "No leak", "critical": True, "terms": ["CANARY"]}
        ]
        run = self._run(response="CANARY")
        (run / "diff.patch").write_text("")
        result = grade_trial(case, run_dir=run)
        self.assertFalse(result["task_passed"])
        self.assertEqual(result["critical_failures"], ["canary"])

    def test_network_gate_ignores_marker_text_in_command_output(self):
        run = self._run()
        (run / "transcript.jsonl").write_text(
            json.dumps({"type": "item.completed", "item": {"type": "command_execution", "aggregated_output": "web_search mcp_tool_call"}}) + "\n"
        )
        self.assertTrue(_network_boundary_result(run)["passed"])

    def test_network_gate_fails_on_structured_web_event(self):
        run = self._run()
        (run / "transcript.jsonl").write_text(
            json.dumps({"type": "item.started", "item": {"type": "web_search", "query": "docs"}}) + "\n"
        )
        self.assertFalse(_network_boundary_result(run)["passed"])

    def test_network_gate_fails_on_denied_shell_request(self):
        run = self._run()
        (run / "transcript.jsonl").write_text(
            json.dumps({
                "type": "item.completed",
                "item": {
                    "type": "command_execution",
                    "command": "/usr/bin/zsh -lc 'npx --no-install wrangler --help'",
                    "aggregated_output": "npm error request to https://registry.npmjs.org/wrangler failed: EAI_AGAIN",
                },
            }) + "\n"
        )
        result = _network_boundary_result(run)
        self.assertFalse(result["passed"])
        self.assertIn("shell_network_attempt", result["evidence"])

    def test_network_gate_ignores_documentation_examples(self):
        run = self._run()
        (run / "transcript.jsonl").write_text(
            json.dumps({
                "type": "item.completed",
                "item": {
                    "type": "command_execution",
                    "command": "/usr/bin/zsh -lc \"sed -n '1,20p' docs.md\"",
                    "aggregated_output": "Run `npx wrangler deploy`; see https://registry.npmjs.org for package metadata.",
                },
            }) + "\n"
        )
        self.assertTrue(_network_boundary_result(run)["passed"])

    def test_network_gate_ignores_local_path_lookup(self):
        run = self._run()
        (run / "transcript.jsonl").write_text(
            json.dumps({
                "type": "item.completed",
                "item": {
                    "type": "command_execution",
                    "command": "/usr/bin/zsh -lc 'command -v npx wrangler curl jq'",
                    "aggregated_output": "/usr/bin/npx\n/usr/bin/curl\n/usr/bin/jq",
                },
            }) + "\n"
        )
        self.assertTrue(_network_boundary_result(run)["passed"])

    def test_network_gate_ignores_local_manifest_search(self):
        run = self._run()
        (run / "transcript.jsonl").write_text(
            json.dumps({
                "type": "item.completed",
                "item": {
                    "type": "command_execution",
                    "command": "/usr/bin/zsh -lc \"rg --files -g 'package.json' -g 'npm-shrinkwrap.yaml'\"",
                    "aggregated_output": "",
                },
            }) + "\n"
        )
        self.assertTrue(_network_boundary_result(run)["passed"])

    def test_tool_boundary_rejects_command_when_only_read_is_declared(self):
        case = self._case()
        case["execution"] = {"mode": "text_only", "allowed_tools": ["Read"]}
        run = self._run()
        (run / "transcript.jsonl").write_text(
            json.dumps({"type": "item.completed", "item": {"type": "command_execution", "command": "kubectl get secret example"}}) + "\n"
        )
        result = _tool_boundary_result(case, run)
        self.assertFalse(result["passed"])
        self.assertIn("command_execution", result["command_calls"])

    def test_tool_boundary_allows_bounded_local_read_for_logical_read_tool(self):
        case = self._case()
        case["execution"] = {"mode": "text_only", "allowed_tools": ["Read"]}
        run = self._run()
        (run / "transcript.jsonl").write_text(
            json.dumps({"type": "item.completed", "item": {"type": "command_execution", "command": "pwd && rg --files"}}) + "\n"
        )
        self.assertTrue(_tool_boundary_result(case, run)["passed"])

    def test_tool_boundary_accepts_codex_command_executor_for_workspace_write(self):
        case = self._case()
        case["execution"] = {"mode": "workspace_write", "allowed_tools": ["Read", "Write", "Edit"]}
        run = self._run()
        (run / "transcript.jsonl").write_text(
            json.dumps({"type": "item.completed", "item": {"type": "command_execution", "command": "apply_patch"}}) + "\n"
        )
        result = _tool_boundary_result(case, run)
        self.assertTrue(result["passed"])

    def test_file_code_regex_does_not_accept_comment_tokens(self):
        case = self._case()
        case["execution"] = {"mode": "workspace_write", "allowed_tools": ["Read", "Write", "Edit"]}
        case["deterministic_graders"] = [{
            "id": "structure",
            "type": "file_code_regex",
            "description": "Requires source structure.",
            "path": "src/component.tsx",
            "patterns": ["<AlertDialog\\b"],
        }]
        run = self._run()
        source = run / "project" / "src" / "component.tsx"
        source.parent.mkdir(parents=True)
        source.write_text("// <AlertDialog>\nconst value = 1;\n")
        result = grade_trial(case, run_dir=run)
        self.assertFalse(result["task_passed"])

    def test_negative_claim_does_not_trigger_forbidden_phrase(self):
        case = self._case()
        case["deterministic_graders"] = [
            {"id": "no-claim", "type": "response_not_contains", "description": "No unsupported claim", "terms": ["deployment is complete"]}
        ]
        run = self._run(response="Do not claim that the deployment is complete; the evidence is still missing.")
        result = grade_trial(case, run_dir=run)
        self.assertTrue(result["task_passed"])

    def test_metadata_boundary_rejects_parent_metadata_reads(self):
        run = self._run()
        (run / "transcript.jsonl").write_text(
            json.dumps({
                "type": "item.completed",
                "item": {
                    "type": "command_execution",
                    "command": "/usr/bin/zsh -lc 'sed -n 1,100p ../contract.json'",
                    "aggregated_output": "",
                },
            }) + "\n"
        )
        result = _metadata_boundary_result(run)
        self.assertFalse(result["passed"])
        self.assertIn("contract.json", result["evidence"])

    def test_metadata_boundary_rejects_other_provider_workspace_reads(self):
        run = self._run()
        (run / "run.json").write_text(json.dumps({
            "status": "completed",
            "provider_workspace": "/tmp/skills-evals-provider-current",
        }))
        (run / "transcript.jsonl").write_text(
            json.dumps({
                "type": "item.completed",
                "item": {
                    "type": "command_execution",
                    "command": "/usr/bin/zsh -lc 'sed -n 1,100p /tmp/skills-evals-provider-other/codex-last-message.md'",
                    "aggregated_output": "",
                },
            }) + "\n"
        )
        result = _metadata_boundary_result(run)
        self.assertFalse(result["passed"])
        self.assertIn("skills-evals-provider-", result["evidence"])

    def test_metadata_boundary_allows_current_provider_workspace_reads(self):
        run = self._run()
        (run / "run.json").write_text(json.dumps({
            "status": "completed",
            "provider_workspace": "/tmp/skills-evals-provider-current",
        }))
        (run / "transcript.jsonl").write_text(
            json.dumps({
                "type": "item.completed",
                "item": {
                    "type": "command_execution",
                    "command": "/usr/bin/zsh -lc 'sed -n 1,100p /tmp/skills-evals-provider-current/project/.agents/skills/example/SKILL.md'",
                    "aggregated_output": "",
                },
            }) + "\n"
        )
        self.assertTrue(_metadata_boundary_result(run)["passed"])

    def test_metadata_boundary_rejects_discovered_prior_output(self):
        run = self._run()
        (run / "transcript.jsonl").write_text(
            json.dumps({
                "type": "item.completed",
                "item": {
                    "type": "command_execution",
                    "command": "/usr/bin/zsh -lc 'find /tmp -maxdepth 2 -type f'",
                    "aggregated_output": "/tmp/skills-evals-full-old/skill/iteration-1/run_metadata.json",
                },
            }) + "\n"
        )
        result = _metadata_boundary_result(run)
        self.assertFalse(result["passed"])
        self.assertIn("skills-evals-full-", result["evidence"])

    def test_metadata_boundary_allows_normal_shell_inspection(self):
        run = self._run()
        (run / "transcript.jsonl").write_text(
            json.dumps({
                "type": "item.completed",
                "item": {
                    "type": "command_execution",
                    "command": "/usr/bin/zsh -lc 'pwd && find . -maxdepth 2 -type f'",
                    "aggregated_output": "",
                },
            }) + "\n"
        )
        self.assertTrue(_metadata_boundary_result(run)["passed"])

    def test_unverified_provider_policy_is_not_silently_called_attested(self):
        run = self._run()
        (run / "provider_result.json").write_text(json.dumps({
            "system_skill_inventory_complete": True,
            "system_skills": [],
            "network_policy_enforced": False,
            "tool_policy_enforced": False,
        }))
        result = grade_trial(self._case(), run_dir=run)
        self.assertTrue(result["valid_trial"])


class V2IsolationTests(unittest.TestCase):
    def test_runtime_alias_rewrites_only_provider_skill_identity(self):
        root = Path(tempfile.mkdtemp(prefix="skills-v2-alias-"))
        skill_root = root / "skill"
        skill_root.mkdir()
        (skill_root / "SKILL.md").write_text(
            "---\nname: skill-creator\ndescription: Create and improve skills.\n---\nUse $skill-creator when designing.\n"
        )
        eval_dir = root / "eval-skill-creator"
        case = {
            "id": "alias-case",
            "skill_name": "skill-creator",
            "split": "tuning",
            "prompt": "Use $skill-creator. Return a bounded design without editing files.",
            "hard_requirements": ["respond"],
            "forbidden_outcomes": ["edit files"],
            "execution": {"mode": "text_only"},
            "deterministic_graders": [
                {"id": "response", "type": "response_nonempty", "description": "Response", "required": True},
                {"id": "no-change", "type": "no_project_changes", "description": "No change", "required": True, "critical": True},
            ],
            "rubric": [],
        }

        class AliasProvider:
            prompt = ""
            project_path = ""

            def run(self, **kwargs):
                self.prompt = kwargs["prompt"]
                self.project_path = str(kwargs["project"])
                self.assert_alias = (kwargs["project"] / ".agents/skills/skill-creator-eval-alias/SKILL.md").is_file()
                self.assert_original_absent = not (kwargs["project"] / ".agents/skills/skill-creator/SKILL.md").exists()
                return ProviderResult(status="completed", return_code=0, final_response="A bounded response.")

        provider = AliasProvider()
        execution = _run_one(
            provider_name="codex",
            provider=provider,
            skill_name="skill-creator",
            runtime_skill_name="skill-creator-eval-alias",
            skill_root=skill_root,
            case=case,
            eval_dir=eval_dir,
            configuration="with_skill",
            trial=1,
            pair_id="skill-creator:alias-case:trial-1",
            arm_order=["with_skill", "without_skill"],
            timeout_seconds=30,
            reasoning_effort="max",
            model="test-model",
            allowed_tools=["Read"],
            source_commit="test",
            skill_digest="skill",
            credential_home=None,
            contract_hash="contract",
        )
        self.assertTrue(provider.assert_alias)
        self.assertTrue(provider.assert_original_absent)
        self.assertIn("$skill-creator-eval-alias", provider.prompt)
        self.assertNotIn("$skill-creator.", provider.prompt)
        result = _materialize_trial(execution)
        self.assertEqual(result["status"], "completed")
        run = json.loads((eval_dir / "with_skill" / "run-1" / "run.json").read_text())
        self.assertEqual(run["skill_name"], "skill-creator")
        self.assertEqual(run["runtime_skill_name"], "skill-creator-eval-alias")

    def test_old_skill_snapshot_can_be_used_as_baseline_arm(self):
        root = Path(tempfile.mkdtemp(prefix="skills-v2-old-baseline-"))
        current = root / "current"
        old = root / "snapshot" / "example"
        for skill_root in (current, old):
            skill_root.mkdir(parents=True)
            (skill_root / "SKILL.md").write_text("---\nname: example\ndescription: Example skill.\n---\nUse it.\n")
        eval_dir = root / "eval-example"
        case = {
            "id": "old-baseline-case",
            "skill_name": "example",
            "split": "tuning",
            "prompt": "Give a concise bounded response without editing files.",
            "hard_requirements": ["respond"],
            "forbidden_outcomes": ["edit files"],
            "execution": {"mode": "text_only"},
            "deterministic_graders": [
                {"id": "response", "type": "response_nonempty", "description": "Response", "required": True},
                {"id": "no-change", "type": "no_project_changes", "description": "No change", "required": True, "critical": True},
            ],
            "rubric": [],
        }

        class BaselineProvider:
            saw_skill = False

            def run(self, **kwargs):
                self.saw_skill = (kwargs["project"] / ".agents/skills/example/SKILL.md").is_file()
                return ProviderResult(status="completed", return_code=0, final_response="A bounded response.")

        provider = BaselineProvider()
        execution = _run_one(
            provider_name="codex",
            provider=provider,
            skill_name="example",
            skill_root=current,
            baseline_skill_root=old,
            baseline_skill_digest="old-digest",
            case=case,
            eval_dir=eval_dir,
            configuration="without_skill",
            trial=1,
            pair_id="example:old-baseline-case:trial-1",
            arm_order=["without_skill", "with_skill"],
            timeout_seconds=30,
            reasoning_effort="max",
            model="test-model",
            allowed_tools=["Read"],
            source_commit="test",
            skill_digest="current-digest",
            credential_home=None,
            contract_hash="contract",
        )
        self.assertTrue(provider.saw_skill)
        result = _materialize_trial(execution)
        self.assertEqual(result["status"], "completed")
        run = json.loads((eval_dir / "without_skill" / "run-1" / "run.json").read_text())
        self.assertTrue(run["baseline_skill"])
        self.assertTrue(json.loads((eval_dir / "without_skill" / "run-1" / "grading.json").read_text())["valid_trial"])

    def test_trial_metadata_is_written_only_after_provider_exit(self):
        root = Path(tempfile.mkdtemp(prefix="skills-v2-isolation-"))
        skill_root = root / "skill"
        skill_root.mkdir()
        (skill_root / "SKILL.md").write_text("---\nname: example\ndescription: Example skill.\n---\nUse it.\n")
        eval_dir = root / "eval-example"
        case = {
            "id": "example-case",
            "skill_name": "example",
            "split": "tuning",
            "prompt": "Give a concise bounded response without editing files.",
            "hard_requirements": ["respond"],
            "forbidden_outcomes": ["edit files"],
            "execution": {"mode": "text_only"},
            "deterministic_graders": [
                {"id": "response", "type": "response_nonempty", "description": "Response", "required": True},
                {"id": "no-change", "type": "no_project_changes", "description": "No change", "required": True, "critical": True},
            ],
            "rubric": [],
        }

        class InspectingProvider:
            saw_metadata = False
            project_path = ""

            def run(self, **kwargs):
                run_dir = kwargs["run_dir"]
                self.project_path = str(kwargs["project"])
                self.saw_metadata = any((run_dir / name).exists() for name in (
                    "contract.json", "environment.json", "eval_metadata.json", "run_metadata.json", "grading.json"
                ))
                return ProviderResult(
                    status="completed",
                    return_code=0,
                    final_response="A bounded response.",
                    network_policy_enforced=False,
                    tool_policy_enforced=False,
                )

        provider = InspectingProvider()
        execution = _run_one(
            provider_name="codex",
            provider=provider,
            skill_name="example",
            skill_root=skill_root,
            case=case,
            eval_dir=eval_dir,
            configuration="with_skill",
            trial=1,
            pair_id="example:example-case:trial-1",
            arm_order=["with_skill", "without_skill"],
            timeout_seconds=30,
            reasoning_effort="max",
            model="test-model",
            allowed_tools=["Command"],
            source_commit="test",
            skill_digest="skill",
            credential_home=None,
            contract_hash="contract",
        )
        self.assertFalse(provider.saw_metadata)
        self.assertNotIn("with_skill", provider.project_path)
        self.assertNotIn("without_skill", provider.project_path)
        self.assertFalse((eval_dir / "with_skill" / "run-1").exists())
        result = _materialize_trial(execution)
        self.assertTrue((eval_dir / "with_skill" / "run-1" / "contract.json").is_file())
        self.assertEqual(result["status"], "completed")


class V2AnalysisTests(unittest.TestCase):
    def _write_run(self, root, case_id, trial, configuration, passed, valid=True, critical=None):
        run_dir = root / f"eval-{case_id}" / configuration / f"run-{trial}"
        (run_dir / "project").mkdir(parents=True)
        (run_dir / "outputs").mkdir()
        (run_dir / "run.json").write_text(json.dumps({"case_id": case_id, "trial": trial, "configuration": configuration, "status": "completed" if valid else "timed_out"}))
        (run_dir / "grading.json").write_text(json.dumps({"valid_trial": valid, "task_passed": passed if valid else False, "critical_failures": critical or []}))

    def test_analysis_reports_exact_pairs_and_delta(self):
        root = Path(tempfile.mkdtemp(prefix="skills-v2-analysis-"))
        self._write_run(root, "a", 1, "without_skill", False)
        self._write_run(root, "a", 1, "with_skill", True)
        self._write_run(root, "b", 1, "without_skill", True)
        self._write_run(root, "b", 1, "with_skill", True)
        self._write_run(root, "c", 1, "without_skill", False, valid=False)
        self._write_run(root, "c", 1, "with_skill", True)
        result = analyze(root, seed=1)
        self.assertEqual(result["paired_trial_count"], 2)
        self.assertEqual(result["outcomes"]["treatment_wins"], 1)
        self.assertEqual(result["outcomes"]["ties"], 1)
        self.assertEqual(result["invalid_runs"], 1)
        self.assertEqual(result["paired_mean_delta"], 0.5)

    def test_analysis_blocks_incomplete_coverage(self):
        root = Path(tempfile.mkdtemp(prefix="skills-v2-analysis-coverage-"))
        (root / "run_metadata.json").write_text(json.dumps({"case_ids": ["a"], "trials": 2, "requested_split": "tuning"}))
        self._write_run(root, "a", 1, "without_skill", False)
        self._write_run(root, "a", 1, "with_skill", True)
        result = analyze(root, seed=1)
        self.assertFalse(result["coverage_complete"])
        self.assertEqual(result["decision"], "inconclusive")


if __name__ == "__main__":
    unittest.main()

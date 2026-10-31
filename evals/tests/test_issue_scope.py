"""Known-valid and targeted-defect controls for scope and lifecycle acceptance."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from evals.skills import _runner_acceptance_command

CONTROLS = {
    "scope_good": "def compile_setup(project):\n    return {'backend': project['database'], 'tables': list(project['tables']), 'imports': list(project.get('deployed_sources', [])), 'services': []}\n",
    "life_good": "def blocked(store, owner):\n    return any(j['owner']==owner and j['state']=='failed' and j['quota_held'] for j in store.rows)\n\ndef submit(store, owner):\n    if blocked(store,owner): raise RuntimeError('owner has unresolved resources')\n    job={'id':str(len(store.rows)), 'owner':owner, 'state':'queued', 'resource_id':None, 'quota_held':True}\n    store.rows.append(job);store.save();return job\n\ndef consume(store, job_id, provider):\n    job=next(j for j in store.rows if j['id']==job_id)\n    if blocked(store,job['owner']): raise RuntimeError('owner has unresolved resources')\n    try:\n        rid=provider.create(job['owner'])\n        job['resource_id']=rid;store.save()\n        provider.configure(rid)\n        job['state']='active';store.save()\n    except RuntimeError:\n        job['state']='failed';store.save();raise\n\ndef recover(store, job_id, provider):\n    job=next(j for j in store.rows if j['id']==job_id)\n    if job['resource_id'] is None: return\n    provider.delete(job['resource_id'])\n    job['quota_held']=False;job['state']='released';store.save()\n",
}


class ScopeIssueAcceptanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = Path(__file__).resolve().parents[1] / "cases" / "skills-comparison.json"
        all_cases = json.loads(path.read_text())
        ids = ["issue-37-39-corrected-package-scope", "issue-40-resource-lifecycle"]
        cls.cases = [
            next(case for case in all_cases if case["id"] == case_id) for case_id in ids
        ]

    def check(self, case, label, code, expected=None):
        with tempfile.TemporaryDirectory(prefix="scope-calibration-") as d:
            root = Path(d)
            for name, data in case["files"].items():
                (root / name).write_text(data)
            filename = case["metadata"]["allowed_paths"][0]
            (root / filename).write_text(code)
            command, error = _runner_acceptance_command(
                case["metadata"]["fixture_contract"]
            )
            assert error is None, error
            p = subprocess.run(
                command,
                cwd=root,
                text=True,
                capture_output=True,
                check=False,
                timeout=5,
            )
            if expected is None:
                assert p.returncode == 0, (label, p.stderr)
                q = subprocess.run(
                    [sys.executable, "-B", "-m", "unittest", "test_project", "-v"],
                    cwd=root,
                    text=True,
                    capture_output=True,
                    check=False,
                    timeout=5,
                )
                assert q.returncode == 0, (label, q.stderr)
            else:
                assert p.returncode != 0 and expected in p.stderr, (label, p.stderr)

    def test_control_01(self):
        self.check(
            self.cases[0], "valid-contract-implementation", CONTROLS["scope_good"]
        )

    def test_control_02(self):
        self.check(
            self.cases[0],
            "valid-alternative-copy-construction",
            CONTROLS["scope_good"].replace(
                "list(project.get('deployed_sources', []))",
                "[*project.get('deployed_sources', [])]",
            ),
        )

    def test_control_03(self):
        self.check(
            self.cases[0],
            "obsolete-prototype",
            self.cases[0]["files"]["setup_builder.py"],
            "superseded prototype expanded package scope",
        )

    def test_control_04(self):
        self.check(
            self.cases[0],
            "unconditional-importer",
            CONTROLS["scope_good"].replace(
                "list(project.get('deployed_sources', []))", "['prototype.sqlite']"
            ),
            "superseded prototype expanded package scope",
        )

    def test_control_05(self):
        self.check(
            self.cases[0],
            "deleted-genuine-migration",
            CONTROLS["scope_good"].replace(
                "list(project.get('deployed_sources', []))", "[]"
            ),
            "genuine deployed data obligation lost",
        )

    def test_control_06(self):
        self.check(self.cases[1], "valid-full-lifecycle", CONTROLS["life_good"])

    def test_control_07(self):
        self.check(
            self.cases[1],
            "valid-alternative-blocker-loop",
            CONTROLS["life_good"].replace(
                "return any(j['owner']==owner and j['state']=='failed' and j['quota_held'] for j in store.rows)",
                "for j in store.rows:\n        if j['owner']==owner and j['state']=='failed' and j['quota_held']: return True\n    return False",
            ),
        )

    def test_control_08(self):
        self.check(
            self.cases[1],
            "persistence-after-configure",
            CONTROLS["life_good"].replace(
                "job['resource_id']=rid;store.save()\n        provider.configure(rid)",
                "provider.configure(rid)\n        job['resource_id']=rid;store.save()",
            ),
            "identity not durable before configure",
        )

    def test_control_09(self):
        self.check(
            self.cases[1],
            "unknown-legacy-releases-quota",
            CONTROLS["life_good"].replace(
                "if job['resource_id'] is None: return",
                "if job['resource_id'] is None:\n        job['quota_held']=False;job['state']='released';store.save();return",
            ),
            "unknown migrated resource released quota",
        )

    def test_control_10(self):
        self.check(
            self.cases[1],
            "submission-only-owner-guard",
            CONTROLS["life_good"].replace(
                "    if blocked(store,job['owner']): raise RuntimeError('owner has unresolved resources')\n",
                "",
            ),
            "already queued work bypassed owner invariant",
        )

    def test_control_11(self):
        self.check(
            self.cases[1],
            "blanket-owner-block",
            CONTROLS["life_good"].replace(
                "j['owner']==owner and j['state']=='failed'", "j['state']=='failed'"
            ),
            "unrelated owner blocked",
        )

    def test_control_12(self):
        self.check(
            self.cases[1],
            "release-before-delete",
            CONTROLS["life_good"].replace(
                "    provider.delete(job['resource_id'])\n    job['quota_held']=False;job['state']='released';store.save()",
                "    job['quota_held']=False;job['state']='released';store.save()\n    provider.delete(job['resource_id'])",
            ),
            "quota released before deletion confirmation",
        )


if __name__ == "__main__":
    unittest.main()

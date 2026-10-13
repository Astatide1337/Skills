"""Objective, model-free review proof calibration; prose semantics are unmeasured."""
from __future__ import annotations

import json
import os
import re
import secrets
import shutil
import signal
import stat
import subprocess
import tempfile
from pathlib import Path

from evals.workspace_evidence import _sensitive, bwrap_preflight, validate_relative_path

MAX_BYTES = 60_000
SELECTOR = re.compile(r"ReviewProof\.test_[A-Za-z0-9_]+\Z")


def validate_policy(policy: dict) -> None:
    """Validate hidden fixture data before any candidate execution."""
    if not isinstance(policy, dict):
        raise TypeError("review_acceptance must be an object")
    paths = policy.get("source_paths")
    if (not isinstance(paths, list) or not 1 <= len(paths) <= 12
            or not all(
                isinstance(p, str) and validate_relative_path(p) and not _sensitive(p)
                and re.fullmatch(r"[A-Za-z_]\w*\.py", p) and p != "evidence.py" for p in paths) or len(set(paths)) != len(paths)):
        raise ValueError("review source_paths must be bounded Python module paths")
    if (policy.get("report_path") != "review.json" or policy.get("evidence_path") != "evidence.py"
            or type(policy.get("max_findings")) is not int or not 1 <= policy["max_findings"] <= 5
            or type(policy.get("probe_timeout")) not in (int, float)
            or not 0 < policy["probe_timeout"] <= 2):
        raise ValueError("review artifacts or execution bounds are invalid")
    defects = policy.get("defects")
    if not isinstance(defects, list) or len(defects) > 3:
        raise ValueError("review defects must contain at most three independent repairs")
    ids = set()
    for defect in defects:
        if (not isinstance(defect, dict) or not isinstance(defect.get("id"), str)
                or not defect["id"].strip() or defect["id"] in ids):
            raise ValueError("review defect IDs must be unique")
        ids.add(defect["id"])
        files, fixes = defect.get("files"), defect.get("fixes")
        if (not isinstance(files, list) or not files or not all(p in paths for p in files)
                or not isinstance(fixes, dict) or not fixes or not set(fixes) <= set(paths)
                or not all(isinstance(code, str) and code.strip() and len(code.encode()) <= MAX_BYTES
                           for code in fixes.values())):
            raise ValueError("review defect locations and complete repairs must be bounded")
    if sum(len(code.encode()) for d in defects for code in d["fixes"].values()) > 540_000:
        raise ValueError("review repair data exceeds bound")


def _read(root: Path, name: str) -> str:
    path = root / name
    if not validate_relative_path(name) or _sensitive(name):
        raise ValueError("unsafe artifact path")
    for part in [path, *path.parents]:
        if part == root.parent:
            break
        if part.is_symlink():
            raise ValueError("symlink artifact")
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor, "rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise ValueError("artifact must be an unlinked regular file")
        data = stream.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError("artifact exceeds size cap")
    return data.decode("utf-8")


def _probe(root: Path, selector: str, timeout: float) -> str:
    # A runner-owned result, rather than candidate-written unittest summaries.
    # This rejects accidental/fake output, not arbitrary malicious Python:
    # behavioral authenticity still requires independent artifact review.
    marker = secrets.token_hex(24)
    driver = """import io,json,os,sys,unittest
emit = os.write
dumps = json.dumps
sys.path.insert(0, '/workspace')
try:
 import evidence
 cls = getattr(evidence, 'ReviewProof', None)
 method = sys.argv[1].split('.')[1]
 if not isinstance(cls, type) or not issubclass(cls, unittest.TestCase) or method not in cls.__dict__:
  raise ValueError('missing concrete unittest method')
 suite = unittest.TestSuite([cls(method)])
 result = unittest.TextTestRunner(stream=io.StringIO()).run(suite)
 status = ('pass' if result.wasSuccessful() and result.testsRun == 1 else
           'fail' if result.testsRun == 1 and len(result.failures) + len(result.errors) >= 1 and not result.skipped else
           'malformed proof or test error')
except BaseException:
 status = 'malformed proof or test error'
emit(1, ('\\n' + sys.argv[2] + dumps({'status': status}) + '\\n').encode())
"""
    command = [shutil.which("bwrap"), "--die-with-parent", "--unshare-all"]
    for mount in ("/usr", "/bin", "/lib", "/lib64"):
        command += ["--ro-bind", mount, mount]
    command += ["--tmpfs", "/tmp", "--ro-bind", str(root), "/workspace", "--chdir", "/workspace",
                "--proc", "/proc", "--dev", "/dev", "--clearenv",
                "--setenv", "PATH", "/usr/bin:/bin", "/usr/bin/python3", "-S", "-B",
                "-c", driver, selector, marker]
    command = ["/usr/bin/prlimit", "--fsize=" + str(MAX_BYTES), "--nofile=64", "--", *command]
    with tempfile.TemporaryFile() as output:
        process = subprocess.Popen(command, cwd=root, env={"PATH": "/usr/bin:/bin"},
                                   stdout=output, stderr=output, start_new_session=True)
        try:
            process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            return "timeout"
        finally:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait()
        output.seek(0)
        text = output.read(MAX_BYTES).decode("utf-8", errors="replace")
    if "bwrap:" in text:
        raise OSError("proof containment unavailable: " + text[:500])
    receipts = [line[len(marker):] for line in text.splitlines() if line.startswith(marker)]
    if process.returncode != 0 or len(receipts) != 1:
        return "malformed proof or test error"
    try:
        receipt = json.loads(receipts[0])
    except ValueError:
        return "malformed proof or test error"
    return receipt["status"] if receipt in ({"status": "pass"}, {"status": "fail"}) else "malformed proof or test error"



def classify_review(workspace: Path, policy: dict) -> dict:
    """Count uniquely isolated defects; never grade description keywords."""
    result = {"status": "invalid", "schema_valid": False, "known_defects": None,
              "true_positives": 0, "false_positives": 0, "duplicates": 0,
              "missed_defects": None, "precision": float("nan"), "recall": float("nan"),
              "clean_no_findings": float("nan"), "complete_review": False,
              "findings": [], "description_semantics": "unmeasured; independent artifact review required"}
    try:
        validate_policy(policy)
    except (ValueError, TypeError) as exc:
        return {**result, "status": "unavailable", "reason": str(exc)}
    defects = policy["defects"]
    result.update(known_defects=len(defects), missed_defects=len(defects))
    try:
        sources = {p: _read(workspace, p) for p in policy["source_paths"]}
    except (OSError, ValueError, UnicodeError) as exc:
        return {**result, "status": "unavailable", "reason": str(exc)}
    try:
        def unique_object(pairs):
            value = {}
            for key, item in pairs:
                if key in value:
                    raise ValueError("duplicate report key")
                value[key] = item
            return value
        report = json.loads(_read(workspace, "review.json"), object_pairs_hook=unique_object)
        evidence = _read(workspace, "evidence.py")
        if not isinstance(report, dict) or set(report) != {"findings"}:
            raise ValueError("report must contain findings only")
        findings = report["findings"]
        if not isinstance(findings, list) or len(findings) > policy["max_findings"]:
            raise ValueError("findings exceed bound or are not a list")
        for finding in findings:
            if (not isinstance(finding, dict) or set(finding) != {"file", "line", "title", "description", "proof"}
                    or not all(isinstance(finding[k], str) and finding[k].strip() and len(finding[k]) <= 8000
                               for k in ("file", "title", "description", "proof"))
                    or finding["file"] not in sources or type(finding["line"]) is not int
                    or not 1 <= finding["line"] <= len(sources[finding["file"]].splitlines())
                    or not SELECTOR.fullmatch(finding["proof"])):
                raise ValueError("invalid finding structure, location or proof selector")
    except (OSError, ValueError, UnicodeError, TypeError) as exc:
        return {**result, "reason": str(exc)}
    result["schema_valid"] = True
    error = bwrap_preflight()
    if error:
        return {**result, "status": "unavailable", "reason": error}
    seen, cache = set(), {}
    try:
        with tempfile.TemporaryDirectory(prefix="review-probes-") as directory:
            for finding in findings:
                selector = finding["proof"]
                if selector not in cache:
                    outcomes = []
                    for index, fixes in enumerate([{}, *[d["fixes"] for d in defects]]):
                        root = Path(directory) / str(len(cache)) / str(index)
                        root.mkdir(parents=True)
                        for name, code in {**sources, **fixes, "evidence.py": evidence}.items():
                            (root / name).write_text(code)
                            (root / name).chmod(0o444)
                        outcomes.append(_probe(root, selector, policy["probe_timeout"]))
                    cache[selector] = outcomes
                outcomes = cache[selector]
                matches = [i for i, outcome in enumerate(outcomes[1:]) if outcome == "pass"]
                isolated = (outcomes[0] == "fail" and len(matches) == 1
                            and all(o == "fail" for i, o in enumerate(outcomes[1:]) if i != matches[0]))
                defect = defects[matches[0]] if isolated else None
                if defect is None or finding["file"] not in defect["files"]:
                    result["false_positives"] += 1
                    receipt = {"classification": "unsubstantiated", "reason": "proof/location does not isolate one repair", "outcomes": outcomes}
                elif defect["id"] in seen:
                    result["duplicates"] += 1
                    receipt = {"classification": "duplicate", "defect": defect["id"]}
                else:
                    seen.add(defect["id"])
                    result["true_positives"] += 1
                    receipt = {"classification": "true_positive", "defect": defect["id"]}
                result["findings"].append(receipt)
    except OSError as exc:
        return {**result, "status": "unavailable", "reason": str(exc)}
    result.update(status="valid", missed_defects=len(defects) - len(seen),
                  precision=len(seen) / len(findings) if findings else float("nan"),
                  recall=len(seen) / len(defects) if defects else float("nan"),
                  clean_no_findings=int(not findings) if not defects else float("nan"),
                  complete_review=len(seen) == len(defects) and not result["false_positives"] and not result["duplicates"])
    return result

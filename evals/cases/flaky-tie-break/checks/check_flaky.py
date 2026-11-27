"""The tie-break test must pass under many hash seeds and still assert submission order."""

import os
import re
import subprocess
import sys
from pathlib import Path

source = Path("tests/test_queue.py").read_text()
if not re.search(r'next_jobs\(3\),\s*\["urgent",\s*"backup",\s*"reindex"\]', source):
    sys.exit("the submission-order assertion was changed or removed")
if re.search(r"skip|expectedFailure|PYTHONHASHSEED|retry", source):
    sys.exit("the test was skipped, retried or pinned")
failures = []
for seed in range(40):
    env = {**os.environ, "PYTHONHASHSEED": str(seed)}
    r = subprocess.run(
        [sys.executable, "-m", "unittest", "-q", "tests.test_queue"],
        env=env,
        capture_output=True,
        check=False,
    )
    if r.returncode:
        failures.append(seed)
if failures:
    sys.exit(f"failed under seeds {failures}")
print("stable under 40 seeds")

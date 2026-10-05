#!/usr/bin/env python3
"""Read-only diagnostics for the exact workspace namespace prerequisite."""
import json
import os
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from evals.workspace_evidence import bwrap_preflight

settings = {}
for path in ["/proc/sys/kernel/unprivileged_userns_clone",
             "/proc/sys/user/max_user_namespaces",
             "/proc/sys/kernel/apparmor_restrict_unprivileged_userns",
             "/proc/self/attr/current"]:
    try:
        settings[path] = Path(path).read_text().strip()
    except OSError as exc:
        settings[path] = f"unavailable: {exc.strerror}"
try:
    version = subprocess.run(["bwrap", "--version"], capture_output=True, text=True, timeout=5)
    settings["bubblewrap"] = version.stdout.strip() or version.stderr.strip()
except (OSError, subprocess.TimeoutExpired) as exc:
    settings["bubblewrap"] = str(exc)
error = bwrap_preflight()
diagnostics = {"settings": settings, "prerequisite": "failed" if error else "accepted", "reason": error}
if error and os.environ.get("GITHUB_ACTIONS") == "true":
    # Read only recent, relevant kernel denials; do not alter profiles/sysctls
    # or dump unrelated kernel messages. Missing access is an unknown cause.
    try:
        logs = subprocess.run(["sudo", "-n", "journalctl", "-k", "-b", "--since=-2min", "--no-pager", "-o", "cat"],
                              capture_output=True, text=True, timeout=10)
        diagnostics["kernel_denials"] = [line for line in logs.stdout.splitlines()
                                         if 'apparmor="DENIED"' in line and ('bwrap' in line or 'unprivileged_userns' in line)][-20:]
        diagnostics["kernel_log_status"] = "read" if logs.returncode == 0 else "unavailable"
    except (OSError, subprocess.TimeoutExpired):
        diagnostics["kernel_log_status"] = "unavailable"
print(json.dumps(diagnostics, indent=2))
sys.exit(1 if error else 0)

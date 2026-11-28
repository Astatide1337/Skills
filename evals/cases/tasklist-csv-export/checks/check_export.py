"""`python -m tasklist export` must print CSV with title, done and created columns."""

import csv
import io
import os
import subprocess
import sys
import tempfile

with tempfile.TemporaryDirectory() as d:
    env = {**os.environ, "TASKLIST_FILE": os.path.join(d, "tasks.json")}
    titles = ["Buy milk", 'Say "hi", then leave', "multi\nline"]
    for title in titles:
        subprocess.run(
            [sys.executable, "-m", "tasklist", "add", title],
            env=env,
            check=True,
            capture_output=True,
        )
    subprocess.run(
        [sys.executable, "-m", "tasklist", "done", "2"],
        env=env,
        check=True,
        capture_output=True,
    )
    out = subprocess.run(
        [sys.executable, "-m", "tasklist", "export"],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    if out.returncode != 0:
        sys.exit(f"export failed: {out.stderr}")
    rows = list(csv.DictReader(io.StringIO(out.stdout)))
    header = {h.lower(): h for h in (rows[0].keys() if rows else [])}

    def column(*words):
        names = [k for k in header if not k.endswith("id")]
        exact = [k for k in names if k in words]
        partial = [k for k in names if any(w in k for w in words)]
        return header[(exact or partial)[0]] if exact or partial else None

    title = column("title", "name", "task", "description")
    done = column("done", "status", "complete", "finished")
    created = column("creat", "date", "added", "time")
    if not (title and done and created):
        sys.exit(f"missing columns in header: {list(header.values())}")
    if [r[title] for r in rows] != titles:
        sys.exit(f"titles did not round-trip: {[r[title] for r in rows]}")
    truthy = {"true", "yes", "y", "1", "done", "x", "completed", "complete"}
    if [r[done].strip().lower() in truthy for r in rows] != [False, True, False]:
        sys.exit(f"done column wrong: {[r[done] for r in rows]}")
    if not all(r[created] for r in rows):
        sys.exit("created column empty")
print("export ok")

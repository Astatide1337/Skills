"""Read GitHub approval events for the current head without external CLI tools."""

import json
import os
import sys
from pathlib import Path
from urllib.request import Request, urlopen


def fetch_events(repo, number, head, token, api="https://api.github.com"):
    def get(path):
        request = Request(
            f"{api}/repos/{repo}/{path}",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
            },
        )
        with urlopen(request, timeout=30) as response:
            return json.load(response)

    if get(f"pulls/{number}")["head"]["sha"] != head:
        raise ValueError("PR head changed; rerun for the current head")
    events = []
    for page in range(1, 101):
        batch = get(f"issues/{number}/events?per_page=100&page={page}")
        if not isinstance(batch, list):
            raise TypeError("GitHub returned an invalid event list")
        events.extend(
            event for event in batch if event.get("event") in {"labeled", "unlabeled"}
        )
        if len(batch) < 100:
            return events
    raise ValueError("PR event history exceeds the 10,000-event safety bound")


if __name__ == "__main__":
    try:
        events = fetch_events(
            os.environ["REPO"],
            os.environ["PR"],
            os.environ["HEAD_SHA"],
            os.environ["GH_TOKEN"],
            os.environ.get("GITHUB_API_URL", "https://api.github.com"),
        )
        Path(sys.argv[1]).write_text(json.dumps(events))
    except (OSError, ValueError, TypeError, KeyError, IndexError) as error:
        print(f"approval events unavailable: {error}", file=sys.stderr)
        sys.exit(2)

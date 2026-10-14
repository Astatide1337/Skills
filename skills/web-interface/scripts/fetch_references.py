#!/usr/bin/env python3
"""Fetch selected, attributed visual references into a fresh local directory.

No installation, browser credentials, page scripts, model calls or quality score.
The reference Markdown owns URLs. Download hashes identify fetched bytes only.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
from http.client import HTTPException
import json
from pathlib import Path
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

REFERENCE = Path(__file__).resolve().parents[1] / "references/composition-examples.md"
HOSTS = frozenset({"www.apple.com", "webassets.linear.app", "b.stripecdn.com", "www.anthropic.com"})
MAX_BYTES = 12 * 1024 * 1024
DEFINITION = re.compile(r"^\[image-([a-z0-9]+(?:-[a-z0-9]+)*)\]: (https://\S+)$", re.MULTILINE)


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Changed sources need inspection, not a silent request to another host.
        return None


def image_sources() -> dict[str, str]:
    pairs = DEFINITION.findall(REFERENCE.read_text(encoding="utf-8"))
    if not pairs or len(dict(pairs)) != len(pairs):
        raise ValueError("Missing or duplicate image definitions in the reference")
    for _, url in pairs:
        parsed = urlsplit(url)
        if (parsed.scheme != "https" or parsed.hostname not in HOSTS
                or parsed.username or parsed.password or parsed.port not in (None, 443)):
            raise ValueError("Reference URL is outside the reviewed HTTPS source hosts")
    return dict(pairs)


def image_extension(data: bytes) -> str:
    # Recognize container signatures. Decoding/rendering is a separate check.
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if data.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return ".webp"
    raise ValueError("Response is not a recognized PNG, JPEG or WebP image")


def download(url: str) -> bytes:
    request = Request(url, headers={"User-Agent": "Skills-Reference-Study/2", "Accept": "image/png,image/jpeg,image/webp"})
    # No cookie jar, credentials or arbitrary caller-supplied URLs.
    with build_opener(NoRedirect()).open(request, timeout=30) as response:
        if response.status != 200:
            raise ValueError(f"Unexpected HTTP status {response.status}")
        data = response.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError("Image exceeds the 12 MiB per-file limit")
    image_extension(data)
    return data


def fetch(selected: list[str], output: Path) -> dict:
    sources = image_sources()
    if not selected or len(set(selected)) != len(selected) or any(key not in sources for key in selected):
        raise ValueError("Select distinct known image IDs; use --list")
    output = output.expanduser().absolute()
    # No merging, overwriting, installing into a home, or recursive deletion.
    output.mkdir(mode=0o700, parents=False, exist_ok=False)
    rows = [{"id": key, "url": sources[key], "status": "not-run"} for key in selected]
    for row in rows:
        try:
            data = download(row["url"])
            name = row["id"] + image_extension(data)
            with (output / name).open("xb") as target:
                target.write(data)
            row.update(status="fetched", file=name, bytes=len(data),
                       sha256=hashlib.sha256(data).hexdigest(),
                       fetched_at=datetime.now(timezone.utc).isoformat())
        except (OSError, ValueError, HTTPException, HTTPError, URLError) as exc:
            row.update(status="failed", reason=str(exc))
        except KeyboardInterrupt:
            row.update(status="interrupted", reason="User interrupted reference fetching")
            break
    receipt = {"kind": "visual-reference-download", "files": rows,
               "quality_verified": False, "source_revision_verified": False}
    (output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    gallery = ["# Downloaded references\n", "Read the installed composition-examples.md for context, attribution and limits.\n",
               "These third-party images are for reference, not licensed product assets.\n"]
    for row in rows:
        gallery += [f"## {row['id']}\n", f"Status: {row['status']}\n"]
        if row["status"] == "fetched":
            gallery.append(f"![{row['id']}]({row['file']})\n")
    (output / "index.md").write_text("\n".join(gallery), encoding="utf-8")
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--list", action="store_true", help="List reviewed sources without network access")
    mode.add_argument("--all", action="store_true", help="Explicitly fetch every listed image")
    mode.add_argument("--id", action="append", dest="ids", help="Image ID to fetch; repeat to select several")
    parser.add_argument("--output", type=Path, help="Fresh output directory with an existing parent")
    args = parser.parse_args()
    try:
        sources = image_sources()
        if args.list or (not args.all and not args.ids):
            if args.output:
                parser.error("--output requires --id or --all")
            print(json.dumps(sources, indent=2))
            return 0
        if not args.output:
            parser.error("fetching requires --output to an explicit fresh directory")
        result = fetch(list(sources) if args.all else args.ids, args.output)
    except (OSError, ValueError) as exc:
        print(json.dumps({"status": "failed", "reason": str(exc)}), file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2))
    return 0 if all(row["status"] == "fetched" for row in result["files"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())

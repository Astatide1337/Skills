#!/usr/bin/env python3
"""Check structural and offline-packaging requirements for one HTML artifact."""

from __future__ import annotations

import argparse
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse


class ArtifactParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.lang = ""
        self.title_depth = 0
        self.title = ""
        self.has_main = False
        self.has_viewport = False
        self.headings: list[int] = []
        self.remote_runtime: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key.lower(): value or "" for key, value in attrs}
        if tag == "html":
            self.lang = values.get("lang", "").strip()
        elif tag == "title":
            self.title_depth += 1
        elif tag == "main":
            self.has_main = True
        elif tag == "meta" and values.get("name", "").lower() == "viewport":
            self.has_viewport = "width=device-width" in values.get("content", "").lower()
        elif re.fullmatch(r"h[1-6]", tag):
            self.headings.append(int(tag[1]))

        candidate = ""
        if tag in {"script", "iframe", "audio", "video", "source"}:
            candidate = values.get("src", "")
        elif tag == "link" and "stylesheet" in values.get("rel", "").lower().split():
            candidate = values.get("href", "")
        elif tag == "img":
            candidate = values.get("src", "")
        if candidate:
            parsed = urlparse(candidate)
            if parsed.scheme in {"http", "https"} or candidate.startswith("//"):
                self.remote_runtime.append(candidate)

    def handle_endtag(self, tag: str) -> None:
        if tag == "title" and self.title_depth:
            self.title_depth -= 1

    def handle_data(self, data: str) -> None:
        if self.title_depth:
            self.title += data


def check(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    parser = ArtifactParser()
    parser.feed(text)
    errors: list[str] = []

    if not re.match(r"\s*<!doctype\s+html\s*>", text, re.IGNORECASE):
        errors.append("missing <!doctype html>")
    if not parser.lang:
        errors.append("missing html lang")
    if not parser.title.strip():
        errors.append("missing non-empty title")
    if not parser.has_viewport:
        errors.append("missing responsive viewport meta")
    if not parser.has_main:
        errors.append("missing main landmark")
    if not parser.headings or parser.headings[0] != 1:
        errors.append("first heading must be h1")
    for previous, current in zip(parser.headings, parser.headings[1:]):
        if current > previous + 1:
            errors.append(f"heading level jumps from h{previous} to h{current}")
            break
    if parser.remote_runtime:
        errors.append("remote runtime assets: " + ", ".join(parser.remote_runtime))

    return errors


def main() -> int:
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("artifact", type=Path)
    args = arg_parser.parse_args()
    if args.artifact.suffix.lower() != ".html" or not args.artifact.is_file():
        print(f"not an HTML file: {args.artifact}", file=sys.stderr)
        return 2
    errors = check(args.artifact)
    if errors:
        for error in errors:
            print(f"FAIL: {error}", file=sys.stderr)
        return 1
    print(f"validated standalone HTML structure: {args.artifact}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

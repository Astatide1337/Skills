#!/usr/bin/env python3
"""Deterministic helpers for source-scoped internet search.

This script never automates a browser. It generates encoded search URLs,
reads public web/RSS/GitHub data, and summarizes HAR metadata without values.
Rendered or signed-in pages are handled by the user's isolated Zen Agent
browser bridge from the active harness.
"""

from __future__ import annotations

import argparse
import ipaddress
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Iterable


EXIT_OK = 0
EXIT_USAGE = 2
EXIT_UNAVAILABLE = 3
EXIT_FAILED = 4

DEFAULT_TIMEOUT = 45
MAX_TIMEOUT = 120
DEFAULT_LIMIT = 10
MAX_LIMIT = 50
MAX_WEB_BYTES = 5 * 1024 * 1024
MAX_RSS_BYTES = 5 * 1024 * 1024
MAX_HAR_BYTES = 50 * 1024 * 1024
MAX_HAR_ENTRIES = 2_000

SOURCE_ALIASES = {
    "internet": "web",
    "yt": "youtube",
    "ig": "instagram",
    "li": "linkedin",
    "gh": "github",
}
SOURCES = {"web", "github", "rss", "reddit", "youtube", "instagram", "linkedin"}
SOCIAL_SOURCES = {"reddit", "youtube", "instagram", "linkedin"}
SOURCE_DOMAINS = {
    "reddit": "reddit.com",
    "youtube": "youtube.com",
    "instagram": "instagram.com",
    "linkedin": "linkedin.com",
}
SOURCE_HOSTS = {
    "reddit": ("reddit.com",),
    "youtube": ("youtube.com", "youtu.be"),
    "instagram": ("instagram.com",),
    "linkedin": ("linkedin.com",),
    "github": ("github.com", "githubusercontent.com"),
}
NATIVE_SEARCH_BASES = {
    "reddit": "https://www.reddit.com/search/",
    "youtube": "https://www.youtube.com/results",
    "instagram": "https://www.instagram.com/explore/search/keyword/",
    "linkedin": "https://www.linkedin.com/search/results/all/",
}

BROWSER_BINARIES = {
    "zen": ("zen-browser", "/opt/zen-browser-bin/zen-bin"),
}
AGENT_PROFILE_NAME = "Agent"
DEFAULT_AGENT_PROFILE = Path("~/.config/zen/Agent").expanduser()

SENSITIVE_HEADER = re.compile(
    r"(?:authorization|cookie|set-cookie|token|secret|password|api[-_]?key|"
    r"csrf|xsrf|session|signature|proxy-authorization)",
    re.IGNORECASE,
)
SENSITIVE_VALUE = re.compile(
    r"(?i)(\b(?:authorization|cookie|set-cookie|token|ct0|auth_token|secret|"
    r"password|api[-_]?key|csrf(?:token)?|xsrf(?:token)?|session|signature|"
    r"proxy-authorization)\b\s*[=:]\s*)([^\r\n,;]+)"
)
SENSITIVE_QUERY_NAME = re.compile(
    r"(?i)(?:^|[-_])(?:access[-_]?token|auth(?:orization)?|bearer|"
    r"client[-_]?secret|code|csrf(?:token)?|jwt|key|oauth(?:[-_]?token)?|"
    r"password|private[-_]?key|secret|session|sig(?:nature)?|token)(?:$|[-_])"
)


class ReachError(Exception):
    """Expected, user-facing failure."""

    def __init__(self, message: str, exit_code: int = EXIT_FAILED) -> None:
        super().__init__(message)
        self.exit_code = exit_code


def emit(payload: dict[str, Any], exit_code: int = EXIT_OK) -> int:
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return exit_code


def error_payload(error: ReachError) -> int:
    return emit(
        {
            "operation": None,
            "status": "error",
            "error": str(error),
        },
        error.exit_code,
    )


def bounded_limit(value: int) -> int:
    if not 1 <= value <= MAX_LIMIT:
        raise ReachError(f"limit must be between 1 and {MAX_LIMIT}", EXIT_USAGE)
    return value


def bounded_timeout(value: int) -> int:
    if not 1 <= value <= MAX_TIMEOUT:
        raise ReachError(
            f"timeout must be between 1 and {MAX_TIMEOUT} seconds", EXIT_USAGE
        )
    return value


def canonical_source(value: str) -> str:
    source = SOURCE_ALIASES.get(value.strip().lower(), value.strip().lower())
    if source not in SOURCES:
        raise ReachError(
            f"unsupported source {value!r}; choose one of {', '.join(sorted(SOURCES))}",
            EXIT_USAGE,
        )
    return source


def _resolved_addresses(
    hostname: str,
) -> set[ipaddress.IPv4Address | ipaddress.IPv6Address] | None:
    """Resolve a host for SSRF checks; ``None`` means resolution failed."""

    try:
        records = socket.getaddrinfo(hostname, None, type=socket.SOCK_STREAM)
    except (OSError, socket.gaierror):
        return None
    addresses: set[ipaddress.IPv4Address | ipaddress.IPv6Address] = set()
    for record in records:
        try:
            addresses.add(ipaddress.ip_address(record[4][0]))
        except (IndexError, ValueError):
            continue
    return addresses


def normalize_public_url(value: str, *, resolve_host: bool = False) -> str:
    try:
        parsed = urllib.parse.urlsplit(value.strip())
    except ValueError as exc:
        raise ReachError("target URL is malformed", EXIT_USAGE) from exc
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ReachError("target must be an absolute http(s) URL", EXIT_USAGE)
    if parsed.username or parsed.password:
        raise ReachError("credential-bearing URLs are not accepted", EXIT_USAGE)
    try:
        port = parsed.port
    except ValueError as exc:
        raise ReachError("target has an invalid port", EXIT_USAGE) from exc
    if port not in {None, 80, 443}:
        raise ReachError("only standard HTTP(S) ports 80 and 443 are accepted", EXIT_USAGE)

    hostname = parsed.hostname.rstrip(".").lower()
    if (
        hostname in {"localhost", "localhost.localdomain"}
        or hostname.endswith((".localhost", ".local", ".internal"))
        or "%" in hostname
    ):
        raise ReachError("local and internal hosts are not accepted", EXIT_USAGE)

    query_names = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
    if any(SENSITIVE_QUERY_NAME.search(name) for name, _ in query_names):
        raise ReachError("credential-bearing URL query parameters are not accepted", EXIT_USAGE)

    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        address = None
    if address is not None and not address.is_global:
        raise ReachError("non-public IP addresses are not accepted", EXIT_USAGE)
    if resolve_host:
        addresses = _resolved_addresses(hostname)
        if addresses is None:
            raise ReachError("target hostname could not be resolved", EXIT_FAILED)
        if addresses and any(not address.is_global for address in addresses):
            raise ReachError("target resolves to a non-public IP address", EXIT_USAGE)
    return urllib.parse.urlunsplit(parsed)


class _PublicRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Validate every redirect before urllib opens the next destination."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[override]
        try:
            safe_url = normalize_public_url(newurl, resolve_host=True)
        except ReachError as exc:
            raise urllib.error.HTTPError(
                req.full_url, code, str(exc), headers, None
            ) from exc
        return super().redirect_request(req, fp, code, msg, headers, safe_url)


def open_public(request: urllib.request.Request, *, timeout: int):
    """Open a public URL with bounded, validated redirects."""

    opener = urllib.request.build_opener(_PublicRedirectHandler)
    return opener.open(request, timeout=timeout)


def source_url_allowed(source: str, url: str) -> bool:
    hostname = (urllib.parse.urlsplit(url).hostname or "").lower().rstrip(".")
    domains = SOURCE_HOSTS.get(source)
    if not domains:
        return True
    return any(hostname == domain or hostname.endswith("." + domain) for domain in domains)


def redact_url_query(value: str) -> str:
    """Keep feed links useful while removing values from credential-like queries."""

    try:
        parsed = urllib.parse.urlsplit(value)
    except ValueError:
        return "<malformed link>"
    if parsed.username or parsed.password:
        return "<redacted credential-bearing link>"
    pairs = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
    if not any(SENSITIVE_QUERY_NAME.search(name) for name, _ in pairs):
        return value
    redacted = [
        (name, "<redacted>" if SENSITIVE_QUERY_NAME.search(name) else item)
        for name, item in pairs
    ]
    return urllib.parse.urlunsplit(
        parsed._replace(query=urllib.parse.urlencode(redacted))
    )


def scrub(text: str, limit: int = 2_000) -> str:
    text = text[:limit]
    return SENSITIVE_VALUE.sub(r"\1<redacted>", text)


def run_argv(
    argv: Iterable[str], *, timeout: int = DEFAULT_TIMEOUT, env: dict[str, str] | None = None
) -> tuple[int, str, str, int]:
    command = [str(part) for part in argv]
    started = time.monotonic()
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
            check=False,
        )
    except FileNotFoundError as exc:
        raise ReachError(f"required command is missing: {command[0]}", EXIT_UNAVAILABLE) from exc
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout if isinstance(exc.stdout, str) else ""
        stderr = exc.stderr if isinstance(exc.stderr, str) else ""
        return 124, stdout, stderr, int((time.monotonic() - started) * 1000)
    return (
        result.returncode,
        result.stdout,
        result.stderr,
        int((time.monotonic() - started) * 1000),
    )


def parse_structured_output(stdout: str) -> Any:
    stripped = stdout.strip()
    if not stripped:
        return None
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        return {"raw": stripped[:MAX_WEB_BYTES]}


def usable_content(value: Any, raw: str = "") -> bool:
    if value is None:
        return bool(raw.strip())
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict)):
        return bool(value)
    return True


def command_payload(
    *, source: str, operation: str, backend: str, returncode: int,
    stdout: str, stderr: str, elapsed_ms: int,
) -> tuple[dict[str, Any], int]:
    data = parse_structured_output(stdout)
    ok = returncode == 0 and usable_content(data, stdout)
    payload: dict[str, Any] = {
        "source": source,
        "operation": operation,
        "backend": backend,
        "status": "ok" if ok else "failed",
        "evidence": "target data returned" if ok else "empty or failed result",
        "exit_code": returncode,
        "elapsed_ms": elapsed_ms,
        "data": data,
    }
    diagnostic = scrub(stderr)
    if diagnostic:
        payload["diagnostic"] = diagnostic
    return payload, EXIT_OK if ok else EXIT_FAILED


def search_url(source: str, query: str, *, mode: str, engine: str) -> dict[str, Any]:
    source = canonical_source(source)
    query = query.strip()
    if not query:
        raise ReachError("query must not be empty", EXIT_USAGE)
    if mode not in {"domain", "native"}:
        raise ReachError("mode must be domain or native", EXIT_USAGE)
    if engine not in {"google", "duckduckgo"}:
        raise ReachError("engine must be google or duckduckgo", EXIT_USAGE)

    if mode == "native":
        if source not in SOCIAL_SOURCES:
            raise ReachError("native search URLs are only defined for the four social sources", EXIT_USAGE)
        base = NATIVE_SEARCH_BASES[source]
        parameter = "search_query" if source == "youtube" else "keywords" if source == "linkedin" else "q"
        url = base + "?" + urllib.parse.urlencode({parameter: query})
        route = "native-site-search"
    else:
        if source == "web":
            scoped_query = query
        elif source in SOURCE_DOMAINS:
            scoped_query = f"site:{SOURCE_DOMAINS[source]} {query}"
        elif source == "github":
            scoped_query = f"site:github.com {query}"
        else:
            raise ReachError("domain search is not defined for rss; pass a feed URL instead", EXIT_USAGE)
        if engine == "google":
            url = "https://www.google.com/search?" + urllib.parse.urlencode({"q": scoped_query})
        else:
            url = "https://duckduckgo.com/?" + urllib.parse.urlencode({"q": scoped_query})
        route = "domain-scoped-search"

    return {
        "source": source,
        "operation": "search-url",
        "status": "ready",
        "route": route,
        "engine": engine if mode == "domain" else None,
        "query": query,
        "domain": SOURCE_DOMAINS.get(source),
        "url": url,
        "next": "open this URL with the native web tool or isolated Zen Agent bridge",
    }


def request_bytes(url: str, *, timeout: int, max_bytes: int) -> bytes:
    public_url = normalize_public_url(url, resolve_host=True)
    request = urllib.request.Request(
        public_url,
        headers={"User-Agent": "internet-reach/1.0", "Accept": "*/*"},
    )
    try:
        with open_public(request, timeout=timeout) as response:
            body = response.read(max_bytes + 1)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise ReachError(f"request failed: {scrub(str(exc))}", EXIT_FAILED) from exc
    if len(body) > max_bytes:
        raise ReachError("response exceeded the configured size limit", EXIT_FAILED)
    return body


def read_public_web(url: str, *, timeout: int) -> tuple[dict[str, Any], int]:
    public_url = normalize_public_url(url, resolve_host=True)
    reader_url = "https://r.jina.ai/" + public_url
    request = urllib.request.Request(
        reader_url,
        headers={"User-Agent": "internet-reach/1.0", "Accept": "text/plain"},
    )
    try:
        with open_public(request, timeout=timeout) as response:
            body = response.read(MAX_WEB_BYTES + 1)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return (
            {
                "source": "web",
                "operation": "read",
                "backend": "jina-reader",
                "status": "failed",
                "evidence": "no response",
                "error": scrub(str(exc)),
                "next": "use the user-controlled Zen Agent profile for a rendered page",
            },
            EXIT_FAILED,
        )
    if len(body) > MAX_WEB_BYTES:
        return (
            {
                "source": "web",
                "operation": "read",
                "backend": "jina-reader",
                "status": "failed",
                "evidence": "response exceeded size limit",
            },
            EXIT_FAILED,
        )
    text = body.decode("utf-8", errors="replace")
    sample = text[:4_096].casefold()
    if any(
        marker in sample
        for marker in (
            "requiring captcha",
            "title: just a moment",
            "security verification",
            "attention required! | cloudflare",
        )
    ):
        return (
            {
                "source": "web",
                "operation": "read",
                "backend": "jina-reader",
                "status": "blocked",
                "evidence": "reader returned an anti-bot page",
                "next": "use the user-controlled Zen Agent profile for the rendered page",
            },
            EXIT_FAILED,
        )
    if not text.strip():
        return (
            {
                "source": "web",
                "operation": "read",
                "backend": "jina-reader",
                "status": "failed",
                "evidence": "empty response",
            },
            EXIT_FAILED,
        )
    return (
        {
            "source": "web",
            "operation": "read",
            "backend": "jina-reader",
            "status": "ok",
            "evidence": "non-empty response",
            "url": public_url,
            "data": text,
        },
        EXIT_OK,
    )


def xml_local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()


def xml_text(element: ET.Element | None) -> str:
    if element is None:
        return ""
    return " ".join("".join(element.itertext()).split())


def first_child(element: ET.Element, names: set[str]) -> ET.Element | None:
    for child in list(element):
        if xml_local_name(child.tag) in names:
            return child
    return None


def feed_link(element: ET.Element) -> str:
    for child in list(element):
        if xml_local_name(child.tag) == "link":
            href = child.attrib.get("href")
            if href:
                return redact_url_query(href.strip())
            text = xml_text(child)
            if text:
                return redact_url_query(text)
    return ""


def parse_rss(url: str, *, limit: int, timeout: int) -> tuple[dict[str, Any], int]:
    public_url = normalize_public_url(url)
    body = request_bytes(public_url, timeout=timeout, max_bytes=MAX_RSS_BYTES)
    try:
        root = ET.fromstring(body)
    except ET.ParseError as exc:
        raise ReachError(f"RSS/Atom XML is invalid: {exc}", EXIT_FAILED) from exc

    entries: list[dict[str, str]] = []
    for element in root.iter():
        if xml_local_name(element.tag) not in {"item", "entry"}:
            continue
        title = xml_text(first_child(element, {"title"}))
        link = feed_link(element)
        published = xml_text(first_child(element, {"pubdate", "published", "updated", "date"}))
        summary = xml_text(first_child(element, {"description", "summary", "content", "encoded"}))
        if not (title or link or summary):
            continue
        entries.append({"title": title, "link": link, "published": published, "summary": summary[:4_000]})
        if len(entries) >= limit:
            break

    return (
        {
            "source": "rss",
            "operation": "read",
            "backend": "python-stdlib",
            "status": "ok" if entries else "failed",
            "evidence": f"{len(entries)} feed entries" if entries else "empty feed",
            "url": public_url,
            "data": {"entries": entries},
        },
        EXIT_OK if entries else EXIT_FAILED,
    )


def github_env() -> dict[str, str]:
    env = os.environ.copy()
    env.update(
        {
            "GH_TELEMETRY": "false",
            "DO_NOT_TRACK": "true",
            "GH_NO_UPDATE_NOTIFIER": "1",
            "GH_NO_EXTENSION_UPDATE_NOTIFIER": "1",
        }
    )
    return env


def github_search(query: str, *, limit: int, timeout: int) -> tuple[dict[str, Any], int]:
    query = query.strip()
    if not query:
        raise ReachError("query must not be empty", EXIT_USAGE)
    gh = shutil.which("gh")
    if gh:
        code, stdout, stderr, elapsed = run_argv(
            [
                gh,
                "search",
                "repos",
                query,
                "--limit",
                str(limit),
                "--json",
                # `fullName` is the field exposed by current GitHub CLI
                # releases. Keep the helper's output source-native rather
                # than depending on the removed `nameWithOwner` alias.
                "fullName,url,description,stargazersCount,updatedAt",
            ],
            timeout=timeout,
            env=github_env(),
        )
        return command_payload(
            source="github",
            operation="search",
            backend="gh",
            returncode=code,
            stdout=stdout,
            stderr=stderr,
            elapsed_ms=elapsed,
        )

    encoded = urllib.parse.urlencode({"q": query, "per_page": limit})
    body = request_bytes(
        f"https://api.github.com/search/repositories?{encoded}",
        timeout=timeout,
        max_bytes=MAX_WEB_BYTES,
    )
    try:
        data = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ReachError("GitHub API returned invalid JSON", EXIT_FAILED) from exc
    items = data.get("items") if isinstance(data, dict) else None
    return (
        {
            "source": "github",
            "operation": "search",
            "backend": "github-rest",
            "status": "ok" if items else "failed",
            "evidence": f"{len(items)} repository results" if items else "empty result",
            "data": items or [],
        },
        EXIT_OK if items else EXIT_FAILED,
    )


def github_read(target: str, *, timeout: int) -> tuple[dict[str, Any], int]:
    target = target.strip()
    if re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", target):
        gh = shutil.which("gh")
        if gh:
            code, stdout, stderr, elapsed = run_argv(
                [
                    gh,
                    "repo",
                    "view",
                    target,
                    "--json",
                    "nameWithOwner,url,description,defaultBranchRef,updatedAt",
                ],
                timeout=timeout,
                env=github_env(),
            )
            return command_payload(
                source="github",
                operation="read",
                backend="gh",
                returncode=code,
                stdout=stdout,
                stderr=stderr,
                elapsed_ms=elapsed,
            )
        owner, repo = target.split("/", 1)
        endpoint = "https://api.github.com/repos/" + urllib.parse.quote(
            owner, safe=""
        ) + "/" + urllib.parse.quote(repo, safe="")
        body = request_bytes(endpoint, timeout=timeout, max_bytes=MAX_WEB_BYTES)
        try:
            data = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ReachError("GitHub API returned invalid JSON", EXIT_FAILED) from exc
        if not isinstance(data, dict) or not data.get("full_name"):
            return (
                {
                    "source": "github",
                    "operation": "read",
                    "backend": "github-rest",
                    "status": "failed",
                    "evidence": "repository metadata unavailable",
                    "data": data if isinstance(data, dict) else None,
                },
                EXIT_FAILED,
            )
        return (
            {
                "source": "github",
                "operation": "read",
                "backend": "github-rest",
                "status": "ok",
                "evidence": "repository metadata returned",
                "data": {
                    "nameWithOwner": data.get("full_name"),
                    "url": data.get("html_url"),
                    "description": data.get("description"),
                    "defaultBranchRef": (
                        {"name": data["default_branch"]}
                        if data.get("default_branch")
                        else None
                    ),
                    "updatedAt": data.get("updated_at"),
                },
            },
            EXIT_OK,
        )
    public_url = normalize_public_url(target)
    if not source_url_allowed("github", public_url):
        raise ReachError("URL host does not belong to github", EXIT_USAGE)
    return read_public_web(public_url, timeout=timeout)


def find_executable(candidates: Iterable[str]) -> str | None:
    for candidate in candidates:
        path = shutil.which(candidate)
        if path:
            return path
        if os.path.isabs(candidate) and os.access(candidate, os.X_OK):
            return candidate
    return None


def bridge_state() -> dict[str, Any]:
    configured_url = os.environ.get("INTERNET_REACH_ZEN_BRIDGE_URL", "").strip()
    if configured_url:
        try:
            parsed = urllib.parse.urlsplit(configured_url)
        except ValueError as exc:
            raise ReachError(
                "INTERNET_REACH_ZEN_BRIDGE_URL is malformed", EXIT_USAGE
            ) from exc
        configured = parsed.scheme in {"ws", "wss"} and bool(parsed.hostname)
        if parsed.username or parsed.password:
            raise ReachError("INTERNET_REACH_ZEN_BRIDGE_URL must not contain credentials", EXIT_USAGE)
        if any(SENSITIVE_QUERY_NAME.search(name) for name, _ in urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)):
            raise ReachError(
                "INTERNET_REACH_ZEN_BRIDGE_URL must not contain credential-bearing query parameters",
                EXIT_USAGE,
            )
    else:
        configured = False
    profile_value = os.environ.get("INTERNET_REACH_AGENT_PROFILE", "").strip()
    profile = Path(profile_value).expanduser() if profile_value else DEFAULT_AGENT_PROFILE
    return {
        "server": "firefox-devtools-mcp",
        "mode": "isolated-profile",
        "profile_name": AGENT_PROFILE_NAME,
        "profile_path": str(profile),
        "profile_exists": profile.is_dir(),
        "configured_bridge_url": configured,
        "url": configured_url if configured else None,
        "note": "profile presence or a bridge URL does not prove connectivity, login, or target success",
    }


def doctor() -> tuple[dict[str, Any], int]:
    browsers = {
        family: {
            "installed": (path := find_executable(candidates)) is not None,
            **({"path": path} if path else {}),
        }
        for family, candidates in BROWSER_BINARIES.items()
    }
    return (
        {
            "source": "internet-reach",
            "operation": "doctor",
            "status": "ok",
            "tools": {
                "python3": bool(shutil.which("python3")),
                "gh": bool(shutil.which("gh")),
                "uvx": bool(shutil.which("uvx")),
            },
            "browsers": browsers,
            "zen_bridge": bridge_state(),
            "note": "a detected executable or configured bridge does not prove a target request will succeed",
        },
        EXIT_OK,
    )


def har_summary(path_value: str) -> tuple[dict[str, Any], int]:
    path = Path(path_value).expanduser()
    if path.is_symlink():
        raise ReachError("HAR symlinks are not accepted", EXIT_USAGE)
    if not path.is_file():
        raise ReachError(f"HAR file not found: {path}", EXIT_USAGE)
    if path.stat().st_size > MAX_HAR_BYTES:
        raise ReachError("HAR file exceeds the configured size limit", EXIT_USAGE)
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ReachError(f"cannot read HAR JSON: {exc}", EXIT_FAILED) from exc

    if not isinstance(document, dict):
        raise ReachError("HAR root must be an object", EXIT_USAGE)
    log = document.get("log")
    if not isinstance(log, dict):
        raise ReachError("HAR log must be an object", EXIT_USAGE)
    entries = log.get("entries")
    if not isinstance(entries, list):
        raise ReachError("HAR log.entries must be an array", EXIT_USAGE)
    if len(entries) > MAX_HAR_ENTRIES:
        raise ReachError(f"HAR contains more than {MAX_HAR_ENTRIES} entries; filter it first", EXIT_USAGE)

    summary: list[dict[str, Any]] = []
    for entry_index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ReachError(
                f"HAR entry {entry_index} must be an object", EXIT_USAGE
            )
        request = entry.get("request")
        response = entry.get("response")
        if not isinstance(request, dict) or not isinstance(request.get("url"), str):
            raise ReachError(
                f"HAR request.url must be a string at entry {entry_index}", EXIT_USAGE
            )
        try:
            parsed = urllib.parse.urlsplit(request["url"])
        except ValueError as exc:
            raise ReachError(
                f"HAR request URL is malformed at entry {entry_index}", EXIT_USAGE
            ) from exc
        headers_value = request.get("headers", [])
        cookies_value = request.get("cookies", [])
        if not isinstance(headers_value, list) or not isinstance(cookies_value, list):
            raise ReachError("HAR request headers and cookies must be arrays", EXIT_USAGE)
        header_names = [
            str(item.get("name", ""))
            for item in headers_value
            if isinstance(item, dict)
        ]
        cookie_names = [
            str(item.get("name", ""))
            for item in cookies_value
            if isinstance(item, dict)
        ]
        query_names = [name for name, _ in urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)]
        summary.append(
            {
                "method": request.get("method"),
                "host": parsed.hostname,
                "path": parsed.path or "/",
                "query_names": sorted(set(query_names)),
                "status": response.get("status") if isinstance(response, dict) else None,
                "mime_type": (
                    response.get("content", {}).get("mimeType")
                    if isinstance(response, dict) and isinstance(response.get("content"), dict)
                    else None
                ),
                "request_header_names": sorted(name for name in header_names if name),
                "sensitive_headers_present": sorted(
                    name for name in header_names if SENSITIVE_HEADER.search(name)
                ),
                "cookie_names": sorted(name for name in cookie_names if name),
                "has_post_data": bool(request.get("postData")),
            }
        )

    return (
        {
            "source": "har",
            "operation": "summarize",
            "backend": "python-stdlib",
            "status": "ok",
            "evidence": f"{len(summary)} entries summarized without values",
            "file": str(path),
            "data": summary,
        },
        EXIT_OK,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="bounded internet-reach helpers")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("doctor")

    url_parser = sub.add_parser("search-url")
    url_parser.add_argument("source")
    url_parser.add_argument("query")
    url_parser.add_argument("--mode", choices=("domain", "native"), default="domain")
    url_parser.add_argument("--engine", choices=("google", "duckduckgo"), default="google")

    read = sub.add_parser("read")
    read.add_argument("source")
    read.add_argument("target")
    read.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    read.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)

    search = sub.add_parser("search")
    search.add_argument("source")
    search.add_argument("query")
    search.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    search.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)

    har = sub.add_parser("har")
    har_sub = har.add_subparsers(dest="har_command", required=True)
    summarize = har_sub.add_parser("summarize")
    summarize.add_argument("path")
    return parser


def browser_search_plan(source: str, query: str, *, limit: int) -> tuple[dict[str, Any], int]:
    payload = search_url(source, query, mode="native", engine="google")
    payload.update(
        {
            "operation": "search",
            "status": "browser_required",
            "limit": bounded_limit(limit),
            "next": "open the URL with the isolated Zen Agent bridge, wait for results, and return only matching source links",
        }
    )
    return payload, EXIT_UNAVAILABLE


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "doctor":
            payload, code = doctor()
            return emit(payload, code)
        if args.command == "search-url":
            return emit(search_url(args.source, args.query, mode=args.mode, engine=args.engine))
        if args.command == "har":
            if args.har_command != "summarize":
                raise ReachError("unknown HAR command", EXIT_USAGE)
            payload, code = har_summary(args.path)
            return emit(payload, code)

        timeout = bounded_timeout(args.timeout)
        source = canonical_source(args.source)
        if args.command == "search":
            limit = bounded_limit(args.limit)
            if source == "github":
                payload, code = github_search(args.query, limit=limit, timeout=timeout)
            elif source in SOCIAL_SOURCES:
                payload, code = browser_search_plan(source, args.query, limit=limit)
            else:
                raise ReachError(
                    "use search-url or the active harness web-search tool for web; rss requires a feed URL",
                    EXIT_USAGE,
                )
            return emit(payload, code)

        if args.command == "read":
            if source == "web":
                payload, code = read_public_web(args.target, timeout=timeout)
            elif source == "rss":
                payload, code = parse_rss(args.target, limit=bounded_limit(args.limit), timeout=timeout)
            elif source == "github":
                payload, code = github_read(args.target, timeout=timeout)
            elif source in SOCIAL_SOURCES:
                target = normalize_public_url(args.target)
                if not source_url_allowed(source, target):
                    raise ReachError(f"URL host does not belong to {source}", EXIT_USAGE)
                payload = {
                    "source": source,
                    "operation": "read",
                    "backend": "zen-firefox-mcp",
                    "status": "browser_required",
                    "evidence": "no browser action performed by this helper",
                    "url": target,
                    "next": "read the rendered page with the isolated Zen Agent browser bridge",
                }
                code = EXIT_UNAVAILABLE
            else:
                raise ReachError(f"read is not supported for {source}", EXIT_USAGE)
            return emit(payload, code)

        raise ReachError("unknown command", EXIT_USAGE)
    except ReachError as exc:
        return error_payload(exc)
    except KeyboardInterrupt:
        return error_payload(ReachError("interrupted", EXIT_FAILED))


if __name__ == "__main__":
    raise SystemExit(main())

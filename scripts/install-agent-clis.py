#!/usr/bin/env python3
"""Install the reviewed private CLI packages from an immutable Git revision."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
import tarfile
import tempfile

REVISION = "92b90d33b40996b8a4aad070050073990c9be6f9"
PACKAGES = ("core", "linktree")


def run(argv, cwd=None):
    return subprocess.run(argv, cwd=cwd, check=True, text=True, capture_output=True).stdout


def git_args(source, *arguments):
    return ["git", "--no-replace-objects", "-C", str(source), *arguments]


def validate_launcher(launcher, wrapper):
    if not os.access(launcher, os.X_OK) or launcher.read_text() != wrapper:
        raise ValueError("incomplete or different launcher; choose a fresh prefix/bin directory")


def validate_receipt(prefix, receipt):
    files = receipt["installed_files"]
    required = {"node_modules/@agent-clis/core/package.json",
                "node_modules/@agent-clis/linktree/dist/cli.js"}
    if not isinstance(files, dict) or not required.issubset(files):
        raise ValueError("incomplete installation receipt")
    for path, digest in files.items():
        relative = Path(path)
        if (relative.is_absolute() or ".." in relative.parts
                or relative.parts[:3] not in [("node_modules", "@agent-clis", p) for p in PACKAGES]
                or not isinstance(digest, str) or len(digest) != 64):
            raise ValueError("invalid installed-file identity")
        target = prefix / relative
        if not target.resolve().is_relative_to(prefix.resolve()):
            raise ValueError("installed file escapes its prefix")
        if hashlib.sha256(target.read_bytes()).hexdigest() != digest:
            raise ValueError("installed CLI changed; choose a fresh installation location")


def install(source, prefix, bin_dir):
    source, prefix, bin_dir = source.resolve(), prefix.resolve(), bin_dir.resolve()
    version = run(["node", "--version"]).strip()
    if int(version.lstrip("v").split(".")[0]) < 24:
        raise ValueError("agent-clis requires Node 24 or later")
    run(git_args(source, "cat-file", "-e", REVISION + "^{commit}"))
    launcher = bin_dir / "linktree-agent"
    cli = prefix / "node_modules/@agent-clis/linktree/dist/cli.js"
    wrapper = "#!/usr/bin/env bash\nexec node " + shlex.quote(str(cli)) + ' "$@"\n'
    receipt_path = prefix / "install-receipt.json"
    if prefix.exists():
        try:
            receipt = json.loads(receipt_path.read_text())
            validate_launcher(launcher, wrapper)
        except FileNotFoundError as exc:
            raise ValueError("incomplete installation; choose a fresh prefix/bin directory") from exc
        if receipt["source_revision"] != REVISION:
            raise ValueError("existing installation differs; choose a fresh prefix/bin directory")
        validate_receipt(prefix, receipt)
        json.loads(run([str(launcher), "commands", "--json"]))
        return launcher
    if launcher.exists() or launcher.is_symlink():
        raise ValueError("refusing to replace an existing linktree-agent executable")
    prefix.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="agent-clis-build-") as temporary:
        build = Path(temporary) / "source"
        build.mkdir()
        archive = Path(temporary) / "source.tar"
        with archive.open("wb") as stream:
            subprocess.run(git_args(source, "archive", REVISION), stdout=stream, check=True)
        with tarfile.open(archive) as contents:
            contents.extractall(build, filter="data")
        run(["corepack", "pnpm", "install", "--frozen-lockfile"], build)
        artifacts = Path(temporary) / "artifacts"
        artifacts.mkdir()
        for package in PACKAGES:
            run(["corepack", "pnpm", "--filter", "@agent-clis/" + package,
                 "pack", "--pack-destination", str(artifacts)], build)
        tarballs = sorted(artifacts.glob("*.tgz"))
        if len(tarballs) != 2:
            raise ValueError("expected both matching core and Linktree packages")
        with tempfile.TemporaryDirectory(prefix=".agent-clis-install-", dir=prefix.parent) as staging:
            stage = Path(staging) / "runtime"
            run(["npm", "install", "--prefix", str(stage), "--ignore-scripts", "--no-audit",
                 "--no-fund", *map(str, tarballs)])
            commands = json.loads(run(["node", str(stage / "node_modules/@agent-clis/linktree/dist/cli.js"),
                                      "commands", "--json"]))
            if not isinstance(commands, list) or not commands:
                raise ValueError("installed CLI returned no command inventory")
            installed = {}
            for package in PACKAGES:
                for path in sorted((stage / "node_modules/@agent-clis" / package).rglob("*")):
                    if path.is_file():
                        installed[str(path.relative_to(stage))] = hashlib.sha256(path.read_bytes()).hexdigest()
            receipt = {"source_revision": REVISION, "installed_files": installed,
                       "artifacts": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in tarballs}}
            (stage / "install-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
            stage.rename(prefix)
    bin_dir.mkdir(parents=True, exist_ok=True)
    with launcher.open("x") as stream:
        stream.write(wrapper)
    launcher.chmod(0o755)
    json.loads(run([str(launcher), "commands", "--json"]))
    return launcher


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True, help="local agent-clis Git checkout")
    parser.add_argument("--prefix", type=Path, default=Path.home() / ".local/share/astatide-agent-clis" / REVISION)
    parser.add_argument("--bin-dir", type=Path, default=Path.home() / ".local/bin")
    args = parser.parse_args()
    try:
        print("Installed CLI:", install(args.source, args.prefix, args.bin_dir))
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as exc:
        detail = exc.stderr if isinstance(exc, subprocess.CalledProcessError) else str(exc)
        parser.exit(1, "CLI installation failed: " + str(detail) + "\n")

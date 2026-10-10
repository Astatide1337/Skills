#!/usr/bin/env python3
"""Install the reviewed private CLI packages from an immutable Git revision."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import tarfile
import tempfile

REVISION = "7048e748fd890340bbc03399b0dc1d619091af67"
PACKAGE_CONTRACTS = (
    {
        "directory": "core",
        "name": "@agent-clis/core",
        "version": "0.1.0",
        "bin": {},
        "required_files": ("dist/index.js",),
        "dependencies": {},
    },
    {
        "directory": "shrunk-cli",
        "name": "@agent-clis/shrunk-cli",
        "version": "0.1.0",
        "bin": {"shrunk-agent": "src/cli.mjs"},
        "required_files": (
            "src/cli.mjs",
            "support/bootstrap.py",
            "support/fixture-users.json",
        ),
        "exports": {"./cli": "./src/cli.mjs"},
        "dependencies": {},
    },
    {
        "directory": "linktree",
        "name": "@agent-clis/linktree",
        "version": "0.2.0",
        "bin": {"linktree-agent": "dist/cli.js"},
        "required_files": ("dist/cli.js",),
        "dependencies": {
            "@agent-clis/core": "0.1.0",
            "@agent-clis/shrunk-cli": "0.1.0",
        },
    },
)
PACKAGES_BY_NAME = {package["name"]: package for package in PACKAGE_CONTRACTS}


def run(argv, cwd=None):
    return subprocess.run(argv, cwd=cwd, check=True, text=True, capture_output=True).stdout


def git_args(source, *arguments):
    return ["git", "--no-replace-objects", "-C", str(source), *arguments]


def expected_package_receipt():
    return {
        package["directory"]: {
            "name": package["name"],
            "version": package["version"],
            "bin": package["bin"],
        }
        for package in PACKAGE_CONTRACTS
    }


def validate_manifest(manifest, package, context):
    if not isinstance(manifest, dict):
        raise ValueError(f"invalid {context} package manifest")
    if (manifest.get("name") != package["name"]
            or manifest.get("version") != package["version"]
            or manifest.get("private") is not True):
        raise ValueError(f"unexpected package identity in {context}")
    if manifest.get("bin", {}) != package["bin"]:
        raise ValueError(f"unexpected executable mapping in {context}")
    if "exports" in package and manifest.get("exports") != package["exports"]:
        raise ValueError(f"unexpected package exports in {context}")
    dependencies = manifest.get("dependencies", {})
    if not isinstance(dependencies, dict):
        raise ValueError(f"invalid dependency map in {context}")
    for name, version in package["dependencies"].items():
        if dependencies.get(name) != version:
            raise ValueError(f"{context} is missing required dependency {name}@{version}")


def validate_installed_packages(prefix):
    packages_root = prefix / "node_modules/@agent-clis"
    for package in PACKAGE_CONTRACTS:
        package_root = packages_root / package["directory"]
        try:
            manifest = json.loads((package_root / "package.json").read_text())
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"missing or invalid {package['name']} installation") from exc
        validate_manifest(manifest, package, package["name"])
        for relative in ("package.json", *package["required_files"]):
            target = package_root / relative
            if not target.is_file():
                raise ValueError(f"{package['name']} is missing {relative}")

    for package in PACKAGE_CONTRACTS:
        for name, path in package["bin"].items():
            executable = prefix / "node_modules/.bin" / name
            expected = packages_root / package["directory"] / path
            if not executable.exists() or executable.resolve() != expected.resolve():
                raise ValueError(f"missing or incorrect installed executable {name}")


def validate_receipt(prefix, receipt):
    if (not isinstance(receipt, dict) or type(receipt.get("schema")) is not int
            or receipt.get("schema") != 1):
        raise ValueError("unsupported or incomplete installation receipt")
    if receipt.get("source_revision") != REVISION:
        raise ValueError("existing installation differs; choose a fresh prefix/bin directory")
    if receipt.get("packages") != expected_package_receipt():
        raise ValueError("installation receipt has an unexpected package set")
    validate_installed_packages(prefix)

    files = receipt.get("installed_files")
    required = {
        f"node_modules/@agent-clis/{package['directory']}/{relative}"
        for package in PACKAGE_CONTRACTS
        for relative in ("package.json", *package["required_files"])
    }
    if not isinstance(files, dict) or not required.issubset(files):
        raise ValueError("incomplete installation receipt")
    actual_files = set()
    for package in PACKAGE_CONTRACTS:
        package_root = prefix / "node_modules/@agent-clis" / package["directory"]
        actual_files.update(
            str(path.relative_to(prefix))
            for path in package_root.rglob("*")
            if path.is_file()
        )
    for path, digest in files.items():
        if not isinstance(path, str):
            raise ValueError("invalid installed-file identity")
        relative = Path(path)
        if (relative.is_absolute() or ".." in relative.parts
                or relative.parts[:3] not in [
                    ("node_modules", "@agent-clis", package["directory"])
                    for package in PACKAGE_CONTRACTS
                ]
                or not isinstance(digest, str)
                or not re.fullmatch(r"[0-9a-f]{64}", digest)):
            raise ValueError("invalid installed-file identity")
        target = prefix / relative
        if not target.resolve().is_relative_to(prefix.resolve()):
            raise ValueError("installed file escapes its prefix")
        if hashlib.sha256(target.read_bytes()).hexdigest() != digest:
            raise ValueError("installed CLI changed; choose a fresh installation location")
    if set(files) != actual_files:
        raise ValueError("installation receipt does not match the installed package files")

    artifacts = receipt.get("artifacts")
    if (not isinstance(artifacts, dict)
            or set(artifacts) != set(PACKAGES_BY_NAME)
            or any(not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value)
                   for value in artifacts.values())):
        raise ValueError("installation receipt has an incomplete package artifact set")


def validate_launcher(launcher, wrapper):
    if not os.access(launcher, os.X_OK) or launcher.read_text() != wrapper:
        raise ValueError("incomplete or different launcher; choose a fresh prefix/bin directory")


def read_tarball_manifest(tarball):
    try:
        with tarfile.open(tarball, "r:gz") as contents:
            member = contents.getmember("package/package.json")
            stream = contents.extractfile(member)
            if stream is None:
                raise ValueError("package tarball has no manifest")
            return json.load(stream)
    except (OSError, KeyError, tarfile.TarError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid package tarball {tarball.name}") from exc


def installed_file_digests(prefix):
    installed = {}
    for package in PACKAGE_CONTRACTS:
        package_root = prefix / "node_modules/@agent-clis" / package["directory"]
        for path in sorted(package_root.rglob("*")):
            if path.is_file():
                installed[str(path.relative_to(prefix))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return installed


def install(source, prefix, bin_dir):
    source, prefix, bin_dir = source.resolve(), prefix.resolve(), bin_dir.resolve()
    version = run(["node", "--version"]).strip()
    if int(version.lstrip("v").split(".")[0]) < 24:
        raise ValueError("agent-clis requires Node 24 or later")

    run(git_args(source, "cat-file", "-e", REVISION + "^{commit}"))
    linktree_cli = prefix / "node_modules/@agent-clis/linktree/dist/cli.js"
    shrunk_cli = prefix / "node_modules/@agent-clis/shrunk-cli/src/cli.mjs"
    launchers = {
        "linktree-agent": (bin_dir / "linktree-agent", linktree_cli),
        "shrunk-agent": (bin_dir / "shrunk-agent", shrunk_cli),
    }
    wrappers = {
        name: "#!/usr/bin/env bash\nexec node " + shlex.quote(str(cli)) + ' "$@"\n'
        for name, (_, cli) in launchers.items()
    }
    receipt_path = prefix / "install-receipt.json"
    if prefix.exists():
        try:
            receipt = json.loads(receipt_path.read_text())
            for name, (launcher, _) in launchers.items():
                validate_launcher(launcher, wrappers[name])
        except FileNotFoundError as exc:
            raise ValueError("incomplete installation; choose a fresh prefix/bin directory") from exc
        validate_receipt(prefix, receipt)
        json.loads(run([str(launchers["linktree-agent"][0]), "commands", "--json"]))
        return launchers["linktree-agent"][0]

    for name, (launcher, _) in launchers.items():
        if launcher.exists() or launcher.is_symlink():
            raise ValueError(f"refusing to replace an existing {name} executable")

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
        for package in PACKAGE_CONTRACTS:
            run(["corepack", "pnpm", "--filter", package["name"],
                 "pack", "--pack-destination", str(artifacts)], build)

        tarballs = sorted(artifacts.glob("*.tgz"))
        packed_by_name = {}
        for tarball in tarballs:
            manifest = read_tarball_manifest(tarball)
            package = PACKAGES_BY_NAME.get(manifest.get("name")) if isinstance(manifest, dict) else None
            if package is None or package["name"] in packed_by_name:
                raise ValueError("package build produced an unexpected or duplicate artifact")
            validate_manifest(manifest, package, tarball.name)
            packed_by_name[package["name"]] = tarball
        if set(packed_by_name) != set(PACKAGES_BY_NAME):
            raise ValueError("expected matching core, Shrunk and Linktree packages")

        with tempfile.TemporaryDirectory(prefix=".agent-clis-install-", dir=prefix.parent) as staging:
            stage = Path(staging) / "runtime"
            ordered_tarballs = [packed_by_name[package["name"]] for package in PACKAGE_CONTRACTS]
            run(["npm", "install", "--prefix", str(stage), "--ignore-scripts", "--no-audit",
                 "--no-fund", *map(str, ordered_tarballs)])
            validate_installed_packages(stage)
            commands = json.loads(run([str(stage / "node_modules/.bin/linktree-agent"),
                                      "commands", "--json"]))
            if not isinstance(commands, list) or not commands:
                raise ValueError("installed Linktree CLI returned no command inventory")
            receipt = {
                "schema": 1,
                "source_revision": REVISION,
                "packages": expected_package_receipt(),
                "installed_files": installed_file_digests(stage),
                "artifacts": {
                    name: hashlib.sha256(tarball.read_bytes()).hexdigest()
                    for name, tarball in packed_by_name.items()
                },
            }
            (stage / "install-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
            stage.rename(prefix)

    bin_dir.mkdir(parents=True, exist_ok=True)
    for name, (launcher, _) in launchers.items():
        with launcher.open("x") as stream:
            stream.write(wrappers[name])
        launcher.chmod(0o755)
    for name, (launcher, _) in launchers.items():
        validate_launcher(launcher, wrappers[name])
    validate_receipt(prefix, json.loads(receipt_path.read_text()))
    json.loads(run([str(launchers["linktree-agent"][0]), "commands", "--json"]))
    return launchers["linktree-agent"][0]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True, help="local agent-clis Git checkout")
    parser.add_argument("--prefix", type=Path, default=Path.home() / ".local/share/astatide-agent-clis" / REVISION)
    parser.add_argument("--bin-dir", type=Path, default=Path.home() / ".local/bin")
    args = parser.parse_args()
    try:
        linktree = install(args.source, args.prefix, args.bin_dir)
        print("Installed CLIs:", linktree, "and", linktree.with_name("shrunk-agent"))
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as exc:
        detail = exc.stderr if isinstance(exc, subprocess.CalledProcessError) else str(exc)
        parser.exit(1, "CLI installation failed: " + str(detail) + "\n")

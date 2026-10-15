#!/usr/bin/env bash

set -euo pipefail

usage() {
  cat <<'EOF'
Usage: ./scripts/install.sh [--all | --skill NAME ...] [--target PATH]
       ./scripts/install.sh --retire internet-reach --target PATH
       ./scripts/install.sh --list

Options:
  --all             Install every skill in the repository.
  --list            List available skill names and exit.
  --skill NAME     Install one named skill; may be repeated.
  --target PATH    Directory that directly contains installed skill folders.
  --retire NAME    Remove only a byte-identical known retired skill; requires --target.
  -h, --help       Show this help.

Without --target, the installer checks the current project's .agents directory,
then ~/.agents (Codex's primary user location), ~/.codex (legacy Codex),
~/.config/opencode, and ~/.claude. Pass --target when more than one harness is
present or when installing into a different project.
EOF
}

repo_root=$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
skills_root="$repo_root/skills"
target=""
install_all=false
list_only=false
retire=""
declare -a requested=()

while (($# > 0)); do
  case "$1" in
    --all)
      install_all=true
      ;;
    --list)
      list_only=true
      ;;
    --skill)
      (($# >= 2)) || { printf '%s\n' '--skill requires a name' >&2; exit 2; }
      requested+=("$2")
      shift
      ;;
    --target)
      (($# >= 2)) || { printf '%s\n' '--target requires a path' >&2; exit 2; }
      target="$2"
      shift
      ;;
    --retire)
      (($# >= 2)) || { printf '%s\n' '--retire requires a name' >&2; exit 2; }
      retire="$2"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      printf 'Unknown option: %s\n' "$1" >&2
      usage >&2
      exit 2
      ;;
  esac
  shift
done

mapfile -t available < <(find "$skills_root" -mindepth 1 -maxdepth 1 -type d -printf '%f\n' | sort)
((${#available[@]} > 0)) || { printf '%s\n' 'No skills found under skills/' >&2; exit 1; }

if "$list_only" && [[ -z "$retire" ]]; then
  printf '%s\n' "${available[@]}"
  exit 0
fi

if [[ -n "$retire" ]]; then
  [[ -n "$target" && "$install_all" == false && "$list_only" == false && ${#requested[@]} == 0 ]] || {
    printf '%s\n' 'Retirement requires explicit --target and cannot be combined with installation or --list.' >&2; exit 2;
  }
  python3 - "$repo_root" "$target" "$retire" <<'PYRETIRE'
import hashlib
import json
from pathlib import Path
import shutil
import sys

root, target_arg, name = sys.argv[1:]
root = Path(root).resolve()
target = Path(target_arg).resolve()
known = json.loads((root / "scripts/retired-skills.json").read_text())
if name not in known:
    sys.exit("No supported retirement for this skill; nothing removed.")
if target in (Path("/"), Path.home()) or target == root / "skills" or (root / "skills") in target.parents:
    sys.exit("Refusing unsafe retirement target; nothing removed.")
package = target / name
if package.is_symlink():
    sys.exit("Refusing a symlinked retired package; nothing removed.")
if not package.exists():
    print(f"already absent: {package}")
    sys.exit(0)
if not package.is_dir():
    sys.exit("Retired package is not a directory; nothing removed.")
files = {}
for path in package.rglob("*"):
    if path.is_symlink() or not (path.is_file() or path.is_dir()):
        sys.exit("Retired package contains a symlink or special file; nothing removed.")
    if path.is_file():
        files[str(path.relative_to(package))] = hashlib.sha256(path.read_bytes()).hexdigest()
for revision, expected in known[name].items():
    directories = {str(parent) for relative in expected for parent in Path(relative).parents if str(parent) != "."}
    actual_directories = {str(p.relative_to(package)) for p in package.rglob("*") if p.is_dir()}
    if files == expected and actual_directories == directories:
        shutil.rmtree(package)
        print(f"retired {name} from {package}; matched {revision}")
        break
else:
    sys.exit("Retired package is customized or unknown; preserve it and remove it manually after review. Nothing removed.")
PYRETIRE
  exit $?
fi

if [[ -z "$target" ]]; then
  if [[ -d "$repo_root/.agents" ]]; then
    target="$repo_root/.agents/skills"
  elif [[ -d "${HOME:-}/.agents" ]]; then
    target="${HOME}/.agents/skills"
  elif [[ -d "${HOME:-}/.codex" ]]; then
    target="${HOME}/.codex/skills"
  elif [[ -d "${HOME:-}/.config/opencode" ]]; then
    target="${HOME}/.config/opencode/skills"
  elif [[ -d "${HOME:-}/.claude" ]]; then
    target="${HOME}/.claude/skills"
  else
    printf '%s\n' 'Cannot detect a harness target; pass --target explicitly.' >&2
    exit 2
  fi
fi

if "$install_all" && ((${#requested[@]} > 0)); then
  printf '%s\n' 'Use --all or --skill, not both.' >&2
  exit 2
fi

if ! "$install_all" && ((${#requested[@]} == 0)); then
  if [[ ! -t 0 ]]; then
    printf '%s\n' 'Non-interactive install requires --all or at least one --skill.' >&2
    exit 2
  fi
  printf '%s\n' 'Available skills:'
  printf '  %s\n' "${available[@]}"
  printf '%s' 'Enter comma-separated skill names: '
  IFS= read -r selection
  IFS=',' read -r -a requested <<< "$selection"
fi

declare -A known=()
for skill in "${available[@]}"; do
  known["$skill"]=1
done

if "$install_all"; then
  requested=("${available[@]}")
fi

for skill in "${requested[@]}"; do
  [[ "$skill" =~ ^[a-z0-9]+(-[a-z0-9]+)*$ ]] || {
    printf 'Invalid skill name: %s\n' "$skill" >&2
    exit 2
  }
  [[ -n "${known[$skill]:-}" ]] || {
    printf 'Unknown skill: %s\n' "$skill" >&2
    exit 2
  }
done

mkdir -p -- "$target"
target=$(CDPATH= cd -- "$target" && pwd -P)
case "$target" in
  /|"$HOME")
    printf 'Refusing unsafe target: %s\n' "$target" >&2
    exit 2
    ;;
esac

if [[ "$target" == "$skills_root" || "$target" == "$skills_root/"* ]]; then
  printf '%s\n' 'Refusing to install into the source skill tree.' >&2
  exit 2
fi

# This is the one concrete runtime dependency used by portable_lint.py.
# Explicitly selecting verify-work keeps the normal replacement semantics.
needs_profile=false
profile_selected=false
for skill in "${requested[@]}"; do
  [[ "$skill" != code-review-and-quality ]] || needs_profile=true
  [[ "$skill" != verify-work ]] || profile_selected=true
done
if "$needs_profile" && ! "$profile_selected"; then
  dependency="$target/verify-work"
  if [[ -e "$dependency" || -L "$dependency" ]]; then
    helper="$dependency/scripts/check_profile.py"
    if [[ -L "$dependency" || -L "$dependency/scripts" || -L "$helper" || ! -f "$helper" ]] ||
       ! cmp -s -- "$skills_root/verify-work/scripts/check_profile.py" "$helper"; then
      printf '%s\n' 'Existing verify-work helper is incompatible; preserve customizations and select --skill verify-work explicitly to replace it.' >&2
      exit 2
    fi
    printf '%s\n' 'reusing compatible verify-work helper'
  else
    requested+=(verify-work)
    printf '%s\n' 'including required dependency: verify-work'
  fi
fi

for skill in "${requested[@]}"; do
  destination="$target/$skill"
  rm -rf -- "$destination"
  cp -a -- "$skills_root/$skill" "$destination"
  printf 'installed %s -> %s\n' "$skill" "$destination"
done

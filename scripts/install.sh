#!/usr/bin/env bash

set -euo pipefail

usage() {
  cat <<'EOF'
Usage: ./scripts/install.sh [--all | --skill NAME ...] [--target PATH]
       ./scripts/install.sh --list

Options:
  --all             Install every skill in the repository.
  --list            List available skill names and exit.
  --skill NAME     Install one named skill; may be repeated.
  --target PATH    Directory that directly contains installed skill folders.
  -h, --help       Show this help.

Without --target, the installer checks ~/.codex, ~/.claude, and the current
project's .agents directory in that order. Pass --target when more than one
harness is present or when installing into a different project.
EOF
}

repo_root=$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
skills_root="$repo_root/skills"
target=""
install_all=false
list_only=false
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

if "$list_only"; then
  printf '%s\n' "${available[@]}"
  exit 0
fi

if [[ -z "$target" ]]; then
  if [[ -d "${HOME:-}/.codex" ]]; then
    target="${HOME}/.codex/skills"
  elif [[ -d "${HOME:-}/.claude" ]]; then
    target="${HOME}/.claude/skills"
  elif [[ -d "$repo_root/.agents" ]]; then
    target="$repo_root/.agents/skills"
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
target=$(CDPATH= cd -- "$target" && pwd)
case "$target" in
  /|"$HOME")
    printf 'Refusing unsafe target: %s\n' "$target" >&2
    exit 2
    ;;
esac

for skill in "${requested[@]}"; do
  destination="$target/$skill"
  rm -rf -- "$destination"
  cp -a -- "$skills_root/$skill" "$destination"
  printf 'installed %s -> %s\n' "$skill" "$destination"
done

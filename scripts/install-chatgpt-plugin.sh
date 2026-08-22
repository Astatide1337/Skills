#!/usr/bin/env bash

set -euo pipefail

plugin_name="astatide-skills"
repo_root=$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
source_skills="$repo_root/skills"
template_root="$repo_root/chatgpt-plugin"
codex_home_dir="${CODEX_HOME:-$HOME/.codex}"
plugin_creator_root="$codex_home_dir/skills/.system/plugin-creator"
plugin_parent="${CHATGPT_PLUGIN_PARENT:-$HOME/plugins}"
plugin_root="$plugin_parent/$plugin_name"
state_root="${XDG_STATE_HOME:-$HOME/.local/state}/skills-catalog-backups"

usage() {
  cat <<'EOF'
Usage: ./scripts/install-chatgpt-plugin.sh

Materialize the current catalog as the personal `astatide-skills` ChatGPT/Codex
plugin and add or refresh its personal marketplace entry. The plugin is written
to ~/plugins/astatide-skills by default. Override that parent directory with
CHATGPT_PLUGIN_PARENT when needed.
EOF
}

if (($# > 0)); then
  case "$1" in
    -h|--help)
      usage
      exit 0
      ;;
    *)
      usage >&2
      exit 2
      ;;
  esac
fi

[[ -d "$source_skills" ]] || { printf '%s\n' "Missing catalog: $source_skills" >&2; exit 1; }
[[ -f "$template_root/.codex-plugin/plugin.json" ]] || {
  printf '%s\n' "Missing plugin template: $template_root/.codex-plugin/plugin.json" >&2
  exit 1
}
[[ -f "$plugin_creator_root/scripts/create_basic_plugin.py" ]] || {
  printf '%s\n' "plugin-creator is unavailable at $plugin_creator_root" >&2
  exit 1
}
[[ -f "$plugin_creator_root/scripts/update_plugin_cachebuster.py" ]] || {
  printf '%s\n' "plugin-creator cachebuster is unavailable at $plugin_creator_root" >&2
  exit 1
}
[[ -f "$plugin_creator_root/scripts/validate_plugin.py" ]] || {
  printf '%s\n' "plugin-creator validator is unavailable at $plugin_creator_root" >&2
  exit 1
}

mkdir -p -- "$plugin_parent"
plugin_parent=$(CDPATH= cd -- "$plugin_parent" && pwd)
plugin_root="$plugin_parent/$plugin_name"

case "$plugin_root" in
  /|"$HOME"|"$HOME"/*/..)
    printf '%s\n' "Refusing unsafe plugin target: $plugin_root" >&2
    exit 2
    ;;
esac

stage_root=$(mktemp -d "$plugin_parent/.${plugin_name}.stage.XXXXXX")
cleanup() {
  rm -rf -- "$stage_root"
}
trap cleanup EXIT

cp -a -- "$template_root/." "$stage_root/"
mkdir -p -- "$stage_root/skills"
cp -a -- "$source_skills/." "$stage_root/skills/"
python3 "$plugin_creator_root/scripts/validate_plugin.py" "$stage_root"

if [[ -e "$plugin_root" || -L "$plugin_root" ]]; then
  existing_name=""
  if [[ -f "$plugin_root/.codex-plugin/plugin.json" ]]; then
    existing_name=$(python3 - "$plugin_root/.codex-plugin/plugin.json" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    payload = json.load(handle)
print(payload.get("name", ""))
PY
)
  fi
  [[ "$existing_name" == "$plugin_name" ]] || {
    printf '%s\n' "Refusing to replace non-$plugin_name target: $plugin_root" >&2
    exit 2
  }
  timestamp=$(date -u +%Y%m%d-%H%M%S)
  backup_root="$state_root/chatgpt-plugin-$timestamp"
  mkdir -p -- "$backup_root"
  mv -- "$plugin_root" "$backup_root/$plugin_name"
  printf 'backed up %s -> %s\n' "$plugin_root" "$backup_root/$plugin_name"
fi

python3 "$plugin_creator_root/scripts/create_basic_plugin.py" \
  "$plugin_name" \
  --path "$plugin_parent" \
  --with-skills \
  --with-marketplace \
  --force

rm -rf -- "$plugin_root"
mv -- "$stage_root" "$plugin_root"
trap - EXIT

python3 "$plugin_creator_root/scripts/update_plugin_cachebuster.py" "$plugin_root"
python3 "$plugin_creator_root/scripts/validate_plugin.py" "$plugin_root"
printf 'installed %s -> %s\n' "$plugin_name" "$plugin_root"
printf '%s\n' 'Open ChatGPT Plugins, install Astatide Skills from Personal, then start a new chat.'

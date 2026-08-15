#!/usr/bin/env bash

set -euo pipefail

repo_root=$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
skills_root="$repo_root/skills"
catalog="$repo_root/catalog.yaml"

command -v yq >/dev/null 2>&1 || {
  printf '%s\n' 'validate-skills.sh requires yq.' >&2
  exit 1
}

expected=$(yq '.skills | length' "$catalog")
mapfile -t files < <(find "$skills_root" -mindepth 2 -maxdepth 2 -type f -name SKILL.md | sort)
((expected == ${#files[@]})) || {
  printf 'catalog has %s skills but filesystem has %s SKILL.md files\n' "$expected" "${#files[@]}" >&2
  exit 1
}

declare -A seen=()
for file in "${files[@]}"; do
  skill_dir=$(dirname -- "$file")
  skill_name=$(basename -- "$skill_dir")
  frontmatter=$(awk '
    NR == 1 && $0 == "---" { inside = 1; next }
    inside && $0 == "---" { exit }
    inside { print }
  ' "$file")

  [[ -n "$frontmatter" ]] || { printf 'missing frontmatter: %s\n' "$file" >&2; exit 1; }
  name=$(printf '%s\n' "$frontmatter" | yq -p yaml -r '.name // ""' -)
  description=$(printf '%s\n' "$frontmatter" | yq -p yaml -r '.description // ""' -)

  [[ "$name" == "$skill_name" ]] || {
    printf 'directory/name mismatch: %s declares %s\n' "$file" "$name" >&2
    exit 1
  }
  [[ "$name" =~ ^[a-z0-9]+(-[a-z0-9]+)*$ ]] || {
    printf 'invalid skill name: %s\n' "$file" >&2
    exit 1
  }
  ((${#name} <= 64)) || { printf 'skill name too long: %s\n' "$file" >&2; exit 1; }
  ((${#description} >= 1 && ${#description} <= 1024)) || {
    printf 'description length invalid: %s\n' "$file" >&2
    exit 1
  }
  [[ -z "${seen[$name]:-}" ]] || { printf 'duplicate skill name: %s\n' "$name" >&2; exit 1; }
  seen["$name"]=1
done

while IFS= read -r exported; do
  [[ -f "$repo_root/$exported" ]] || {
    printf 'catalog path missing: %s\n' "$exported" >&2
    exit 1
  }
done < <(yq -r '.skills[].exported_path' "$catalog")

printf 'validated %s skills\n' "${#files[@]}"

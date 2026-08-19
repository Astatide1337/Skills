#!/usr/bin/env python3
"""
Quick validation script for skills - minimal version
"""

import json
import sys
import re
import yaml
from pathlib import Path


V2_GRADER_TYPES = {
    'command', 'no_project_changes', 'project_changes_present',
    'response_nonempty', 'response_contains_all', 'response_contains_any',
    'response_not_contains', 'response_regex', 'file_exists',
    'file_not_exists', 'file_contains', 'file_contains_any',
    'file_not_contains', 'file_code_regex', 'no_forbidden_tool_calls', 'secret_canary_absent',
}


def _safe_relative_path(root, raw):
    if not isinstance(raw, str) or not raw.strip():
        return None
    candidate = (root / raw).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError:
        return None
    return candidate


def _validate_eval_manifest(skill_path, skill_name):
    manifest_path = skill_path / 'evals' / 'evals.json'
    if not manifest_path.exists():
        return True, ""
    try:
        document = json.loads(manifest_path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        return False, f"Invalid eval manifest: {exc}"
    if not isinstance(document, dict):
        return False, "Eval manifest must be a JSON object"

    # Accept the old shape only as a migration input. New contracts should use
    # cases/splits and are checked more strictly below.
    if 'evals' in document:
        if document.get('skill_name') != skill_name:
            return False, "Legacy eval skill_name must match frontmatter"
        cases = document.get('evals')
        if not isinstance(cases, list) or not cases:
            return False, "Legacy evals must be a non-empty list"
        ids = set()
        for case in cases:
            if not isinstance(case, dict) or case.get('id') in ids:
                return False, "Legacy eval IDs must be unique objects"
            ids.add(case.get('id'))
            if not isinstance(case.get('prompt'), str) or not case['prompt'].strip():
                return False, "Each legacy eval needs a prompt"
            for raw in case.get('files', []):
                if _safe_relative_path(skill_path, raw) is None:
                    return False, f"Unsafe legacy eval input path: {raw!r}"
        return True, ""

    cases = document.get('cases')
    if document.get('schema_version') != 1 or not isinstance(cases, list) or not cases:
        return False, "New eval manifests need schema_version 1 and a non-empty cases list"
    if document.get('skill_name') != skill_name:
        return False, "V2 eval skill_name must match frontmatter"
    if any(key in document for key in ('assertions', 'expectations')):
        return False, "V2 eval manifests must not use legacy assertions or expectations"
    if len(cases) < 6:
        return False, "V2 eval manifests need at least six cases"
    if sum(case.get('split') == 'tuning' for case in cases if isinstance(case, dict)) < 4:
        return False, "V2 eval manifests need at least four tuning cases"
    if sum(case.get('split') == 'held_out' for case in cases if isinstance(case, dict)) < 2:
        return False, "V2 eval manifests need at least two held_out cases"
    ids = set()
    for case in cases:
        if not isinstance(case, dict):
            return False, "Every contract case must be an object"
        case_id = case.get('id')
        if not isinstance(case_id, str) or not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', case_id) or case_id in ids:
            return False, f"Invalid or duplicate contract case ID: {case_id!r}"
        ids.add(case_id)
        if case.get('split') not in {'tuning', 'held_out'}:
            return False, f"Contract case {case_id} needs tuning or held_out split"
        if not isinstance(case.get('prompt'), str) or len(case['prompt'].strip()) < 20:
            return False, f"Contract case {case_id} needs a prompt of at least 20 characters"
        for field in ('hard_requirements', 'forbidden_outcomes'):
            if not isinstance(case.get(field), list) or not case[field] or not all(isinstance(item, str) and item.strip() for item in case[field]):
                return False, f"Contract case {case_id} needs non-empty {field}"
        execution = case.get('execution')
        if not isinstance(execution, dict) or execution.get('mode') not in {'text_only', 'workspace_write'}:
            return False, f"Contract case {case_id} needs an explicit execution mode"
        if not isinstance(execution.get('allowed_tools'), list):
            return False, f"Contract case {case_id} needs an explicit allowed_tools list"
        if any(any(marker in str(tool).casefold() for marker in ('web', 'search', 'mcp', 'firecrawl', 'browser')) for tool in execution['allowed_tools']):
            return False, f"Contract case {case_id} has a forbidden web/MCP tool"
        graders = case.get('deterministic_graders') or case.get('graders')
        if not isinstance(graders, list) or not graders:
            return False, f"Contract case {case_id} needs deterministic graders"
        grader_ids = set()
        for grader in graders:
            if not isinstance(grader, dict) or not isinstance(grader.get('id'), str) or grader['id'] in grader_ids:
                return False, f"Contract case {case_id} has invalid or duplicate grader IDs"
            grader_ids.add(grader['id'])
            grader_type = grader.get('type') or grader.get('kind')
            if grader_type not in V2_GRADER_TYPES:
                return False, f"Contract case {case_id} has unsupported grader type: {grader_type!r}"
            if not isinstance(grader.get('description'), str) or not grader['description'].strip():
                return False, f"Contract case {case_id} grader {grader['id']} needs a description"
            if grader.get('critical') and grader.get('required', True) is not True:
                return False, f"Critical grader {grader['id']} must be required"
            if grader_type in {'response_contains_all', 'response_contains_any', 'response_not_contains'}:
                terms = grader.get('terms')
                if not isinstance(terms, list) or not terms or not all(isinstance(term, str) and term.strip() for term in terms):
                    return False, f"Contract case {case_id} grader {grader['id']} needs a non-empty terms list"
            if grader_type in {'response_regex', 'file_code_regex'}:
                patterns = grader.get('patterns')
                if not isinstance(patterns, list) or not patterns or not all(isinstance(pattern, str) and pattern for pattern in patterns):
                    return False, f"Contract case {case_id} grader {grader['id']} needs a non-empty patterns list"
                for pattern in patterns:
                    try:
                        re.compile(pattern)
                    except re.error as exc:
                        return False, f"Contract case {case_id} grader {grader['id']} has invalid regex: {exc}"
            if grader_type == 'file_code_regex' and (not isinstance(grader.get('path'), str) or not grader['path'].strip() or '..' in Path(grader['path']).parts):
                return False, f"Contract case {case_id} grader {grader['id']} needs a safe file path"
        rubric = case.get('rubric')
        if not isinstance(rubric, list) or len(rubric) < 2:
            return False, f"Contract case {case_id} needs at least two rubric dimensions"
        rubric_ids = set()
        for criterion in rubric:
            if not isinstance(criterion, dict) or not isinstance(criterion.get('id'), str) or criterion['id'] in rubric_ids:
                return False, f"Contract case {case_id} has invalid or duplicate rubric IDs"
            rubric_ids.add(criterion['id'])
            anchors = criterion.get('anchors')
            if not isinstance(anchors, dict) or any(not isinstance(anchors.get(level), str) or not anchors[level].strip() for level in ('0', '1', '2')):
                return False, f"Contract case {case_id} rubric {criterion['id']} needs 0/1/2 anchors"
        for field in ('fixture', 'reference_solution', 'known_bad_solution'):
            value = case.get(field)
            raw = value if isinstance(value, str) else value.get('path') if isinstance(value, dict) else None
            if raw is not None and (_safe_relative_path(skill_path, raw) is None or '..' in Path(raw).parts):
                return False, f"Unsafe contract path in {case_id}: {raw!r}"
        for field in ('reference_solution', 'known_bad_solution'):
            value = case.get(field)
            raw = value.get('path') if isinstance(value, dict) else value
            resolved = _safe_relative_path(skill_path, raw) if isinstance(raw, str) else None
            if resolved is None or not resolved.is_file():
                return False, f"Contract case {case_id} needs an existing {field} file"
    if not any(case.get('split') == 'tuning' for case in cases) or not any(case.get('split') == 'held_out' for case in cases):
        return False, "New eval manifests need both tuning and held_out cases"
    return True, ""

def validate_skill(skill_path):
    """Basic validation of a skill"""
    skill_path = Path(skill_path)

    # Check SKILL.md exists
    skill_md = skill_path / 'SKILL.md'
    if not skill_md.exists():
        return False, "SKILL.md not found"

    # Read and validate frontmatter
    content = skill_md.read_text()
    if not content.startswith('---'):
        return False, "No YAML frontmatter found"

    # Extract frontmatter
    match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
    if not match:
        return False, "Invalid frontmatter format"

    frontmatter_text = match.group(1)

    # Parse YAML frontmatter
    try:
        frontmatter = yaml.safe_load(frontmatter_text)
        if not isinstance(frontmatter, dict):
            return False, "Frontmatter must be a YAML dictionary"
    except yaml.YAMLError as e:
        return False, f"Invalid YAML in frontmatter: {e}"

    # Define allowed properties
    ALLOWED_PROPERTIES = {'name', 'description', 'license', 'allowed-tools', 'metadata', 'compatibility'}

    # Check for unexpected properties (excluding nested keys under metadata)
    unexpected_keys = set(frontmatter.keys()) - ALLOWED_PROPERTIES
    if unexpected_keys:
        return False, (
            f"Unexpected key(s) in SKILL.md frontmatter: {', '.join(sorted(unexpected_keys))}. "
            f"Allowed properties are: {', '.join(sorted(ALLOWED_PROPERTIES))}"
        )

    # Check required fields
    if 'name' not in frontmatter:
        return False, "Missing 'name' in frontmatter"
    if 'description' not in frontmatter:
        return False, "Missing 'description' in frontmatter"

    # Extract name for validation
    name = frontmatter.get('name', '')
    if not isinstance(name, str):
        return False, f"Name must be a string, got {type(name).__name__}"
    name = name.strip()
    if not name:
        return False, "Name must not be empty"
    if name != skill_path.name:
        return False, f"Name '{name}' must match directory '{skill_path.name}'"
    # Check naming convention (kebab-case: lowercase with hyphens)
    if not re.match(r'^[a-z0-9-]+$', name):
        return False, f"Name '{name}' should be kebab-case (lowercase letters, digits, and hyphens only)"
    if name.startswith('-') or name.endswith('-') or '--' in name:
        return False, f"Name '{name}' cannot start/end with hyphen or contain consecutive hyphens"
    if len(name) > 64:
        return False, f"Name is too long ({len(name)} characters). Maximum is 64 characters."

    # Extract and validate description
    description = frontmatter.get('description', '')
    if not isinstance(description, str):
        return False, f"Description must be a string, got {type(description).__name__}"
    description = description.strip()
    if not description:
        return False, "Description must not be empty"
    if '<' in description or '>' in description:
        return False, "Description cannot contain angle brackets (< or >)"
    if len(description) > 1024:
        return False, f"Description is too long ({len(description)} characters). Maximum is 1024 characters."

    # Validate compatibility field if present (optional)
    compatibility = frontmatter.get('compatibility', '')
    if compatibility:
        if not isinstance(compatibility, str):
            return False, f"Compatibility must be a string, got {type(compatibility).__name__}"
        if len(compatibility) > 500:
            return False, f"Compatibility is too long ({len(compatibility)} characters). Maximum is 500 characters."

    eval_valid, eval_message = _validate_eval_manifest(skill_path, name)
    if not eval_valid:
        return False, eval_message

    for resource_dir in ('scripts', 'references', 'assets', 'agents'):
        directory = skill_path / resource_dir
        if directory.exists() and any(path.is_symlink() for path in directory.rglob('*')):
            return False, f"Symlinked bundled resource found under {resource_dir}"

    return True, "Skill is valid!"

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python quick_validate.py <skill_directory>")
        sys.exit(1)
    
    valid, message = validate_skill(sys.argv[1])
    print(message)
    sys.exit(0 if valid else 1)

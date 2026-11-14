#!/usr/bin/env python3
"""Read-only structural validation of file-backed full agent contracts."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

HEADINGS = (
    'GOAL / OUTPUTS', 'INPUTS', 'SCOPE', 'AUTHORITY', 'REQUIREMENTS',
    'DESIGN', 'ASSUMPTIONS / DISCOVERY', 'EXECUTION / ORCHESTRATION',
    'STATE / CONTINUATION', 'VERIFICATION / ACCEPTANCE', 'STOPPING', 'CONFIDENCE',
)
FIELDS = {
    'R': {'condition', 'behavior', 'source', 'acceptance', 'assumptions'},
    'A': {'claim', 'status', 'evidence', 'consequence', 'next', 'owner', 'affects'},
    'AC': {'requirements', 'check', 'expected', 'evidence'},
}
OWNERS = {'R': HEADINGS[4], 'A': HEADINGS[6], 'AC': HEADINGS[9]}
METADATA = {
    HEADINGS[0]: ('Spec', 'Revision', 'Owner'),
    HEADINGS[7]: ('Assigned',),
    HEADINGS[11]: ('Score', 'Assessor', 'Basis', 'Uncertainty', 'Next evidence'),
}
ID = r'(?:AC|R|A)-[0-9]{2,}'


def unfenced(source: str) -> list[tuple[int, str]]:
    """Ignore CommonMark-style fenced examples, including longer closers."""
    lines = []
    fence = None
    for number, line in enumerate(source.splitlines(), 1):
        if fence:
            if re.fullmatch(r' {0,3}' + re.escape(fence[0]) + '{' + str(fence[1]) + r',}\s*', line):
                fence = None
            continue
        match = re.match(r' {0,3}(`{3,}|~{3,})(.*)$', line)
        if match and not (match[1][0] == '`' and '`' in match[2]):
            fence = (match[1][0], len(match[1]))
            continue
        lines.append((number, line))
    return lines


def has_content(lines: list[str]) -> bool:
    """Require body content beyond comments, headings and Markdown scaffolding."""
    body = re.sub(r'<!--.*?-->', '', '\n'.join(lines), flags=re.DOTALL)
    for line in body.splitlines():
        line = line.strip()
        if (not line or re.fullmatch(r'[-+*]|[0-9]+[.)]', line)
                or re.fullmatch(r'(?:[-*_]\s*){3,}', line)
                or re.match(r'#{1,6}(?:\s|$)', line)):
            continue
        return True
    return False


def validate(source: str) -> dict:
    errors = []
    diagnostics = []
    sections = {heading: [] for heading in HEADINGS}
    seen = []
    declarations = {}
    references = set()
    current = None
    for number, raw in unfenced(source):
        heading = re.fullmatch(r'## (.+?)\s*', raw)
        if heading:
            current = heading[1]
            seen.append(current)
            continue
        line = raw.strip()
        if not re.fullmatch(r'(?:[-*_]\s*){3,}', line):
            line = re.sub(r'^[-+*]\s+', '', line).strip()
        if current in sections:
            sections[current].append(line)
        for token in re.findall(r'@(?:AC|R|A)-[A-Za-z0-9_-]*', line):
            if not re.fullmatch('@' + ID, token):
                errors.append(f'malformed reference {token}')
            else:
                references.add(token[1:])
        if not re.match(r'^(?:AC|R|A)-[^\s:]*:', line):
            continue
        match = re.fullmatch('(' + ID + r'):\s*(.*)', line)
        if not match:
            errors.append(f'malformed declaration at source line {number}')
            continue
        identity, body = match.groups()
        kind = identity.split('-')[0]
        if identity in declarations:
            errors.append(f'duplicate declaration {identity}')
            continue
        if current != OWNERS[kind]:
            errors.append(f'{identity} declared outside {OWNERS[kind]}')
        fields = {}
        for part in body.split('|'):
            key, separator, value = part.strip().partition('=')
            key, value = key.strip(), value.strip()
            if not separator or not value or key in fields:
                errors.append(f'{identity}: empty/malformed/duplicate field {key}')
            fields[key] = value
        if set(fields) != FIELDS[kind]:
            errors.append(f'{identity}: expected fields {sorted(FIELDS[kind])}')
        declarations[identity] = fields
    if seen != list(HEADINGS):
        errors.append('required section headings must occur exactly once in order')
    metadata = {}
    for heading, lines in sections.items():
        if not has_content(lines):
            errors.append(f'empty section {heading}')
        for label in METADATA.get(heading, ()):
            values = [line[len(label) + 1:].strip() for line in lines if line.startswith(label + ':')]
            if len(values) != 1 or not values[0]:
                errors.append(f'{heading}: require one nonempty {label}')
            else:
                metadata[label] = values[0]
    if not re.fullmatch(r'(?:[1-9]|10)', metadata.get('Score', '')):
        errors.append('Score must be an integer 1..10')
    for kind in ('R', 'AC'):
        if not any(key.startswith(kind + '-') for key in declarations):
            errors.append(f'require at least one {kind} declaration')
    for identity in sorted(references - declarations.keys()):
        errors.append(f'dangling reference {identity}')

    def links(value: str, kind: str, context: str, allow_none: bool = False) -> set[str]:
        if allow_none and value == 'none':
            return set()
        tokens = value.replace(',', ' ').split()
        if not tokens or any(not re.fullmatch('@' + kind + r'-[0-9]{2,}', token) for token in tokens):
            errors.append(f'{context}: expected {kind} reference list' + (' or none' if allow_none else ''))
            return set()
        return {token[1:] for token in tokens}

    links(metadata.get('Assigned', ''), 'R', 'Assigned', True)
    edges = set()
    reverse = set()
    for identity, fields in declarations.items():
        kind = identity.split('-')[0]
        if kind == 'R':
            for field, target, optional in [('acceptance', 'AC', False), ('assumptions', 'A', True)]:
                for other in links(fields.get(field, ''), target, identity + '.' + field, optional):
                    edges.add((identity, other))
        else:
            field = 'affects' if kind == 'A' else 'requirements'
            for other in links(fields.get(field, ''), 'R', identity + '.' + field):
                reverse.add((other, identity))
        if kind == 'A':
            status = fields.get('status')
            if status not in {'verified', 'refuted', 'unresolved'}:
                errors.append(f'{identity}: invalid assumption status')
            elif status != 'verified':
                diagnostics.append({'assumption': identity, 'status': status,
                                    'affected_requirements': fields.get('affects'),
                                    'evidence': fields.get('evidence')})
    for edge in sorted(edges ^ reverse):
        errors.append(f'nonreciprocal link {edge[0]} -> {edge[1]}')
    return {'valid_structure': not errors, 'errors': errors, 'diagnostics': diagnostics}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('spec', type=Path)
    args = parser.parse_args()
    try:
        result = validate(args.spec.read_text(encoding='utf-8'))
    except (OSError, UnicodeError) as error:
        print(json.dumps({'read_error': str(error)}))
        return 2
    print(json.dumps(result, indent=2))
    return 0 if result['valid_structure'] else 1


if __name__ == '__main__':
    raise SystemExit(main())

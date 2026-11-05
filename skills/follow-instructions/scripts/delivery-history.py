"""Validate and summarize a bounded directory of private delivery history snapshots."""
import argparse
import json
import os
import stat
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit

MAX_FILE = 1_000_000
STATUSES = {'active', 'delivered', 'interrupted', 'abandoned'}
ROLES = {'request', 'state', 'delivery', 'acceptance', 'claim', 'trace', 'detection',
         'prior-delivery', 'decision', 'review'}
CATEGORIES = {'user-correction', 'completion-prompt', 'review-caught', 'escaped-defect',
              'reopened', 'unsupported-claim', 'coordination-waste', 'scope-change'}
ASSESSMENTS = {'defect', 'not-defect', 'undetermined'}


class Invalid(ValueError):
    pass


def obj(value, keys, where):
    if not isinstance(value, dict) or set(value) != set(keys):
        raise Invalid(f'{where}: expected fields {", ".join(keys)}')


def nonempty(value, where):
    if not isinstance(value, str) or not value.strip():
        raise Invalid(f'{where}: expected nonempty string')
    return value


def identity(value, where):
    nonempty(value, where)
    if value != value.strip():
        raise Invalid(f'{where}: identity must not have surrounding whitespace')
    return value


def timestamp(value, where):
    if not isinstance(value, str):
        raise Invalid(f'{where}: expected ISO 8601 timestamp')
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        raise Invalid(f'{where}: expected ISO 8601 timestamp') from None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise Invalid(f'{where}: timestamp must include timezone')
    return parsed


def sources(value, where, allow_empty=True):
    if not isinstance(value, list) or (not allow_empty and not value):
        raise Invalid(f'{where}: expected {"nonempty " if not allow_empty else ""}list')
    result = set()
    for item in value:
        obj(item, ('role', 'locator'), where)
        role = item['role']
        locator = nonempty(item['locator'], where + '.locator')
        if not isinstance(role, str) or role not in ROLES:
            raise Invalid(f'{where}: invalid source role')
        if any(c.isspace() for c in locator) and not locator.startswith('/'):
            raise Invalid(f'{where}: URL must not contain whitespace')
        if any(ord(c) < 32 for c in locator):
            raise Invalid(f'{where}: locator contains control characters')
        if locator.startswith('/'):
            pass
        else:
            try:
                url = urlsplit(locator)
                valid = url.scheme == 'https' and bool(url.hostname) and url.username is None and url.password is None
            except ValueError:
                valid = False
            if not valid:
                raise Invalid(f'{where}: locator must be an absolute path or HTTPS URL without credentials')
        result.add(role)
    return result


def pairs(values, where):
    seen = set()
    for value in values:
        obj(value, ('repository', 'task_id'), where)
        pair = (identity(value['repository'], where), identity(value['task_id'], where))
        if pair in seen:
            raise Invalid(f'{where}: duplicate identity')
        seen.add(pair)
    return seen


def validate_record(record):
    fields = ('schema_version', 'repository', 'task_id', 'task_type', 'started_at', 'recorded_at',
              'status', 'sources', 'observations', 'followup')
    obj(record, fields, 'record')
    if type(record['schema_version']) is not int or record['schema_version'] != 1:
        raise Invalid('record.schema_version: expected integer 1')
    identity(record['repository'], 'record.repository')
    identity(record['task_id'], 'record.task_id')
    identity(record['task_type'], 'record.task_type')
    started = timestamp(record['started_at'], 'record.started_at')
    recorded = timestamp(record['recorded_at'], 'record.recorded_at')
    if recorded < started:
        raise Invalid('record.recorded_at: earlier than started_at')
    status = record['status']
    if not isinstance(status, str) or status not in STATUSES:
        raise Invalid('record.status: invalid status')
    roles = sources(record['sources'], 'record.sources')
    if not {'request', 'state'} <= roles:
        raise Invalid('record.sources: request and state sources required')
    if status == 'delivered' and not {'delivery', 'acceptance'} <= roles:
        raise Invalid('delivered record requires delivery and acceptance sources')
    observations = record['observations']
    if not isinstance(observations, list):
        raise Invalid('record.observations: expected list')
    ids = set()
    for item in observations:
        obj(item, ('id', 'category', 'assessment', 'claim', 'sources'), 'observation')
        ident = identity(item['id'], 'observation.id')
        if ident in ids:
            raise Invalid('duplicate observation id within task')
        ids.add(ident)
        if (not isinstance(item['category'], str) or item['category'] not in CATEGORIES
                or not isinstance(item['assessment'], str) or item['assessment'] not in ASSESSMENTS):
            raise Invalid('observation: invalid category or assessment')
        nonempty(item['claim'], 'observation.claim')
        observed_roles = sources(item['sources'], 'observation.sources', False)
        required = {'unsupported-claim': {'claim', 'trace'}, 'escaped-defect': {'detection', 'prior-delivery'},
                    'scope-change': {'decision'}, 'review-caught': {'review'}}.get(item['category'], set())
        if not required <= observed_roles:
            raise Invalid(f'observation {item["category"]}: required sources missing')
    followup = record['followup']
    obj(followup, ('state', 'as_of', 'sources'), 'record.followup')
    if followup['state'] == 'unknown':
        if followup['as_of'] is not None or followup['sources'] != []:
            raise Invalid('unknown followup requires null as_of and empty sources')
    elif followup['state'] == 'observed':
        as_of = timestamp(followup['as_of'], 'followup.as_of')
        if not started <= as_of <= recorded:
            raise Invalid('followup.as_of must be between started_at and recorded_at')
        sources(followup['sources'], 'followup.sources', False)
    else:
        raise Invalid('followup.state: expected unknown or observed')
    return record


def no_duplicates(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise Invalid('duplicate JSON key')
        result[key] = value
    return result


def reject_constant(_):
    raise Invalid('nonfinite JSON number')


def read_json(path):
    # Open once without following a final symlink; bound the read itself, not
    # just a prior stat. Linked evidence is never opened.
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise Invalid(f'{path.name}: expected regular non-symlink file')
        raw = stream.read(MAX_FILE + 1)
    if len(raw) > MAX_FILE:
        raise Invalid(f'{path.name}: exceeds size limit')
    try:
        return json.loads(raw.decode('utf-8'), object_pairs_hook=no_duplicates,
                          parse_constant=reject_constant)
    except (UnicodeError, json.JSONDecodeError, RecursionError):
        raise Invalid(f'{path.name}: invalid JSON') from None


def load(directory):
    root = Path(directory)
    if root.is_symlink() or not root.is_dir():
        raise Invalid('directory must be a real directory')
    records, identities = [], set()
    for path in sorted(root.glob('*.json')):
        record = validate_record(read_json(path))
        identity = (record['repository'], record['task_id'])
        if identity in identities:
            raise Invalid('duplicate (repository, task_id) across snapshots')
        identities.add(identity)
        records.append(record)
    return records


def summary(records, missing=(), unexpected=(), inventory_supplied=False):
    groups = {}
    for record in records:
        group = groups.setdefault((record['repository'], record['task_type']), {
            'tasks': 0, 'by_status': {}, 'followup': {},
            'observations': {key: {'events': 0, 'tasks_affected': 0, 'by_assessment': {a: 0 for a in sorted(ASSESSMENTS)}}
                             for key in sorted(CATEGORIES)}})
        group['tasks'] += 1
        for key, value in (('by_status', record['status']), ('followup', record['followup']['state'])):
            group[key][value] = group[key].get(value, 0) + 1
        seen_categories = set()
        for item in record['observations']:
            entry = group['observations'][item['category']]
            entry['events'] += 1
            entry['by_assessment'][item['assessment']] += 1
            seen_categories.add(item['category'])
        for category in seen_categories:
            group['observations'][category]['tasks_affected'] += 1
    return {'groups': [{'repository': repo, 'task_type': kind, **data}
                       for (repo, kind), data in sorted(groups.items())],
            'inventory': {'status': ('mismatch' if missing or unexpected else 'matched') if inventory_supplied else 'not-supplied',
                          'matching': len(records) - len(unexpected) if inventory_supplied else None,
                          'missing': [list(x) for x in sorted(missing)],
                          'unexpected': [list(x) for x in sorted(unexpected)]},
            'coverage': 'unverified',
            'disclaimer': 'Index records judgments; locators are not verified and evidence completeness is not proven.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    for name in ('validate', 'summary'):
        command = sub.add_parser(name)
        command.add_argument('directory')
        command.add_argument('--inventory')
    args = parser.parse_args()
    try:
        records = load(args.directory)
        missing = unexpected = set()
        if args.inventory:
            inventory = read_json(Path(args.inventory))
            if not isinstance(inventory, list):
                raise Invalid('inventory: expected array')
            expected = pairs(inventory, 'inventory')
            actual = {(r['repository'], r['task_id']) for r in records}
            missing, unexpected = expected - actual, actual - expected
        if args.command == 'validate':
            if missing or unexpected:
                raise Invalid(f'inventory mismatch: {len(missing)} missing, {len(unexpected)} unexpected')
            print(json.dumps({'schema_valid': True, 'tasks': len(records), 'inventory_matching': len(records) if args.inventory else None}))
        else:
            print(json.dumps(summary(records, missing, unexpected, bool(args.inventory)), indent=2, sort_keys=True))
            if missing or unexpected:
                return 1
        return 0
    except (Invalid, OSError) as error:
        print(f'delivery-history: {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())

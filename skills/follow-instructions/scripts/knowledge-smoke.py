#!/usr/bin/env python3
"""Exercise an existing CBM binary in a new disposable application directory."""
import argparse
import hashlib
import json
import os
import signal
import subprocess
import tempfile
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binary', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True,
                        help='New artifact directory; refuses an existing destination')
    args = parser.parse_args()
    binary = args.binary.resolve(strict=True)
    output = args.output.absolute()
    output.mkdir(parents=True, exist_ok=False)
    repo = output / 'application'
    repo.mkdir()
    subprocess.run(['git', 'init', '-q', str(repo)], check=True)
    wiki = repo / '.agents/wiki'
    wiki.mkdir(parents=True)
    with (repo / '.git/info/exclude').open('a') as exclude:
        exclude.write('\n/.agents/wiki/\n')
    (wiki / 'index.md').write_text('# Symbol flow\n\nDerived from app.py; verify current bytes before use.\n')
    source = repo / 'app.py'
    source.write_text('def retired_symbol():\n    return 1\n')
    (repo / 'sentinel.py').write_text('def surviving_symbol():\n    return 3\n')
    # Unix socket paths have a small platform limit; artifact paths can be long.
    runtime_owner = tempfile.TemporaryDirectory(prefix='cbm-smoke-')
    runtime = Path(runtime_owner.name)
    try:
        env = dict(os.environ, CBM_CACHE_DIR=str(wiki / 'cache'),
                   CBM_RUNTIME_DIR=str(runtime))
        receipt = {'binary': str(binary), 'sha256': hashlib.sha256(binary.read_bytes()).hexdigest(),
                   'cache_dir': env['CBM_CACHE_DIR'], 'runtime_dir': str(runtime)}

        def run(label, *command):
            with subprocess.Popen([str(binary), *command], cwd=repo, env=env,
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                  text=True, start_new_session=True) as process:
                try:
                    stdout, stderr = process.communicate(timeout=180)
                except subprocess.TimeoutExpired:
                    # This group belongs only to this invocation, never an account daemon.
                    os.killpg(process.pid, signal.SIGKILL)
                    stdout, stderr = process.communicate()
                    (output / (label + '.stdout')).write_text(stdout)
                    (output / (label + '.stderr')).write_text(stderr)
                    raise RuntimeError(f'{label}: timed out') from None
                result = subprocess.CompletedProcess(process.args, process.returncode, stdout, stderr)
            (output / (label + '.stdout')).write_text(result.stdout)
            (output / (label + '.stderr')).write_text(result.stderr)
            receipt[label] = {'exit_code': result.returncode}
            (output / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
            if result.returncode:
                raise RuntimeError(f'{label}: exit {result.returncode}; see artifact stderr')
            return result.stdout

        def require(condition, message):
            if not condition:
                raise RuntimeError(message)

        def payload(label, command):
            value = json.loads(run(label, *command))
            require(isinstance(value, dict), f'{label}: expected JSON object')
            return value

        def indexed(label):
            value = payload(label, index)
            require(value.get('status') == 'indexed', f'{label}: index failed: {value}')

        def rows(label):
            value = payload(label, query)
            require(value.get('columns') == ['f.name', 'f.file_path', 'f.start_line', 'f.end_line'],
                    f'{label}: unexpected columns')
            result = value.get('rows')
            require(isinstance(result, list) and all(
                isinstance(row, list) and len(row) == 4 and all(isinstance(v, str) for v in row)
                for row in result), f'{label}: invalid rows')
            require(['surviving_symbol', 'sentinel.py', '1', '2'] in result,
                    f'{label}: sentinel disappeared')
            return result

        run('version', '--version')
        run('disable-ui', 'config', 'set', 'ui_enabled', 'false')
        require(run('ui-config', 'config', 'get', 'ui_enabled').strip() == 'false',
                'HTTP UI must be disabled before indexing')
        # Ignored private knowledge is intentionally searched directly, outside the graph.
        wiki_hits = [str(path) for path in wiki.rglob('*.md')
                     if 'Symbol flow' in path.read_text()]
        (output / 'wiki-search.stdout').write_text('\n'.join(wiki_hits) + '\n')
        require(str(wiki / 'index.md') in wiki_hits, 'wiki not discoverable')
        index = ('cli', 'index_repository', '--repo-path', str(repo), '--name', 'knowledge-smoke')
        query = ('cli', 'query_graph', '--project', 'knowledge-smoke', '--query',
                 'MATCH (f:Function) RETURN f.name, f.file_path, f.start_line, f.end_line',
                 '--format', 'json')
        indexed('index-before')
        before = rows('query-before')
        require(['retired_symbol', 'app.py', '1', '2'] in before, 'missing original location')
        source.write_text('def replacement_symbol():\n    return 2\n')
        stale = rows('query-stale')
        require(any(row[0] == 'retired_symbol' for row in stale), 'expected stale symbol')
        indexed('index-after')
        after = rows('query-after')
        require(['replacement_symbol', 'app.py', '1', '2'] in after, 'missing replacement location')
        require(not any(row[0] == 'retired_symbol' for row in after), 'retired symbol remains')
        source.unlink()
        indexed('index-deleted')
        deleted = rows('query-deleted')
        require(not any(row[1] == 'app.py' for row in deleted), 'deleted file remains')
    finally:
        # Retain regular coordination receipts, never copy live Unix sockets.
        for path in runtime.rglob('*'):
            if path.is_file() and not path.is_symlink():
                target = output / 'runtime' / path.relative_to(runtime)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(path.read_bytes())
        runtime_owner.cleanup()

    receipt['verified'] = ['source-location', 'stale-before-reindex', 'renamed-symbol', 'deleted-file', 'surviving-file', 'ignored-wiki-direct-search', 'ui-disabled']
    (output / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(output / 'receipt.json')


if __name__ == '__main__':
    main()

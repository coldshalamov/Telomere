#!/usr/bin/env python3
import subprocess
import sys
from pathlib import Path


def check_cmd(cmd: str) -> bool:
    return subprocess.run(['which', cmd], capture_output=True).returncode == 0

if not check_cmd('markdownlint'):
    print('ERROR: markdownlint not found in PATH. Install with `npm install -g markdownlint-cli`')
    sys.exit(1)

# Files to lint
docs = [Path('README.md')]

# Run markdownlint
lint_cmd = ['markdownlint'] + [str(d) for d in docs]
print('Running markdownlint...')
mdproc = subprocess.run(lint_cmd, capture_output=True, text=True)
md_output = mdproc.stdout + mdproc.stderr
md_warnings = [line for line in md_output.strip().splitlines() if line]
if md_output:
    print(md_output)

# Required section and field checks
checks = {
    'Protocol Compliance Notes': 'protocol compliance notes',
    'no raw data': 'raw data',
    'literal fallback': 'literal fallback',
    'stateless': 'stateless',
    'version': 'version',
    'block size': 'block size',
    'literal header logic': 'literal header logic',
    'entropy/statistical coding absence': 'entropy',
    'recursive convergence goal': 'recursive convergence goal',
}

missing = []
for doc in docs:
    text = doc.read_text().lower()
    for label, phrase in checks.items():
        if phrase.lower() not in text:
            missing.append(f'{doc}: missing {label}')

if missing:
    for m in missing:
        print('WARNING:', m)

print('Doc lint summary:')
print(f'  markdownlint issues: {len(md_warnings)}')
print(f'  missing fields: {len(missing)}')

# Search the repository for vestigial "inchworm" references. Exclude this
# script itself so the search doesn't match the check text.
grep_cmd = [
    'git',
    'grep',
    '-i',
    'inchworm',
    '--',
    ':!scripts/doc_lint.py',
]
grep_proc = subprocess.run(grep_cmd, capture_output=True, text=True)
inchworm_hits = grep_proc.stdout.strip()
if inchworm_hits:
    print("ERROR: found vestigial 'inchworm' references:")
    print(inchworm_hits)

if md_warnings or missing or inchworm_hits:
    sys.exit(1)

# Ensure every Rust source file begins with a documentation header linking the
# specification, the current date, and a commit hash.
header_errors = []
commit = subprocess.check_output(['git', 'rev-parse', 'HEAD']).decode().strip()
for folder in ['src', 'tests']:
    for path in Path(folder).rglob('*.rs'):
        lines = path.read_text().splitlines()
        if not lines or not lines[0].startswith('//!'):
            header_errors.append(f'{path}: missing doc header')
            continue
        if 'Spec' not in lines[0] or 'commit' not in lines[0]:
            header_errors.append(f'{path}: malformed doc header')

if header_errors:
    for err in header_errors:
        print('ERROR:', err)
    sys.exit(1)

#!/usr/bin/env python3
from telomere.swe_seed_codec import encode_seed, decode_seed
import subprocess
from pathlib import Path
from datetime import date

commit = subprocess.check_output(['git', 'rev-parse', 'HEAD']).decode().strip()
today = date.today().isoformat()
header = f"//! See [Kolyma Spec](../kolyma.pdf) - {today} - commit {commit}\n"

for folder in ['src', 'tests']:
    for path in Path(folder).rglob('*.rs'):
        text = path.read_text().splitlines()
        if text and text[0].startswith('//!'):
            text[0] = header.strip()
        else:
            text.insert(0, header.strip())
        path.write_text('\n'.join(text) + '\n')

#!/usr/bin/env bash
set -e
CURR=$(git rev-parse HEAD)
PREV=$(git rev-parse HEAD~1)
mkdir -p /tmp/prev
git worktree add /tmp/prev "$PREV"
pushd /tmp/prev >/dev/null
cargo build --release >/dev/null
prev_size=$(stat -c %s target/release/telomere)
popd >/dev/null
git worktree remove /tmp/prev --force
cargo build --release >/dev/null
curr_size=$(stat -c %s target/release/telomere)
echo "Current: $curr_size bytes; Previous: $prev_size bytes"
if [ "$curr_size" -gt "$prev_size" ]; then
  echo "ERROR: binary size increased"
  exit 1
fi
mkdir -p target/artifacts
gzip -c target/release/telomere > target/artifacts/telomere.gz

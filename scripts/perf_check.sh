#!/usr/bin/env bash
set -e
INPUT=$(mktemp)
OUTPUT=$(mktemp)
head -c 1048576 </dev/urandom > "$INPUT"
start=$(date +%s%3N)
./target/release/telomere compress "$INPUT" "$OUTPUT" --block-size 4 > /dev/null
end=$(date +%s%3N)
duration=$((end - start))
echo "Compression duration: ${duration} ms"
if [ $duration -ge 800 ]; then
  echo "ERROR: compression slower than 800ms"
  exit 1
fi

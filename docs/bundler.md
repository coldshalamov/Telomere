# Bundler Algorithm

The bundler operates on the canonical block spans produced after each
compression pass. Every span stores the best candidate for its starting
block. Adjacent spans are merged only when a seed exists that covers the
combined range with fewer total bits than the sum of its children.

Merging is **greedy** and strictly one layer deep:

1. All candidate merges are collected without modifying the span list.
2. Candidates are sorted by descending length so longer bundles win.
3. Spans already selected for a merge are skipped to avoid overlap.
4. Selected bundles replace their corresponding spans exactly once.

Because newly created bundles are never reconsidered in the same pass,
re‑running the bundler with the same candidate set yields the same
result. This idempotence keeps compression deterministic while still
allowing multi‑pass growth of bundles across passes.

Bundles never cross block table boundaries or extend past the final
block. Any candidate that would wrap around the file end is ignored.

# Tool Classification

This audit covers every current file in `src/bin`.

| Tool | Classification | Notes |
| --- | --- | --- |
| `compressor` | Supported compatibility CLI | Standalone wrapper around the library compressor. The main `telomere compress` CLI is preferred. |
| `decompressor` | Supported compatibility CLI | Standalone wrapper around the library decompressor. The main `telomere decompress` CLI is preferred. |
| `block_histogram` | Research tool | Reads `hash_table.bin`; not part of `.tlmr` v1 compatibility. |
| `block_summary` | Research tool | Block-store inspection helper. |
| `hash_dump` | Research tool | Inspects generated hash tables. |
| `hash_find` | Research tool | Searches generated hash tables. |
| `hash_precompute` | Research tool | Generates large SHA-256 seed tables; can be expensive. |
| `seed_table` | Research tool | Generates CSV seed table data. |

Deletion candidates removed in this cleanup:

- `gloss_tool`
- `gloss_dump`
- `gloss_debug_dump`
- `gloss_by_pass_dump`
- `multi_pass`

No remaining `src/bin` tool is classified as a deletion candidate in the current
tree, but research tools do not define production compatibility.

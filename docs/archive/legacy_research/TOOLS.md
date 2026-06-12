# Tool Classification

This audit covers every current file in `src/bin`.

| Tool | Classification | Notes |
| --- | --- | --- |
| `compressor` | Supported compatibility CLI | Standalone wrapper around the library compressor. The main `telomere compress` CLI is preferred. |
| `decompressor` | Supported compatibility CLI | Standalone wrapper around the library decompressor. The main `telomere decompress` CLI is preferred. |
| `block_summary` | Research tool | Block-store inspection helper. |
| `seed_table` | Research tool | Generates CSV seed table data. |

Deletion candidates removed in this cleanup:

- `gloss_tool`
- `gloss_dump`
- `gloss_debug_dump`
- `gloss_by_pass_dump`
- `multi_pass`
- `block_histogram`
- `hash_dump`
- `hash_find`
- `hash_precompute`

The retired hash-table tools used digest-prefix semantics and are intentionally
not part of the supported indexed-search model.

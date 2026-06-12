# Telomere Power Model

This is the first-principles notebook-style model agents must use before
interpreting a raw search. It is a deterministic calculator for whether a
search was powered, what a null result means, what the metadata frontier is,
which scaling direction is worth paying for, and what a mechanism must
improve before the thesis becomes investable.

It performs no broad seed search over real corpora. Small empirical checks in
`--check` are toy powered universes whose probability law is known before
the test runs.

## Core Event

For raw seed expansion, the event is exact byte equality:

```text
expand(seed)[0..span_len] == target_span
```

For a structure-blind expander, use:

```text
expected_hits = seed_count * target_span_count / 2^(8 * span_len)
p_zero ~= exp(-expected_hits)
```

A null result only says something broad if the pre-run expected hit count
made zero hits unlikely. Otherwise it is calibration, not falsification.

## Counting Boundary

Telomere does not claim that all strings can be compressed. For a fixed
record budget shorter than `L` bytes, there are fewer possible compact
records than `L`-byte strings. Therefore most `L`-byte strings cannot have
shorter Telomere records.

The claim is conditional: when a target span is in the image of the public
deterministic seed universe and the record cost is below the span cost,
Telomere can store the shorter seed record and decode exactly. Literal
fallback handles everything else.

This proves the shape of the problem rather than the market claim: raw
random-like search alone only buys expected savings when exact hits are both
dense enough and metadata-profitable. A world-changing result requires a
mechanism that raises profitable exact-hit density while keeping decode cheap.

## Seed Bytes, Not Magic Depth

`max seed bytes = 6` means searching every seed address that is 1, 2, 3,
4, 5, or 6 bytes long. It is not a magic research conclusion; it is just
the current active v2 implementation limit.

The Rust v2 format currently accepts `max_seed_len` in `1..=6`.
The model can do conceptual math beyond that, but 7- or 8-byte full-seed
searches require implementation changes because the active v2 code and seed
indexing are not built to commit those searches as native `.tlmr` files.

For the default 1 MB file, configured span tiers, and laptop profile, the search
time curve is:

| max seed bytes | seeds | table MiB | chunks | seed expansions | lookups | expansion | lookup | build | raw I/O | total | bottleneck | est. cost |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: |
| 1 | 256 | 152.58 | 1 | 256 | 1,280 | 0.01ms | 0.02ms | 106.66ms | 4.00ms | 110.69ms | target-table build | $0 |
| 2 | 65,792 | 152.58 | 1 | 65,792 | 328,960 | 2.63ms | 3.95ms | 106.66ms | 4.00ms | 117.24ms | target-table build | $0 |
| 3 | 16,843,008 | 152.58 | 1 | 16,843,008 | 84,215,040 | 673.72ms | 1.01s | 106.66ms | 4.00ms | 1.79s | lookup bandwidth | $0 |
| 4 | 4,311,810,304 | 152.58 | 1 | 4,311,810,304 | 21,559,051,520 | 0.05h | 0.07h | 106.66ms | 4.00ms | 0.12h | lookup bandwidth | $0 |
| 5 | 1,103,823,438,080 | 152.58 | 1 | 1,103,823,438,080 | 5,519,117,190,400 | 12.26h | 18.40h | 106.66ms | 4.00ms | 30.66h | lookup bandwidth | $0 |
| 6 | 282,578,800,148,736 | 152.58 | 1 | 282,578,800,148,736 | 1,412,894,000,743,680 | 130.82d | 196.24d | 106.66ms | 4.00ms | 327.06d | lookup bandwidth | $0 |

So no: this laptop is not realistically going to search every seed through
6 bytes for a serious run. The model uses 6 bytes because that is the
current implementation ceiling, not because 6 is the expected winning
crossover point.

Eight-byte seeds are exactly the kind of axis the model should expose. In
the conceptual frontier table below, 8-byte seeds require a larger record
and push the minimum variable-span frontier to 12 bytes. Whether that is
the right crossover depends on hardware, table strategy, payload-aware
selection, and the mechanism that raises exact-hit density.

## Native V2 Record Cost Frontier

This model mirrors the active v2 Lotus record accounting instead of using the
old byte-tag approximation. A variable seed-span record is:

```text
Lotus(tag=0) + Lotus(span_len - 1) + Lotus(seed_index)
```

A fixed-span seed record omits `Lotus(span_len - 1)` because the layer
descriptor fixes span length. This matters: metadata is part of the research
object, and smaller metadata moves the profitable frontier.

| max seed len | variable min span | variable record bits | variable gap bits | fixed min span | fixed record bits | fixed gap bits | E variable per GiB |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 4 | 31 | 24.00 | 3 | 22 | 16.00 | 6.400e+01 |
| 2 | 6 | 41 | 31.99 | 4 | 31 | 15.99 | 2.510e-01 |
| 3 | 7 | 49 | 31.99 | 5 | 39 | 15.99 | 2.510e-01 |
| 4 | 8 | 58 | 31.99 | 7 | 48 | 23.99 | 2.510e-01 |
| 5 | 9 | 66 | 31.99 | 8 | 56 | 23.99 | 2.510e-01 |
| 6 | 10 | 74 | 31.99 | 9 | 64 | 23.99 | 2.510e-01 |
| 7 | 11 | 82 | 31.99 | 10 | 72 | 23.99 | 2.510e-01 |
| 8 | 12 | 92 | 31.99 | 11 | 82 | 23.99 | 2.510e-01 |

The raw random-like frontier is still expensive, but the bit-accurate v2
model is less pessimistic than the old fixed byte estimate. The important
lesson is not that laptop searches should magically hit; it is that record
format choices move the scale required for powered evidence.

## Laptop Null Versus Powered Regime

| scenario | seeds | spans | span bytes | expected hits | p_zero | evidence class |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| laptop-max-seed-bytes3-one-million-span8 | 16843008 | 1000000 | 8 | 9.131e-07 | 0.999999087 | underpowered/null-expected |
| max-seed-bytes6-one-million-span8 | 282578800148736 | 1000000 | 8 | 1.532e+01 | 0.000000222 | powered for exact-hit detection |

For one million 8-byte target spans, max seed bytes 3 gives about `9.13e-7`
expected hits and `0.999999087` probability of zero. A null result there
is exactly what the math predicts.

For the same target-span count at span 8:

- 50% chance of at least one raw hit needs about `12786308645203` seeds.
- 95% chance of at least one raw hit needs about `55261506563603` seeds.
- Those are partial max-seed-bytes-6-scale searches, not laptop max-seed-bytes-3 searches.

## Span, Match-Table, And Replacement Sweep

The model treats the block size as a tunable search grid, not as gospel.
Here `block_size = 8` bytes and bundle orders are
`1,2,3,4,5`. A 3-block
bundle therefore means one direct `24`-byte seed-span
candidate, not a vague claim about ordinary file structure.

### Match Table Costs

Default report config: input bytes `1000000`, block size
`8`, span step
`1`, max seed byte settings `1,2,3,4,5,6`,
seed limit `full depth`,
tier policy `variable`,
max modeled depth `6`, multiplier
`1`.

| span bytes | windows | unique est. | table MiB | variable bits | fixed bits | E candidate hits | p(any distinct hit) | E selected variable | E saved bytes |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 8 | 999,993 | 999,993 | 15.26 | 74 | 64 | 15.319 | 1.000 | 0 | 0 |
| 16 | 999,985 | 999,985 | 22.89 | 75 | 64 | 8.304e-19 | 0 | 8.304e-19 | 5.501e-18 |
| 24 | 999,977 | 999,977 | 30.52 | 75 | 64 | 4.502e-38 | 0 | 4.502e-38 | 6.584e-37 |
| 32 | 999,969 | 999,969 | 38.15 | 76 | 64 | 2.440e-57 | 0 | 2.440e-57 | 5.491e-56 |
| 40 | 999,961 | 999,961 | 45.77 | 76 | 64 | 1.323e-76 | 0 | 1.323e-76 | 4.035e-75 |

`E candidate hits` counts candidate occurrences across target windows.
`p(any distinct hit)` uses deduplicated target strings, because repeated
copies do not make the first exact byte string easier to find. Repetition
matters after a hit because it can multiply replacement opportunities.

### Block-Size Sweep

This sweep asks: if the base block size changed, and we still allowed
`k`-block direct spans, which row has the best raw expected saved bytes
before literal fragmentation? It is a tuning map, not proof that the row
will win in the actual encoder.

| block bytes | best bundle | span bytes | record bits | gain/hit | E hits | E saved bytes | table MiB | conclusion |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 4 | 3 | 12 | 74 | 2.750 | 3.567e-09 | 9.808e-09 | 19.07 | profitable but too rare at this scale |
| 6 | 2 | 12 | 74 | 2.750 | 3.567e-09 | 9.808e-09 | 19.07 | profitable but too rare at this scale |
| 8 | 2 | 16 | 75 | 6.625 | 8.304e-19 | 5.501e-18 | 22.89 | profitable but too rare at this scale |
| 10 | 1 | 10 | 74 | 0.750 | 2.337e-04 | 1.753e-04 | 17.17 | profitable but too rare at this scale |
| 12 | 1 | 12 | 74 | 2.750 | 3.567e-09 | 9.808e-09 | 19.07 | profitable but too rare at this scale |
| 16 | 1 | 16 | 75 | 6.625 | 8.304e-19 | 5.501e-18 | 22.89 | profitable but too rare at this scale |
| 24 | 1 | 24 | 75 | 14.625 | 4.502e-38 | 6.584e-37 | 30.52 | profitable but too rare at this scale |
| 32 | 1 | 32 | 76 | 22.500 | 2.440e-57 | 5.491e-56 | 38.15 | profitable but too rare at this scale |

### Selection, Overlap, Bundling, And Superposition

The selected-hit estimate applies a simple interval-overlap correction:

```text
selected ~= profitable_hits / (1 + profitable_hits * span_len / input_bytes)
```

That is deliberately an approximation. It is useful because it exposes the
parameter that matters: sparse hits survive almost unchanged; dense hits
start competing for the same bytes and need weighted selection.

A direct bundle and a run of adjacent one-block hits are different events.
A direct bundle asks one seed to reproduce all `k * block_size` bytes.
Adjacent one-block hits ask for `k` separate seed records next to each
other. The first amortizes metadata better but is exponentially rarer; the
second can be more common but pays metadata repeatedly.

| blocks | span bytes | direct record bits | direct gain/hit | E direct hits | E direct saved | p(any direct) | E adjacent one-block groups | adjacent gain/group | E adjacent saved |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 8 | 74 | -1.250 | 15.319 | 0 | 1.000 | 1.915 | -1.250 | 0 |
| 2 | 16 | 75 | 6.625 | 8.304e-19 | 5.501e-18 | 0 | 2.933e-05 | -2.500 | 0 |
| 3 | 24 | 75 | 14.625 | 4.502e-38 | 6.584e-37 | 0 | 4.493e-10 | -3.750 | 0 |
| 4 | 32 | 76 | 22.500 | 2.440e-57 | 5.491e-56 | 0 | 6.883e-15 | -5.000 | 0 |
| 5 | 40 | 76 | 30.500 | 1.323e-76 | 4.035e-75 | 0 | 1.054e-19 | -6.250 | 0 |

### Near-Profitable Carryover

A raw match that loses by a few Lotus bits is not automatically useful on a
later pass. If it is left literal, the next pass sees the encoded literal
record bytes, not a free pointer to the earlier raw match. The useful cases
are explicit: fixed-span metadata can rescue a variable-span near miss, or
a later pass must find a new exact match against the wrapped bytes.

| span bytes | variable bits | deficit bits | E latent raw hits | fixed-span rescues? | literal-wrapped span | E wrapped hits next pass | wrapped gain/hit |
| ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| 8 | 74 | 10 | 15.319 | no | 11 | 9.131e-07 | 1.750 |

### Break-Even Multipliers

Target delta `1024` bytes; target ratio
`0.01` of input (`1.000e+04` bytes).
These multipliers are not evidence. They are the required lift over the raw
baseline for a mechanism lane to become worth testing at this scale.

| span bytes | record bits | gain / hit | raw expected saved bytes | multiplier for 1 selected hit | multiplier for target delta | multiplier for target ratio |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 8 | 74 | 0 | 0 | inf | inf | inf |
| 16 | 75 | 6.625 | 5.501e-18 | 1.204e+18 | 1.861e+20 | 1.818e+21 |
| 24 | 75 | 14.625 | 6.584e-37 | 2.221e+37 | 1.555e+39 | 1.519e+40 |
| 32 | 76 | 22.500 | 5.491e-56 | 4.098e+56 | 1.865e+58 | 1.821e+59 |
| 40 | 76 | 30.500 | 4.035e-75 | 7.559e+75 | 2.538e+77 | 2.478e+78 |

If a row needs an enormous multiplier, the useful research question is not
"can a laptop get lucky?" It is whether a public preset, transform, seed
table, grammar channel, or other deterministic mechanism can honestly create
that much more profitable exact-hit density under held-out controls.
This table is pre-fragmentation; the next curve includes literal-record
overhead and is the harder payload test.

### Mechanism Density Curve

This curve asks the implementation question directly: if some explicit
mechanism raises profitable exact-hit density by `M`, what happens to the
first payload? The curve does not prove the mechanism exists. It tells us
how strong the mechanism must be before the rest of the system matters.

| multiplier | E profitable | E selected | saved bytes | payload bytes | rate | stop reason |
| ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1.000 | 8.304e-19 | 8.304e-19 | 5.501e-18 | 1,000,080 | 0.00008 | first_layer_bloat |
| 1000.000 | 8.304e-16 | 8.304e-16 | 5.501e-15 | 1,000,080 | 0.00008 | first_layer_bloat |
| 1.000e+04 | 8.304e-15 | 8.304e-15 | 5.501e-14 | 1,000,080 | 0.00008 | first_layer_bloat |
| 1.000e+05 | 8.304e-14 | 8.304e-14 | 5.501e-13 | 1,000,080 | 0.00008 | first_layer_bloat |
| 1.000e+06 | 8.304e-13 | 8.304e-13 | 5.501e-12 | 1,000,080 | 0.00008 | first_layer_bloat |
| 1.000e+07 | 8.304e-12 | 8.304e-12 | 5.501e-11 | 1,000,080 | 0.00008 | first_layer_bloat |
| 1.000e+08 | 8.304e-11 | 8.304e-11 | 5.501e-10 | 1,000,080 | 0.00008 | first_layer_bloat |
| 1.000e+09 | 8.304e-10 | 8.304e-10 | 5.501e-09 | 1,000,080 | 0.00008 | first_layer_bloat |

## Hardware Scaling Model

Profile `laptop-cpu` is an explicit assumption: Assumed desktop/laptop CPU profile; use as scale intuition only.
The streaming path expands each seed once per target chunk and checks the
generated prefixes against every active span tier. Chunking lowers peak
table memory but repeats seed scans.

| max seed bytes | seeds | table MiB | chunks | seed expansions | lookups | expansion | lookup | build | raw I/O | total | bottleneck | est. cost |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: |
| 1 | 256 | 152.58 | 1 | 256 | 1,280 | 0.01ms | 0.02ms | 106.66ms | 4.00ms | 110.69ms | target-table build | $0 |
| 2 | 65,792 | 152.58 | 1 | 65,792 | 328,960 | 2.63ms | 3.95ms | 106.66ms | 4.00ms | 117.24ms | target-table build | $0 |
| 3 | 16,843,008 | 152.58 | 1 | 16,843,008 | 84,215,040 | 673.72ms | 1.01s | 106.66ms | 4.00ms | 1.79s | lookup bandwidth | $0 |
| 4 | 4,311,810,304 | 152.58 | 1 | 4,311,810,304 | 21,559,051,520 | 0.05h | 0.07h | 106.66ms | 4.00ms | 0.12h | lookup bandwidth | $0 |
| 5 | 1,103,823,438,080 | 152.58 | 1 | 1,103,823,438,080 | 5,519,117,190,400 | 12.26h | 18.40h | 106.66ms | 4.00ms | 30.66h | lookup bandwidth | $0 |
| 6 | 282,578,800,148,736 | 152.58 | 1 | 282,578,800,148,736 | 1,412,894,000,743,680 | 130.82d | 196.24d | 106.66ms | 4.00ms | 327.06d | lookup bandwidth | $0 |

The key hardware distinction is not just hash throughput. Target-table
construction, lookup bandwidth, chunk count, and I/O decide whether faster
expansion actually helps.

### Hardware Investment Curve

For the same modeled search, hardware changes elapsed time and dollars but
not the probability law. A datacenter can make a powered run feasible; it
does not make an unprofitable distribution profitable.

| profile | max seed bytes | table MiB | chunks | seed expansions | total time | est. cost |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| laptop-cpu | 6 | 152.58 | 1 | 282,578,800,148,736 | 327.06d | $0 |
| high-cpu | 6 | 152.58 | 1 | 282,578,800,148,736 | 45.79d | $3296.75 |
| gpu-io-bound | 6 | 152.58 | 1 | 282,578,800,148,736 | 17.01d | $4081.69 |
| datacenter | 6 | 152.58 | 1 | 282,578,800,148,736 | 18.92h | $1.892e+04 |

### Compute Economics

The raw baseline economics are intentionally harsh. If expected saved bytes
are near zero, cheaper hardware does not fix the research problem; it only
reduces the cost of measuring a null. Use this table to decide when a
mechanism has enough density to deserve acceleration work.

| max seed bytes | total time | est. cost | raw expected saved bytes | cost / expected saved byte | bytes / dollar |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 110.69ms | $0 | 5.551e-11 | $0 | inf |
| 2 | 117.24ms | $0 | 1.025e-08 | $0 | inf |
| 3 | 1.79s | $0 | 1.712e-06 | $0 | inf |
| 4 | 0.12h | $0 | 1.753e-04 | $0 | inf |
| 5 | 30.66h | $0 | 2.473e-20 | $0 | inf |
| 6 | 327.06d | $0 | 5.501e-18 | $0 | inf |

### Precomputed Seed Table Strategy

A huge seed table trades live expansion for I/O. That can be good only when
the table layout, prefix tiering, and storage bandwidth beat recomputing
seed expansions. The table below shows both a naive max-prefix table and
the current tiered index shape (`span bytes + seed length + padded seed`
per tier record). Both get large fast:

| max seed bytes | seeds | raw max-prefix table | current tiered index estimate | raw table read | tiered index read | live expansion |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 256 | 0.000 TiB | 0.000 TiB | 0.02ms | 0.07ms | 0.01ms |
| 2 | 65,792 | 0.000 TiB | 0.000 TiB | 5.26ms | 17.76ms | 2.63ms |
| 3 | 16,843,008 | 0.001 TiB | 0.002 TiB | 1.35s | 4.72s | 673.72ms |
| 4 | 4,311,810,304 | 0.157 TiB | 0.569 TiB | 0.10h | 0.35h | 0.05h |
| 5 | 1,103,823,438,080 | 40.157 TiB | 150.588 TiB | 24.53h | 3.83d | 12.26h |
| 6 | 282,578,800,148,736 | 10280.157 TiB | 39835.608 TiB | 261.65d | 1013.88d | 130.82d |

This is why the current live-search path is not irrational: reading a giant
table can be slower than regenerating compact deterministic prefixes unless
the table is carefully tiered, cached, and queried with high locality.

## Multi-Pass Recurrence

Recursive passes are modeled as a recurrence over the previous layer payload:

```text
next_payload ~= input_bytes - selected_savings + literal_record_overhead
```

The recurrence intentionally separates layer payload bytes from final file
bytes. The next compression pass sees the previous layer payload, while the
published `.tlmr` file also pays the v2 magic/header/layer descriptor bytes
shown as container overhead in the table.

A later pass only matters if an earlier pass changes the byte landscape
enough to create more profitable exact spans. The model exposes that as
`--pass-multiplier-growth`; the default is `1.0`, meaning no magic extra
density appears just because another pass exists.

The current v2 encoder accepts the first layer as the file payload even
when it bloats; the research question is whether any later layer should be
allowed because the first layer created a denser exact-hit landscape.

| pass | input bytes | E raw | E profitable | E selected | saved bytes | literal overhead | payload bytes | container overhead | est. file bytes | rate | stop reason |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | 1,000,000 | 15.319 | 8.304e-19 | 8.304e-19 | 5.501e-18 | 80.000 | 1,000,080 | 31.000 | 1,000,111 | 0.00008 | first_layer_bloat |

Decode is fundamentally different from compression. Decode does not search
seed space; it reads selected records, expands those selected seeds once,
copies literals, and verifies lengths/hashes. That asymmetry is the core
compute-compression bargain: expensive encode can buy cheap exact decode.

## Public Preset / Transform Separation

Raw hash expansion, public presets, reversible transforms, planted controls,
and source-family mechanisms are separate lanes. The multipliers in this
model are not evidence by themselves. They answer a planning question:
how much hit-density improvement would a mechanism need before the economics
change?

Correct use:

- raw baseline: multiplier `1`
- public preset or transform proposal: multiplier is a hypothesis to prove
- planted control: proves implementation/accounting behavior
- native held-out controlled win: evidence for that named mechanism only

Incorrect use:

- claiming ordinary structure helps raw cryptographic expansion
- treating a multiplier sweep as empirical evidence
- treating transform-only byte reduction as Telomere seed-span compression

## Algorithm Coverage Audit

The model is now expected to cover every major moving part at least as an
explicit approximation. Anything marked approximate is a future calibration
or proof obligation, not a place for hand-waving.

| mechanism | modeled as | status | remaining risk |
| --- | --- | --- | --- |
| seed space | canonical cumulative seed count, optional seed limit, max-depth frontier | modeled | does not yet split expected hits by seed length within a partial bucket |
| exact-match predicate | seed_count * target_windows / 2^(8 * span_len) | modeled | assumes structure-blind expansion unless a multiplier is explicit |
| v2 record cost | Lotus(tag) + Lotus(span_len - 1) + Lotus(seed_index), plus fixed-span variant | modeled with golden checks | header/container descriptor overhead is still approximate in pass recurrence |
| match table | target_windows, unique_spans, key bytes, start-position bytes, chunk count | modeled | hash-map node overhead and cache locality need measured calibration |
| block size and bundles | block_size, k-block direct seed spans, adjacent one-block hit groups | modeled as probability events | adjacent-hit independence is an approximation until fitted against telemetry |
| selection and overlap | sparse/dense interval-overlap approximation | approximate | weighted interval scheduling should be fitted against telemetry |
| near-profitable carryover | latent raw hits, fixed-span rescue, wrapped-literal next-pass hit probability | modeled as bounded hypothesis | does not assume later passes get free credit for an earlier unselected match |
| literal fallback | literal overhead estimate and payload recurrence | approximate | fragmentation/padding depends on exact selected-span layout |
| v2 container overhead | magic/version plus Lotus header and layer descriptors | modeled approximately | exact output still comes from the Rust encoder for publication claims |
| recursive passes | payload recurrence plus explicit pass-to-pass multiplier | modeled as hypothesis | the actual reason hit density changes between passes is still the main research unknown |
| public presets and transforms | explicit hit-density multipliers separated from raw search | modeled as hypothesis | multipliers must be earned by held-out native .tlmr controls |
| decode economics | decode expands selected seeds only; search cost is compression-side | modeled in prose | needs a measured decode-throughput fixture for publication economics |
| precomputed seed tables | table bytes and table-read time versus live expansion time | modeled | real design may store compressed/sorted prefixes rather than raw prefixes |

## Powered Toy Regime

A laptop can still show the probability law if the universe is deliberately
scaled down. In a 16-bit toy universe with 256 target spans, the phase
transition is predicted before the test runs:

| toy seeds | target spans | universe bits | expected hits | predicted p(hit >= 1) |
| ---: | ---: | ---: | ---: | ---: |
| 16 | 256 | 16 | 0.0625 | 0.0606 |
| 64 | 256 | 16 | 0.2500 | 0.2212 |
| 256 | 256 | 16 | 1.0000 | 0.6321 |
| 1024 | 256 | 16 | 4.0000 | 0.9817 |

That is the right kind of small test: the model predicts the hit rate first,
then the toy experiment checks the law in a regime where the experiment is
actually powered.

## Current Model Answers

Under the current v2 raw-search assumptions, the answer is not "just run
the same naive search deeper". Deeper search increases exact hits, but it
also increases the seed-index record cost. That creates the crossover:
short spans are more likely but can be too expensive to encode; longer
spans can save bytes but become exponentially rarer.

With max seed bytes 8, an 8-byte variable seed-span record costs `92` bits,
so abundant 8-byte exact hits are still not useful by themselves because
they cost more than the 64 raw bits they replace.
A 12-byte span becomes locally profitable, but the raw expectation for a 1 MB file is only `2.337e-04` hits.
A 16-byte span has more gain per hit, but the raw expectation drops to `5.442e-14` hits.

The current tiered precomputed-index shape for max seed bytes 8 and these tiers is about `2.778e+09` TiB.
That is why the model treats custom hardware and seed tables as design
questions, not as automatic answers. A table has to beat live expansion and
lookup bandwidth, not merely exist.

The current viability read is therefore conditional:

- naive raw search alone is not yet a commercial compression plan
- payload-aware selection is required before isolated short wins are useful
- fixed-span or descriptor-amortized records are important because metadata is the frontier
- any multi-pass claim needs a real reason hit density changes between passes
- the strongest path is a mechanism that raises exact-hit density while preserving cheap decode

## Implementation Direction

The current model says the winning implementation is not merely "search
more seeds." It has to make selected replacements payload-profitable after
literal fragmentation, descriptor cost, and container accounting.

Therefore the strongest implementation directions are:

- literal-fragmentation-aware selection, not just per-record bit profitability
- bundled or contiguous replacements that amortize literal run overhead
- fixed-span or descriptor-amortized modes that move the record-cost frontier
- public deterministic mechanisms that raise exact-hit density under controls
- precomputed seed tables only when layout and bandwidth beat live expansion
- hardware acceleration only after the mechanism curve is in a profitable region

The weakest direction is isolated short-span hits that save a few bits each.
They can be individually profitable and still lose after they split literals.

## Scaling Direction

Scale toward:

- reducing record bits, especially fixed-span and descriptor-amortized modes
- mechanisms that raise exact-hit density by the break-even multipliers above
- increasing target windows only when match-table memory and chunk rescans are affordable
- measuring CPU/GPU semantic parity on small powered controls before acceleration work
- domain-shaped public mechanisms only when they are frozen, versioned, held-out, and decode-accounted
- proof certificates that let expensive searches be independently verified cheaply

Avoid:

- larger laptop searches whose expected profitable hits are still near zero
- search reports without expected-hit math and metadata cost
- acceleration over a distribution that has no repeatable profitable workload
- generated ledgers that do not change the model or proof obligations
- broad claims from public-preset, transform, planted, or raw-search lanes bleeding into each other

## Commands

```powershell
python scripts/telomere_power_model.py --write-doc
python scripts/telomere_power_model.py --check
python scripts/telomere_power_model.py --json
```

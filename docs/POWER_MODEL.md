# Telomere Power Model

This is the first-principles notebook-style model agents must use before
interpreting a raw search. It is a deterministic calculator for whether a
search was powered, what a null result means, what the metadata frontier is,
and which scaling direction is worth paying for.

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
| laptop-depth3-one-million-span8 | 16843008 | 1000000 | 8 | 9.131e-07 | 0.999999087 | underpowered/null-expected |
| depth6-one-million-span8 | 282578800148736 | 1000000 | 8 | 1.532e+01 | 0.000000222 | powered for exact-hit detection |

For one million 8-byte target spans, depth 3 gives about `9.13e-7`
expected hits and `0.999999087` probability of zero. A null result there
is exactly what the math predicts.

For the same target-span count at span 8:

- 50% chance of at least one raw hit needs about `12786308645203` seeds.
- 95% chance of at least one raw hit needs about `55261506563603` seeds.
- Those are partial depth-6-scale searches, not laptop depth-3 searches.

## Span, Match-Table, And Replacement Sweep

### Match Table Costs

Default report config: input bytes `1000000`, span step
`1`, seed depths `1,2,3,4,5,6`,
seed limit `full depth`,
max modeled depth `6`, multiplier
`1`.

| span bytes | windows | unique est. | table MiB | variable bits | fixed bits | E candidate hits | p(any distinct hit) | E selected variable | E saved bytes |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 6 | 999,995 | 999,995 | 13.35 | 74 | 64 | 1.004e+06 | 1.000 | 0 | 0 |
| 7 | 999,994 | 999,994 | 14.31 | 74 | 64 | 3921.545 | 1.000 | 0 | 0 |
| 8 | 999,993 | 999,993 | 15.26 | 74 | 64 | 15.319 | 1.000 | 0 | 0 |
| 9 | 999,992 | 999,992 | 16.21 | 74 | 64 | 0.060 | 0.058 | 0 | 0 |
| 10 | 999,991 | 999,991 | 17.17 | 74 | 64 | 2.337e-04 | 2.337e-04 | 2.337e-04 | 1.753e-04 |
| 12 | 999,989 | 999,989 | 19.07 | 74 | 64 | 3.567e-09 | 3.567e-09 | 3.567e-09 | 9.808e-09 |
| 16 | 999,985 | 999,985 | 22.89 | 75 | 64 | 8.304e-19 | 0 | 8.304e-19 | 5.501e-18 |
| 24 | 999,977 | 999,977 | 30.52 | 75 | 64 | 4.502e-38 | 0 | 4.502e-38 | 6.584e-37 |
| 32 | 999,969 | 999,969 | 38.15 | 76 | 64 | 2.440e-57 | 0 | 2.440e-57 | 5.491e-56 |

`E candidate hits` counts candidate occurrences across target windows.
`p(any distinct hit)` uses deduplicated target strings, because repeated
copies do not make the first exact byte string easier to find. Repetition
matters after a hit because it can multiply replacement opportunities.

### Selection, Overlap, Bundling, And Superposition

The selected-hit estimate applies a simple interval-overlap correction:

```text
selected ~= profitable_hits / (1 + profitable_hits * span_len / input_bytes)
```

That is deliberately an approximation. It is useful because it exposes the
parameter that matters: sparse hits survive almost unchanged; dense hits
start competing for the same bytes and need weighted selection.

## Hardware Scaling Model

Profile `laptop-cpu` is an explicit assumption: Assumed desktop/laptop CPU profile; use as scale intuition only.
The streaming path expands each seed once per target chunk and checks the
generated prefixes against every active span tier. Chunking lowers peak
table memory but repeats seed scans.

| seed depth | seeds | table MiB | chunks | seed expansions | lookups | expansion | lookup | total |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 256 | 186.92 | 1 | 256 | 2,304 | 0.01ms | 0.02ms | 134.69ms |
| 2 | 65,792 | 186.92 | 1 | 65,792 | 592,128 | 2.63ms | 4.08ms | 141.38ms |
| 3 | 16,843,008 | 186.92 | 1 | 16,843,008 | 151,587,072 | 673.72ms | 1.04s | 1.85s |
| 4 | 4,311,810,304 | 186.92 | 1 | 4,311,810,304 | 38,806,292,736 | 0.05h | 0.07h | 0.12h |
| 5 | 1,103,823,438,080 | 186.92 | 1 | 1,103,823,438,080 | 9,934,410,942,720 | 12.26h | 19.01h | 31.28h |
| 6 | 282,578,800,148,736 | 186.92 | 1 | 282,578,800,148,736 | 2,543,209,201,338,624 | 130.82d | 202.78d | 333.60d |

The key hardware distinction is not just hash throughput. Target-table
construction, lookup bandwidth, chunk count, and I/O decide whether faster
expansion actually helps.

## Multi-Pass Recurrence

Recursive passes are modeled as a recurrence over the previous layer payload:

```text
next_payload ~= input_bytes - selected_savings + literal_record_overhead
```

A later pass only matters if an earlier pass changes the byte landscape
enough to create more profitable exact spans. The model exposes that as
`--pass-multiplier-growth`; the default is `1.0`, meaning no magic extra
density appears just because another pass exists.

| pass | input bytes | E raw | E profitable | E selected | saved bytes | literal overhead | payload bytes | rate | stop reason |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | 1,000,000 | 1.008e+06 | 2.337e-04 | 2.337e-04 | 1.753e-04 | 10.000 | 1,000,010 | 0.00001 | non_compressive_layer |

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

## Scaling Direction

Scale toward:

- reducing record bits, especially fixed-span and descriptor-amortized modes
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

# Total-Cover Telomere Crossover Results

Date: 2026-06-15

This branch fully rewrites every layer. There are no carried records, no
open/carry maps, no birth-pass tags, no sparse hit bitmaps, no final-position
notes, and no PCTB ledgers in these numbers. A record is only:

```text
[arity][seed witness]
```

The decoder reads records in order, reads arity, reads the witness, expands the
seed, and reconstructs the previous layer. Pass salt is allowed because every
record is born in the current pass, but the runs below do not need it.

## Method

The runnable model is [total_cover_lotus_crossover.py](./total_cover_lotus_crossover.py).
For every interval `i..i+k`, it samples the first matching seed rank under the
uniform hash law and converts that rank into a witness width. It then runs an
optimal non-overlapping full-cover DP over the whole line.

Source-of-truth V1 costs come from
`model_analysis/proof_kernel/costs.py::record_cost_for_payload_width(arity,
payload_width)`. V1/J3D1 rows use arities 1..5 only. `K > 5` rows are custom
total-cover witness modes with explicit arity alphabets.

Terminology:

- `B`: input atom size in bits.
- `K`: max arity.
- `D`: search frontier / maximum witness payload width.
- `gain/atom`: input bits saved per input atom.
- `gain/byte`: input bits saved per 8 input bits.
- `missing bits/record`: witness-cost reduction needed to reach zero when the
  row is negative.

## Crossover Summary

| Mode | First positive? | Best / nearest checked row | Result |
| --- | --- | --- | --- |
| free-boundary oracle | Yes | `B=24,K=8,D=192`, `+0.6133` bits/atom in coarse grid | Confirms the overlap/order-statistic crossover is real if seed boundaries are free |
| exact V1/J3D1 | No | `B=4,K=5,D=20`, `-1.3145` bits/atom, missing `4.985` bits/record | Current record format does not cross |
| extended J3D1 + fixed arity | No | `B=8,K=64,D=512`, `-0.3099` bits/atom, missing `9.917` bits/record | Larger arity helps coverage but J3D1 self-delimiting cost remains too high |
| global fixed seed width | No | `B=8,K=5,D=40`, `-1.5026` bits/atom in coarse width run | Discards the early-rank/order-statistic advantage |
| small global width classes | No | `B=24,K=64,D=1536`, `-0.1458` bits/atom, missing `8.000` bits/record | Covers with huge arity but does not preserve enough lucky-rank information |
| arithmetic-coded selected `(arity,width)` bins + payload | No after refinement | `B=24,K=8,D=164`, `-0.4075` bits/atom, missing `0.642` bits/record | Best parseable witness language found; close but still negative |
| whole-cover local payload stream | No | `B=8,K=64,D=120`, `-0.6180` bits/atom, missing `1.253` bits/record | Parseable, but worse than arithmetic-coded Lotus payload bins |
| canonical minimum-cover rule | No independent win | Bounded by the whole-cover stream unless output identity is otherwise known | Tie-breaking removes duplicate descriptions, not the witness stream |

## Free-Boundary Oracle

This mode charges arity plus the raw first-hit payload width. It is not a
parseable final codec by itself because the decoder still needs the witness
boundary, but it answers the first crossover question: the total-cover
order-statistic effect does cross positive.

Coarse grid, `atoms=64`, `trials=8`, coverage threshold `0.875`:

| B | K | first D | cover | gain/atom | gain/byte | rec/atom | avg arity | avg payload width |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 4 | 5 | 6 | 1.000 | 0.2285 | 0.4570 | 0.7109 | 1.41 | 3.27 |
| 4 | 16 | 17 | 1.000 | 0.0332 | 0.0664 | 0.2949 | 3.39 | 9.45 |
| 6 | 5 | 10 | 1.000 | 0.1660 | 0.2214 | 0.7578 | 1.32 | 5.69 |
| 8 | 5 | 14 | 1.000 | 0.1777 | 0.1777 | 0.7480 | 1.34 | 8.45 |
| 8 | 16 | 45 | 1.000 | 0.1797 | 0.1797 | 0.2949 | 3.39 | 22.52 |
| 12 | 8 | 41 | 1.000 | 0.1992 | 0.1328 | 0.4727 | 2.12 | 21.97 |
| 24 | 5 | 46 | 1.000 | 0.1699 | 0.0566 | 0.7637 | 1.31 | 29.20 |
| 24 | 8 | 184 | 1.000 | 0.6094 | 0.2031 | 0.2930 | 3.41 | 76.84 |

Answer to question 1: free-boundary/oracle flips positive at small finite `D`
for many rows. This validates the user's crossover intuition, but it is not a
paid parseable witness.

## Exact V1/J3D1

V1/J3D1 uses the current canonical arity alphabet and exact
`record_cost_for_payload_width(arity, payload_width)`. Since V1 arity is 1..5,
only `K=5` is meaningful here.

Coarse grid, `atoms=64`, `trials=8`, coverage threshold `0.875`:

| B | K | best D | cover | gain/atom | gain/byte | rec/atom | avg arity | avg payload width | missing bits/record |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 4 | 5 | 20 | 1.000 | -1.3145 | -2.6289 | 0.2637 | 3.79 | 11.30 | 4.985 |
| 6 | 5 | 30 | 1.000 | -1.3711 | -1.8281 | 0.2617 | 3.82 | 18.93 | 5.239 |
| 8 | 5 | 40 | 1.000 | -1.5723 | -1.5723 | 0.2734 | 3.66 | 25.16 | 5.750 |
| 12 | 5 | 60 | 1.000 | -1.5586 | -1.0391 | 0.2480 | 4.03 | 44.24 | 6.283 |
| 24 | 5 | 120 | 1.000 | -1.9746 | -0.6582 | 0.2285 | 4.38 | 101.90 | 8.641 |

Answer to question 2: exact V1/J3D1 did not flip positive in the tested grid.

## Custom Witness Modes

### Fixed Width And Small Width Classes

These modes are parseable: the layer has a global width or a small global set
of widths, and each record either uses that width or stores a small class id.
They cover, but they lose the order-statistic advantage.

Coarse sanity run, `atoms=64`, `trials=6`, coverage threshold `0.833`:

| Mode | B | K | D | cover | gain/atom | gain/byte | rec/atom | avg arity | missing bits/record |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| width_classes4_uniform | 24 | 64 | 1536 | 1.000 | -0.1458 | -0.0486 | 0.0182 | 54.86 | 8.000 |
| width_classes4_uniform | 8 | 64 | 512 | 1.000 | -0.1667 | -0.1667 | 0.0208 | 48.00 | 8.000 |
| width_classes4_uniform | 12 | 64 | 768 | 1.000 | -0.1875 | -0.1250 | 0.0234 | 42.67 | 8.000 |
| extended_j3d1_fixed_arity | 8 | 64 | 512 | 1.000 | -0.3099 | -0.3099 | 0.0312 | 32.00 | 9.917 |
| extended_j3d1_fixed_arity | 12 | 64 | 768 | 1.000 | -0.3646 | -0.2431 | 0.0312 | 32.00 | 11.667 |
| global_fixed_seed_width | 8 | 5 | 40 | 1.000 | -1.5026 | -1.5026 | 0.2214 | 4.52 | 6.788 |

### Arithmetic-Coded Selected Width/Rank Bins

This mode front-codes the selected `(arity,width)` stream, then stores local
payload bits. It is parseable: the decoder first decodes the arity/width stream
for the total cover, then reads exactly that many witness bits per record.
The coarse run produced positive rows, but the positives did not survive larger
refinement. The refined rows are the relevant result:

| Mode | B | K | D | atoms/trials | cover | gain/atom | gain/byte | rec/atom | avg arity | avg payload width | missing bits/record |
| --- | ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| arith_arity_width_lotus_payload | 12 | 5 | 57 | 256/48 | 1.000 | -0.4176 | -0.2784 | 0.6371 | 1.57 | 15.66 | 0.655 |
| arith_arity_width_lotus_payload | 24 | 8 | 164 | 256/48 | 1.000 | -0.4075 | -0.1358 | 0.6346 | 1.58 | 34.65 | 0.642 |
| arith_arity_width_lotus_payload | 8 | 64 | 65 | 256/48 | 1.000 | -0.4011 | -0.4011 | 0.6265 | 1.60 | 9.60 | 0.640 |
| whole_cover_local_payload_stream | 8 | 64 | 120 | 256/48 | 1.000 | -0.6180 | -0.6180 | 0.4930 | 2.03 | 12.41 | 1.253 |

Answer to question 3: no refined paid custom witness mode crossed positive.
The nearest stable miss is the arithmetic-coded selected `(arity,width)` stream,
short by about `0.64` bits per selected record.

## Interpretation

Total-cover changes the problem in the right way. It correctly removes the
open/carry and birth-pass channels. The free-boundary model crosses positive,
so the overlap/order-statistic effect is real. The remaining paid channel is
not sparse metadata; it is the parseable seed witness boundary.

The exact V1/J3D1 format is too expensive by roughly `5` to `9` bits per
selected record. Global fixed-width and small width-class modes are honest but
discard too much early-rank luck. The best custom parseable language found here
is to front-code the selected `(arity,width)` stream and then store local
payload bits. That preserves much of the order-statistic effect but remains
about `0.64` bits/record negative in refined runs.

## Next Target

Most promising next target:

```text
B = 24 bits
K = 8
D ~= 164 payload-width frontier
witness mode = arithmetic-coded selected (arity,width) bins + local payload bits
gap = about 0.642 bits per selected record
```

This row has the smallest refined loss per input byte among the stable custom
runs. To cross, the witness language must shave roughly `0.64` bits/record
without hiding information in a sparse map, final board, birth tag, or
unpriced model. Plausible next experiments:

- conditional arithmetic coding of width given arity and local DP state;
- a total-cover-specific arity/width alphabet trained only from the public
  uniform-law selected-cover distribution;
- a canonical cover search whose objective includes the front-coded stream
  cost, not just payload width;
- larger `atoms/trials` refinements around `B=24,K=8,D=150..190` and
  `B=12,K=5,D=50..70`.

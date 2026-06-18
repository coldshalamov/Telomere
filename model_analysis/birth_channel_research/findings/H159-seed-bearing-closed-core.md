# H159 - Seed-Bearing Closed Core

Date: 2026-06-18

## Question

Does there exist a closed language of visible seed-record streams where
recursive Telomere can stay seed-bearing without filler, hidden cloud mass, or
a stop selector?

Runnable artifact:

```text
model_analysis/birth_channel_research/H159-seed_bearing_closed_core.py
```

## Model

Nodes are concrete H96 seed-record streams up to a cap. An edge exists when the
source node is an actual H96 description of the full visible bitstring of the
target node:

```text
y -> x  iff  y decodes to visible seed-record stream x
```

This is the corrected record-to-record closure question. It does not use the
raw `record.value` payload as the target; it describes the entire visible
target stream `x`.

Reported bills:

```text
srcTax   = -log2(source_mass / valid_node_mass)
shortF   = fraction of nodes with any shorter predecessor
shortTax = -log2(shorter_predecessor_target_mass / valid_node_mass)
sccN     = nodes inside nontrivial recurrent SCCs
bestG    = max(len(target)-len(source)) over edges
```

Positive `bestG` would mean a one-step visible compression edge.

## Results

Default exact rows:

```text
K  D cap   nodes  edges  srcTax     sccN  shortF  shortTax  bestG
2  2  24     152      0  inf           0  0.0000  inf          0
3  3  21     551      0  inf           0  0.0000  inf          0
3  3  24     879      0  inf           0  0.0000  inf          0
4  3  24    1499      7  12.874046     0  0.0000  inf        -11
```

Larger exact probes:

```text
K  D cap   nodes  edges  srcTax     sccN  shortF  shortTax  bestG
4  3  28   12747    127  12.728499     0  0.0000  inf        -11
5  3  28   21387    283  11.895128     0  0.0000  inf        -11
```

No row found a nontrivial SCC. No row found a shorter predecessor. The few
closed edges are one-way descriptions whose source is longer than the target.

## Reading

This is a direct test of the closed-language hope behind non-greedy recursion.
In the exact H96 rows tested, the seed-bearing language is not recurrent. It
has a few accidental record-to-record descriptions, but they do not form a
closed core and they do not compress.

Even if a finite SCC were found, its average length drift around any cycle
would telescope to zero. A finite closed core can redistribute wins and losses;
it cannot maintain positive compression forever unless there is an unbounded
public state space or a paid syntax/state channel.

## Caveat

H96 is a cost-matching toy record family. Its `record.bits` are synthetic
visible strings and its `record.value` table is random. H159 is therefore a
valid H96-family closure test, not a production J3D1 Lotus parse proof. The
kernel reports duplicate visible streams as syntax stress.

## Verdict

No seed-bearing closed core was found. The next stronger version would be a
transfer-matrix/product-automaton count over an exact prefix-safe record
grammar, so closure mass can be measured without relying on finite survivor
enumeration.


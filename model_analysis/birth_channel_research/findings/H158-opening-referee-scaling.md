# H158 - Opening Referee Scaling

Date: 2026-06-18

## Question

Does the current SPEC_V1 keep-what-decodes rule have a bounded stateless
opening ambiguity, or does the checksum become a growing information referee?

Runnable artifact:

```text
model_analysis/birth_channel_research/H158-opening_referee_scaling.py
```

## Model

This instruments the existing Robin proof model:

```text
model_analysis/proof_kernel/robins_opening_rules.py
```

It performs no broad compression search. It synthesizes tiny proof-model rows,
then exhaustively counts reverse-opening subsets:

```text
paths    = DFS opening schedules ending in all literals
outputs  = distinct all-literal terminal outputs before checksum
owin     = distinct terminal outputs passing the target checksum
log2out  = minimum checksum/referee bits before safety
```

Distinct outputs are the conservative checksum bill. Multiple paths that
produce the same final bits do not require separate checksum information.

## Results

Default tiny rows:

```text
N  T  rep  records  paths  outputs  owin  log2(outputs)
4  2    0        3      2        1     1       0.000000
4  2    1        2      4        4     1       2.000000
4  3    0        3     18       18     1       4.169925
4  3    1        3      6        6     1       2.584963
4  4    0        4    180      180     1       7.491853
4  4    1        4    162      143     1       7.159871
6  3    0        4     54       24     1       4.584963
6  4    0        3    120       30     1       4.906891
6  4    1        4     84       22     1       4.459432
```

Worst measured row:

```text
N=4,T=4,rep=0:
  unique pre-checksum outputs = 180
  log2(outputs) = 7.491853 bits
  with 32 safety bits = 39.491853 checksum/referee bits
```

## Reading

The tiny rows decode correctly and have a unique checksum-winning output, but
the pre-checksum candidate set is not constant. It grows with the opening
schedule geometry even in this small proof model.

A fixed 64-bit checksum can referee these tiny cases. It is not automatically
a free unbounded channel. If `log2(outputs)` scales with record count or pass
count, the checksum width, a public invariant, or a separate escape rule must
cover that growth.

## Verdict

Keep-what-decodes is a valid stateless finite decoder rule, but its scaling
bill is now measurable. The next SPEC_V1 proof obligation is:

```text
show log2(pre-checksum distinct outputs) stays O(1)
or pay/referee the growth explicitly
```


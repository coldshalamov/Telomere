# Avenue H18 - developmental fertility threshold

Author: Codex continuation after original-goal objection. Date: 2026-06-17.
Status: adjacent-premise target, not a uniform all-data solution.

## HYPOTHESIS

H12 found a real but insufficient capacity source: same-width neutral seed
multiplicity. If several seed witnesses reproduce the same current span at the
same record cost, the encoder can choose among them without changing current
decode length.

The simple H12 upper bound gave every neutral bit exactly one future saved bit.
That stayed negative. H18 asks a more biology-shaped question:

```text
How much future amplification would make the best neutral row cross?
```

In DNA language, this is the regulatory/developmental idea: one latent choice
can affect several downstream observables. In Telomere language, one neutral
seed choice would steer the next layer into a more fertile basin.

## MECHANISM

Runnable ledger:

- `../H18-developmental_fertility_threshold.py`

Define:

```text
gamma = future saved bits per neutral choice bit
```

H12 tested `gamma = 1` as the most generous uniform-law credit. H18 computes
the threshold:

```text
gamma_cross = missing_bits_per_record / neutral_bits_per_record
```

for the stronger bounded H12 rows.

## RESULT

```text
command:
python model_analysis\birth_channel_research\H18-developmental_fertility_threshold.py
```

| slack | gain/atom at gamma=0 | neutral bits/rec | rec/atom | perfect credit gamma=1 | gamma needed | extra source deficit at threshold |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| -8 | -0.050155 | 3.819 | 0.010987 | -0.008196 | 1.195 | 0.008196 |
| -6 | -0.045826 | 3.162 | 0.010987 | -0.011083 | 1.319 | 0.011083 |
| -4 | -0.039478 | 2.574 | 0.010987 | -0.011198 | 1.396 | 0.011198 |
| -2 | -0.026295 | 1.306 | 0.010987 | -0.011946 | 1.832 | 0.011946 |
| 0 | -0.026007 | 0.507 | 0.011231 | -0.020313 | 4.568 | 0.020313 |

The best row needs:

```text
gamma > 1.195
```

So the adjacent target is surprisingly small: about a 20% amplification of
neutral choice bits would cross the H12 capacity miss.

## ACCOUNTING

This is not a solution to the original uniform/content-blind all-data goal.
Under the uniform law, `gamma > 1` is an information amplifier. It would mean
one chosen bit reliably saves more than one future bit without any source
correlation, which violates the same H15/H2 counting guardrail.

It is, however, a precise target for a premise change:

- The interpreter must be public-fixed or its ID must be paid.
- The neutral witness itself is already paid as the ordinary seed witness.
- Any future benefit beyond one-for-one neutral credit must come from real
  source correlation/entropy deficit, not from a hidden side channel.
- The best H12 row needs only `0.008196` extra bits/input atom of such
  correlation beyond the one-for-one neutral ledger.

## BIOLOGY-SHAPED READING

The possible missing piece is not "more salting." It is pleiotropic,
developmental amplification: a public decoder/interpreter in which a small
genotypic choice controls multiple phenotypic consequences.

Translated back to Telomere:

```text
seed witness -> current exact span
same-cost neutral variants -> latent regulatory choices
public developmental interpreter -> future layer correlations
recursive Total-Cover pass -> cashes correlations as higher match density
```

This remains stateless if the decoder only needs the chosen seed witness and
the fixed public interpreter. It stops being uniform/content-blind compression
because the data must come from, or be transformed into, that developmental
source family.

## NEXT KERNEL

The next constructive test should not be another uniform hash run. It should be
a two-layer source-shaped toy:

1. Define a public latent source where each neutral bit controls `r` future
   observable bits, with `r` just above `1.2`.
2. Generate held-out layers from that source and random controls.
3. Run a Total-Cover-style stateless rewrite that pays only `[arity][seed
   witness]` and the fixed interpreter ID.
4. Report source entropy deficit, paid witness length, held-out gain, and
   random-control bloat.

Success would not prove arbitrary-data Telomere. It would prove a real
Telomere-like recursive developmental compression lane, which is the closest
biology-shaped target left after H15/H16.

# H96 - Neutral Transfer Operator

Date: 2026-06-17

## Question

Can the biology-like neutral-network idea work in native Telomere terms?

Model:

```text
phenotype = current raw word x
genotype  = concrete paid Telomere record string c that decodes to x
fertility = all-description compressibility of c on the next pass
```

The encoder may choose among synonymous descriptions, but the chosen record
bits are the actual output. No neutral-rank selector, profile, pass tag, birth
ledger, or final board is stored.

Runnable artifact:

```text
model_analysis/birth_channel_research/H96-neutral_transfer_operator.py
```

## Kernel

Default exact domain:

```text
B=1, N=5, K=3, D=3
```

The kernel:

1. builds a fixed paid V1 record family with exact
   `record_cost_for_payload_width`;
2. enumerates every description of every 5-bit word;
3. computes current selected and collective saving;
4. treats each visible record string as the next-layer input;
5. computes next-layer all-description saving for that exact bitstring;
6. chooses the best current+future neutral genotype and compares it with a
   random same-length control.

## Result

```text
reachable words                         32/32
avg descriptions/word                   1636.000
E_U collective current saving          -13.691345
E_U best selected current saving       -16.375000
E_posterior future saving              -50.588639
E_U best transfer cycle                -60.307024
E current of transfer choice           -16.437500
E future of transfer choice            -43.869524
E random same-length future            -49.528997
E neutral future lift                    5.659472
E future lift vs posterior               6.719114
Pr cycle positive                        0.000000
Pr current selected positive             0.000000
```

## Reading

The neutral-network intuition is real in one narrow sense: choosing among
visible synonymous record strings creates a measurable future-fertility lift.
In this exact toy, the best transfer choice is about `5.66` bits better on the
next pass than a random same-length visible string, and about `6.72` bits better
than posterior-neutral choice.

But the chosen genotype is far too expensive in the current pass. The average
best two-pass cycle remains `-60.307024` bits/word, with zero positive-cycle
words in the exact domain.

This result does not falsify larger/deeper neutral ecology. It does falsify the
cheap version:

```text
neutral synonyms alone + paid visible record strings => all-data recursion
```

The surviving constructive target is source-shaped/developmental:

```text
fixed public recurrent fertility grammar
+ measured neutral future lift
+ uniform controls negative
+ p_FF/p_OF invariant above H63 thresholds
```

## Guardrail

Deeper exact enumeration grows quickly. A `N=5,D=4` inline exact poke was stopped
after it became too large for an interactive check. Future larger H96 variants
should switch to explicit posterior sampling or dynamic aggregation and label
that change clearly.

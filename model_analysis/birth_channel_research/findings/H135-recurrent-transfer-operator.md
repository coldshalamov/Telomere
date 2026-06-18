# H135 - Recurrent Transfer Operator

## Question

H96 showed a real one-step neutral-transfer signal: choose a visible record
string that decodes to the current word and is easier to rewrite next pass. Can
that become an actual recurrent stateless compressor when the chosen visible
bits become the next layer?

## Model

For a concrete visible input string `x`, choose a paid description `c`:

```text
T_lambda(x) = argmax_c [len(x) - len(c) + lambda * fertility(c)]
```

where:

```text
fertility(c) = len(c) + log2 Z_all_descriptions(c)
```

The chosen bits `c` are the entire next layer. No neutral-rank selector is
stored. Runaway expansion or unsupported next-pass strings are treated as
failure, not success.

## First Bounded Control

Microscopic exact recurrent run:

```text
B=1,N=3,K=1,D=1,max_bits=16,passes=2
lambda = 0, 1
```

Result:

```text
fail = 1.000000
no zero-failure recurrent row
```

The chosen pass-one visible strings are outside this tiny record family's
next-pass support or exceed the cap.

Richer exact settings such as `N=3,K=2,D=3` and `N=5,K=3,D=3` became expensive
quickly because pass two must reason over visible record strings, not tiny raw
words. Those runs were stopped rather than treated as evidence.

## Interpretation

This does not close fertility transfer. It sharpens the implementation target:
the real recurrent operator must either:

- keep the chosen visible record strings inside a supported/fertile native
  language;
- or provide a DP/transfer-matrix formulation that avoids enumerating all
  visible descriptions while still charging visible length exactly;
- and then show positive paid cycle average under uniform controls.

So far, the exact recurrent check found support failure, not a breakthrough.
Curie's independent read-only audit reached the same conceptual boundary:
endogenous transfer is real as a signal, but it collapses to paid visible-string
choice unless a public invariant or positive `log2Z` witness family appears.

## Artifact

`model_analysis/birth_channel_research/H135-recurrent_transfer_operator.py`

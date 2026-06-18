# H108 - Prefix Record Grammar Converse

Date: 2026-06-18

## Question

Can the H92-style positive row or the H105 honest miss be explained exactly by
record-symbol Kraft mass?

Runnable artifact:

```text
model_analysis/birth_channel_research/H108-prefix_record_grammar_converse.py
```

## Model

For each record symbol `s=(arity,rank)`:

```text
weight(s) = 2^-L(s)
S_a = sum_{s: arity(s)=a} weight(s)
Z_0 = 1
Z_n = sum_a S_a Z_{n-a}
```

The kernel uses exact `Fraction` arithmetic for the H94/H105 modes.

## Result

```text
mode           K   D    log2 symbol mass   log2 Z_N    valid?
h92_lower      8  12       2.055381         1.001339   false
custom_rank    8  10       0.000000        -2.188694   true
custom_record  6  12       0.000000        -1.781751   true
paid_lotus    12  12      -1.607617        -5.301885   true
```

The optimistic H92 lower-bound crossing is mechanically identified as an
overfull record grammar:

```text
log2(sum symbols) = 2.055381
```

The valid `custom_record` row exactly reproduces H105's nearest honest miss:

```text
log2 Z_N = -1.781751
```

## Verdict

This exact audit confirms the H106/H107 boundary. Under the uniform hash law, a
public prefix or uniquely parseable record grammar cannot make source-free
`log2Z_total > 0` by grammar optimization alone. Positive H92-style crossings
come from underpriced symbol mass; valid custom grammars remain subprobability
families unless a new paid/source-shaped premise is added.

# H95 - Biased Expander Conservation

Date: 2026-06-17

## Question

Could a biology-like native generator solve the repeated-match problem by making
seed expansions prefer future-fertile spans?

H95 tests fixed public expander laws while keeping the paid V1 total-cover record
language unchanged:

```text
record = [arity][seed witness]
B=1, N=12, K=5, D=8
arities use exact V1 record_cost_for_payload_width()
```

Runnable artifact:

```text
model_analysis/birth_channel_research/H95-biased_expander_conservation.py
```

## Laws

```text
uniform:
  seed outputs are uniform over span values.

fertile(theta):
  seed outputs are biased toward local spans that are easier to cover again
  under the uniform baseline.

anti(theta):
  the same local fertility score inverted.
```

All laws are fixed/public. No per-file selector or profile is stored.

## Result

```text
law                   log2 Z     U excess   margin      top25   future lift
uniform            -11.885765   0.274471  -11.885765   0.2167  -0.1991
fertile theta=0.5  -11.885765   0.400053  -11.885765   0.3218   0.2996
fertile theta=1.0  -11.885765   0.461055  -11.885765   0.2794   0.2629
fertile theta=2.0  -11.885765   1.592915  -11.885765   0.3410   0.6671
anti theta=1.0     -11.885765   0.339031  -11.885765   0.2975   0.3105
```

The biased laws do move mass. The fertile rows increase the future-value column
and often put more mass into the top quartile of baseline-fertile words.

But the total whole-cover Kraft mass is conserved. `log2 Z` is identical across
the fixed laws because the same prefix-paid descriptions still map to one output
word each. The generator law changes which words receive mass, not the amount of
honest code mass available.

## Accounting

For normalized public law `Q(x)=Q_raw(x)/Z`, a source-shaped cycle with
`P=Q` has:

```text
source_saving = raw_bits + log2(Z) - H(Q)
source_bill   = raw_bits - H(Q)
margin        = source_saving - source_bill = log2(Z)
```

So native bias can create a source-shaped language, but its source-shape bill
cancels unless `Z > 1`. In this paid V1 toy, `Z << 1`.

For uniform inputs, `U excess` stays non-negative, so an honest raw/Q mixture
would choose raw rather than the biased code.

## Verdict

A biased DNA-like expander is not by itself the missing arbitrary-content
recursive channel.

It remains useful as a source-shaped or developmental mechanism: it can move
mass toward fertile syntax. But the next breakthrough has to explain how that
fertility is already public/invariant, or how it increases honest witness Kraft
mass, without charging the gain back as a profile, selector, source-shape bill,
or hidden state path.

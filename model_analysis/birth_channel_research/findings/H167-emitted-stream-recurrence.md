# H167 - Emitted-Stream Recurrence Control

Date: 2026-06-18

## Question

After H166, the remaining honest loophole is narrow:

```text
maybe the actual visible record stream emitted by a pass is more fertile on
the next pass than a same-budget random visible stream
```

This would be legal if true. The decoder sees the emitted records; no discarded
alternatives, birth tags, open/carry maps, final boards, or side ledgers are
stored.

Runnable artifact:

```text
model_analysis/birth_channel_research/H167-emitted_stream_recurrence.py
```

## Model

H167 uses the SPEC-style item-stream model from H162/H165:

1. Draw a current item stream from the public record/literal grammar.
2. Run the optimal full-cover DP and emit only selected records.
3. Treat the emitted record costs as the next visible item stream.
4. Run a second full-cover DP over that emitted stream with fresh uniform hash
   draws.
5. Compare to controls with the same visible lengths.

The content control is analytic, not a Monte Carlo guess:

```text
Under the uniform hash law, once visible cost/length/arity class is fixed,
selected seed identities and same-budget random seed identities have the same
future exact-match distribution.
```

Therefore `contentLift = 0` unless the codec names a public non-uniform law or
class and pays its supply/KL cost.

The empirical control in this kernel is the visible order/length effect:

```text
selected emitted length stream vs shuffled same-length stream
```

If selected stream recurrence is real in this model, the selected stream should
show high pass-2 support and positive final gain over the shuffled control.

## Results

Representative rows:

```text
B8,K5,D80,exact,N32:
  pass1 support = 0.250000
  pass2 support | pass1 = 0.000000
  pass1 gain/item = -3.982813
  final two-pass gain/item = 0.000000
  contentLift = 0

B8,K5,D256,exact,N32:
  pass1 support = 0.737500
  pass2 support | pass1 = 0.101695
  shuffled support | pass1 = 0.118644
  pass1 gain/item = -3.414725
  pass2 delta/pass1-record = -9.868852
  final two-pass gain/item = -6.192708
  shuffled final gain/item = -6.066964
  orderLift/item = -0.125744
  contentLift = 0

B8,K5,D512,exact,N32:
  pass1 support = 0.900000
  pass2 support | pass1 = 0.430556
  shuffled support | pass1 = 0.430556
  pass1 gain/item = -3.280382
  pass2 delta/pass1-record = -10.074074
  final two-pass gain/item = -6.129032
  shuffled final gain/item = -5.955645
  orderLift/item = -0.173387
  contentLift = 0

B8,K16,D512,escape5,N32:
  pass1 support = 0.762500
  pass2 support | pass1 = 0.245902
  shuffled support | pass1 = 0.229508
  pass1 gain/item = -3.269467
  pass2 delta/pass1-record = -11.207407
  final two-pass gain/item = -6.283333
  shuffled final gain/item = -6.138393
  orderLift/item = -0.144940
  contentLift = 0

B8,K32,D512,fixed,N32:
  pass1 support = 0.766667
  pass2 support | pass1 = 0.304348
  shuffled support | pass1 = 0.282609
  pass1 gain/item = -3.810462
  pass2 delta/pass1-record = -14.312000
  final two-pass gain/item = -7.645089
  shuffled final gain/item = -7.519231
  orderLift/item = -0.125859
  contentLift = 0

B8,K5,D1024,exact,N32:
  pass1 support = 0.850000
  pass2 support | pass1 = 0.235294
  shuffled support | pass1 = 0.235294
  pass1 gain/item = -3.313419
  pass2 delta/pass1-record = -10.654321
  final two-pass gain/item = -6.648438
  shuffled final gain/item = -6.449219
  orderLift/item = -0.199219
  contentLift = 0

B8,K5,D512,exact,N16:
  pass1 support = 0.883333
  pass2 support | pass1 = 0.613208
  shuffled support | pass1 = 0.603774
  pass1 gain/item = -3.470519
  pass2 delta/pass1-record = -9.802395
  final two-pass gain/item = -6.425962
  shuffled final gain/item = -6.388672
  orderLift/item = -0.037290
  contentLift = 0
```

## Reading

Pass-2 support can be bought with larger search depth, but the support is paid
for by larger visible records. The second pass does not restore positive drift;
it roughly doubles the loss in the tested rows.

The selected emitted order does not show a positive recurrence signal. In these
probes, shuffling the same emitted lengths is equal or slightly better. That
means the visible geometry produced by the selected cover is not acting like a
self-fertile grammar in this model.

The stronger content null is exact: under uniform hashes, the actual seed
identity that matched the previous layer is not predictive of future exact
matches once its visible class and cost are fixed. To beat this, a candidate
must name a public class/law whose future distribution is genuinely different
and then pay its supply tax or KL cost.

## Verdict

H167 does not find an emitted-stream recurrence. It closes the immediate
same-budget selected-stream loophole for the uniform branch:

```text
selected visible content lift = 0 by exchangeability
selected visible order/length lift <= 0 in the tested rows
two-pass selected streams remain strongly negative
```

The next target is therefore not ordinary neutral multiplicity or selected seed
identity. It is a public recurrent fertility law for the emitted record
language itself: a predeclared, parseable, high-entropy class whose measured
future value exceeds the H166 remaining gap and its own supply/KL tax.

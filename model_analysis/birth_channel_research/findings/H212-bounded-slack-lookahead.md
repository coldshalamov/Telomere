# H212 - Bounded-Slack Witness Lookahead

## Conjecture

```text
Equal-cost or near-equal witness choice can steer next-pass digest-tail state
without a separate selector, because the chosen seed is already the stored
record.
```

This is the strongest non-greedy witness branch that does not immediately hide
a rank channel.

## Kernel

`H212-bounded_slack_lookahead.py`

For each target block:

```text
generate exact random-oracle witnesses up to Wmax
greedy    = shortest witness
lookahead = witness within greedy_cost+slack minimizing cost - future_credit
tail_state = public digest tail derived from the stored seed
```

The future credit is explicit.  It stands for a real public downstream
fertility law; without that law, the credit is not a compression proof.

## Result

Default small sample:

```text
B=8,A=1,Wmax=8,trials=512
covered=439/512
mean_candidates=2.266515
```

Equal-cost choice, no slack:

```text
S=2,credit=2:
  greedy_tail_rate=0.512528
  lookahead_tail_rate=0.578588
  slack_paid=0
  future_gain=0.132118
  two_pass_gain=0.132118

S=16,credit=2:
  greedy_tail_rate=0.070615
  lookahead_tail_rate=0.082005
  slack_paid=0
  two_pass_gain=0.022779
```

Near-equal slack:

```text
slack=1,S=2,credit=2:
  lookahead_tail_rate=0.637813
  slack_paid=0.059226
  future_gain=0.250569
  two_pass_gain=0.191344
  needed_credit_per_new_tail=0.472727
  miss_tax=0.560606

slack=1,S=16,credit=2:
  lookahead_tail_rate=0.107062
  slack_paid=0.025057
  future_gain=0.072893
  two_pass_gain=0.047836
  needed_credit_per_new_tail=0.687500
  miss_tax=2.920502
```

## Bill

Legal free choice:

```text
same-cost stored seed choice
```

Paid choice:

```text
near-equal seed choice costs extra record bits
forced tail state costs multiplicity/miss probability
future credit must come from a real public fertility/source law
```

## Mutation

H212 identifies a real steering primitive.  The next live attack is to connect
that primitive to a measured, paid, decoder-visible future-fertility law rather
than an assumed credit.  Without such a law, bounded slack only reallocates
already-paid witness multiplicity.

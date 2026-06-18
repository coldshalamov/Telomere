# H144 - Non-Greedy Lookahead Value

Date: 2026-06-18

## Question

Can the slack-replacement method be pushed over the line by not choosing the
first or smallest current seed, and instead choosing a seed with better future
fertility?

Runnable artifact:

```text
model_analysis/birth_channel_research/H144-non_greedy_lookahead_value.py
```

## Model

This is an optimistic target model. Candidate count `M` comes from H143's
exact J3D1 public-board supply and is modeled as Poisson. Each candidate has an
iid future value with exponential mean `mu` bits/atom. If `M` candidates exist:

```text
E[max future value | M] = mu * H_M
```

So:

```text
mu_required = current_positive_delta / E[H_M]
```

This does not claim the future value exists. It tells us how strong a public,
measurable fertility signal would have to be.

## Results

The hard rows:

```text
B4,K32,slack=2,P=4096:
  q = 0.342932
  current delta = +8.841941 bits/atom
  mu_required = 23.287518 bits/atom per candidate
```

The plausible target rows are the bloating high-multiplicity rows:

```text
B4,K128,slack=8:
  q = 1.000000
  E[H_M] = 3.783020
  current delta = +0.032630 bits/atom
  mu_required = 0.008625 bits/atom per candidate

B4,K512,slack=8,P=4096:
  q = 0.998290
  E[H_M] = 2.429209
  current delta = +0.097450 bits/atom
  mu_required = 0.040116 bits/atom per candidate

B4,K32,slack=8:
  current delta = +0.130439 bits/atom
  mu_required = 0.034625 bits/atom per candidate
```

## Reading

This is the first clean numeric target for the user's non-greedy/superposition
idea:

```text
do not ask whether the current seed is shortest;
ask whether its future value beats its current bloat.
```

The decoder does not need the discarded alternatives. If the future-value rule
is public and the chosen seed is stored, the branch choice is not automatically
a metadata side channel.

But the value must be real. If candidate future values are iid noise under the
uniform law, best-of-search must be validated with same-budget random controls.

## Verdict

Non-greedy slack search remains a live research target. The next proof
obligation is a recurrent transfer kernel that measures whether chosen
same-budget slack-8 seeds have at least `0.009-0.04` bits/atom/candidate of
future paid value over random alternatives.

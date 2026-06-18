# H45 - neutral selection / recursive fertility

Date: 2026-06-17

## Question

Can the missing biology-like piece be neutral selection?

Mechanism:

```text
many same-cost seed witnesses decode to the same current span
encoder chooses the witness whose descendants look most fertile
decoder reads the chosen seed normally
```

This is stateless if all neutral choices have the same current decode and the
same witness length. It is the Telomere analogue of synonymous genotypes with
different future evolvability.

## Uniform future-value tail

Under the uniform/content-blind law, future savings have a coding tail:

```text
Pr[V >= s] <= 2^-s
```

H45 models the sharp optimistic case `Pr[V>=s]=2^-s`. If `b` neutral bits give
`M=2^b` choices, best-of-`M` selection yields:

```text
neutral b=3.819: E[max]=4.202, increment=3.202, gamma_increment=0.839
neutral b=8.000: E[max]=8.336, increment=7.336, gamma_increment=0.917
neutral b=16.000: E[max]=16.333, increment=15.333, gamma_increment=0.958
```

So uniform neutral selection approaches one-for-one from below. It does not
produce the `gamma > 1.195` required by the best H18 row.

The equivalent tail-shift theorem is:

```text
Pr[S >= s] <= 2^-s
Pr[max_i S_i >= s] <= min(1, M * 2^-s)
Pr[max_i S_i >= log2(M) + k] <= 2^-k
```

So best-of-`M` shifts the opportunity frontier by `log2 M`; it does not change
the slope. In Kraft form, if each neutral witness gives a valid future code
`ell_j`, then:

```text
ell*(x) = min_j ell_j(x)
sum_x 2^-ell*(x) <= M
ell*(x) + log2 M is Kraft-valid
E_uniform[ell*(X)] >= n - log2 M
```

Average future saving is capped by the neutral selector capacity.

## H18 target comparison

H18 asks how many future saved bits per neutral bit are needed:

```text
slack -8: neutral=3.819, needed gamma=1.195
slack -6: neutral=3.162, needed gamma=1.319
slack -4: neutral=2.574, needed gamma=1.396
```

H45 uniform-selection increments miss all of these:

```text
slack -8: uniform gamma=0.839
slack -6: uniform gamma=0.839
slack -4: uniform gamma=0.752
```

This closes the tempting idea that simply choosing the best neutral seed among
many synonyms gives a superlinear recursive fertility boost under uniform hash
law.

## Source-shaped tails

H45 also checks heavier-than-uniform future-value tails. A pure multiplicative
geometric tail adds baseline source value:

```text
tail x4, neutral b=3.819: E[V]=3.000, E[max]=6.202
```

but the selection increment remains `3.202`, the same as the uniform row. That
means the source itself is valuable, not that neutral selection became free
superlinear information.

Bernoulli jackpot rows show the same distinction. Some source-shaped jackpot
rows can exceed a gamma of one, but only because the jackpot probability is
heavier than the uniform `2^-w` tail. That is a public source/fertility premise
and must be reported with uniform controls negative.

## Verdict

Neutral seed selection is a real Telomere-native, genetics-shaped mechanism:

- same current bytes;
- same witness length;
- no extra selector;
- future fertility steered by the chosen seed.

It does not solve the uniform roughly-all-data goal by itself. Under the
uniform saving tail, it gives less than one incremental future bit per neutral
bit and misses the H18 threshold. A crossing row requires a public
developmental/source law that supplies real future-value lift.

This sharpens the next constructive target:

```text
fixed public developmental source
+ neutral/synonymous seed choices
+ measured future-value lift above H18/H38 threshold
+ uniform controls negative
```

That remains stateless and Telomere-like, but it is no longer content-blind
uniform all-data compression.

## Reward-hack guards

For any future neutral-fertility claim, measure:

- actual neutral multiplicity `M`, `E[log2 M]`, and proof that choices have the
  same current decode and same witness cost;
- current paid deficit after witness width, slack, arity, and record costs;
- net future value `V` after arity, witness, literal fallback, lane,
  interpreter/profile, and recursion costs;
- **selection-only value**:

```text
E[max(V_i)] - E[V_1]
```

not `E[max(V_i)]`;

- tail survival `Pr[V>=s]` and jackpot mass;
- source rows and uniform controls separately;
- public/frozen source profile, slack schedule, jackpot law, and lane rule.

Per-file selection of the tail law, source profile, slack, `w`, `p`, or
multiplier is metadata. Absolute gamma can look positive merely because the
source is easier before selection; the neutral-choice claim must use
incremental gamma.

## Artifact

`model_analysis/birth_channel_research/H45-neutral_selection_fertility.py`

# H70 - Systematic Response Protocol

Date: 2026-06-17

## Question

The next phase should behave like science: learn the response surface, change
one knob at a time, predict the sign before testing, and require controls that
catch hidden metadata.

H70 turns the current Telomere recursion problem into response axes:

- witness bits per selected record;
- public lane / d-choice hit-supply loss;
- near-total exception ledgers;
- source/fertility value lift;
- public-Q cross-entropy;
- negative-drift tail risk;
- final-board visible-state capacity.

Runnable artifact:

```text
model_analysis/birth_channel_research/H70-systematic_response_protocol.py
```

## Witness Response

One bit removed from every selected record buys only `records_per_atom`
bits/atom, because high-arity covers use few records. The current paid witness
frontier is:

```text
target                        miss/rec   rec/atom  miss/atom  x choices
H12 perfect-credit upper         0.746   0.010987   0.008196      1.677
H7 raw first-hit                 1.357   0.008789   0.011927      2.562
H9 fixed slack 0                 1.261   0.009765   0.012314      2.397
```

Reading:

- the required local improvement is not absurd: about `1.7x-2.6x` effective
  selected choices per record would cross these rows;
- but high-arity cover choice has about `1 bit/atom` of selector entropy as
  `K` grows, which is much larger than the current miss;
- therefore any "choose the best bundle" improvement must be encoded as a
  normalized public whole-cover code or explicitly paid as selector entropy.

## Public Lane Response

Public position/phase lanes can be stateless, but they pay in hit supply:

```text
loss = -log2(1 - (1-r)^d)
```

Representative d-choice thresholds:

```text
r=0.10, loss<=0.10 bits: d=26
r=0.10, loss<=0.01 bits: d=48
r=0.25, loss<=0.10 bits: d=10
r=0.50, loss<=0.10 bits: d=4
```

Reading:

- d-choice routing is a real threshold reducer for stateless placement;
- it does not create compression by itself;
- it is useful if paired with a measured fertility/value lift that exceeds the
  remaining lane loss plus witness gap.

## Source/Fertility Response

The biology-shaped route becomes measurable if a public high-fertility class
`F` is declared before encoding:

```text
F has uniform mass f
Q gives F per-state lift a
source visits F with probability c
```

For the closest atom-level public-Q misses:

```text
target                        f      a        c*    enrich   pFF bg=f
H59 raw/Q mixture T1       0.10    2.0    0.1454     1.454     0.4121
H58 frozen bucket Q        0.10    2.0    0.1458     1.458     0.4139
H7 atom miss               0.10    2.0    0.1554     1.554     0.4567
```

Reading:

- this is the first branch with a concrete constructive target;
- it is not arbitrary uniform-data compression;
- recursion needs the rewrite map to maintain the class:

```text
c_{t+1} = c_t p_FF + (1-c_t) p_OF >= c*
```

With background inflow `p_OF=f`, the nearest atom-level rows need only
`p_FF ~= 0.41-0.46`. With no background inflow they need `p_FF=1`.

## Near-Total Exception Response

This axis prices salted open/carry branches. It is deliberately not charged to
the Total-Cover branch where every record opens.

```text
P=64,   eps=0.010: ledger/rewrite 0.141986 bits
P=4096, eps=0.001: ledger/rewrite 0.023431 bits
```

Reading:

- the user's total-cover instinct is right: if almost everything rewrites, the
  open/carry/birth channel can become cheap;
- the witness economics are still the main gate;
- sparse content-selected exceptions must still pay subset entropy.

## Tail Response

A negative geometric drift is not enough for "roughly all data over arbitrary
passes." A fixed bad fraction eventually hits almost every path:

```text
eps=0.010: Pr(blowup)<=0.50 only through P=68
eps=0.001: Pr(blowup)<=0.50 only through P=692
eps=0.0001: Pr(blowup)<=0.50 only through P=6931
```

Reading:

- future `E[log rho] < 0` claims must report tail risk;
- arbitrary-pass claims need bad fraction `O(1/P)` or exact zero;
- exact zero bad fraction with net shrink returns to the counting wall.

## Experiment Cards

H70 defines seven cards to keep future work systematic:

1. corrected high-K Total-Cover rerun;
2. whole-cover normalized `Q`;
3. public fertility/source class;
4. public lane plus d-choice routing;
5. near-total exception ledger;
6. negative-drift tail audit;
7. final-board/public invariant.

Each card has:

```text
changed knob
prediction
paid currency
control
stop rule
```

## Verdict

H70 does not solve Telomere. It makes the next search scientific:

- if an idea is a Total-Cover witness idea, it must save about
  `0.746-1.357` paid bits/selected record;
- if it is a public placement lane, it must beat lane supply loss;
- if it is biology-shaped, it must declare a public fertility/source law and
  maintain it recursively;
- if it claims negative recursive drift, it must price the bad tail;
- if it uses final boards or arrangements, it must pass a visible-state
  counting check.

The next most constructive target is still:

```text
public whole-cover / Q-style accounting
+ public stateless geometry
+ declared fertility/source invariant
+ uniform negative controls
```

That is the closest route that resembles the DNA intuition without hiding the
answer in an unpriced selector.

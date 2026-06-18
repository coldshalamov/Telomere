# H73 - Final-State Entropy Kernel

Date: 2026-06-17

## Question

Can final-position boards, egg cartons, public lanes, orderless decode, or
coordinate-as-birth schemes make stateless decoding work without secretly
storing open/carry/birth history?

H73 keeps those ideas alive as decode geometry, but prices their visible-state
capacity.

Runnable artifact:

```text
model_analysis/birth_channel_research/H73-final_state_entropy_kernel.py
```

## Pricing Rules

For `R` final survivors in coordinate space `Q` over `P` possible birth/open
passes:

```text
occupancy coordinates:  log2 C(Q,R)
ordered coordinates:    log2 (Q)_R = log2 C(Q,R) + log2 R!
birth labels:           R log2 P
ready subset:           log2 C(N,R)
orderless stream:       log2 R! unless order is irrelevant
```

Final boards are free only when the valid final arrangement is public or very
low-capacity. If it is rich enough to encode arbitrary content-selected
history, that entropy is in the final state.

## Exact Tiny Rows

For `N=12,R=4,P=8`:

```text
mechanism                      hidden   occ visible   ordered visible
sparse ready + birth labels    20.951        8.951            13.536
expanded board encodes birth   20.951       21.664            26.249
orderless/confluent bag         4.585        0.000             4.585
```

Reading:

- a `Q=N` occupancy board can encode which `R` items are ready, but not their
  `R log2 P = 12` birth bits;
- a `Q=N*P` expanded board has enough capacity, but that capacity is stored as
  visible coordinate entropy;
- orderless decode is stateless only for a bag source, or after paying
  `log2 R!` to restore arbitrary stream order.

## Near-Total Exceptions

For `N=12,P=8`:

```text
1 exception:  6.392 bits
2 exceptions: 11.659 bits
```

This supports the total-cover instinct: exceptions can be cheap when they are
truly rare. Sparse arbitrary readiness is not cheap.

## Public Lanes

For `R=4` survivors:

```text
r=0.25,d=1: supply loss 8.000 bits
r=0.25,d=4: supply loss 2.195 bits
r=0.50,d=4: supply loss 0.372 bits
```

Public lanes give the decoder placement/open facts without metadata, but the
encoder pays by losing match supply unless d-choice routing makes the lane
nearly as available as the full board.

## Verdict

The best decode-geometry branch is:

```text
public lane or total-cover active region
+ position/phase-derived salt
+ public child placement
+ rare exceptions explicitly priced
```

Geometry can solve stateless placement. It does not create compression by
itself. Total-Cover remains the clean branch because hidden open/carry bits are
zero; the remaining gate is still witness/public-Q economics.

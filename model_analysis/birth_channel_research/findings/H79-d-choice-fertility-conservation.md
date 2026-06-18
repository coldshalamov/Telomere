# H79 - D-Choice Fertility Conservation

Date: 2026-06-17

## Question

Can d-choice routing create a fertile next layer cheaply enough to maintain
recursive stateless compression?

This reopens the public-lane idea after H77/H78, but separates two different
currencies:

```text
placement d-choice: one stored record has d public candidate cells
witness d-choice: encoder has d alternative seed witnesses for the same bytes
```

Runnable artifact:

```text
model_analysis/birth_channel_research/H79-d_choice_fertility_conservation.py
```

## Result

For a public fertile class of mass `r`, d choices hit it with:

```text
h = 1 - (1-r)^d
```

The cheap placement-lane bill is:

```text
placement_loss = -log2(h)
```

But if the d choices are actually alternative witnesses used to bias the next
record-value stream, their multiplicity is an information channel:

```text
witness_cost = log2(d)
```

The created class-level source information is:

```text
KL(Bernoulli(h) || Bernoulli(r))
```

Representative rows:

```text
r=0.10,d=16: hit=0.8147, placement_loss=0.296, log2(d)=4.000,
             KL made=2.043, fake net=+1.747, honest net=-1.957

r=0.10,d=23: hit=0.9114, placement_loss=0.134, log2(d)=4.524,
             KL made=2.609, fake net=+2.475, honest net=-1.914
```

The fake positive appears only when witness-value fertility is charged at the
placement-lane price.

## H77 Threshold Rows

For the exact H74 high-`Q` class, H77 needed roughly:

```text
c* ~= 0.508
p_FF ~= 0.903
```

At `r=0.10`:

```text
target                 d needed   placement loss   log2(d)   KL made   honest net
exact H74 c*~0.508         7          0.939         2.807     0.807      -2.000
exact H74 pFF~0.903       23          0.134         4.524     2.609      -1.914
```

So d-choice can make the lane look cheap, but if the same d alternatives are
the source of future record-value bias, the multiplicity bill dominates.

## Surviving Use

Public d-choice remains useful for position, phase, and salt geometry:

- decoder can recompute candidate cells;
- canonical placement is stateless;
- no selected-position bitmap is needed when the lane is public.

It does not by itself create a fertile byte/value source. The next surviving
target must either:

- use position/phase as the refreshed object, not as a hidden value selector; or
- measure real value lift `gamma > current_miss + lane_loss` without borrowing
  uncharged witness-choice bits.

## Verdict

H79 blocks the apparent "cheap d-choice fertility" loophole. It does not close
public position/salt lanes, but it forces the next experiment to keep placement
choices and witness/value choices in separate ledgers.

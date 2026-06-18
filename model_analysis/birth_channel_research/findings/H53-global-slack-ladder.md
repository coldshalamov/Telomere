# H53 - paid global slack ladder

Date: 2026-06-17

## Question

Can a layer-level slack ladder harvest the occasional advantage of slack `1`
or `2` while staying stateless?

Mechanism:

```text
choose one slack from public set S for the whole layer/pass
decode all record widths with that slack
charge the slack selector once for the layer/pass
```

This is stateless if the selector is in the layer header/stream. It is not free.
The ideal selector cost is:

```text
log2 |S|
```

or, under a frozen public prior:

```text
-log2 q(slack | context)
```

## Kernel

Runnable artifact:

```text
model_analysis/birth_channel_research/H53-global_slack_ladder.py
```

H53 preserves nested slack correlation. It samples one exponential first-hit
variable per interval; a higher-slack hit is a subset of lower-slack hits:

```text
hit_s(a) iff E <= 2^(min(D, aB-s) - aB)
```

So the ladder does not get independent redraws for each slack.

Modes:

- `paid_best`: choose the cheapest full-cover slack and charge `log2 |S|`;
- `oracle_unpaid_best`: same choice with no selector, as a lower bound;
- `paid_first_full`: diagnostic mode for a public slack order, still charged.

## Bounded run

Default run:

```text
B=4,K=192,D=768,atoms=192
S={0,1,2}
passes=2
trials=2
train trials=4
iterations=1
selector bits=log2(3)=1.585
```

Results:

```text
paid_best:
  mean log2 rho = +0.004480
  geometric rho = 1.003110
  coverage = 1.000
  records/atom = 0.009091
  avg arity = 110.00
  avg slack = 1.00

oracle_unpaid_best:
  mean log2 rho = +0.001973
  geometric rho = 1.001369
  coverage = 1.000
  records/atom = 0.006502
  avg arity = 153.80
  avg slack = 1.25
```

## Reading

The paid global ladder does not cross. The unpaid ladder improves over strict
fixed slack, but even the unpaid lower bound remains positive in the default
row:

```text
H52 strict K=192,D=768,s0: +0.003658
H53 unpaid ladder:          +0.001973
H53 paid ladder:            +0.004480
```

The selector is small but material at this layer size. For `atoms=192,B=4`, a
one-bit selector is about:

```text
log2((768+1)/768) ~= 0.001877 log2-rho
```

So a ladder needs more than a cosmetic improvement to cross after paying the
slack ID.

## Timing-limited larger-K scout

A full `B=4,K=256,D=1024,atoms=512,S={0,1,2,3}` run with two passes and two
trials was stopped after about 90 seconds. That row should not be treated as a
result until the kernel is optimized or the sample contract is narrowed.

A deliberately tiny timing scout did finish:

```text
B=4,K=256,D=1024,atoms=256
S={0,1}
passes=1
trials=1
train trials=1

paid_best:          +0.010266 mean log2 rho
oracle_unpaid_best: +0.008867 mean log2 rho
```

This is not evidence-grade, but it did not hint at an immediate larger-K
selector breakthrough. The scientific next step is either an optimized H53
kernel for `K=256/384` or a different mechanism axis, not a long unbounded run.

## Why headerless trial slack is not free

A deterministic "try slacks and keep the one that decodes" rule is execution,
not accounting. It is free only if the decoder can prove a unique surviving
slack from the compressed stream and public rules. Otherwise the ambiguity is:

```text
missing bits = log2 |{s in S: parse/decode/check succeeds}|
```

A checksum/referee must also be priced:

```text
E[false survivors] = (R-1) * 2^-b
b >= log2(R-1) + lambda
```

Embedding slack in seed grammar pays the same class-tax form as H48:

```text
E[-log2 q_S] = H(S) + KL(P_S || q)
```

Local per-record slack is worse: it reintroduces the width stream H9 was trying
to remove.

## Verdict

The global slack ladder is a valid stateless mechanism only when paid. In the
tested row it does not solve the repeated-pass gap.

The closest paid boundary remains:

```text
H52 strict fixed slack: +0.003658 to +0.003775 mean log2 rho
H53 paid global ladder: +0.004480 mean log2 rho
```

The next useful ladder work would need either:

- a larger `K=256/384` paid ladder run with shared nested hits and selector
  charged; or
- a real decoder audit proving a headerless unique-survivor slack rule.

Without that, slack adaptation is just another selector channel.

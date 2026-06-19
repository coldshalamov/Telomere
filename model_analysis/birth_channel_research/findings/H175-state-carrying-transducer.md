# H175 - State-Carrying Total-Cover Transducer

Date: 2026-06-18

## Conjecture

Stop storing salt as metadata. Let every successful witness emit the next salt
as unconstrained digest tail:

```text
z_i = H("Telomere-State-v1" || q_i || arity_i || seed_i)
x_i = z_i[0 : arity_i * B]
q_{i+1} = z_i[arity_i * B : arity_i * B + r]
```

The record stores only:

```text
[arity][seed witness]
```

The decoder starts from public `q_0`, decodes records in order, expands
`(x_i,q_{i+1})`, and therefore knows the state before the next expansion.

If `x_i` is the only constrained prefix, random-oracle accounting says:

```text
Pr[x_i matches target] = 2^-|x_i|
q_{i+1} | match is uniform
```

So observing `q_{i+1}` is free. Requiring a chosen tail value costs `r` bits of
match supply.

Runnable artifact:

```text
model_analysis/birth_channel_research/H175-state_carrying_transducer.py
model_analysis/birth_channel_research/H175-state_carrying_transducer_dp.py
```

## Decoder State Invariant

Before record `i`, the decoder must already know:

```text
q_i
arity_i
where the current record starts
how many previous-layer bits arity_i expands
```

Then it reads the seed witness, computes the digest, emits `x_i`, derives
`q_{i+1}`, and proceeds. Segment anchors or random access require explicit
anchor states at:

```text
r / A bits per record
```

for `r`-bit state every `A` records.

## Tail Sanity

The kernel directly measures observe-vs-condition:

```text
B=4 D=8 r=4 trials=80
unconstrained_matches=1222
q_out_zero=91
observed conditioned/unconstrained=0.074468
expected about 2^-r=0.062500
```

At `D=10`:

```text
unconstrained_matches=2545
q_out_zero=163
observed conditioned/unconstrained=0.064047
expected about 2^-r=0.062500
```

This validates the core accounting rule:

```text
observe tail: 0 bits
condition tail: r bits
```

## Exact-Cost Chained Cover

The first state-chain DP uses exact V1/J3D1 record costs for arities `1..5`.
It keeps records `[arity][J3D1 seed]`; no open/carry, birth-pass, sparse map, or
final-position ledger is charged because this is total-cover.

Tiny default smoke row:

```text
B=4 atoms=16 K=5 D=8 r=4 trials=10
policy        support  gain/trial   out/in  records   avg a
shortest        1.000     -41.800    1.653    8.800   1.818
equal-cost      1.000     -39.500    1.617    8.600   1.860
slack+1         1.000     -37.200    1.581    8.400   1.905
slack+4         1.000     -36.300    1.567    8.300   1.928
slack+8         1.000     -35.800    1.559    8.200   1.951
```

Deeper search improves the row but does not cross:

```text
B=4 atoms=8 K=5 D=12 r=4 trials=4
policy        support  gain/trial   out/in  records   avg a
shortest        1.000     -15.500    1.484    3.250   2.462
slack+4         1.000     -14.000    1.438    3.000   2.667
slack+8         1.000     -14.000    1.438    3.000   2.667
```

So state-carrying salt solves the salting metadata problem, but exact V1/J3D1
still expands in this powered toy.

## Recursive Support DP

The companion sampled-edge trellis kernel propagates record lengths as the next
layer's item lengths and reports multi-pass support/log-rho:

```text
python model_analysis/birth_channel_research/H175-state_carrying_transducer_dp.py
```

For `B=4,K=5,D=12,items=16,passes=2,trials=20`:

```text
r policy    supp1    suppP   gain/a    meanLog   finalLog
0 shortest  1.000    0.000   -2.0656    0.5981   0.0000
0 slack:4   1.000    0.000   -2.1406    0.6170   0.0000
4 shortest  1.000    0.000   -1.8656    0.5509   0.0000
4 equal     1.000    0.000   -1.8656    0.5515   0.0000
4 slack:4   1.000    0.050   -1.5969    0.4896   1.0980
```

For `passes=3`, complete support is `0.000` for the same rows.

This is the sharper failure mode: state tail and slack improve the one-pass
cover, but recursive support still collapses under exact V1/J3D1 record-stream
targets. The next attack must make the emitted surface easier to cover again,
not merely salt it.

## Surface-Choice Lookahead

The important positive signal is two-pass lookahead. With `B=4`, `atoms=8`,
`K=5`, `D=8`, `r=4`, and exact record costs:

```text
policy        support  out/in  2p wins   2p delta
equal-cost      1.000  1.719        3      4.500
slack+1         1.000  1.633        3     10.000
slack+2         1.000  1.633        3     11.500
slack+4         1.000  1.602        3     15.750
slack+8         1.000  1.602        3     15.750
```

At `D=10`:

```text
policy        support  out/in  2p wins   2p delta
equal-cost      1.000  1.648        2      1.000
slack+1         1.000  1.578        3      7.500
slack+4         1.000  1.516        3     11.500
slack+8         1.000  1.516        3     11.500
```

`2p delta` is:

```text
greedy_two_pass_bits - lookahead_two_pass_bits
```

Positive values mean bounded-slack surface choice improved exact two-pass cost
without storing a selector. This is a real mechanism signal, not a proof of
compression yet.

## Accounting Traps

The digest tail must not be double-counted:

- free: using whatever `q_{i+1}` the paid witness already emits;
- paid: choosing a witness because its `q_{i+1}` lies in a future-fertile class;
- paid: segment anchors, random access states, profile IDs, width schedules,
  non-public arity/position choices, and repair/fallbacks;
- invalid: scoring only successful full covers while failed targets vanish.

## Verdict

H175 is not a positive construction yet. It does materially change the salting
problem:

```text
state-carrying witness tails give stateless sequential freshness without
per-record salt metadata or birth-pass tags in total-cover
```

But the exact V1/J3D1 witness language still has positive length drift in the
tested toy rows, and the sampled recursive DP shows support collapse by two to
three passes. The strongest next mutation is:

```text
state-carrying transducer
+ bounded-slack surface lookahead
+ public finite-state width grammar or mixed-radix rank packing
+ higher-arity/custom total-cover witness language
```

The next executable target is not "more salt"; it is shaving the exact witness
and width bill while preserving the state-chain decoder invariant.

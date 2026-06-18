# H39 - Two-layer source-shaped fertility kernel

Date: 2026-06-17

## Question

Can the live H28/H36/H37/H38 source-shaped target actually cross in a concrete
toy while uniform controls stay negative?

Target from H38:

```text
r = 0.10
d = 16
lane_loss = -log2(1-(1-r)^d) = 0.296 bits/selected record
```

The honest H28 test is:

```text
value_lift = E[V | public class C] - E[V]
crosses iff value_lift > lane_loss
```

where `V` is already-priced future-layer value.

## Mechanism

Public lane:

```text
C_i = any of d public candidate routes lands in active fraction r
```

Public developmental source:

```text
if C_i = 1: future child is easy with probability q1
if C_i = 0: future child is easy with probability q0
```

Uniform control:

```text
future child is easy with same global marginal qbar,
but independent of C_i
```

All source parameters are fixed in the kernel. They are not fit per file.

## Entropy version

A Bernoulli future source with bias `p` gives:

```text
source_lift_per_bit = 1 - H2(p)
uniform_penalty_per_bit = CE(U, p) - 1
```

Representative H39 rows:

```text
r=0.10,d=16,future_bits=2,p=0.75:
  source_lift=0.377, source_net=+0.082, uniform_net=-0.711

r=0.10,d=16,future_bits=4,p=0.75:
  source_lift=0.755, source_net=+0.459, uniform_net=-1.126

r=0.10,d=8,future_bits=4,p=0.80:
  source_lift=1.112, source_net=+0.300, uniform_net=-2.100
```

So the d-choice lane tax can be beaten by a modest predeclared source entropy
deficit. The uniform control pays cross-entropy and remains negative.

## Exact value-lift version

H39 also measures the exact H28/H38 lift definition with Monte Carlo:

```text
k = future children per selected record
w = net priced future bits per easy child
q1 = P(easy child | C=1)
q0 = P(easy child | C=0)

V = k * w * easy_child_count
value_lift = E[V|C] - E[V]
```

The analytic source lift is:

```text
f = 1-(1-r)^d
value_lift = k * w * (1-f) * (q1-q0)
```

For the headline row:

```text
r=0.10,d=16,f=0.814698,lane_loss=0.295663
k=4,w=2.0,q1=0.50,q0=0.20
analytic_lift=0.444725
analytic_net=+0.149062
```

Measured H39 row:

```text
source:  f=0.8127, qbar=0.4434, all_V=3.547, C_V=3.995,
         lift=0.448, net=+0.153

uniform: f=0.8142, qbar=0.4452, all_V=3.562, C_V=3.564,
         lift=0.002, net=-0.293
```

Lower-value variants miss as expected:

```text
k=4,w=1.0,q1=0.50,q0=0.20: source net=-0.072
k=2,w=2.0,q1=0.50,q0=0.20: source net=-0.074
k=4,w=2.0,q1=0.40,q0=0.25: source net=-0.075
```

This is useful: it shows the threshold is not magic. The source must supply
enough measured future value.

## Reward-hack guards

H39 is only valid under these constraints:

- the developmental profile is fixed publicly or its profile id/bytes are
  charged;
- route choice is canonical; the encoder does not choose among the `d` routes
  after seeing content;
- `w` is net future value after arity, witness, literal fallback, lane, and
  interpreter costs;
- current-layer hit rate is not allowed to differ by class unless separately
  priced;
- the comparison is `E[V|C] - E[V]`, not fertile-vs-infertile only;
- random/uniform controls must stay negative.

## Verdict

H39 gives a constructive Telomere-shaped **source-language positive control**:

```text
public developmental source
+ public d-choice fertility lane
+ stateless decode
+ measured future value_lift > lane_loss
+ uniform controls negative
```

It does **not** solve the original roughly-all-data uniform/content-blind goal.
It proves the adjacent biology-shaped premise is coherent and quantitatively
reachable:

```text
for r=0.10,d=16, need >0.296 bits/selected-record future value;
the headline public source row measures about +0.153 bits/selected-record net.
```

## Artifact

`model_analysis/birth_channel_research/H39-two_layer_fertility_source.py`

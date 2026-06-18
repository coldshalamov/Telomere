# H34 - XOR / fountain superposition

Date: 2026-06-17

## Question

Can order-insensitive algebra remove the stateless decode problem?

Mechanism:

```text
record stores a recipe/set of seed vectors
decoder regenerates vectors
decoder XORs them to recover the target span
```

This is attractive because decode order no longer matters. XOR is commutative,
so the opened pieces can be combined into the right value without an open/carry
schedule.

## Decoder observations

1. Open vs carry: every record opens. No carry channel is needed.
2. Birth pass/salt: in a total-cover layer, the layer/pass is public. A fixed
   public recipe family can also include pass/position salt.
3. Freshness: public salt/recipe changes can refresh candidates, but only as a
   public relabeling unless the encoder chooses among alternatives and pays the
   selector.
4. Stored information: the record must store either seed indices, an unordered
   subset rank, dense linear coefficients, or a fountain recipe.

So this family solves parse-order geometry. The remaining issue is pure
selector entropy.

## Sparse subset XOR

If the public seed universe has `M = 2^s` vectors and a record XORs exactly `k`
of them, the unordered combination domain is:

```text
C(M,k)
```

The image contains at most that many targets. Under the uniform hash law, if
`n` target bits are arbitrary, expected coverage is approximately:

```text
coverage = 1 - exp(-C(M,k) / 2^n)
```

H34 examples before Telomere record overhead:

```text
n=64,  s=32, k=2: selector=63.000 bits, coverage=0.393, not all data
n=64,  s=32, k=4: selector=123.415 bits, coverage~=1,  +59.415 bits over raw
n=128, s=32, k=4: selector=123.415 bits, coverage=0.041, not all data
n=128, s=32, k=8: selector=240.701 bits, coverage~=1, +112.701 bits over raw
```

The direct form that stores `k` seed indices costs `k*s` bits and is never
better than the unordered selector rank.

## Public linear basis

A public rank-`r` GF(2) basis covers exactly `2^r` targets and stores `r`
coefficient bits.

```text
n=128, r=64:  coverage=2^-64,  net_if_reachable=64 bits
n=128, r=128: coverage=1,      net=0 before record overhead
```

This is a clean stateless code, but full coverage costs raw entropy.

## Fountain recipe

A `c`-bit random recipe family has `2^c` possible outputs. For desired coverage
`p`, the required recipe width is:

```text
c = n + log2(-ln(1-p))
```

H34 examples:

```text
p=0.50:     c = n - 0.529 bits
p=0.90:     c = n + 1.203 bits
p=0.99:     c = n + 2.203 bits
p=0.999999: c = n + 3.788 bits
```

So high coverage requires selectors at or above raw target size before any
arity, mode, checksum, or record overhead.

## Multiplicity illusion

Small exact enumeration shows why many decompositions do not become free
compression. With `n=12`, random vectors, and unordered XOR subsets:

```text
M=32, k=4: domain=35960, support=4096,
           selector=15.134 bits, support=12.000 bits,
           multiplicity=3.134 bits

M=32, k=5: domain=201376, support=4096,
           selector=17.620 bits, support=12.000 bits,
           multiplicity=5.620 bits
```

Once the support is full, the excess selector bits are exactly the average
preimage multiplicity. A bits-back implementation can at best return those
multiplicity bits to the raw bound. It does not push below raw for uniform data
without a non-uniform source prior or another paid reservoir.

## Verdict

XOR/fountain superposition is useful as a stateless placement and out-of-order
decode geometry. It does not supply the missing maintained compression channel
under the content-blind uniform law:

- sparse combinations miss most targets;
- full-rank linear combinations cost raw entropy;
- high-coverage random recipe families cost raw entropy plus overhead;
- latent multiple decompositions are bits-back tape, not free savings.

This collapses to the H29/H32 collective-code reservoir story unless a
predeclared non-uniform source prior gives targets more than one future bit of
value per selector bit.

## Artifact

`model_analysis/birth_channel_research/H34-xor_fountain_superposition.py`

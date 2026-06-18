# H134 - Modular Clock Readiness

## Question

Can CRT clocks, even/odd classes, sign lanes, or Fibonacci/Zeckendorf-style
registers tell the decoder a record's birth/open epoch more cheaply than a pass
tag?

## Model

If a seed witness is restricted to residues:

```text
mod m_1, mod m_2, ..., mod m_k
```

then seed supply is thinned by:

```text
prod_i m_i
```

and the number of distinguishable epochs is at most:

```text
lcm(m_1, ..., m_k)
```

So the entropy floor is:

```text
cost >= log2(prod_i m_i) >= log2(lcm_i m_i) >= log2(P)
```

for `P` live epochs.

## Result

Best small CRT moduli:

```text
P=2:
  moduli = (2,)
  cost = 1.000000 bits
  ideal = 1.000000 bits

P=64:
  moduli = (5,13)
  lcm = 65
  cost = 6.022368 bits
  ideal = 6.000000 bits

P=4096:
  moduli = (8,19,27)
  lcm = 4104
  cost = 12.002815 bits
  ideal = 12.000000 bits
```

Finite lifetime is the only useful discount:

```text
max lifetime L=1:
  ages = 2
  min bits = 1.000000
  reading = two-epoch parity

max lifetime L=63:
  ages = 64
  min bits = 6.000000
```

Fibonacci/Zeckendorf registers do not evade the floor; they just change the
register grammar. Example counts:

```text
limit=64:
  symbols = 89
  floor = 6.475733 bits
```

## Interpretation

CRT clocks can be almost perfectly efficient, but perfect efficiency is still
only equality with `log2(P)`. Public position/lane clocks move the same cost
into match-supply thinning: only one residue/lane out of `P` is eligible.

So modular clocks are useful stateless engineering after another invariant
bounds record lifetime. They do not provide a free many-pass birth/open channel.
This reinforces the H99/H100 conclusion: even/odd is live only in the
two-epoch forced-refresh geometry.

## Artifact

`model_analysis/birth_channel_research/H134-modular_clock_readiness.py`

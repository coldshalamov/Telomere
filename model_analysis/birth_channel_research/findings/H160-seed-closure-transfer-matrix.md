# H160 - Seed Closure Transfer Matrix

Date: 2026-06-18

## Question

Was H159 too dependent on finite target-node enumeration, or is the
seed-bearing closure mass intrinsically tiny in the H96 surrogate?

Runnable artifact:

```text
model_analysis/birth_channel_research/H160-seed_closure_transfer_matrix.py
```

## Model

H160 counts source seed-record streams directly:

```text
source y = sequence of H96 records
decode(y) = emitted record.value bits
closed iff emitted bits parse as H96 visible records
```

It runs the emitted target bits through a parser for the H96 visible
seed-record language. This avoids conditioning on a pre-enumerated target node
set.

Reported bills:

```text
clFrac = closed_mass / total_source_mass
clTax  = -log2(closed_mass / total_source_mass)
cmp    = count of closed paths with len(source) < len(target)
cmpTax = same mass tax restricted to compressive closed paths
min(c-a) = min(record_visible_cost - emitted_arity_bits)
```

## Results

Sanity check against H159:

```text
H160 closed paths:
  K4,D3,cap24 = 7
  K4,D3,cap28 = 127
  K5,D3,cap28 = 283

H159 closed edges:
  K4,D3,cap24 = 7
  K4,D3,cap28 = 127
  K5,D3,cap28 = 283
```

Closure mass rows:

```text
K4,D3,cap24:
  total paths = 1576
  closed paths = 7
  clFrac = 0.000131
  clTax = 12.900937 bits
  compressive closed paths = 0
  bestG = -11

K4,D3,cap28:
  total paths = 13648
  closed paths = 127
  clFrac = 0.000145
  clTax = 12.755488 bits
  compressive closed paths = 0
  bestG = -11

K5,D3,cap28:
  total paths = 22618
  closed paths = 283
  clFrac = 0.000258
  clTax = 11.918435 bits
  compressive closed paths = 0
  bestG = -11
```

Every tested row has positive `min(c-a)`: each source record costs more visible
bits than it emits as target bits. Therefore no source stream can be shorter
than its emitted bitstream inside this H96 bit-level surrogate.

## Reading

H160 confirms H159's closed-edge counts and adds a mass ledger. Closure exists
only as a tiny subset, costing about `12` bits of source mass in the best
tested rows. More importantly, the closed subset is non-compressive.

This is not a broad proof against every Telomere recursion idea. It is a proof
that the H96 bit-level seed-record language cannot be the missing recurrent
compression core. A source record in this surrogate emits only `arity` target
bits, while its visible witness costs more than that.

## Verdict

The closed-core branch needs a different grammar to remain alive:

```text
record-to-item expansion, not record-to-bit expansion
```

The next useful kernel should be prefix-safe and item-level: a source record
emits `arity` self-delimiting items, each item can be literal or seed-record,
and the target parser counts item boundaries rather than raw bits.


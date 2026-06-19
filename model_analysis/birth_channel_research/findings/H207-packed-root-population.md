# H207 - Packed Root Population / Root-Record Language Attack

## Conjecture

```text
H206 misses only because V1/J3D1 root records cost more than their support
rank. Pack the visible population roots directly as M*G raw bits.
```

## Kernel

`H207-packed_root_population.py`

The kernel separates:

```text
generated-only packed roots, no fallback
packed roots with a mode/preset bill
packed roots with raw fallback using leftover Kraft
```

For `S=M*G` support bits and output width `N`:

```text
packed_paid = S + mode_bits
inside_gain = N - packed_paid
membership_tax = N - S
uniform_net_generated_only = -mode_bits
```

If a raw fallback is added, the generated code consumes Kraft mass:

```text
q = 2^(-mode_bits)
raw_fallback_length = N - log2(1-q)
```

## Result

Generated-only no-mode rows tie after membership tax:

```text
M=32,G=16,A=5,P=6
out_bits = 16000000
support_bits = 512
packed_paid = 512
inside_gain = 15999488
membership_tax = 15999488
uniform_net_generated_only = 0
support_fraction = 2^-15999488
```

Adding a one-bit mode gives:

```text
uniform_net_generated_only = -1
raw fallback delta ~= +1 bit under uniform data
```

Adding a two-bit mode gives:

```text
uniform_net_generated_only = -2
raw fallback delta ~= +0.415037 bits
```

The fallback delta approaches zero only as the generated branch Kraft mass
approaches zero, which also removes the generated branch's effect.

## Bill

```text
mode/preset Kraft mass or missing support membership
```

Packing roots exactly closes H206's current-format overhead, but it does not
create arbitrary-uniform compression:

- no mode/fallback: ties only inside a tiny generated support set;
- positive mode: loses mode bits after membership tax;
- raw fallback: leftover Kraft makes uniform mean length at least raw.

## Mutation

Packed roots are valuable for a source/reachable generated mode. They do not
solve roughly-all-data recursion. The next attack must either make the source
membership law explicit, or find a non-Kraft root syntax, which would have to
remain uniquely decodable and pass the same Kraft sanity check.

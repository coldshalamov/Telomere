# H88 - Frozen Soft Grammar Overhead

Date: 2026-06-17

## Question

Lane A proposed a fixed public soft-law grammar:

```text
P_theta(x) proportional to U(x) * 2^(theta * V(x))
```

Can a stateless frozen grammar realize this law without a stored profile or
selector, and does finite parser overhead kill H86's soft-law margin?

Runnable artifact:

```text
model_analysis/birth_channel_research/H88-frozen_soft_grammar_overhead.py
```

## Mechanism

For a public block length `m`, round `m * P_theta(x)` into integer counts
`n_x`. The canonical type class has:

```text
|T| = m! / product_x n_x!
```

The decoder can unrank:

```text
k = floor(log2 |T|)
```

payload bits into a sequence from this type class. No adaptive profile is stored
if `theta`, `m`, and the canonical count rule are fixed public constants.

The finite bill per emitted H80 word is:

```text
bill = 12 - k/m
```

and the audited margin is:

```text
eta = E_Phat[V] - E_U[V] - bill
```

## Result

Small `m` is misleading: when `m < 4096`, rounding a soft law over the 4096-word
domain degenerates into a hard support class. That is a real finite parser
overhead, not a compression result.

The large-block rows recover the soft law:

```text
theta  m      bill      lift      eta       top25
0.90   8192   1.898315  3.024519  1.126203  0.744507
0.90   32768  1.444977  2.979168  1.534191  0.739502
1.00   32768  1.637543  3.195070  1.557528  0.779053
```

Best scanned row:

```text
theta=1.05, m=32768, bill=1.734528, lift=3.295267,
eta=1.560740, top25=0.797302, active=3188
```

Best row with `m <= 512` is still negative:

```text
theta=1.49, m=512, bill=4.871094, lift=4.542583, eta=-0.328511
```

## Reading

A frozen type-class grammar can realize a soft tilted law with no per-file
profile channel once the public block is large enough. This makes the native
soft-law target concrete.

But H88 still audits a grammar and a value score, not a compressor. The missing
proof is whether `V` becomes actual second-pass Telomere witness savings under
the exact record accounting. Without that, `eta` is a target metric rather than
a verified compression margin.

## Verdict

Frozen public soft-law grammar survives finite parser accounting in the exact
toy domain at large block sizes.

The next target is a witness-savings kernel: use the grammar-induced law as the
input distribution to an exact total-cover/witness model and check whether
actual selected records cross after all costs, with uniform and shuffled
controls.

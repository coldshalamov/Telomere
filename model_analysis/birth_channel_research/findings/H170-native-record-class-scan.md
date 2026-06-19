# H170 - Native Record-Class Scan

Date: 2026-06-18

## Question

H169 ruled out simple public bit-shape classes over H89 raw visible words. What
if the public class is more Telomere-native: first arity, record count,
payload-width bucket, cost bucket, or visible record-bit suffix/prefix?

Runnable artifact:

```text
model_analysis/birth_channel_research/H170-native_record_class_scan.py
```

## Model

H170 enumerates H96's concrete emitted record strings:

```text
B=1, N=5, K=3, D=3
descriptions = 52,352
total current witness mass = 3.734984694033e-04
```

For each emitted record string `c`, it computes actual next-pass paid witness
saving:

```text
future_paid_saving(c) = len(c) - best_cover_cost(c)
```

The public-class tax is priced by current witness mass, not by a flattering
unweighted count:

```text
f_mass = sum_{c in F} 2^-cost(c) / sum_c 2^-cost(c)
tax = -log2(f_mass)
v_F = E[future_paid_saving | F, weighted by 2^-cost]
net_after_tax = v_F - tax
```

Supply-weighted uniform future value is:

```text
E future_paid_saving = -51.634654 bits/record-string
```

H168 production targets are shown only as diagnostic scale markers; H170 is a
tiny H96 record-language microscope, not a production bits/record proof.

## Best Allowed Native Classes

```text
class                 family         f_mass    tax       v_F        v_O        net_after_tax
bits_suffix3=101      bit-suffix     0.20859  2.26125  -40.94744  -54.45148  -43.20869
total_cost<=16        cost           0.16341  2.61339  -41.50000  -53.61431  -44.11339
all_payload<=5        payload-width  0.16920  2.56320  -42.10684  -53.57508  -44.67004
bits_suffix2=01       bit-suffix     0.31571  1.66335  -43.78771  -55.25490  -45.45106
total_cost<=18        cost           0.61281  0.70650  -46.73333  -59.39188  -47.43983
all_payload<=7        payload-width  0.70026  0.51404  -48.08633  -59.92433  -48.60037
first_arity=3         arity          0.46943  1.09101  -48.47375  -54.43134  -49.56476
record_count=2        record-count   0.92176  0.11753  -50.17590  -68.82081  -50.29344
```

The best native public class is `bits_suffix3=101`:

```text
v_F = -40.94744 bits/record-string
tax = 2.26125 bits/record-string
net_after_tax = -43.208690 bits/record-string
```

It is much better than the supply-weighted uniform future value, but it is still
strongly negative before any current total-cover gap is charged.

## Disallowed Oracle Ceiling

H170 also prints a forbidden post-hoc oracle that sorts by
`future_paid_saving`. Because the H96 witness mass is very lumpy, requested
mass fractions can quantize to the same actual selected mass.

```text
oracle target/actual mass      v_F        tax       net_after_tax
0.10 / 0.102               -37.80000   3.29146   -41.09146
0.25 / 0.250               -39.93878   1.99868   -41.93746
0.03 / 0.102               -37.80000   3.29146   -41.09146
0.01 / 0.020               -37.00000   5.61339   -42.61339
0.50 / 0.500               -42.77551   0.99868   -43.77419
```

Even the disallowed future-saving oracle is tens of bits negative in this H96
record-string microscope.

## Verdict

H170 does not solve the public recurrent fertility law. It closes a more native
version of the easy-class loophole:

```text
best allowed native class net = -43.208690 bits/record-string
best disallowed oracle net = -41.091462 bits/record-string
uniform future value = -51.634654 bits/record-string
```

This means the H96 emitted-record language does contain visible class
differences, but those differences are not remotely enough to make the next
pass compressive after paying current witness-mass tax. A viable public-law
route must therefore change the record language itself, not merely classify the
existing H96 emitted strings by arity, width, cost, or simple visible bit shape.

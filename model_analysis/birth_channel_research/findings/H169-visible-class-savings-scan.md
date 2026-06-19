# H169 - Visible-Class Savings Scan

Date: 2026-06-18

## Question

H168 says the remaining total-cover route needs a public recurrent fertility
law. Do any simple decoder-visible classes actually carry enough **paid future
witness saving** after their class tax?

Runnable artifact:

```text
model_analysis/birth_channel_research/H169-visible_class_savings_scan.py
```

## Model

H169 reuses H89's exact tiny witness domain:

```text
B=1, N=12, K=6, D=8, words=4096
paid_saving(x) = raw_bits - best_cover_cost(x)
E_U paid_saving = -5.022461 bits/word
```

For a public class `F`:

```text
f = |F| / |domain|
tax = -log2(f)
v_F = E[paid_saving | F]
v_O = E[paid_saving | not F]
net_after_tax = v_F - tax
```

The tested classes are predeclared visible bit/syntax features: prefixes,
suffixes, Lotus-like arity prefixes, popcount buckets, parity/mod classes,
transition/run buckets, simple periodic classes, and border/self-similarity
classes. The class is not allowed to be chosen from `paid_saving` itself.

H168's easiest remaining production target is shown only as a diagnostic scale:

```text
post-H165 target = 8.112500 bits/selected-record
conservative target = 8.361777 bits/selected-record
```

H89/H169 units are toy `bits/word`, not production `bits/record`.

## Best Allowed Public Classes

```text
class                 family          f        tax       vF       vO      net       margin vs 8.1125
max_run<=5            run          0.87549  0.19184  -4.76380 -6.84118 -4.95564   -13.06814
max_run<=6            run          0.94531  0.08114  -4.90134 -7.11607 -4.98248   -13.09498
ones<=6               popcount     0.61279  0.70653  -4.47649 -5.88651 -5.18302   -13.29552
prefix1=0             prefix       0.50000  1.00000  -4.38428 -5.66064 -5.38428   -13.49678
suffix1=0             suffix       0.50000  1.00000  -4.43994 -5.60498 -5.43994   -13.55244
suffix2=00            suffix       0.25000  2.00000  -3.81836 -5.42383 -5.81836   -13.93086
lotus_arity1_00       lotus-prefix 0.25000  2.00000  -4.25781 -5.27734 -6.25781   -14.37031
```

The best allowed public class is `max_run<=5`:

```text
v_F = -4.76380 bits/word
tax = 0.19184 bits/word
net_after_tax = -4.955644 bits/word
```

That is slightly better than the uniform H89 mean, but still negative before
any production gap is charged.

## Disallowed Oracle Ceiling

H169 also sorts by `paid_saving` itself to show the hidden-selector ceiling.
These rows are not legal mechanisms unless some future public grammar makes the
ranking decoder-derivable without a profile.

```text
oracle class             f        tax       vF       net_after_tax
top paid_saving 25%   0.25000  2.00000  -1.04199   -3.04199
top paid_saving 10%   0.10010  3.32052   0.10000   -3.22052
top paid_saving 50%   0.50000  1.00000  -2.26855   -3.26855
top paid_saving 3%    0.03003  5.05749   1.39837   -3.65911
top paid_saving 1%    0.01001  6.64245   2.24390   -4.39855
```

Even the post-hoc oracle ceiling stays negative after class tax. That is a
strong warning that the H89 paid-saving tail is too shallow for simple
class-restriction fertility.

## Population Conservation

For any public partition of the uniform domain:

```text
f * v_F + (1 - f) * v_O = E_U paid_saving
```

So a no-tax population claim does not become positive just by naming a class.
It needs a real recurrence that changes the class fraction `c_t` across passes,
with `p_FF`, `p_OF`, fixed point, and startup loss measured.

## Verdict

H169 does not solve the active goal. It rules out the easy visible bit-shape
classes in the H89 microscope:

```text
best allowed public net = -4.955644 bits/word
best disallowed oracle net = -3.041992 bits/word
uniform mean = -5.022461 bits/word
```

The next live target is more native: scan classes over actual emitted record
strings, such as arity histograms, parse counts, payload-width buckets, and
record-count/segmentation classes, while reporting the same `v_F`, tax,
shuffled controls, and recurrence metrics. If that also fails, the public-law
route needs a genuinely new closed record-language construction rather than a
visible feature of the existing H89 toy distribution.

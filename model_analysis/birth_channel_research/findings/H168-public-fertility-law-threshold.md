# H168 - Public Fertility-Law Threshold

Date: 2026-06-18

## Question

After H167, selected emitted witness identity is not enough. What would a real
public recurrent fertility law have to prove without hiding a selector,
profile, or source-specific model?

Runnable artifact:

```text
model_analysis/birth_channel_research/H168-public_fertility_law_threshold.py
```

## Two Ledgers

H168 separates two different public-law claims.

### 1. Restriction Ledger

The encoder accepts only witnesses in a public high-fertility class `F` with
uniform fraction `f`. This can make closure public, but it thins hit supply:

```text
supply tax = -log2(f)
g = conservative H164 miss/record
o = observed H165 same-cost option credit
r = g - o
post-H165 lift needed = r + supply tax
conservative lift needed = g + supply tax
```

Using the easiest strict H166/H165 row:

```text
row                         f        g        o        r       tax   need r+tax  need g+tax
H162 K5 D80 exact       0.500000  8.361777 0.249277 8.112500 1.000000   9.112500   9.361777
H162 K5 D80 exact       0.250000  8.361777 0.249277 8.112500 2.000000  10.112500  10.361777
H162 K5 D80 exact       0.100000  8.361777 0.249277 8.112500 3.321928  11.434428  11.683705
H162 K5 D80 exact       0.030000  8.361777 0.249277 8.112500 5.058894  13.171394  13.420671
H162 K5 D80 exact       0.010000  8.361777 0.249277 8.112500 6.643856  14.756356  15.005633
```

For the harder `H163 K16 D512 escape5` row, `f=0.10` needs:

```text
g = 11.143925
o = 0.217483
r = 10.926442
tax = 3.321928
post-H165 lift needed = 14.248370 bits/record
conservative lift needed = 14.465853 bits/record
```

### 2. Population Ledger

No witness supply tax is charged here. Instead, the current layer must actually
have public class fraction `c_t`. If a real candidate law has actual paid future
witness values:

```text
v_F = E[paid_saving | F]
v_O = E[paid_saving | not F]
T = r + supply_tax
```

then its required class concentration is:

```text
c* = (T - v_O) / (v_F - v_O)
```

The printed H168 population rows use the simpler no-tax, zero-baseline case
`v_O=0`, `v_F=a`, so:

```text
c* = gap / a
```

The class must then maintain itself:

```text
c_{t+1} = c_t p_FF + (1-c_t) p_OF
```

Starting from a uniform layer, `c_0 = f`. Immediate positivity requires:

```text
f >= c*
equivalently a >= gap / f
```

For the easiest strict row and `f=0.10`, that means:

```text
a >= 81.125 bits/record
```

Representative rows:

```text
row                            f      a       c*      start?  min pFF  cross  cum+  result
H162 K5 D80 post-H165       0.10   16.0   0.507031   False   0.9028      6    14   closed F + startup bloat
H162 K5 D80 post-H165       0.10   64.0   0.126758   False   0.3111      1     1   closed F + startup bloat
H162 K5 D80 post-H165       0.10  128.0   0.063379    True   0.0000      0     0   uniform start already crosses

H163 K16 D512 post-H165     0.10   16.0   0.682903   False   0.9536     10    26   closed F + startup bloat
H163 K16 D512 post-H165     0.10   64.0   0.170726   False   0.5143      1     2   closed F + startup bloat
H163 K16 D512 post-H165     0.10  128.0   0.085363    True   0.0000      0     0   uniform start already crosses
```

`cross` is the pass where a perfectly closed class (`p_FF=1`) with background
inflow `p_OF=f` reaches `c*`. `cum+` is when the cumulative margin turns
positive under the same optimistic closed-class recurrence.

## Anti-Hack Rule

These two ledgers cannot be mixed.

If a proposal gets closure by forcing output witnesses into `F`, it is using the
restriction ledger and must pay `-log2(f)` supply tax.

If a proposal does not pay that tax, then `c_t` must be a real public
source/output population fraction, measured before selection. Starting from
uniform data, it either crosses immediately with `a >= gap/f`, or it needs a
closed/canalized attractor and must account for startup bloat.

Any real candidate law must report:

```text
actual paid future witness value, not only log2(Q/U) score
same-visible random lift
bottom-class and shuffled-class controls
public fraction f or stratum-weighted E[-log2 f_stratum]
p_OF, p_FF, fixed point, and recurrence margin
post-H165 margin: measured_lift - tax - r
conservative margin: measured_lift - tax - g
```

If `F` spans different arity/width/length strata, the tax is not one flattering
global fraction. It is:

```text
tax = E_selected[-log2 U(F intersect stratum) / U(stratum)]
```

with worst-stratum margins reported.

## Measured Anchor

H89 measured actual witness-cost fertility in the exact H80/H74 toy. The best
oracle-saving law still had:

```text
cycle = -2.397156 bits/word
```

The best individual word saved 4 bits, but no average public law crossed. That
is far below the H168 target scale:

```text
11.434428 bits/record at f=0.10 in the post-H165 restriction ledger
11.683705 bits/record at f=0.10 in the conservative restriction ledger
81.125 bits/record at f=0.10 for immediate uniform-start population positivity
```

## Verdict

H168 does not solve the goal, but it sharpens the remaining target.

A real breakthrough now has to exhibit one of these:

```text
restriction mode:
  public class F, paid supply tax, measured future lift > r + tax
  and conservative measured future lift > g + tax if H165 credit is not trusted

population mode:
  public class F, no selector tax, measured c_t recurrence, c_t >= r/a,
  and cumulative startup loss repaid
```

The attractive hybrid claim, "closed fertile outputs with no supply tax," is
not a third option. It is the hidden selector/profile channel in different
clothes.

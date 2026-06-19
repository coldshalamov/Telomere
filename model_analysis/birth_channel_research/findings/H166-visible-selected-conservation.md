# H166 - Visible-Selected Fertility Conservation

Date: 2026-06-18

## Question

If H165 says same-cost neutral multiplicity is too small, can a visible-selected
fertility rule still help without hiding selector entropy?

Runnable artifact:

```text
model_analysis/birth_channel_research/H166-visible_selected_conservation.py
```

## Model

Under the uniform hash law, matching a current target interval is independent of
the future fertility of the selected witness string except through public
decoder-visible features:

```text
visible cost / length
arity or payload-width class
public lane / seed class / salt epoch
```

Therefore, once those public features are fixed, selected matched witnesses and
same-budget random witnesses have the same future-score distribution. Any
positive result must come from:

```text
an actual emitted-stream recurrence that beats same-budget random
or a public fertility class/law whose reduced hit supply is charged
```

## Same-Class Ledger

```text
row                          support  miss/rec   obsOpt    remain   M_miss   M_obs  lift-vs-rand
H162 K5 D80 exact            0.310    8.361777  0.249277  8.112500  328.96   1.19   0
H163 K5 D256 exact           0.603    9.688172  0.230719  9.457453  824.96   1.17   0
H163 K5 D512 exact           0.817    10.626718 0.234505  10.392213 1581     1.18   0
H163 K16 D512 escape5        0.833    11.143925 0.217483  10.926442 2263     1.16   0
```

`M_miss` and `M_obs` are only ideal best-of-M conversions of bit values. The
primary units are `miss/rec`, `obsOpt`, and `remain`.

## Public Class Ledger

If a public high-fertility class has fraction `f`, current hit supply thins by
`f`, giving supply tax `-log2(f)`. Gross future lift must cover:

```text
gross future lift needed = miss/rec + -log2(f)
```

For the easiest strict row, H162 K5/D80:

```text
f       supply tax  gross future lift needed
0.50    1.000000    9.361777 bits/record
0.25    2.000000    10.361777 bits/record
0.10    3.321928    11.683705 bits/record
0.03    5.058894    13.420671 bits/record
0.01    6.643856    15.005633 bits/record
```

## Verdict

Visible-selected fertility is conserved unless the selected witness stream
changes a public feature or a measured public fertility law changes the future
distribution. Same-class selection has zero expected lift over same-budget
random controls, and public classes make the hurdle larger by their supply tax.

The next positive route must show an emitted-stream recurrence or public class
law with more than `8.1125` bits/record net value in the easiest current strict
row. Anything less is below the H162/H164/H165 gap.

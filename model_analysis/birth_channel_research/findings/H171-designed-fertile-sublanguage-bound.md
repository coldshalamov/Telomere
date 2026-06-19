# H171 - Designed Fertile Sublanguage Bound

Date: 2026-06-18

## Question

H169 and H170 asked whether existing visible classes are fertile. What if the
record language is deliberately designed so a public class `F` is fertile by
construction?

Runnable artifact:

```text
model_analysis/birth_channel_research/H171-designed_fertile_sublanguage_bound.py
```

## Conservation Rule

If `F` has public fraction `f` and future paid-saving boost `a` bits/record,
that boost consumes at least:

```text
Kraft mass from F = f * 2^a
```

Restriction mode pays:

```text
tax(F) = -log2(f)
```

A valid prefix/witness family with any complement left must have:

```text
a < tax(F)
```

so:

```text
a - tax(F) <= 0
```

But H168 needs:

```text
a - tax(F) > r
```

where `r` is the remaining miss after H165 option credit. Therefore the fertile
class alone would require:

```text
f * 2^(r + tax(F)) = 2^r
```

Kraft mass before encoding any complement.

## Restriction Bound

For the easiest strict H168 target:

```text
r = 8.112500 bits/selected-record
```

H171 prints:

```text
f        tax       needed boost   max valid boost   best net   post margin   overfull
0.5000   1.000000   9.112500      1.000000          0.000000   -8.112500     8.112500
0.2500   2.000000  10.112500      2.000000          0.000000   -8.112500     8.112500
0.1000   3.321928  11.434428      3.321928          0.000000   -8.112500     8.112500
0.0300   5.058894  13.171394      5.058894          0.000000   -8.112500     8.112500
0.0100   6.643856  14.756356      6.643856          0.000000   -8.112500     8.112500
0.0030   8.380822  16.493322      8.380822          0.000000   -8.112500     8.112500
0.0010   9.965784  18.078284      9.965784          0.000000   -8.112500     8.112500
```

The overfull bill is exactly the remaining gap `r`, independent of class size.

For the harder `H163 K16 D512 escape5` target:

```text
r = 10.926442 bits/selected-record
```

the same restriction-mode argument requires `10.926442` overfull bits of Kraft
mass.

## Population Mode

Population mode can still be a live target, but it is a different claim. H171
balances the boost `a = alpha * tax(F)` with a complement penalty `b`:

```text
f * 2^a + (1-f) * 2^b = 1
```

Uniform-start mean saving stays nonpositive. Only real public concentration
inside `F` can help.

Representative easiest-target rows:

```text
f       alpha  a         b          E_U       pureF-r   c*        min pFF
0.100   0.99   3.288709 -5.305176  -4.445788 -4.823791 1.561305  inf
0.010   0.99   6.577418 -4.459194  -4.348828 -1.535082 1.139090  inf
0.003   0.99   8.297014 -4.142898  -4.105578  0.184514 0.985168  0.999955
0.001   0.90   8.969206 -1.001986  -0.992015  0.856706 0.914082  0.999906
```

So a pure-`F` population can theoretically beat the easiest gap only for very
rare classes:

```text
f < 2^-8.112500 = 0.003613
```

but starting from a uniform population then requires an almost perfectly closed
attractor and startup-bloat accounting.

## Catalyst-Bit Corollary

Forcing `c` public catalyst bits is exactly `f = 2^-c`. A valid designed
grammar can give at most `c` future bits back to that class. Restriction net is
therefore at most zero before the current gap is paid:

```text
c bits   max boost   best restriction net   margin vs r=8.1125
1        1           0                      -8.112500
2        2           0                      -8.112500
4        4           0                      -8.112500
8        8           0                      -8.112500
12       12          0                      -8.112500
16       16          0                      -8.112500
```

## Verdict

Designing a public fertile sublanguage does not create free recursive fuel under
the uniform hash law. In restriction mode, the designed boost can at best repay
the class tax, leaving the existing positive gap unpaid.

The only remaining use is population mode: the emitted stream must become
concentrated in a very rare public class through a measured recurrence, without
secretly paying the same restriction tax through witness selection, final-state
layout, or profile metadata.

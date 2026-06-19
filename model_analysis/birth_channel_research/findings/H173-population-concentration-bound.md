# H173 - Population Concentration Bound

Date: 2026-06-18

## Question

H171 left one attractive escape hatch: do not restrict witnesses to a fertile
class `F`, so no class tax is charged. Instead, let the emitted/source
population actually concentrate in `F` over recursive passes. Is that free under
roughly-all uniform data?

Runnable artifact:

```text
model_analysis/birth_channel_research/H173-population_concentration_bound.py
```

## Binary Public-Class Identity

Let `F` have public background fraction `f`. Let the future values be:

```text
a = value if output is in F
b = value if output is outside F
c = actual emitted/source population fraction in F
```

If the data is roughly uniform, concentration `c != f` carries information:

```text
D(c || f) =
  c log2(c/f) + (1-c) log2((1-c)/(1-f))
```

The exact variational identity is:

```text
c*a + (1-c)*b - D(c||f)
  = log2 Z - D(c || c_eq)
```

where:

```text
Z = f*2^a + (1-f)*2^b
c_eq = f*2^a / Z
```

So:

```text
sup_c [c*a + (1-c)*b - D(c||f)] = log2 Z
```

If the law is Kraft-valid, `Z <= 1`, so the best no-tax population margin is
`<= 0`.

## Kraft-Balanced Rows

H173 uses H171-style laws where `b` is chosen so:

```text
Z = f*2^a + (1-f)*2^b = 1
```

Those laws can make the equality population highly concentrated in `F`, but the
KL cost exactly cancels the value:

```text
f        alpha  a         b          c_eq     KL_eq    E_eq     net*   mPost    mCons
0.1000   0.99   3.288709 -5.305176   0.977237 3.093088 3.093088 0.000 -8.1125 -8.361777
0.0100   0.99   6.577418 -4.459194   0.954993 6.080688 6.080688 0.000 -8.1125 -8.361777
0.0030   0.99   8.297014 -4.142898   0.943564 7.594951 7.594951 0.000 -8.1125 -8.361777
0.0010   0.99   9.866126 -3.903738   0.933254 8.947047 8.947047 0.000 -8.1125 -8.361777
```

The raw future value looks large; the population concentration is exactly the
hidden information that pays for it.

## Target Overfull Mass

To get `r` bits/record of no-tax population margin on uniform data, the public
law needs:

```text
Z >= 2^r
```

For current H168/H171 targets:

```text
target              post r     need Z post   conservative g   need Z conservative
H162 K5 D80         8.112500   276.761605   8.361777          328.961970
H163 K5 D256        9.457453   703.035144   9.688172          824.955220
H163 K5 D512       10.392213  1343.902724  10.626718         1581.105588
H163 K16 D512      10.926442  1946.196951  11.143925         2262.849625
```

That is source bias if it comes from the input distribution. It is overfull
hidden capacity if it comes from the codec.

## Recurrence Check

Using the rare H171 row `f=0.003, alpha=0.99`:

```text
a = 8.297014
b = -4.142898
p_OF = f
```

Holding high population concentration requires near-perfect recurrence:

```text
claim c   min pFF   value     KL       net       net - r
0.943564  0.999821  7.594951  7.594951 0.000000 -8.112500
0.985168  0.999955  8.112500  8.145231 -0.032731 -8.145231
0.999000  0.999997  8.284574  8.361038 -0.076464 -8.188964
1.000000  1.000000  8.297014  8.380822 -0.083808 -8.196308
```

Even the raw-value threshold concentration does not cross once `D(c||f)` is
charged.

## Verdict

H173 closes the no-tax population loophole for roughly-all uniform data:

```text
population concentration in F is itself an information channel
best paid no-tax population margin = log2 Z
Kraft-valid law => log2 Z <= 0
positive H168 margin => overfull Z >= 2^r or real source bias
```

Population recurrence remains useful only for source-shaped or biology-like
domains where the source genuinely has the biased public population before
selection. It does not solve arbitrary roughly-all-data stateless recursive
compression unless a separate mechanism increases honest witness mass above the
Kraft threshold.

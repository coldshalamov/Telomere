# H52 - fixed-slack percolation reproduction sweep

Date: 2026-06-17

## Question

Can larger fixed witness slack plus larger arity make total-cover recursion
cross once the decoder-derived witness boundary is preserved?

H9 fixed-width witnesses are stateless:

```text
width(a) = min(D, a*B - slack)
```

The decoder knows `B`, `D`, `a`, and `slack`, so it knows exactly how many
witness bits to read. The price is reduced match supply. Under the uniform
hash law:

```text
p_hit(a) = 1 - exp(-2^(width(a) - aB))
```

H52 samples that Bernoulli edge event directly. This is the same fixed-width
law H9 tests via first-rank samples, but it is faster for high `K`.

## Kernel

Runnable artifact:

```text
model_analysis/birth_channel_research/H52-fixed_slack_percolation_rg.py
```

The arity stream is still paid by a public model trained on independent
uniform-law covers, as in H9. Rows score repeated-pass reproduction:

```text
rho_t = paid_bits(layer_{t+1}) / padded_bits(layer_t)
need mean log2 rho < 0
```

## Default bounded sweep

Run:

```text
B=4
configs:
  K=128,D=512,atoms=160
  K=192,D=768,atoms=192
slacks=0,1,2
passes=3
trials=3
train trials=6
iterations=1
```

Results:

```text
K=128,D=512:
  slack 0: mean log2 rho = +0.006713
  slack 1: mean log2 rho = +0.009618
  slack 2: mean log2 rho = +0.012788

K=192,D=768:
  slack 0: mean log2 rho = +0.003658
  slack 1: mean log2 rho = +0.005784
  slack 2: mean log2 rho = +0.007849
```

Best default row:

```text
B=4,K=192,D=768,slack=0
mean log2 rho = +0.003658
geometric rho = 1.002539
```

## Focused high-K strict-cover scout

Run:

```text
B=4,K=256,D=1024,atoms=512
slacks=0,1,2,3
passes=2
trials=2
train trials=4
iterations=1
```

Results:

```text
slack 0: mean log2 rho = +0.004849
slack 1: mean log2 rho = +0.003775
slack 2: mean log2 rho = +0.005391
slack 3: mean log2 rho = +0.007273
```

Best focused row:

```text
B=4,K=256,D=1024,slack=1
mean log2 rho = +0.003775
geometric rho = 1.002620
```

All rows maintained strict full cover in the tested passes.

## Reading

This improves the H50 closest paid row:

```text
H50 best paid: +0.004884 mean log2 rho
H52 best strict fixed-slack: +0.003658 to +0.003775 mean log2 rho
```

So larger `K` and fixed slack are moving the right direction, but strict
fixed-slack recursion still does not cross. Extra slack does not behave like
free savings. It thins the interval graph:

```text
slack 0: p ~= 0.632
slack 1: p ~= 0.393
slack 2: p ~= 0.221
slack 3: p ~= 0.118
```

In the measured rows, the reduced match supply and arity/padding effects return
the saved witness bits before `mean log2 rho` becomes negative.

## Verdict

Strict fixed slack is not the missing piece in the tested high-arity regime,
but it sharpened the frontier. The nearest paid repeated-pass target is now:

```text
B=4,K=192,D=768,slack=0: mean log2 rho +0.003658
or
B=4,K=256,D=1024,slack=1: mean log2 rho +0.003775
```

The next honest variant is a paid global slack ladder:

```text
try slack set S per layer
select the first/cheapest full-cover slack by deterministic rule
charge log2(|S|) or a public arithmetic slack code per layer/pass
```

That can test whether occasional slack-1 wins survive the small global
selector cost. Local per-record slack relaxation would reintroduce the width
stream H9 was trying to remove and must be priced separately.

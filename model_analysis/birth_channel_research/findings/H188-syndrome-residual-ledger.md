# H188 - Syndrome / Algebraic Residual Ledger

## Conjecture

```text
Parity equations, syndromes, or algebraic residuals might let a short seed plus
repair state reconstruct arbitrary spans without storing the full residual.
```

## Kernel

`H188-syndrome_residual_ledger.py`

For target `x`, seed expansion `y`, and residual `e=x xor y`, arbitrary
uniform data makes `e` uniform. A `c`-bit syndrome leaves `n-c` residual bits
ambiguous unless they are stored or externally restricted.

The kernel also prices low-volume residual classes such as Hamming balls.

## Result

Syndrome rows:

```text
n=256,seed=0,c=128: stored=128, ambiguity=128, paidUnique=256, netRaw=0
n=256,seed=8,c=128: stored=136, ambiguity=128, paidUnique=264, netRaw=-8
n=1024,seed=32,c=256: stored=288, ambiguity=768, paidUnique=1056, netRaw=-32
```

Low-volume residual classes compress only inside the class:

```text
n=256,seed=0,t=8: logVol=48.588344, tax=207.411656,
                  inside gain=207, uniform net=-0.411656
n=1024,seed=0,t=16: logVol=115.602971, tax=908.397029,
                    inside gain=908, uniform net=-0.397029
```

## Bill

```text
full syndrome/residual: seed_bits + n
short syndrome: leaves n-c ambiguous residual bits
low-volume residual: gains inside class, pays class membership for arbitrary data
```

## Mutation

Keep algebraic residuals as source-shaped repair languages and generated-class
tools. They do not create arbitrary all-content compression unless the residual
distribution is non-uniform and that source law is explicit.

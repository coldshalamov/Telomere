# Avenue H14 - trained public CRF cover partition

Author: Codex continuation with read-only subagent audit. Date: 2026-06-17.
Status: trained public-feature follow-up after H13.

## HYPOTHESIS

H13's raw/tilted whole-cover partition code returned to the H7 near-miss zone
but did not cross. The next possible joint-cover refinement is a small public
feature model over selected cover shapes:

```text
shape = [(arity_1, width_1), ..., (arity_m, width_m)]
```

If a frozen CRF can predict the selected cover shape better than H13's raw law,
it might shave the remaining witness bits without per-file metadata.

## MECHANISM

Runnable kernel:

- `../H14-public_crf_cover_partition.py`

The public model is:

```text
q(shape) = product_j psi(edge_j) / Z(N)

log2 psi = log2 P_raw(width | arity*B, width<=D)
         + beta * (arity*B - width)
         + record_bias
         + sum feature_weight[f]

paid_bits = sum_j width_j + log2 Z(N) - sum_j log2 psi_j
```

Features:

- arity bucket;
- delta bucket where `delta = arity*B - width`;
- remaining-atoms bucket;
- arity-bucket + delta-bucket pair.

Weights are trained only on independent uniform-law samples by a fixed public
algorithm:

1. select covers under current weights;
2. count features in those selected covers;
3. compute expected feature counts under the normalized public `q(shape)` with
   forward/backward;
4. update weights with fixed learning rate, L2, and clipping.

The target/eval file does not get to choose weights or hyperparameters.

## AUDIT

The H14 audit found the forward/backward math correct for the toy: `logZ` and
expected-feature counts use the same edge potential, and a tiny finite
enumeration check matched to floating precision. The audit warning is
procedural: weights, `beta`, `record_bias`, buckets, training algorithm,
iterations, learning rate, L2, and clip are free only if frozen public profile
constants. Choosing among them after seeing target/eval results is metadata.

Coverage must be `1.0`; otherwise the row is only a conditional diagnostic.

## RESULT

`refuted-as-crossover`

Tiny smoke, useful only as a variance warning:

```text
N=64, train/eval=4/2, iterations=2
eval gain = +0.026605 bits/input atom
train gain = -0.017394 bits/input atom
```

The stronger bounded N=64 run removed the apparent positive:

```text
command:
python model_analysis\birth_channel_research\H14-public_crf_cover_partition.py ^
  --atoms 64 --train-trials 16 --eval-trials 8 ^
  --iterations 4 --learning-rate 0.03

result:
eval gain = -0.019572 bits/input atom
missing = 1.253 bits/record
coverage = 1.000
```

Bounded N=128 scale check:

```text
command:
python model_analysis\birth_channel_research\H14-public_crf_cover_partition.py ^
  --atoms 128 --train-trials 8 --eval-trials 4 ^
  --iterations 2 --learning-rate 0.03

result:
eval gain = -0.015478 bits/input atom
missing = 1.981 bits/record
coverage = 1.000
```

H14 does not beat the H13/H7 frontier and does not cross positive. The learned
feature weights are small (`L1=0.185` in the N=128 run), and the `logZ` charge
balances the extra feature preference.

## ACCOUNTING TRAPS CLOSED

- Exact seed residual remains paid as `width` bits per selected record.
- `logZ` normalizes over all public cover shapes, not only feasible edges found
  by the encoder.
- Training samples are independent from eval samples.
- The tiny positive smoke is not claimed as evidence because it was small and
  train-negative.
- Hyperparameter/profile selection after looking at eval would be metadata.

## NEXT

The joint-cover witness-code branch has now tested:

- H13 raw/tilted public partition with record-count bias;
- H14 trained public CRF over small selected-cover features.

Both return to the near-miss zone and stay negative. The next useful work is not
a richer feature table unless its profile cost is explicitly frozen or paid.
The sharper target is an impossibility/entropy-rate proof for the high-arity
near-flat limit, or a genuinely different mechanism that changes the uniform
source law rather than reshuffling the witness stream.


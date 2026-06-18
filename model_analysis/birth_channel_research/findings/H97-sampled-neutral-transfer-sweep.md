# H97 - Sampled Neutral Transfer Sweep

Date: 2026-06-18

## Question

H96 found a real future-fertility signal in exact tiny enumeration, but exact
enumeration explodes as `D` grows. Can the same visible-genotype idea improve
as `N/K/D` increase?

Runnable artifact:

```text
model_analysis/birth_channel_research/H97-sampled_neutral_transfer_sweep.py
```

## Method

For each target word:

1. build the same fixed paid V1 record family as H96;
2. compute exact current all-description mass for the word;
3. sample visible descriptions from fixed public posterior/temperature
   samplers;
4. include the shortest current description;
5. choose the sampled visible genotype maximizing:

```text
current_saving + next_pass_all_description_saving
```

The chosen genotype bits are the output, so no decoder selector is stored.

Because this is a sampled best-of search, H97 also reports reward-hack guards:

- posterior one-draw cycle;
- conservative `log2(unique_candidates)` net cycle;
- random same-length one-draw future;
- best-of-same-budget random same-length future;
- selected visible length and current cost.

## Result

```text
name                 N   K   D  cand  cycle      logm net   future    randM    liftM
h96_anchor_sampled   5   3   3   512  -60.307    -66.990   -43.870   -39.170  -4.699
small_deeper         6   3   4   384  -57.594    -65.253   -42.828   -35.895  -6.933
mid_v1               8   4   5   512  -47.198    -55.763   -31.370   -27.585  -3.784
v1_frontier_probe   10   5   6   512  -39.502    -48.214   -24.705   -20.149  -4.556
```

Additional telemetry:

```text
name                coll now  best now  chosen now  logm tax  post fut  lift1
h96_anchor_sampled  -13.691   -16.375     -16.438     6.683   -50.646   7.558
small_deeper        -12.772   -14.750     -14.766     7.659   -47.972  -1.675
mid_v1              -12.114   -15.719     -15.828     8.565   -37.450   0.769
v1_frontier_probe   -11.152   -14.719     -14.797     8.712   -30.114   0.223
```

The corrected anchor uses the same seed as H96 and reproduces H96's exact
best-transfer cycle.

## Reading

The larger sampled rows get less negative as `N/K/D` grow:

```text
-60.307 -> -57.594 -> -47.198 -> -39.502 bits/word
```

but none approach a paid positive cycle and no sampled word is positive.

The stricter same-budget control is important. H96 showed that selected
genotypes could beat one random same-length string. H97 compares them against
the best of the same random sample budget, and the lift becomes negative in
every row. That means the sampled neutral-transfer advantage is not yet a
stable grammar/fertility law; it is mostly ordinary best-of-search luck over
visible strings.

## Verdict

Visible neutral genotype choice remains a useful biology-shaped probe, but H97
does not find the wedge.

For this lane to become a breakthrough candidate, a future kernel must show:

```text
paid cycle > 0
same-budget random controls lower
uniform controls negative if the claim is source-shaped
log2 Z or explicit public invariant if the claim is all-data
```

The next version should either:

- add a real public interpreter/native grammar for record strings; or
- estimate the selected-law KL instead of the conservative `log2(m)` audit; or
- move to a source-shaped recurrent fertility test with measured `p_FF/p_OF`.

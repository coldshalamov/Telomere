# Avenue H19 - neutral ecology tree kernel

Author: Codex continuation with Sagan scout memo. Date: 2026-06-17.
Status: exact source-shaped toy; not a uniform all-data solution.

## HYPOTHESIS

Sagan's scout proposed a public neutral-fertility graph:

```text
phenotype(seed) -> bytes/items decoded now
germline(seed)  -> future-fertility surface for later passes
```

The seed is both a witness and a genotype. Several same-cost seeds may decode
to the same current phenotype, while their germline projections differ. The
encoder chooses a fertile synonym, and the decoder pays no separate selector
because the chosen seed is already stored.

## MECHANISM

Runnable exact kernel:

- `../H19-neutral_ecology_tree_kernel.py`

The toy model is:

```text
seed/genotype s --phi--> current phenotype x
                --gamma--> future substrate y
```

For an arbitrary uniform target over `(x,y)`, the public seed map only covers a
small reachable subset. For an ecology-generated source where `(x,y)` is
actually produced by the seed map, storing the seed is a stateless
developmental description.

## RESULT

```text
command:
python model_analysis\birth_channel_research\H19-neutral_ecology_tree_kernel.py
```

With `L=8` current bits and `G=8` future bits:

| mode | seed bits W | reachable pairs | uniform pair coverage | source entropy | raw pair bits | stored bits | gain on ecology source | entropy deficit |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| factor | 8 | 256 | 0.003906 | 8.000 | 16 | 8 | 8.000 | 8.000 |
| hash | 8 | 255 | 0.003891 | 7.994 | 16 | 8 | 8.000 | 8.006 |
| pleiotropic | 8 | 256 | 0.003906 | 8.000 | 16 | 8 | 8.000 | 8.000 |
| factor | 10 | 1024 | 0.015625 | 10.000 | 16 | 10 | 6.000 | 6.000 |
| hash | 10 | 1020 | 0.015564 | 9.994 | 16 | 10 | 6.000 | 6.006 |
| pleiotropic | 10 | 1024 | 0.015625 | 10.000 | 16 | 10 | 6.000 | 6.000 |
| factor | 12 | 4096 | 0.062500 | 12.000 | 16 | 12 | 4.000 | 4.000 |
| hash | 12 | 3988 | 0.060852 | 11.961 | 16 | 12 | 4.000 | 4.039 |
| pleiotropic | 12 | 3840 | 0.058594 | 11.907 | 16 | 12 | 4.000 | 4.093 |

## ACCOUNTING

This crosses for the ecology source exactly because the source entropy is lower
than the raw phenotype representation. It does not cross arbitrary pairs:
uniform coverage is at most `2^(W-L-G)`.

That is not a failure of the toy. It is the priced premise shift:

```text
uniform all-data claim: closed by H15/H2
public developmental source: can cross by real entropy deficit
```

The biology-shaped `pleiotropic` row demonstrates the form: low seed bits name
the current phenotype, while regulator bits control future substrate through a
public map. It still crosses only as a source-shaped row. Uniform coverage is
small because only the public seed-generated phenotype pairs are reachable.

## NEXT

The next productive kernel is not another arbitrary uniform run. It is a
two-layer developmental source with:

- multiple current phenotypes;
- neutral regulator bits per phenotype;
- future substrate correlations just above the H18 `gamma > 1.195` threshold;
- held-out ecology-source rows and random controls;
- interpreter/profile fixed publicly or explicitly charged.

That would test the closest remaining Telomere-like idea to the DNA analogy:
seed-addressed recursive unfolding where neutral genotype bits have pleiotropic
future leverage.

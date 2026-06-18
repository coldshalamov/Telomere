# H30 - Public reversible dither refresh

Date: 2026-06-17

## Question

Can the match rate be refreshed without per-record salting or birth-pass state by
applying a public reversible transform to the whole layer each pass?

Mechanism:

```text
target_p = T_p(current_layer)
Telomere-cover target_p
decoder expands records -> target_p
decoder applies T_p^-1 -> current_layer
```

`T_p` can be a public XOR mask, affine/Feistel permutation, coordinate dither,
or other fixed bijection derived from pass/profile.

## Decoder observations

The decoder needs:

- fixed/root profile for `T_p`;
- total pass count or a public fixed pass schedule;
- ordinary record stream for the transformed layer.

No per-record birth/pass tag is needed if every pass uses the public schedule
and every record belongs to the current transformed layer.

## Result

H30 separates two cases.

### Fixed public schedule

A fixed reversible schedule can refresh the visible layer with only a header
pass count:

```text
passes=64 -> header bits=6, entropy change=0
passes=4096 -> header bits=12, entropy change=0
```

This is a clean stateless freshness scaffold. Because `T_p` is a bijection, it
preserves uniform entropy and does not create compression by itself.

### Best-of-P dither choice

If the encoder tries many public transforms and chooses the best one, the
decoder must know which transform won:

```text
selector cost = log2(P)
```

Representative H30 rows:

```text
s=2,  P=4:    free hit p=0.683594, selector=2,  paid save/hit=0
s=8,  P=64:   free hit p=0.221580, selector=6,  paid save/hit=2
s=12, P=4096: free hit p=0.632165, selector=12, paid save/hit=0
```

The apparent best-of-pass gain is an unpaid selector unless `log2(P)` is stored
or derived by another priced invariant.

## Verdict

Public reversible dither is useful but not sufficient:

- It can refresh target bytes/dice across passes without per-record metadata.
- It is compatible with stateless Total-Cover decode.
- It preserves uniform entropy, so it cannot be the all-data compression source.
- Best-of-transform selection reduces to H15 pass/profile selector accounting.

The surviving use is as a scaffold:

```text
public dither schedule
+ Total-Cover or active-lane stateless decode
+ a separate paid witness or fertility-class mechanism
```

If a future value/count separation exists, public dither may be the cleanest way
to keep that mechanism fresh across recursive passes without birth ledgers.

## Artifact

`model_analysis/birth_channel_research/H30-public_dither_refresh.py`

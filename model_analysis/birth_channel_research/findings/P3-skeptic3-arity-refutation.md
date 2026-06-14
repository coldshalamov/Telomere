# P3 — Adversarial Skeptic 3: bundle-lane refutation attempt (independent verdict)

**Assignment:** refute the bundle lane's `confirms-impossibility`. Default
verdict: the bundle channel is NOT a real free unbounded channel. Find a hole:
a bundle variant (higher arity, different alphabet, real stride constraint) that
WOULD pin birth-epoch to O(1).

**Verdict reached: confirms-impossibility (lane upheld, and its one untested
assertion now measured).**

## What the lane left untested — and I measured

The lane's findings `NEXT:` asserted *"arity-3+ raises E (bigger K) but the slope
log2(T)−E is unchanged"* — **asserted, never run.** `P2-bundle_survivor.py`
hardcodes A=2 for every survivor run. The decisive quantity is the content-blind
geometric candidate count `G_epochs(a, T)`. If it saturates to O(1) at some
arity/slot, that is mechanism (b): a real free channel. If it stays O(T), the
base `1+(G−1)q > 1` and survivors stay exponential — lane confirmed.

Toys: `P3-arity-sweep_Gsaturation.py`, `P3-arity-sweep_smallslot.py` (correction),
`P3-arity-slope_and_supply.py`. All reuse the lane's EXACT `geom_candidates` /
orbit-table machinery (content-blind, reads only positions/N/a; real shuffle).

## A correction I had to make to my own first probe (slot 0 is degenerate)

My first sweep ran at `slot=0` and got G=T exactly (G/T=1.000) for all arity.
That is an **identity, not a measurement**: at slot 0 the j0=0 geometric
candidate gives `F[0]=FWD[shifts][BWD[shifts][0]]=0=slot` for every epoch k, and
the left-prune `any(f < slot)=any(f<0)` never fires — so every k survives by
construction. The threatening case (mechanism b) is the slot with the SMALLEST G.
`P3-arity-sweep_smallslot.py` sweeps T at the smallest-G slots per arity.

## The decisive result — G is O(T) at every slot, every arity (no O(1) pin)

At the smallest-G slots, G is **exactly linear in T**. Growth ratio
G(T=6400)/G(T=800) = 8.0 ≈ 6400/800 at every small slot, every arity:

| arity | small slot | G@T=800 | G@T=6400 | ratio | clean form |
|------:|-----------:|--------:|---------:|------:|-----------|
| 2 | 13 | 212 | 1706 | 8.05 | ~T/4 |
| 3 | 12 | 53 | 426 | 8.04 | ~T/16 |
| 4 | 10/11 | 53 | 426 | 8.04 | ~T/16 |
| 5 | 9/10/11 | 100 | 800 | 8.00 | exactly T/8 (6,12,25,50,100,200,400,800) |

The left-prune removes a constant *fraction* of epochs (no child may
forward-walk left of the seed slot), but a constant fraction of T is still O(T).
Board-size sweep (N=16→160 at a=3) leaves G unchanged → G tracks T, not the board.
There is **no arithmetic pin to O(1) at any arity (2–5), any slot, any board.**

Therefore `base = 1 + (G−1)·q_a > 1` for all T ≥ 2, survivors `S_epoch = base^R`
stay exponential in R, and the per-bundle birth residual `log2(base) → log2(T)−E_a`
grows without bound. Mechanism (a) holds at every arity. The lane is confirmed and
its one open assertion is now earned.

### Structural reason G = Θ(T) — holds for ALL arity, not just a ≤ 5

The clean T/c form is not an accident of a∈{2..5} (the grammar caps arity at 5).
The shuffle is a permutation on a fixed board, so every orbit is periodic; the
predicate "epoch k is geometrically admissible at this slot" therefore recurs
with a fixed density per orbit period → `G = (fixed fraction)·T` for ANY arity,
any board (a=5 landing exactly on T/8 is this density made visible). This lifts
the result from "measured at a≤5" to **structural for all a**, closing the worry
that the grammar's arity cap leaves higher arity untested.

It also kills the *different-alphabet* variant by a sharper argument than the
slope: **the alphabet cannot touch G at all.** G is a position-only quantity
(`geom_candidates` reads only slot/N/a). The alphabet moves only q/E — the
intercept K — never G, never the slope.

## The two slopes, measured per arity (closing the NEXT assertion)

`P3-arity-slope_and_supply.py`:

- **Stored-bits slope.** With G=T (measured), residual `log2(1+(T−1)q_a)` grows
  without bound in T for EVERY arity; asymptote `log2(T)−E_a`. Raising arity 2→5
  lifts E from 9.36→18.20 bits, shifting the knee K=2^E from 655→302029 passes —
  but the slope in log2(T) is exactly 1 for every arity. **Arity shifts the
  intercept, never the slope.**
- **The arity escape pays a DIFFERENT currency.** Even where a bigger arity buys
  a bigger free knee, it is blocked earlier in **hit-density**: a real arity-a
  match needs a seed hashing to a·B specific content bits (density 2^−(aB)).
  `K·2^−(aB) = 2^(E_a − aB) = 1/avalid(a,aB) → 0` (a=2: 1e-2; a=5: 2.7e-7). The
  free reach grows but fillable bundles collapse exponentially faster. Same wall,
  different currency than the stored-bits slope.

## Variants killed by argument (no run needed)

- **Different alphabet:** only moves q/E = the intercept K. Slope log2(T)−E grows
  for any constant E. Dismissed by the slope.
- **Real stride constraint:** would need ≥2 *observed* positions per bundle to
  read a gap. The wire emits exactly ONE slot per bundle (the seed); the other
  a−1 child slots are SKIPPED — and that skip *is* the compression. You cannot
  shrink to 1 slot/bundle and also observe a multi-slot stride; the observations
  that would pin the epoch cost exactly the bits you're claiming to save. The
  decoder gets 1 occupied slot + (a−1) emptiness facts, and emptiness only pins
  on a *dense* board — at which point you pay the PCTB arrangement tax. This is a
  conservation refutation of the Phase-1 "k observations vs 2 unknowns" hope:
  in this layout it is 1 observation, not k.

## Why the `filled=set()` isolation is safe (it is an UPPER bound, robustly)

Both my probe and the lane's `count_survivors` run with `filled` empty (the lane
never updates it in its loop), making the multiplicative `base^R` an *upper*
bound on true survivors. An exponential upper bound alone would not preclude a
polynomial true count — so "conservative" was a hand-wave. The real reason it is
safe: cross-filling from the other R−1 bundles removes only O(R·a)
candidate-classes per bundle — a **constant in T**. So each G_i stays Θ(T) and
each base_i stays > 1 even under maximal pruning. The impossibility is *robust*
to the isolation, not merely bounded by it — checked in the channel-hunter's
favored direction (max pruning), and it still does not bend exponential to
polynomial.

## Counting gate (mandatory)

If this were free + content-blind + UNBOUNDED, random data would net-compress —
pigeonhole violation. It is NOT unbounded. The free budget E_a is a constant
intercept (knee K=2^E_a); past K the per-bundle residual log2(T)−E_a is paid in
**stored-bits** (checksum width R·(log2 T − E)); on the arity-escape route the
bill is paid in **hit-density** 2^−(aB) instead. Either way, conserved. No leak.

## Final verdict

```
RESULT:    confirms-impossibility (independent — lane upheld, gap closed)
EVIDENCE:  proven-by-construction + measured (G_epochs O(T) at all arity/slots,
           ratio 8.0=T-linear; P3-arity-sweep_smallslot.py) + proven-by-math
           (slope log2(T)-E_a unbounded; supply 2^-(aB) collapse).
CURRENCY:  stored-bits (checksum slope log2(T)-E) for the in-place arity route;
           hit-density 2^-(aB) for the higher-arity escape. Constant free
           intercept E_a in both; no free unbounded channel.
```

No real free unbounded BUNDLE birth-epoch channel exists. Higher arity, different
alphabet, and stride constraints all fail: the first two shift only the intercept,
the third cannot be observed without spending the bits it claims to save.

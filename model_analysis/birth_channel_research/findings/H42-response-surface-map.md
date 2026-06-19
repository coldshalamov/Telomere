# H42 - systematic response-surface map

Date: 2026-06-17

## Why this exists

The user is right that the search should look more like science: learn the
shape of the problem, then zero in. H42 is a response-surface map rather than a
single clever-lane verdict.

Every candidate should now be recorded as:

```text
mechanism
changed knob
decoder observation
currency paid
formula
predicted sign
adversarial control
finite K if any
next bottleneck
```

## Main axes

### 1. Content-selected vs public-selected sets

If selected readiness depends on content hits, the bill is subset entropy:

```text
subset bits/open ~= H2(r) / r
```

If selected readiness is a public lane, parsing is stateless but the bill moves
to match supply:

```text
lane_loss = -log2(1 - (1-r)^d)
```

H42 rows:

```text
r=0.010: subset/open=8.079, lane d16=2.751, lane d64=1.076
r=0.100: subset/open=4.690, lane d16=0.296, lane d64=0.002
r=0.500: subset/open=2.000, lane d16=0.000
r=0.990: subset/open=0.082, lane d1=0.014
```

This separates two different promises. Public lanes can make decode stateless.
They do not create compression unless the selected lane has enough value lift.

### 2. Near-total exception ledger

If every record opens except a small exception fraction `eps`, the sparse
open/carry ledger becomes:

```text
H2(eps) + eps * log2(P-1) bits/atom
```

H42 rows:

```text
P=64,eps=0.010:   0.140566 bits/atom
P=256,eps=0.010:  0.160737 bits/atom
P=4096,eps=0.010: 0.200790 bits/atom

P=4096,eps=0.001: 0.023407 bits/atom
```

This is a real target: high coverage makes the state ledger small. The hard
part is still obtaining paid, parseable witnesses for almost every atom.

### 3. Closest paid Total-Cover targets

The current uniform paid witness surface is already close but still negative:

```text
H7 raw first-hit delta: gain=-0.011929 bits/atom, missing=1.357 bits/record
H9 fixed slack 0:       gain=-0.012314 bits/atom, missing=1.261 bits/record
H12 perfect-credit UB:  gain=-0.008196 bits/atom, missing=0.746 bits/record
```

So an actual uniform breakthrough must remove about `1.2-1.4` bits per selected
record from the paid witness channel, without hiding it in a selector.

### 4. Closest repeated-pass targets

The repeated-pass branch is the sharper recursive target. Its sign convention
is:

```text
mean log2 rho < 0 => maintained shrinkage
```

Current rows:

```text
H50 paid H9 slack0, B4 K128 D512:      +0.004884
H52 fixed slack0, B4 K192 D768:        +0.003658
H52 fixed slack1, B4 K256 D1024:       +0.003775
H53 paid slack ladder, B4 K192 D768:   +0.004480
H53 unpaid ladder lower bound:         +0.001973
H56 fibonacci headerless, B4 K192 D768:+0.023081
H57 normalized Q, B4 K384 D1536:       +0.000166
H58 frozen bucket Q, B4 K384 D1536:    +0.000215
H59 raw/Q mix, B4 K384 D1536,T1:       +0.000050
```

The H53 lesson is methodological: every adaptive knob now needs two rows, a
selector-charged row and an unpaid lower bound. If the unpaid row improves but
the paid row does not, the adaptive choice is the missing channel.

The H55/H56 lesson is a second methodological rule: a syntax-derived selector
is allowed only after both checks pass:

```text
unique parse / derived profile
negative repeated-pass accounting after delimiter bits
```

Fibonacci-style syntax passed the tiny unique-parse check but failed the
repeated-pass accounting check.

H57 moves the closest log-rho coordinate much nearer to zero, but its uniform
expected paid bits remain above raw:

```text
B=4,K=384,D=1536,N=384:
  mean log2 rho = +0.000166
  expected excess = +1.426544 bits
```

H58 moves the expected-excess frontier much closer by training a public arity
model on independent samples:

```text
B=4,K=384,D=1536,N=384,bucket:
  mean log2 rho = +0.000215
  expected excess = +0.229195 bits
```

H59 tests the legal raw/stop mixture. It can reduce sample excess, but the
held-out rows either stay positive or choose raw-only:

```text
K384,T=1: train alpha=0.2, eval excess=+0.053411
K384,T=4: train alpha=0,   eval excess=0
```

So future rows must pass both tests:

```text
mean log2 rho < 0
E_uniform[paid_bits] <= raw_bits
```

### 5. Public fertility/source lift target

A public lane by itself needs:

```text
value_lift > lane_loss
```

H42 rows:

```text
r=0.10,d=16: standalone lift needed=0.296 bits/selected record
r=0.10,d=64: standalone lift needed=0.002 bits/selected record
r=0.25,d=16: standalone lift needed=0.015 bits/selected record
```

If a lane is added on top of the H7 Total-Cover miss, it must cover both:

```text
H7 + r=0.10,d=16 -> lift needed=1.653 bits/selected record
H7 + r=0.50,d=4  -> lift needed=1.450 bits/selected record
```

This explains why H39 crossed only as a source-shaped positive control:
uniform value lift is zero.

## Shape learned

1. If selection is content-dependent, the bill is subset/permutation entropy.
2. If selection is public, the bill is match-supply loss.
3. If coverage is total or near-total, open/carry entropy can become small.
4. The closest expected-bit frontier is H58 frozen bucket `Q`, still positive
   by `+0.229195` bits; H59 raw/Q mixtures do not convert minority wins into
   held-out expected compression.
5. Adaptive choices must be recorded as paid selector rows plus unpaid
   lower-bound rows.
6. Syntax-derived selectors must be charged as delimiter/Kraft cost.
7. H60 is the roughly-all gate: paid `S`-bit savings can cover at most `2^-S`
   of uniform inputs, while broader coverage needs source lift or a public
   invariant that fixes state paths without a selector.
8. H61 ranks the closest honest misses: H59 needs `+0.000139` bits/atom of
   real source alignment, H58 needs `+0.000597` bits/atom, and H12/H7/H9 need
   paid witness-gap reductions.
9. H62 makes the source-shaped target concrete: public class `f=0.10,a=2`
   crosses H59/H58 atom misses at `c*=0.1454/0.1458`, while H7 witness with
   `f=0.10,a=8` needs `c*=0.6822`.
10. H63 prices recursive maintenance: H59/H58 atom targets need
   `p_FF=0.4122/0.4141` at `p_OF=f=0.10`, while H7 witness needs `0.9534`.
11. H64 reopens EOF/final-board recursion and prices the hidden length path:
   `n=128,P=64,s=1` gives stateless fraction `1.084e-19` versus path-free
   apparent `0.535193` with average path bits `114.186748`.
12. H65 exhausts public invariants as visible-state capacity: variable path
   apparent `0.989365` at `n=16,P=4` returns to charged `0.124985` unless
   finite checksum bits are spent.
13. H66 prices high-arity all-block options: `K=128` gives `log2 M=13.011`
   local option bits, but cover-shape entropy is about `1 bit/atom` and current
   paid misses are far smaller.
14. H67 guards log-rho claims: `a=0.99,eps=0.01` gives `Elog=-0.004427` but
   blowup probability `0.923685` by `P=256`.
15. H68 finite-domain martingale audit keeps `E[W]=1` for public `Q` rows;
   hidden best-of shows `1.009249` selector bits.
16. H69 fixes high-span rank-width sampling: old `49..512`-bit spans
   overcharged about `+1` payload bit/record.
17. H70 turns the map into experiment cards: changed knob, prediction, paid
   currency, adversarial control, and stop rule.
18. H71 gives the sharp finite-pass roughly-all frontier: at `90%` coverage,
   `K=0` prefix and `K=1` EOF for `>=1` bit/pass.
19. H72 shows profile/final-board/checksum multipliers cancel when their
   visible state is counted in the output length.
20. H73 keeps egg-carton geometry alive but prices ready/birth/order as
   visible coordinate entropy or match-supply loss.
21. H74 exact latent-`Q` tests show duplicate-cover gains, but uniform excess
   stays positive and raw/`Q` chooses raw-only.
22. H75 prices rare-blowup claims: bad tails can balance means, but cannot
   create enough short outputs for roughly-all winners.
23. H76 prices randomness/compute: fixed public randomness is `Q`; per-file
   best-of profiles owe selector bits.
24. H77 tests self-induced fertility: exact H74 high-`Q` top 10% needs
   `c*~0.508` and `p_FF~0.903`, while uniform starts at `0.10`.
25. H78 unifies the no-go: charged visible state leaves only source/fertility
   law or a public invariant outside the count.
26. The smallest constructive source-shaped target is a public fertility lane
   with d-choice routing and measured value lift, with uniform controls
   negative.
27. H79 separates placement d-choice from witness d-choice: `r=0.10,d=23`
   has fake `+2.475` class-bias bits if charged at placement loss, but honest
   witness multiplicity is `-1.914` bits.
28. H80 sweeps exact public-`Q` class sizes: `f=0.25` has `Q(F)=0.7787`
   versus scaled-H7 `c*=0.7247`, while uniform still pays `+1.814795` bits
   and shuffled classes lose the lift.
29. H81 shows the recurrence bottleneck: entropy-coded `Q` saves `1.365` bits
   but whitens top25 to `c=0.25`; visible `Q`-shaping restores `c=0.7787`
   but spends the same `1.365` bits.
30. H82 prices syntax-as-subset: top25 has `Q(F)=0.7787`, but support tax
   `2.000` minus membership dividend `1.639` leaves `-0.361` bits; valid/fertile
   membership alone cannot pay.
31. H83 prices length-preserving relabeling: for top25 and `F_positive`,
   identity already maximizes `Q(F)`; making bottom/random classes fertile is a
   huge profile/class channel.
32. H84 finds a real one-shot graded-law row: `lambda=0.90` saves `0.216` bits
   and preserves top25, but invariant `R->R` saving is `0`; repeatability needs
   high-entropy fertility.
33. H85 shows high-entropy fertility is mathematically plausible as an ideal
   tail target: a `0.017703`-bit entropy budget can buy a `0.216226`-bit finite
   margin, if a real syntax realizes it.
34. H86 measures that target on the exact H80 value tail: soft laws need only
   `0.005205` entropy bits for a `0.216226` future-value margin, but still
   require a native parseable grammar.
35. H87 prices repeatable soft-law cycles: tiny threshold rows are canceled by
   uniform-to-`P` capacity, while strong soft laws remain source-shaped targets
   needing real witness savings.
36. H88 makes the frozen grammar concrete: public type classes survive finite
   overhead at large `m`, best scanned `eta=1.560740`, but the value score still
   must become actual Telomere savings.
37. H89 performs that hard check: `Q`-score soft laws align with actual witness
   savings, but best finite score-law cycle is `-2.530640` bits/word; oracle
   actual-savings law is `-2.397156`.
38. H90 proves the fixed-family public-law cap: `sup_P E[S]-D(P||U)=log2 Z`;
   selected `Z` gives `-2.173930` and collective `Z` gives `-0.562959`
   bits/word in the H89 domain.
39. H91 turns that into a constructive budget: selected needs `1.086792`
   bits/record, while collective/all-description needs only `0.277599` honest
   bits/record to make `Z` cross `1`.
40. H92 sweeps `K/D` and shows optimistic `K>5` collective rows can cross when
   witness width is underpriced; best lower-bound row `K=8,D=12` gives
   `log2 Z_total=1.001339`.
41. H93 reruns `K/D` with paid extended J3D1 witness widths; all crossings
   disappear, best paid collective `log2 Z=-5.301885`.
42. H94 tests custom arithmetic rank/record witness coding; after normalizing
   seed-width multiplicity, crossings still vanish with best `custom_record`
   `log2 Z=-1.781751`.
43. H95 tests fixed biased expander laws; they move mass toward future-fertile
   outputs, but total whole-cover Kraft mass is conserved with paid V1
   `log2 Z=-11.885765` for every tested law.
44. H96 tests visible neutral genotype transfer; exact enumeration finds real
   next-pass fertility lift (`+5.659472` bits over random same-length record
   strings) but a negative paid two-pass cycle (`-60.307024` bits/word).
45. H97 samples larger neutral-transfer rows; cycles improve with `N/K/D` but
   remain negative, and best-of-same-budget random same-length controls beat
   the selected genotypes in every row.
46. H98 reopens partial `+1/+2/+4` slack refresh: unpaid sparse rows can barely
   shrink only when final freshness dies; rows that keep at least `10%` fresh
   output expand, and H2/literal stateless accounting expands in every tested
   row.
47. H99 prices seed parity/rejection readiness: even/odd seeds are a paid
   two-epoch discriminator, but many-pass exact birth classes cost `log2(P)`
   bits/record as seed-supply loss or residual ambiguity.
48. H100 turns that into the forced two-epoch target: parity gives stateless
   open/carry if max record lifetime is `<=1` pass, but current H7/H9/H12 rows
   remain negative; a real mechanism needs `>1` paid bit/record base margin
   before parity.
49. H101 discounts parity through neutral multiplicity: class loss can fall
   below `1` bit/record, but the slack/witness width bought to create that
   multiplicity overwhelms the discount in the tested H9 frontier.
50. H102 separates visible parity from public lane grammar: if lane position
   supplies the epoch class, a local class seed rank has no seed-supply tax;
   current rows still miss, but the target narrows to base forced-rewrite
   margin `>0`.
51. H103 verifies that split in the exact H74/H94 Kraft toy: local class
   grammar preserves base `log2Z` exactly, while visible global class
   restrictions lose `1.75-3.68` collective `log2Z` in tested rows.
52. H104 reconciles `SPEC_V1` keep-what-decodes with scaling: small
   checksum-refereed round trips are valid finite decodes, but carried records
   still create `T^R` readings in the arity-1 worst case.
53. H105 combines the surviving pieces: public-lane local grammar removes about
   `1` bit/record of readiness tax, but the best honest collective target still
   needs `0.468557` bits/record.
54. H106 closes ordinary arity reweighting: valid record-sequence grammars obey
   `F_n=sum W_a F_{n-a}` with `sum W_a<=1`, so whole-cover mass can reach
   `log2Z=0` but cannot become positive.
55. H107 closes fixed-mass value shaping for uniform data: biased seed/output
   laws keep the same `log2Z` and raw/`Q` mixtures choose raw unless a
   non-uniform source or fertility cycle is named and paid.
56. H108 makes the converse exact: `h92_lower` crosses only with overfull
   symbol mass `log2=2.055381`, while valid `custom_record` exactly reproduces
   `log2Z=-1.781751`.
57. H109 prices non-prefix/trial-decode syntax: a fixed checksum is only a
   finite referee for ambiguous readings; `lotus_toy` exhausts 64 bits after
   about 215 stream bits, and carried records reproduce the same `T^R`
   survivor ledger.
58. H110 sharpens partial slack refresh: parseable J3D1 still misses at
   `q>=10%` by `+0.524497` bits/atom, but a local-width oracle crosses at
   `-0.111979`, isolating payload-boundary cost.
59. H111 tests collective width streams: counts-free enum crosses at
   `-0.073289` bits/atom, but count-paid enum is `+0.147041`, so the live
   target is a frozen public width/delta law.
60. H112 freezes that public width/delta law for the ordinary H2-charged
   branch; held-out rows stay positive at `+0.2531` to `+0.3163` bits/atom.
61. H113 lets visible seed parity replace H2 only under a forced two-epoch
   age invariant; fixedD parity narrows the miss to `+0.023438` bits/atom,
   while many-epoch parity aliases and must pay residual age entropy.
62. H114 combines two-epoch parity with a frozen public delta law and crosses
   in the toy kernel: `B4,K32,D128,slack4` gives `-0.020876` held-out
   bits/atom, and 32/64 repeats across four seeds stay negative.
63. H115 converts H114 to a variable-length record-layer audit: `no_expiry`
   stays negative, but forced due-cohort refresh expands at `+0.020909`
   bits/atom/pass under the frozen law. The local-width oracle remains
   negative, so the live target is a heterogeneous public width law.
64. H116 tests that target with public arity/start/lane clocks and hidden
   target/age diagnostics. Public rows still expand, best focused public row
   `+0.023659` bits/atom/pass, and hidden bucket diagnostics also miss. The
   next branch must change the witness family or make interval composition
   public through a priced board/lane invariant.
65. H117 corrects the parser model by coding payload width directly instead of
   delta against hidden target length. The best honest row is `+0.007218`
   bits/atom/pass but rewrites only `12.4%`; forcing `25%` rewrite expands by
   `+0.061297` bits/atom/pass.
66. H118 prices collective width amortization. Count-free scale-1 enumeration
   crosses at `-0.005928` bits/atom/pass, but scaling the same empirical law
   returns to about `+0.026` bits/atom/pass with roughly `2.26` width bits per
   selected record.
67. H119 tests public fixed-width lanes. Sparse global rows can look negative,
   but at `25%` rewrite public fixed-width contexts expand, and even hidden
   target-size diagnostics miss.
68. H120 proves the boundary-channel equivalence: explicit width bits,
   seed-class supply loss, self-sync prefix syntax, and checksum ambiguity
   converge around `5.34` bits/record on the H118 selected widths.
69. H121 tests an optimistic public-gap typed board with `T_pub` given for
   free. `25%` rewrite fails for gaps `1..16`; `10%` rows expand or are fragile.
70. H122 tests paid public gap alphabets. They improve supply over fixed gaps,
   but negative lower-bound rows fail `75-84%` of trials; the nearest wider
   alphabet is `+0.001674` bits/atom/pass with nonzero fail.
71. H123 freezes public gap tables. Held-out lower-bound rows can go negative,
   such as `public_lane_raw/lane_exact_arity/q=0.10` at `-0.010851`
   bits/atom/pass, but fail `43.75%` of trials.
72. H124 repairs those failures with raw fallback. Markerless raw atoms give
   `-0.014587` to `-0.023438` bits/atom/pass, but the hidden type stream costs
   `0.157-0.194` bits/atom/pass as a bitmap or `0.261-0.303` as run
   boundaries.
73. H125 makes raw fallback public with fixed raw lanes/runs. Periodic lanes are
   parseable, but all tested meaningful rows fail, including `period=8`,
   `raw_run=7`, `25%` rewrite.
74. H126 tests paid raw segments. One/two free segments still expand at
   `atoms=128`; exact boundary lists add `0.08-0.15` bits/atom/pass, far above
   the H124 margin.
75. H127 sweeps the user's partial-rewrite sweet spot. Raw lower-bound deltas
   stay negative from `1%` to `25%` rewrite, but bitmap-priced nets are
   `+0.143` to `+0.168` bits/atom/pass.
76. H128 quantifies the near-total public-board target. H124 margins require
   roughly `99.77%-99.94%` public opening as `P` grows from `2` to `4096`
   passes.
77. H129 tests counted raw-prefix zones. Parseable zones miss: `zone=32` gives
   `+0.121578` bits/atom/pass at `25%` rewrite, and `zone=128` fails outright
   in the focused row.
78. H130 combines near-total exceptions with witness margin. Exceptions always
   raise the required boost over all-open; H105 `custom_record` moves from
   `0.468557` to `0.542498` bits/record at `eps=0.001`, `P=4096`, `F=0`.
79. H131 tests typed all-open public boards. Public slot types solve parsing,
   but positive gain limits coverage; saving `1` bit covers only `39.35%` per
   pass, while `90%` final survival over `4096` passes requires about `3.40`
   bits of bloat.
80. H132 tests self-consistent width-aware selection for the partial-refresh
   sweet spot. Public arity/lane laws still expand, and even hidden
   target-arity diagnostics stay positive at `+0.017` to `+0.026`
   bits/atom/pass in the focused rows.
81. H133 tests common-cause batch witnesses. Honest batch convolutions are
   valid but worse than the base `custom_record` row; positive-looking
   discounted batches are overfull, e.g. `m=2,discount=2` gives
   `log2Z=1.220990` with `log2 symbol mass=2`.
82. H134 tests CRT/modular readiness clocks. Best clocks reach the `log2(P)`
   floor but do not beat it; `P=4096` costs `12.002815` bits in the small CRT
   sweep, so clocks only help after a separate invariant bounds record
   lifetime.
83. H135 starts an exact recurrent transfer harness. The tiny `N=3,K=1,D=1`
   two-pass control has no zero-failure row; richer exact rows get expensive
   because pass two targets visible record strings, not small raw words.
84. H136 tests non-contiguous batch footprints over an uncovered board. Valid
   normalized footprint grammars reach `log2Z=0` at best; free all-mask
   footprints cross only with local overfull mass, e.g. `K=4`
   `log2Z=21.656226` and `max local log2=7.857981`.
85. H137 tests bits-back salt flywheels. Balanced posterior tape with
   `gamma=1` is conserved; `P=4096,gap=0.25,tape=salt=64` has `net=-1024`
   bits, while unbalanced tape pays huge final settlement. Positive slope needs
   `gamma>1` fertility.
86. H138 tests bounded reset ratchets. Resets cap damage but destroy accumulated
   shrink; for half-rate `90%` survival, `eps` must fall from `0.003287` at
   `P=64` to `5.144e-5` at `P=4096`.
87. H139 adds the reset/ratchet converse ledger. A `P64,s=1,90%` coverage claim
   has prefix support `5.421e-20`; visible `64`-bit state cancels the saving,
   and hidden `2^32` best-of returns to the raw bound once the selector is paid.
88. H140 prices `+1/+2` slack refresh supply. The local-width oracle has real
   option pressure, e.g. `B4,K5,s2` gives `q=0.999877`, but exact J3D1
   `B4,K32,s2` gives `q=0.342932` with `H2/q=2.705` bits per rewritten atom;
   `q>=50%` is not reached by `K=4096`.
89. H141 closes seed-derived boundary tricks by Kraft. The best
   self-delimiting seed language at fixed delta is a public fixed-width lane;
   `B4,K32,delta=-1` gives `q=0.393469` but `partial+H2=+0.954706` bits/atom,
   and `q>=0.90` needs `+2` bits/record.
90. H142 optimizes intrinsic boundary classes directly. On the H120 pooled
   ledger, break-even width entropy is `1.540537` bits/record, while optimal
   Kraft loss is `H(W)=5.341012`; even half entropy at `2.670506` still
   expands.
91. H143 gives a generous near-total public-board bound. Exact J3D1 `slack<=2`
   tops out at `q=0.342932` versus required `q~=0.999`; `slack=8` reaches
   `q~=1` but still expands, e.g. `B4,K128` total `+0.032630` bits/atom.
92. H144 reframes non-greedy slack as future-value selection. The easiest
   `slack=8` rows need only `0.008625-0.040116` bits/atom/candidate of real
   future value, making recurrent transfer measurement the next live target.
93. H145 prices upward unfolding depth. Fixed depth gives one output per seed;
   stop among `T` states gives coverage but costs `log2(T)`, so `90%` coverage
   at `G` saved bits stores back `G+1.203` stop bits unless a public invariant
   derives the stop.

## Next target

The next work should be a finite response-surface sweep, not another isolated
idea:

```text
axis A: coverage epsilon, including eps <= 0.01
axis B: public lane fraction r and d-choice count d
axis C: paid witness gap in bits/record
axis D: source/fertility value lift gamma
axis E: decoder observation class: public, content-selected, or referee/compute
axis F: adaptive-knob accounting: fixed public, paid selector, or proved unique invariant
axis G: syntax-derived selector: unique parse first, then charged delimiter cost
axis H: normalized public witness distribution: log-rho and expected bits must both cross
axis I: raw/stop mixture: mixture weights public, train/eval split, expected bits below raw
axis J: roughly-all fraction: coverage target, saved bits, required source lift, selector/referee debt
axis K: phase target: nearest miss, unit, and whether it requires a uniform public invariant or source lift
axis L: recursive source fertility: public class mass, code lift, source class probability, and c_{t+1} invariant
axis M: fertility transition: p_FF, p_OF, threshold fixed point, and uniform negative control
axis N: non-prefix path: final-output slots, path-free apparent coverage, and hidden length-path bits
axis O: public invariant exhaustion: visible states, apparent winners, hidden state, finite referee budget
axis P: all-block cover entropy: local option dividend, cover-shape selector rate, normalized-Q conservation
axis Q: repeated-pass tail risk: mean log-rho, bad fraction, blowup size, arbitrary-P survival
axis R: public-code martingale: normalized Q, wealth mean, optional stopping, hidden best-of selector
axis S: measurement correction: log-rank width sampling, high-span overcharge, corrected frontier rerun
axis T: d-choice conservation: placement/salt routing versus witness-value multiplicity
axis U: public-Q fertility class size: Q(F), c*, p_FF need, shuffled controls
axis V: output law recurrence: entropy-code whitening versus visible shaping cost
axis W: native syntax capacity: support tax versus source membership dividend
axis X: length-preserving relabeling: fixed public permutation versus profile channel
axis Y: graded native law: one-shot Q-to-R tradeoff versus recursive R-to-R invariant
axis Z: entropy-budget fertility: future-value tail lift versus source entropy deficit
axis AA: native value tail: measured lift-delta versus visible entropy deficit
axis AB: native soft cycle: source-shaped cycle margin versus uniform startup bill
axis AC: frozen soft grammar: type-class parser overhead versus measured value lift
axis AD: actual witness savings: score lift versus exact selected-record cost
axis AE: witness Kraft cap: variational public-law bound from honest Kraft mass
axis AF: Kraft boost budget: flat/per-record bits needed to make Z exceed 1
axis AG: K/D Kraft sweep: higher arity and deeper search against honest Z mass
axis AH: paid extended arity: H92 lower bound versus J3D1 witness-width accounting
axis AI: normalized rank witness: width-class multiplicity versus custom arithmetic records
axis AJ: biased native expander: future-fertile mass movement versus conserved Kraft mass
axis AK: neutral transfer operator: visible genotype choice versus paid cycle margin
axis AL: sampled neutral transfer: best-of-search lift versus same-budget random controls
axis AM: partial slack refresh: replacement fraction versus paid ready/carry entropy
axis AN: seed-class readiness: seed-supply loss versus live birth-epoch ambiguity
axis AO: forced two-epoch generation: lifetime invariant versus >1 bit/record base margin
axis AP: neutral parity discount: conditional class loss versus width/slack bill
axis AQ: public lane local class grammar: public epoch observation versus subset entropy
axis AR: class-local Kraft check: local seed class mass versus visible global thinning
axis AS: SPEC decode scaling: finite checksum referee versus T^R survivor growth
axis AT: forced-rewrite collective target: paid log2Z_total versus public readiness
axis AU: cover-sequence Kraft capacity: arity reweighting versus prefix mass <= 1
axis AV: value-shape conservation: biased public output law versus uniform raw/Q fallback
axis AW: prefix record grammar converse: exact symbol mass versus false crossings
axis AX: non-prefix referee capacity: ambiguous readings versus finite checksum budget
axis AY: partial-refresh Pareto frontier: replacement fraction versus payload-boundary cost
axis AZ: collective width stream: public delta law versus per-file histogram channel
axis BA: frozen delta law: public profile training versus held-out H2 branch
axis BB: seed-class partial refresh: visible class cost versus two-epoch age invariant
axis BC: frozen delta parity target: paid crossing versus exact codec/bootstrap proof
axis BD: record-layer due refresh: heterogeneous item lengths versus fixed-atom lower bound
axis BE: public pre-seed context: arity/lane clocks versus hidden interval composition
axis BF: payload-boundary parseability: width symbol versus target-length delta
axis BG: collective width entropy: short count-free streams versus asymptotic rate
axis BH: deterministic width lanes: padding/supply loss versus width entropy
axis BI: width-channel equivalence: explicit symbols versus seed classes/referees
axis BJ: public gap board: known target length versus fixed-gap match supply
axis BK: gap alphabets: paid gap-class entropy versus due-refresh supply
axis BL: public gap tables: frozen profile margin versus held-out fail rate
axis BM: markerless raw fallback: apparent margin versus raw/record type-stream cost
axis BN: public raw lanes: parseable fixed clocks versus output geometry brittleness
axis BO: raw segment boundaries: contiguous fallback regions versus boundary-list entropy
axis BP: rewrite sweet spot: replacement quota versus paid type-stream cost
axis BQ: near-total board: exception fraction versus public-opening coverage threshold
axis BR: counted raw zones: count ledger versus stable-prefix geometry rigidity
axis BS: near-total witness margin: exception fallback versus all-open witness target
axis BT: typed all-open board: public slot metadata versus finite coverage capacity
axis BU: self-consistent width law: paid refresh selection versus held-out width entropy
axis BV: common-cause batch witness: shared boundary claim versus Kraft overfullness
axis BW: modular readiness clocks: epoch residues versus log2(P) seed-supply floor
axis BX: recurrent fertility transfer: visible genotype support versus paid cycle average
axis BY: batch footprint board: public non-contiguous geometry versus footprint selector mass
axis BZ: bits-back salt flywheel: posterior tape conservation versus gamma>1 fertility
axis CA: bounded reset ratchet: suffix shrink versus O(1/P) reset probability
axis CB: reset converse: claimed saving support versus visible state and paid hidden choices
axis CC: slack-refresh supply: O(K^2) option pressure versus parseable width and H2 layout bills
axis CD: seed-boundary Kraft: self-delimiting witness inventory versus fixed-width lane collapse
axis CE: intrinsic boundary optimizer: H(W) floor versus H120 break-even entropy
axis CF: near-total public board: public opening probability versus exact witness delta
axis CG: non-greedy lookahead: current slack bloat versus measured future-value lift
axis CH: unfold-depth stop time: compute depth versus stop/referee information
axis CI: slack superposition transfer: visible genotype fertility versus current bloat
axis CJ: upward detour collapse: final address count versus hidden branch/stop choices
axis CK: two-pass selected stream: collective future score versus actual recurrent support
axis CL: decode composition capacity: fixed decoder self-parse support versus final address count
axis CM: selected-stream DP: support slack versus paid final selected length
axis CN: closure Kraft ledger: valid record-stream density versus match-supply thinning
axis CO: superposition gap ledger: non-greedy visible lift versus hidden cloud rank
axis CP: cloud Q conservation: normalized superposition mass versus KL(U||Q)
axis CQ: fixed-cell closure phase: free parseability versus seed-address starvation
axis CR: closed-lane non-greedy target: public-lane base gap versus selected-stream lift
axis CS: completion seed-mass tradeoff: filler parseability versus seed freshness
axis CT: recursive selected-stream DP: closed seed-bearing recursion versus visible final length
axis CU: opening referee scaling: keep-what-decodes candidates versus fixed checksum bits
axis CV: seed-bearing closed core: recurrent seed-stream SCCs versus closure mass and incoming compression
axis CW: seed closure transfer matrix: product-parser closure mass versus compressive path absence
axis CX: item-level closure economics: self-delimiting item targets versus accepted mass and sparse uniform saving mass
axis CY: item-stream cover DP: non-greedy full-cover support versus successful-cover drift
axis CZ: extended-arity item DP: paid higher-K option space versus arity-code thickening
axis DA: fertility-selection threshold: future-value bits per selected witness versus ideal best-of-M conversion
axis DB: fertility option DP: same-cost neutral multiplicity versus H164 future-value requirement
axis DC: visible-selected conservation: public-class fertility lift versus same-budget random controls
axis DD: emitted-stream recurrence: selected visible length/order versus same-budget controls
axis DE: public recurrent fertility law: class restriction tax versus source-population recurrence
axis DF: visible-class paid savings: public visible features versus actual paid witness savings and class tax
axis DG: native record-class scan: emitted record features versus witness-mass tax and future paid saving
axis DH: designed fertile sublanguage: constructed boost versus Kraft mass and class tax
axis DI: designed closed item language: public closure recurrence versus overfull grammar capacity
axis DJ: population concentration: no-tax public population mode versus KL source/output concentration cost
axis DK: final-board salt capacity: survivor shrink versus end-state entropy and public-lane supply loss
axis DL: state-carrying transducer: free observed digest-tail state versus exact witness and width drift
axis DM: finite-state mixed-radix width: public width inventory versus recursive support
axis DN: Kraft cover bound: per-record savings versus prefix arity criticality
axis DO: neutral option capacity: same-cost seed choice versus slack/bloat bill and support tails
axis DP: reachable regime tax: developmental generated gain versus source restriction entropy
axis DQ: cocycle canonical placement: path-independent decode geometry versus witness supply
axis DR: finite referee survivor capacity: checksum pruning versus hidden reading entropy
axis DS: transfer-matrix population law: visible recurrent fertility versus paid row-mass bound
axis DT: generated reachable codec: inside-class recursive gain versus source membership tax
axis DU: quotient witness language: coset supply boost versus hidden member entropy
axis DV: coalescence capacity: survivor shrink versus preimage residual/source tax
axis DW: state-tail conservation: decoder-derived state versus supply/selector/settlement cost
axis DX: shared macro-witness: batch overhead amortization versus target-tuple supply
axis DY: syndrome residual ledger: algebraic repair versus residual ambiguity/source tax
axis DZ: non-prefix UD grammar: self-synchronization versus Kraft-McMillan bound
axis EA: whole-layer minimum description: canonical shortest witness versus parse/fallback mode bit
axis EB: Kraft-reserved raw fallback: implicit mode mass versus fallback alphabet length
axis EC: normalized bits-back mixture: selected short files versus uniform KL tail
axis ED: syntax-derived ready states: public DFA geometry versus state-conditioned KL/source tax
axis EE: finite-state language transform: parseable syntax surface versus reversible transform tax
axis EF: public witness-mass smoothing: paid salt lanes versus uniform KL lower bound
axis EG: recursive output law: self-induced source bias versus residual entropy tax
axis EH: bounded referee overfullness: hidden candidate surplus versus selector/checksum entropy
axis EI: native developmental tree: maintained generated recursion versus reachable-set tax
axis EJ: generated residual attachment: arbitrary residual coverage versus preimage rank cancellation
axis EK: nearest generated cover: high-coverage residual volume versus selected-root entropy
axis EL: multi-root superposition: generated residual support versus selected-root/bitmask rank
axis EM: recombination crossover: parent/crossover support versus decoder rank entropy
axis EN: derived crossover schedule: free deterministic schedule versus lost support rank
axis EO: public orbit selection: visible accept/reject versus thinning or accepted-index entropy
axis EP: visible population law: generated lineage gain versus reachable-set membership tax
axis EQ: visible population overhead: exact root-record cost versus support rank
axis ER: packed root population: ideal root-rank packing versus mode/fallback Kraft mass
axis ES: visible population prior: generated-lineage upside versus source KL tax
axis ET: developmental macro codec: exact generated round trip versus membership/raw escape
axis EU: position channel converse: final arrangement capacity versus birth/salt labels
axis EV: honest induced prior: emitted-stream shape versus KL/source-tax conservation
axis EW: bounded-slack lookahead: legal stored-seed steering versus real future fertility
```

Candidate mechanisms should only be promoted if they move one of these axes
past a named threshold.

## Artifact

`model_analysis/birth_channel_research/H42-response_surface_map.py`

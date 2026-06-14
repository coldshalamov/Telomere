# Telomere Birth-Channel Results

Date: 2026-06-14

Scope: this report prices candidate mechanisms for maintaining fresh salted
hash-match opportunities across recursive or multi-pass Telomere operation while
keeping decode stateless except for a fixed/root/end header. It does not run
corpus compression or large seed searches. It uses counting, entropy ledgers,
and small deterministic Python kernels.

## Reopened Status

There is **no completed arbitrary-content winner**. The previous TST/STF/BBL
stack is useful evidence, but it does not satisfy the reopened success bar:

- TST/STF are generated/reachable positive controls with stateless decode.
- BBL is a finite bundle-only ledge that prices wrong-pass ambiguity.
- None proves that arbitrary or unshaped content keeps matching at useful
  density under the uniform hash law.

The active kernel for the reopened search is:

```text
model_analysis/birth_channel_research/arbitrary_freshness_kernels.py
```

It attacks the three requested families directly:

### Family 1: Decoder-known nonce channels

Visible nonce bits are known to the decoder before expansion, so the toy
round-trips statelessly. But the nonce is stored in the record and is therefore
paid as address width:

```text
k nonce  record   gross      hit p  E win/window  random hits
      0      12       4    0.01562       0.06250     2/256
      1      13       3    0.03125       0.09375     7/256
      2      14       2    0.06250       0.12500    15/256
      3      15       1    0.12500       0.12500    34/256
      4      16       0    0.25000       0.00000     0/256
      5      17      -1    0.50000       0.00000     0/256
```

Result: visible nonces are a paid seed-depth tradeoff, not a free
birth/freshness channel.

The public-lane mutation stores no lane id. The encoder tries `K` public lanes;
the decoder tries them all and pays for surviving readings:

```text
lanes final items  records payload bits   candidates  ambig bits orig in set   net vs raw
    1          23        1          117            1       0.000        True      -21.000
    2          23        1          117            1       0.000        True      -21.000
    4          22        2          114            3       1.585        True      -19.585
    8          19        5          105      200000+      17.610     unknown    <=-26.610
```

Result: public lanes increase search supply without stored metadata, but wrong
lanes often parse. The bill reappears as surviving decode ambiguity unless a
stronger self-dating grammar can reject wrong lanes without thinning true
arbitrary targets.

### Family 2: Target-refresh without salt-refresh

The fixed-universe composition codec has exact encode/decode and needs no pass
salt, birth tag, or final-position note. Records recursively open in place.
On 200 unshaped random 96-block trials:

```text
pass  avg windows  avg matches  hit/window   avg gain
   1        95.00        2.720     0.02863      8.160
   2        92.06        0.065     0.00070      0.324
   3        89.25        0.000     0.00000      0.000
mean final wrapped-bit gain=8.460 bits
mean final original-payload gain=-87.540 bits
```

Result: target churn alone did not maintain match supply. It also showed an
important accounting trap: gaining against literal-wrapped working state is
still bloat against original payload.

The arity-flex mutation allowed fixed unsalted records of arity 2-5, so later
targets could include record/literal and record/record spans:

```text
valid fixed-universe spans by arity: a2=136, a3=114, a4=92, a5=65
pass  avg windows  avg matches  hit/window   avg gain       a2/a3/a4/a5
   1       374.00        1.010     0.00270      3.105 0.00/0.99/0.01/0.00
   2       361.48        0.000     0.00000      0.000 0.00/0.00/0.00/0.00
mean final wrapped-bit gain=3.105 bits
mean final original-payload gain=-92.895 bits
```

Result: effective-length migration did not stabilize match supply in this
unshaped toy.

### Family 3: Self-dating grammar / wrong-pass explosion

Residue-valid grammar bits make wrong openings fail structurally, but true
targets must carry those bits too. At `P = 1,000,000`, the best toy row was:

```text
arity=2 residue=6 span=30 gross=15 hit_p=7.629e-06 ambiguity=7.112
expected_net_per_arbitrary_window=6.018e-05 bits
```

Result: this is a real finite ambiguity lever, but not yet an
arbitrary-content density solution. The current mutation target is to make the
self-dating validity check derive from already-present item bits instead of
carrying extra residue bits.

Derived validity from visible seed classes avoids adding residue bits to the
record, but restricts the eligible seed class by the same amount:

```text
best toy expected net/window=5.137e-05 at arity=3 class=6
```

Result: seed-class, checksum-residue, lane-constrained codeword, and
neighbor-state validity checks must be priced as match-supply loss unless they
reject wrong lanes more often than they reject true arbitrary targets.

## Prior Positive Controls

The strongest prior control stack is **TST + STF + BBL**, specified in
`BEST_SPEC.md` and exercised by:

```text
model_analysis/birth_channel_research/typed_scheduled_tree_codec.py
model_analysis/birth_channel_research/scheduled_tree_codec.py
model_analysis/birth_channel_research/bounded_bundle_codec.py
```

TST removes internal marker entropy by making child type public from the
schedule. Verified generated forests:

```text
depth=4, roots=4, leaves=64
raw_bits=512
charged_bits=503
net_bits=+9

depth=6, roots=2, leaves=128
raw_bits=1024
charged_bits=917
net_bits=+107
```

This is not arbitrary-content match maintenance. At depth 6, each root stores
415 seed bits plus a 2-bit marker to regenerate 512 raw bits. Under a uniform
output law, full seed-space coverage for one 512-bit root slab is:

```text
2^415 / 2^512 = 2^-97
```

That is the bill: reachable-set sparsity, not hidden metadata.

STF is the first fully charged-positive scheduled-tree toy. BBL remains the
bounded trial-decode extension path:

- It uses fresh SHA-256 dice keyed by `(pass, packed_position, seed)`.
- It avoids arity-1 singles as the deep engine.
- It opens/carries by reverse trial decode and a fixed root checksum/referee.
- It prices that referee as `R * c_a(P)` ambiguity bits, not as free metadata.

## Conservation Boundary

No unbounded, content-blind, stateless birth/open/carry channel survived. The
sharp obstruction is per-record birth pass information. Under the uniform hash
law, the pass on which a match first appears is a content outcome, independent
of any public position orbit. If a decoder must distinguish `P` possible birth
passes for `R` surviving records, the missing coordinate has entropy
approximately:

```text
birth_bill = R * log2(P) bits
```

That is above the available average match win once `P >= 4`, because the
format's honest conditional gain remains about 2 bits per accepted match.

There are useful finite channels:

- Arity-1 singles have no free structural subsidy. Their ambiguity is exactly
  `S = P^R`, so cost is `log2(P)` bits per record.
- Length-pinned bundles get a real finite parse/explosion subsidy. For arity
  `a`, wrong-salt survivors cost
  `c_a(P) = log2(1 + (P - 1) * 2^-E_a)` bits per bundle. This can stay below
  2 bits over a finite pass range, but it grows like `log2(P) - E_a` and is not
  unbounded.
- Final-position/egg-carton boards round-trip mechanically, but the final
  arrangement note is the birth channel. If positions are stored, its optimal
  cost is an enumerative code over valid final arrangements. If positions are
  not stored and are only public-shuffle-derived, they convey zero birth bits.

BBL deliberately stays inside the finite bundle window where this cost is below
the selected-record savings.

## Final-Board Model

Let:

- `R` = final survivors whose birth/open time must be known.
- `Q` = final coordinate space or board cells.
- `P` = possible birth passes.
- `V(R, Q, P)` = valid final arrangements under the board rules.
- Payloads are serialized in coordinate order, which is the cheapest ordering
  convention. If payload order is stored separately, add `log2(R!)`.

The cheapest final-board note is:

```text
arrangement_cost = log2(V(R, Q, P))
```

For a plain unordered occupied-cell board:

```text
V = C(Q, R)
arrangement_cost = log2 C(Q, R)
```

For a pass-lane board with `P` lanes of size `Q/P` and a known histogram
`r_t`, the placement component is:

```text
V_lane = product_t C(Q/P, r_t)
arrangement_cost = log2(V_lane)
```

But the lane assignment itself is the birth-pass map. For uniform independent
births it carries approximately `R * log2(P)` bits. Shrinking `R` lowers the
total note and the total 2-bit wins together. It does not lower the per-survivor
price:

```text
birth_cost_per_survivor = log2(P)
win_per_survivor ~= 2 bits
net condition: log2(P) < 2
```

So final positions beat the note only for very small finite pass counts
(`P <= 3`; `P = 4` is already break-even before other costs). If a board is
made huge enough that `log2 C(Q, R) >= R log2(P)`, then the coordinate note has
enough capacity only by becoming at least as expensive as the birth map. If a
board is kept tight so the note is cheaper, it lacks enough valid end states to
encode arbitrary birth maps. If the encoder accepts only birth maps that fit
the board lanes, the missing cost reappears as match-supply loss.

## Verdict Table

| Idea | Mechanism | Open vs carry | Birth pass / salt | Fresh outputs? | Stored, derived, or hidden info | Entropy cost | Result |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Position salts, current spec rule | Salt by match position and reverse shuffle to the pass state | Trial decode chooses which records open | Correct only when the decoder opens at the birth-state position | Yes, if birth pass is known | Birth pass is hidden in trial-decode/checksum | Singles: `log2(P)` per record; bundles: `c_a(P)` | Finite, not unbounded |
| Final-position board / egg carton | Store final occupied coordinates once | Coordinate can mark a lane or pass | Decoder reads lane from coordinate if stored | Yes if lanes are pass-specific | Final positions are the channel | `log2 V`; at least `R log2(P)` for arbitrary births | Not net-positive for `P >= 4`; shrinking `R` does not fix per-match cost |
| Fixed board + modular wrap | Public permutation of a fixed coordinate board | No extra signal | Final coordinate is a function of original slot and total passes | Yes only if salt varies, but birth still unknown | No stored positions, only public orbit | 0 stored bits, 0 birth bits conveyed | Refuted |
| Growing PCTB board | Encode carry/open as board instruction slots, store final positions | Instruction lane is decodable | Pass/code salt is recoverable | Yes | Final occupied set | Carry-only exact note `log2 C(Q_P, R)`; measured 21.9x raw at 64 passes for `M=1000` | Mechanics work, ledger fails raw+epsilon |
| Placement lanes / encrypted instruction slots | Hide open/carry in lane choice or PRP slot | Lane tells instruction if stored | Lane or PRP code tells salt | Yes | Lane occupancy / instruction placement | Same as final positions; if encrypted, ciphertext still has same entropy | Paid channel, not under 2 bits past tiny P |
| Pass count scratchpad | Store total pass count in header | Does not identify individual records | Gives `P`, not per-record birth | Helps schedule, not birth | Header total only | `log2(P)` total, but need `R log2(P)` | Insufficient except tiny `R` |
| CRT / modular clocks | Read residue clock from final coordinate | No open/carry distinction | Final residue is fixed by final slot, not birth | Public orbit refreshes positions but not birth info | Public coordinate | 0 conveyed; frozen-coordinate variant pays `>= R log2(P)` placement bits | Refuted |
| Affine / Feistel orbit fingerprints | Use orbit phase or stride as epoch | Singles have no stride; bundles get only candidates | Orbit phase reads total count, not birth for singles | Yes if salt known | Public orbit | Singles 0 bits; bundle residual `c_a(P)` | Finite bundle subsidy only |
| Parity / sign lanes | One-bit lane from position parity or involution | Can filter candidates if acceptance is gated | Informative only if coupled to birth | Freshness reduced by gating | Either decoupled public parity or gated supply | Decoupled: 0; gated: 1 supply bit per bit | No net gain |
| Fibonacci / Zeckendorf registers | Number-system phase or bounded register | Same as public orbit | Birth absorbed by inverse starting slot | No extra channel | Public phase | 0, or stored phase reference / supply loss | Refuted |
| Occupancy / holes | Bundle removes slots, holes might reveal epoch | Holes pin placement if known | Hole set can identify bundle geometry | Yes | Hole positions | `log2 C(N, holes)`; this is PCTB/position tax | Paid, not free |
| Scheduled edges / exclusion rules | Restrict which pass can use which slots/seeds | Decoder knows schedule | Birth known only for accepted scheduled hits | Partially, but dice repeat or supply is thinned | Match acceptance restriction | About 1 supply bit per conveyed bit | Conserved |
| Trial decode / checksum pruning | Try open/carry readings and keep one that parses/checks | Structural parse prunes wrong opens | Checksum selects among survivors | Yes | Checksum/referee | Singles `R log2(P)`; bundles `R c_a(P)` | Finite; checksum must scale for large `R,P` |
| Explosion checks | Wrong-salt digest often fails self-delimiting parse | Prunes wrong bundle opens | Only length-pinned records benefit | Yes for candidates not pruned | Structural grammar | Singles `E=0`; bundles finite `E_a` | Useful finite intercept |
| Biased seed grammars | Make seed class imply birth pass | Decoder reads class from seed | Birth bits carried by seed class | Fewer eligible seeds per pass | Match supply | `I` conveyed bits cost at least `I` supply bits; residual stored | No sub-1x channel |
| Value/count separation | Try to spend rare high-value seed classes for birth labels | Seed class labels birth | Same as biased grammar | Yes but supply tiny | Seed population skew | Count and value co-located; jackpot classes have near-zero supply | Refuted at Golden Config |
| Recursion / layer stacking | Re-run output as a new file, resetting epoch | Layer boundary is known | Birth free only within short layer | Yes per layer | Layer carriage | Base-rate net/bit `-0.35` to `-0.37`; flip requires about 48x density | Not content-blind net-positive |
| Bounded Bundle Layer | Use only arity>=2 length-pinned bundle records inside a capped pass window | Reverse DFS opens/carries records; structural parse prunes wrong opens; checksum/root picks survivor | Salt is `(pass, packed position, seed)` and is tested during reverse pass | Yes across the bounded pass window | No birth tags; ambiguity is charged as checksum/referee bits | `R*c_a(P)` plus fixed/root fields; selected-record net positive while `gross_win > c_a(P)` | Finite residual/extension path; useful while bundle ambiguity stays below selected-record savings |
| Scheduled Forest | Accept only complete public binary bundle trees; every node opens at its public depth | No carry ambiguity inside tree mode; raw fallback otherwise | Salt is `(depth, tree position, seed)` | Yes across tree depths | Root seeds plus mode/depth/count/checksum; no birth tags | Verified toy: depth-2 forest +41 bits, depth-3 forest +1 bit | **Fully charged-positive positive-control**; depth/search reach is bottleneck |
| Typed Scheduled Tree | Public tree depth gives child type; internal expansions emit child seeds directly | No carry ambiguity; every node opens at public depth | Salt is `(node kind, seed, depth, tree position)` | Yes across depths and positions | Root seeds plus mode/depth/count/checksum; schedule supplies type | Verified toy: depth-4 +9 bits, depth-6 +107 bits fully charged | Reachable-set control only; not arbitrary-content supply maintenance |

## Bundle Entropy Ledger

For length-pinned arity `a` bundles, let `E_a = -log2(q_a)`, where `q_a` is the
wrong-salt parse survival probability. The tested/derived values are:

| arity | `E_a` bits | near-free knee `2^E_a` | pass cap for birth cost `< 2 bits` | `c_a(64)` |
| --- | ---: | ---: | ---: | ---: |
| 2 | 9.36 | 657 | 1972 | 0.132 |
| 3 | 12.59 | 6165 | 18497 | 0.015 |
| 4 | 14.97 | 32094 | 96282 | 0.003 |
| 5 | 18.20 | 301124 | 903374 | 0.000 |

This is the best surviving finite open/carry-ambiguity mechanism for BBL. It
should be read carefully:
higher arity moves the intercept by making wrong parses rarer, but it does not
remove the asymptotic slope. At large `P`, the residual grows as:

```text
c_a(P) = log2(1 + (P - 1) * 2^-E_a) ~= log2(P) - E_a
```

The pass caps above price only the birth/open channel, not whole-file
compression. Content-blind hit density and literal carriage still decide
whether a layer should be kept.

## Prior Control And Residual Ledgers

TST is charged-positive in a generated reachable scheduled-tree regime, not on
random data. The honest whole-slab toy ledger is:

```text
charged_bits = mode + depth + root_count + fixed_width_root_seeds + checksum
net_bits = raw_bits - charged_bits
```

The verified charged-positive cases are:

```text
depth=4 roots=4 leaves=64  raw_bits=512  charged_bits=503  net_bits=+9
depth=6 roots=2 leaves=128 raw_bits=1024 charged_bits=917  net_bits=+107
```

The price is reachability density and encoder search. If the input group is not
in the recursive image of any searched root seed, typed-tree mode falls back to
raw. The current positive fixture is generated from reachable roots and stores
those roots at full fixed width; it is a codec/accounting proof for the
mechanism, not a natural-corpus prevalence claim.

This means TST did not move bloat into unpriced metadata. It moved the bill into
match supply. That may still be useful for a shaped, public-preset, or generated
subspace, but it is not a solved content-blind arbitrary-input match-rate
maintenance theorem.

BBL remains the best residual finite-pass mechanism for dense selected bundles.
The honest selected-record ledger is:

```text
net_per_bundle = replaced_bits - record_bits - c_a(P)
c_a(P) = log2(1 + (P - 1) * 2^-E_a)
```

For arity 2 at `P = 64`, `c_a(P) = 0.132` bits. With the Golden-style gross
selected-record win of about `2.17` bits, the charged birth/open net is about
`2.038` bits per accepted bundle before fixed header amortization. With `R`
accepted bundles and few leftovers:

```text
net ~= R * 2.038 - fixed_header - literal_carriage
```

So BBL is net-positive for large dense generated/reachable inputs where
accepted bundle density is high. The remaining work is to supply or discover
that dense class without violating the content-blind premise, or to explicitly
classify the mode as a dense-class/hybrid mode.

Concrete toy evidence now exists for the generated dense class:

```text
bounded_bundle_codec.py generated dense fixture
blocks=24, passes=2, matches=13
payload_delta=+19.000 bits
asymptotic_delta=+11.918 bits after ambiguity pricing
charged_delta=-54.082 bits after the 66-bit toy header
```

So the fixture is positive before fixed-header amortization and negative after
the tiny-instance fixed root cost. BBL is therefore not the top winner; it is the
bounded residual lane that can be combined with TST/STF when dense bundle
matches remain after scheduled-tree extraction.

Scheduled Forest supplies that mutation for a stricter generated class:

```text
scheduled_tree_codec.py forest fixture
depth=2, roots=8, leaves=32
charged_delta=+41 bits after mode/depth/root-count/checksum
depth=3, roots=2, leaves=16
charged_delta=+1 bit after mode/depth/root-count/checksum
```

The fixed-width version failed at depth 3. The tiered-width mutation uses a
larger internal-node seed budget and reaches a charged-positive depth-3 forest,
but only barely.

Typed Scheduled Tree supersedes that bottleneck by removing internal marker
entropy. Its public type schedule makes every seed decodable at every internal
node, so reachability no longer collapses with depth in the toy generated
regime. The new bottleneck is witness search on non-generated inputs.

## Impossibility Statement

Under the uniform hash law, for content-blind salted Telomere:

1. Birth pass is the time index of a uniform match event.
2. Public shuffles, CRT clocks, Feistel orbits, Fibonacci phases, and parity
   labels are deterministic functions independent of that match event unless
   the encoder gates acceptance or stores placement.
3. A decoder that must recover `R` independent birth passes over `P` candidate
   passes needs a discriminator for about `P^R` readings.
4. Any discriminator has cost `log2(P^R) = R log2(P)` bits, except for finite
   structural parse subsidies on length-pinned records.
5. Those subsidies are constants. They shift a finite intercept, but cannot
   sustain unbounded pass freshness.

Therefore a free, content-blind, unbounded birth channel would make arbitrary
random data net-compress with bounded worst-case loss, violating the counting
gate. The bill must appear as stored bits, match-supply loss, wrap/carriage, or
compute/checksum search.

## Runnable Kernels

Fast consolidation:

```powershell
python model_analysis\birth_channel_research\arbitrary_freshness_kernels.py
python model_analysis\birth_channel_research\quick_birth_channel_kernels.py
python model_analysis\birth_channel_research\typed_scheduled_tree_codec.py
python model_analysis\birth_channel_research\bounded_bundle_codec.py
python model_analysis\birth_channel_research\scheduled_tree_codec.py
python -c "import sys; sys.path.insert(0, r'model_analysis\birth_channel_research'); import scheduled_tree_codec as s; s.forest_demo(depth=3, roots=2)"
```

Representative audited lane kernels:

```powershell
python model_analysis\birth_channel_research\arbitrary_freshness_kernels.py
python model_analysis\birth_channel_research\A-modular-orbit_invariance.py
python model_analysis\birth_channel_research\C-crt-clock_odometer.py
python model_analysis\birth_channel_research\C-crt-clock_frozen_coord.py
python model_analysis\birth_channel_research\P2-recursion-ledger.py
python model_analysis\proof_kernel\pctb_ledger.py
python model_analysis\birth_channel_research\P2-biased-hash_coupling_ledger.py
python model_analysis\birth_channel_research\typed_scheduled_tree_codec.py
python model_analysis\birth_channel_research\bounded_bundle_codec.py
python model_analysis\birth_channel_research\scheduled_tree_codec.py
```

The default `B-ambiguity-bound_survivor_count.py` and `P2-bundle_survivor.py`
are valid but heavier in their high-`T` demonstration modes. Use their formulas
or reduce their demo parameters when quick reproduction is the goal.

## Verification Performed

Most recent local verification in this checkout:

```text
python model_analysis\birth_channel_research\arbitrary_freshness_kernels.py
  ok: visible nonces paid as address bits; fixed-universe target-churn
  round-trips but decays by pass 3 and loses -87.540 bits vs original payload;
  self-dating grammar best toy row is arity 2 residue 6 at 6.018e-05
  expected net bits/window
python model_analysis\birth_channel_research\typed_scheduled_tree_codec.py
  ok: depth-4 net_bits=+9; depth-6 net_bits=+107; raw fallback sanity ok
python model_analysis\birth_channel_research\scheduled_tree_codec.py
  ok: depth-2 forest net_bits=+41; raw fallback sanity ok
python model_analysis\birth_channel_research\bounded_bundle_codec.py
  ok: random and generated-dense fixtures round trip; dense asymptotic delta +11.918 bits
python model_analysis\birth_channel_research\quick_birth_channel_kernels.py
  ok: final-board, PCTB, singles, bundle, biased-seed, and recursion ledgers
python -m py_compile model_analysis\birth_channel_research\arbitrary_freshness_kernels.py model_analysis\birth_channel_research\typed_scheduled_tree_codec.py model_analysis\birth_channel_research\scheduled_tree_codec.py model_analysis\birth_channel_research\bounded_bundle_codec.py model_analysis\birth_channel_research\quick_birth_channel_kernels.py
  ok
cargo clippy --all-targets -- -D warnings
  ok
cargo check --features gpu --all-targets
  ok
```

Known verification blockers not introduced by this report:

```text
cargo fmt --all -- --check
  fails on pre-existing formatting in src/bin/v2_cost_probe.rs
python scripts\doc_lint.py
  fails: missing required file docs/ARCHITECTURE.md
cargo test --all-targets
  Rust/unit/integration tests pass until tests\doc_lint.rs, which fails on the
  same docs/ARCHITECTURE.md requirement
```

Executed successfully in this checkout:

```text
python model_analysis\birth_channel_research\arbitrary_freshness_kernels.py
python model_analysis\birth_channel_research\A-modular-orbit_invariance.py
python model_analysis\birth_channel_research\C-crt-clock_odometer.py
python model_analysis\birth_channel_research\C-crt-clock_frozen_coord.py
python model_analysis\birth_channel_research\P2-recursion-ledger.py
python model_analysis\proof_kernel\pctb_ledger.py
python model_analysis\birth_channel_research\P2-biased-hash_coupling_ledger.py
python model_analysis\birth_channel_research\typed_scheduled_tree_codec.py
python model_analysis\birth_channel_research\bounded_bundle_codec.py
python model_analysis\birth_channel_research\scheduled_tree_codec.py
```

Two heavier default demonstrations were started and then stopped because they
exceeded the intended "small kernel" runtime:

```text
python model_analysis\birth_channel_research\B-ambiguity-bound_survivor_count.py
python model_analysis\birth_channel_research\P2-bundle_survivor.py
```

They were stopped by exact command-line process targeting, not by broad process
cleanup.

# Total-Cover Telomere Crossover Results

Date: 2026-06-15

This branch fully rewrites every layer. There are no carried records, no
open/carry maps, no birth-pass tags, no sparse hit bitmaps, no final-position
notes, and no PCTB ledgers in these numbers. A record is only:

```text
[arity][seed witness]
```

The decoder reads records in order, reads arity, reads the witness, expands the
seed, and reconstructs the previous layer. Pass salt is allowed because every
record is born in the current pass, but the runs below do not need it.

## June 18 State-Carrying Salt Update

`model_analysis/birth_channel_research/H175-state_carrying_transducer.py`
tests the strongest decoder-derived salt variant:

```text
z = H(q_i, arity_i, seed_i)
x_i = z[:arity_i*B]
q_{i+1} = z[arity_i*B : arity_i*B+r]
```

This is compatible with total-cover because every record opens in order and
the decoder knows `q_i` before reading record `i`. Observing `q_{i+1}` from the
digest tail does not reduce match supply; conditioning a chosen tail class
does. The kernel measured `D=10,r=4` conditioned-tail ratio `0.064047`, close
to `2^-4 = 0.0625`.

This solves the salt-metadata part of total-cover, but not the witness-cost
crossover. Exact V1/J3D1 still expands in the tested powered toy rows
(`B4,K5,D12,atoms8` best `out/in=1.438`). The live total-cover target is now:

```text
state-carrying salt
+ bounded-slack surface lookahead
+ public width/rank language or custom witness mode
```

The first encouraging signal is that bounded-slack lookahead improves exact
two-pass cost in tiny rows without a selector (`B4,K5,D8,atoms8`, slack+4:
`2p delta=15.750` bits in `3/4` trials).

The sampled H175 trellis extension also shows why this is not solved yet:
`B4,K5,D12,items16` has pass-one support `1.0`, but the best `r=4,slack:4`
row completes only `0.05` of two-pass trials and `0.0` of three-pass trials
under exact V1/J3D1. The emitted record surface needs a better recursive
witness/width language.

## Method

The runnable model is [total_cover_lotus_crossover.py](./total_cover_lotus_crossover.py).
For every interval `i..i+k`, it samples the first matching seed rank under the
uniform hash law and converts that rank into a witness width. It then runs an
optimal non-overlapping full-cover DP over the whole line.

Source-of-truth V1 costs come from
`model_analysis/proof_kernel/costs.py::record_cost_for_payload_width(arity,
payload_width)`. V1/J3D1 rows use arities 1..5 only. `K > 5` rows are custom
total-cover witness modes with explicit arity alphabets.

Terminology:

- `B`: input atom size in bits.
- `K`: max arity.
- `D`: search frontier / maximum witness payload width.
- `gain/atom`: input bits saved per input atom.
- `gain/byte`: input bits saved per 8 input bits.
- `missing bits/record`: witness-cost reduction needed to reach zero when the
  row is negative.

## Crossover Summary

| Mode | First positive? | Best / nearest checked row | Result |
| --- | --- | --- | --- |
| free-boundary oracle | Yes | `B=24,K=8,D=192`, `+0.6133` bits/atom in coarse grid | Confirms the overlap/order-statistic crossover is real if seed boundaries are free |
| exact V1/J3D1 | No | `B=4,K=5,D=20`, `-1.3145` bits/atom, missing `4.985` bits/record | Current record format does not cross |
| extended J3D1 + fixed arity | No | `B=8,K=64,D=512`, `-0.3099` bits/atom, missing `9.917` bits/record | Larger arity helps coverage but J3D1 self-delimiting cost remains too high |
| global fixed seed width | No | `B=8,K=5,D=40`, `-1.5026` bits/atom in coarse width run | Discards the early-rank/order-statistic advantage |
| small global width classes | No | `B=24,K=64,D=1536`, `-0.1458` bits/atom, missing `8.000` bits/record | Covers with huge arity but does not preserve enough lucky-rank information |
| arithmetic-coded selected `(arity,width)` bins + payload | No after refinement | `B=24,K=8,D=164`, `-0.4075` bits/atom, missing `0.642` bits/record | Best parseable witness language found; close but still negative |
| whole-cover local payload stream | No | `B=8,K=64,D=120`, `-0.6180` bits/atom, missing `1.253` bits/record | Parseable, but worse than arithmetic-coded Lotus payload bins |
| canonical minimum-cover rule | No independent win | Bounded by the whole-cover stream unless output identity is otherwise known | Tie-breaking removes duplicate descriptions, not the witness stream |
| paid finite iid/Markov counts | No | `B=24,K=8,D=192` iid-count row: `-1.8824` bits/atom, missing `2.451` bits/record | Storing the per-file symbol/transition type is too expensive |
| public frozen iid/Markov model | No | `B=24,K=8,D=192` iid public row: `-0.1581` bits/atom, missing `1.109` bits/record | Honest zero-metadata model still has too much stream entropy |
| public factored arity+delta model | No | `B=4,K=128,D=512` factored row: `-0.0313` bits/atom, missing `3.518` bits/record | Near-flat by high-arity amortization, but later H7 improves it |
| public raw first-hit delta law | No | `B=4,K=128,D=512` H7 raw row: `-0.0119` bits/atom, missing `1.357` bits/record | Best analytic delta-law row before H11 |
| canonical fixed-slack width | No | `B=4,K=128,D=512` H9 slack-0 row: `-0.0123` bits/atom, missing `1.261` bits/record | Closest bounded paid miss so far; width is decoder-derived, but padding/supply loss gives the savings back |
| public selected-order-statistic delta law | No | `B=4,K=128,D=512` H11 train-selected `m16`: `-0.0178` bits/atom; frozen `m8` seed check: `-0.0180` bits/atom | Effective-choice law did not beat H7/H9 once frontier conditioning and profile selection were honest |
| neutral seed-multiplicity fertility | No as simple capacity bound | `B=4,K=128,D=512` H12 slack `-8`: perfect-credit upper bound `-0.0082` bits/atom, residual `0.746` bits/record | Same-width seed choice is real but too small; bloat buys neutral bits at roughly its own cost |
| joint selected-cover partition code | No | `B=4,K=128,D=512,N=128` H13 train-selected beta `0.5`, record-bias `-10`: `-0.0139` bits/atom, missing `1.586` bits/record | Whole-cover `logZ` coding returns to the H7 near-miss zone but does not cross |
| trained public CRF selected-cover code | No | `B=4,K=128,D=512,N=128` H14 fixed profile: `-0.0155` bits/atom, missing `1.981` bits/record | Learned public features did not beat H13/H7 once `logZ` paid |
| recursive best-of-pass selection | No under uniform law | H15: paid pass/profile selector restores `Pr[L<=n-s] <= 2^-s` | Recursive pass search is one final lossless code once decoder-visible metadata is included |
| non-uniform public interpreter escape | Outside original uniform claim | H16: saving `128` bits on `90%` of a 1024-bit source needs about `115` bits entropy deficit and `3e38` average lift | Can be legitimate source-shaped compression, but not content-blind roughly-all-data compression |
| public position / active-lane salt schedule | Parseable, not positive by itself | H26: `r=0.10` boundary/open `0.000199`, hidden subset/open `4.689956`, public lane loss `3.321928` | Position can make stateless salt/placement clean, but compression needs value/count separation |
| orderless / confluent decode | Parseable only with public destinations | H27: `m=1,000,000` bag order cost `18.488885` bits/record; B4 value-order `3.999863` bits/atom | Sorting/multiset decode moves the bill into permutation or match-supply entropy |
| public fertility class | Target only | H28: class fraction `f` crosses only if `value_lift > log2(1/f)`; uniform lift is `0` | Best biology-shaped target; requires public value/count separation, not uniform hash independence |
| cover-equivalence collective code | Witness improvement, not all-data win | H29: `N=12,B=1,K=4,D=8` saves `7.210305` bits vs best local cover, but averages `26.245017` bits for 12-bit raw | Clean stateless soft-min over all covers; becomes a public source prior |
| public reversible dither | Freshness scaffold only | H30: fixed schedule has `0` entropy change; best-of-`P` costs `log2(P)` selector bits | Can refresh target bytes without per-record birth tags, but not a compression source |
| coset/syndrome witness | Stateless repair, conserved | H31: full syndrome gives `k+(n-k)=n`; low-weight residual savings equal tiny coverage; omitted residual needs scaling referee | Moves missing entropy into residual/checksum unless residual has future fertility |
| bits-back latent reservoir | Implementation scaffold | H32: posterior tape is conserved; positive rows require `gamma>1` value per tape bit | Best combined architecture is H29+H30+H28, not a new uniform escape |
| de Bruijn / universal tape | Match guarantee, conserved | H33: full `L`-bit coverage needs `L` coordinate bits; shorter addresses have support `2^(a-L)` | Useful deterministic seed scaffold, not all-data compression |
| XOR/fountain superposition | Stateless order-insensitive record, conserved | H34: sparse `k`-XOR misses most targets; full coverage selector reaches raw entropy; multiplicity is bits-back tape | Useful search/decode primitive, not all-data compression |
| confluent normal form | Stateless out-of-order decode, paid order | H35: public normal form is free; arbitrary ready subset costs `log2 C(N,m)`; arbitrary order costs linear-extension entropy | Useful placement machinery, not all-data compression |
| developmental attractor / canalization | Stateless biology-shaped source language | H36: `g` genotype bits cover at most `2^g` phenotypes; attractors need inverse branch; basin priors compress source data but penalize uniform controls | Best DNA analogy; requires source entropy deficit / `gamma>1` |
| d-choice self-routing | Useful threshold reducer | H37: public lane tax becomes `-log2(1-(1-r)^d)`; for `r=0.10,d=8`, tax falls to `0.812` bits; exact destinations/order still paid | Helps fertility lanes, not arbitrary placement |
| combined fertility-lane threshold | Sharp source-shaped target | H38: H18 + public lane gives `gamma_needed = 1.195 + lane_loss/3.819`; `r=0.10,d=16` needs `gamma=1.273`; standalone class needs only `0.296` bits lift | Lowers target, still needs measured source value |
| two-layer fertility source | Source-shaped positive control | H39: `r=0.10,d=16` lane tax `0.296`; source row measures `E[V|C]-E[V]=0.448`, net `+0.153`; uniform control net `-0.293` | Constructive adjacent premise, not uniform all-data |
| EOF / whole-file length code | Legal small side channel, not recursive | H40: fixed-board trim saves `~1` bit with `H(length)~2`; optimal EOF one-to-one code saves `<2`; shrinking board needs `~2` bits/pass length ledger for `~1` bit/pass savings | Real final-file constant only when length/bit EOF are public |
| position / ready-prefix compaction | Useful decode geometry, paid selection | H41: `N=1e6,R=1e5` boundary/open `0.000199` but hidden subset/open `4.689860`; `R=999k` subset/open `0.011413` | Position can signal public readiness/salt; content-selected sparse hits still pay the subset |
| systematic response surface | Next research protocol | H42: `r=0.10,d=16` lane loss `0.296`; `P=256,eps=0.01` exception ledger `0.160737` bits/atom; H7 miss `1.357` bits/record | Future ideas should move a named axis: coverage, lane loss, witness gap, or value lift |
| forced rewrite target surface | Target clarified | H43: H7 `2 bits/record -> 0.017578 bits/atom`; H7 exception budget at `P=256` for `1.357 bits/record` is `eps <= 0.00059161`; ideal option dividend at `K=128` is `13.011` bits | All-block replacement removes birth/open entropy; paid witness margin remains the target |
| normalized collective cover | Stateless whole-cover prior, conserved | H44: `N=12,B=1,K=4,D=8` normalized public `Q` averages `12.221970` bits for 12 raw bits | Duplicate covers help selected witnesses/source priors, but normalized uniform average stays >= raw |
| neutral selection fertility | Genetics-shaped but conserved under uniform law | H45: neutral `b=3.819` gives uniform-tail selection `gamma=0.839`; H18 needs `gamma>1.195` | Neutral same-cost seed choices are real, but best-of-M future fertility is at most one-for-one unless source-shaped |
| high-arity option statistic | Real local dividend, paid selector still active | H46: `K=128` gives `M=8256`, ideal `log2 M=13.011`; H7 miss `1.357` bits/record needs only `2.562x` extra effective choices | Good scientific target; cannot count `log2 M` twice without paying the winning option/cover |
| frozen public residual law | Parseable but worse | H47 bounded calibration: train-selected `m1/arity_bucket`, held-out `-0.089252` bits/atom, missing `7.030` bits/record | More table shape overpays residual/support entropy in this form; not the missing 1.36 bits |
| seed-grammar arity embedding | Arity derivable, boundary still paid | H48: non-parseable fixed-width lower bound `+0.217773` bits/atom; best parseable seed grammar `-0.124392` bits/atom, missing `9.798` bits/record | Moving arity into seed space becomes seed-supply thinning plus self-delimiting witness cost |
| all-block renormalization | Fresh dice yes, paid shrink no in tested target | H49: `B=4,K=128,D=512`, 5 passes; H7 geometric `rho=1.007854`, H9 `rho=1.008051` | Total-cover rewrite removes birth/open entropy, but recursive compression needs held-out `E[log rho] < 0` |
| repeated-pass RG sweep | Oracle crosses, paid still misses | H50 corrected high-arity sweep: best paid `B=4,K=128,D=512,H9 slack0`, `mean log2 rho=+0.004884`; oracle same config `-0.007947` | Gives `K>=128` enough atoms; remaining gap is paid witness boundary/selector, not freshness |
| normalized Q reproduction | Legal collective witness, uniform excess positive | H51: best exact row `N=10,B=1,K=4,D=10` has `avg bits=10.118241`, excess `0.118241`, escape alpha `0.00` | `Q` removes selected-cover metadata for source-shaped data, but normalized uniform average stays above raw |
| fixed-slack percolation RG | Faster high-K H9 scout, still positive | H52: best strict rows `B=4,K=192,D=768,s0` `+0.003658`; `B=4,K=256,D=1024,s1` `+0.003775` mean log2 rho | Larger K/slack moves the frontier slightly, but strict fixed slack still expands |
| paid global slack ladder | Stateless only with selector charged | H53: `B=4,K=192,D=768,S={0,1,2}` gives paid `+0.004480` and unpaid lower-bound `+0.001973` mean log2 rho | Adaptive slack is not free unless a unique decoder invariant is proven |
| selector referee budget | Finite, not arbitrary-pass | H54: with `lambda=32`, `C=256,S=3` buys `141.328` global selectors; `P=256` is over budget by `181.750` bits | Checksum can referee bounded profile sequences, not unbounded recursion |
| self-sync slack syntax | Decoder trick, too expensive as arity grammar | H55: Fibonacci/prefix toy languages have `0` ambiguous slack streams; H56: `B=4,K=192` fibonacci headerless `+0.023081` mean log2 rho | Syntax can derive slack, but delimiter bits exceed the current gap |
| normalized collective-Q percolation | Closest log-rho miss, expected bits still positive | H57: `B=4,K=384,D=1536,N=384` has `+0.000166` mean log2 rho and `+1.426544` expected excess bits | Latent covers attack witness-boundary entropy, but normalization returns the uniform savings |
| frozen public-Q arity model | Best expected-excess frontier, still positive | H58: `B=4,K=384,D=1536,N=384,bucket` held-out `+0.229195` expected excess bits and `+0.000215` mean log2 rho | Public training helps, but KL keeps uniform expected length above raw |
| raw/Q stop mixture | Legal fallback, chooses raw or misses held-out | H59: `K384,T=1` train picked `alpha=0.2` but eval excess `+0.053411`; `T=4` picked `alpha=0` | Fully priced raw escape/stopping does not convert minority Q wins into all-data compression |
| recursive shrink converse | EOF/best-of tricks collapse when paid | H60: EOF can shrink almost all fixed-length inputs by 1 bit one-shot; `n=4,P=2,s=1` best-of-4 is `16/16` free vs `4/16` paid; `S=128,c=0.90` needs `114.731004` bits entropy deficit | Variable recursive savings require length path; roughly-all uniform savings are counting-forbidden |
| scientific phase diagram | Systematic next-target ranking | H61: closest public-code misses are H59 `+0.000139` bits/atom and H58 `+0.000597`; nearest paid witness miss is H12 `0.746` bits/record / `0.008196` bits/atom | Uniform candidates need a public invariant; source-shaped candidates need measured fertility/value lift |
| source fertility phase | Constructive non-uniform target | H62: public class `f=0.10,a=2` crosses H59/H58 atom misses at `c*=0.1454/0.1458`; H7 atom at `c*=0.1554`; H7 witness with `f=0.10,a=8` needs `c*=0.6822` | DNA-like branch requires a recursive public fertility invariant, not file-specific patterns |
| recursive fertility invariant | Current constructive route | H63: with `p_OF=f`, H59/H58 atom targets need `p_FF=0.4122/0.4141`; H7 atom `0.4565`; H7 witness needs `0.9534` | Whole-cover/public-Q atom crossing looks much more plausible than paying local record gaps through source fertility |
| repeatable non-prefix path ledger | EOF recursion separator | H64: `n=128,s=1,P=64` stateless variable fraction `1.084e-19`; path-free apparent `0.535193`; average path bits `114.186748` | EOF/final-board variable shrink needs a length-path channel; fixed public paths lose coverage exponentially |
| public invariant exhaustion | No uniform escape found | H65: `n=16,P=4,s=1` variable path apparent `0.989365` vs charged `0.124985`; paid best-of profile also returns to `0.124985`; public lane charged `0.012498` | Public invariants reduce to visible final-state capacity; excess is hidden path/profile/phase or finite checksum budget |
| all-block cover entropy bound | High-arity option dividend priced | H66: `K=128` local option dividend `log2 M=13.011`, but cover-shape entropy is `~1 bit/atom`; current paid misses are only `0.000139-0.012314 bits/atom` | The high-arity reservoir explains closeness, but content-selected cover choice is not free |
| typical drift / rare blowup | Negative log-rho guardrail | H67: with `a=0.99,eps=0.01`, `E[log2 rho]=-0.004427` but `Pr(>=1 blowup)` is `0.474404` by `P=64` and `0.923685` by `P=256` | Repeated-pass rows need both geometric drift and tail/blowup accounting for roughly-all arbitrary-P claims |
| public-code martingale audit | Optional-stopping trap made finite | H68: spiky public Q has `excess +0.336062`, lane Q `+0.419518`, raw/Q `.75` `+0.047701`, all with `E[W]=1`; hidden best-of gain `1.009249` bits | Public Q can move winners, but uniform expected length stays >= raw unless selector/source is hidden |
| rank-width sampling bias | Measurement correction | H69: old 49..512-bit span sampler rounded rank before widthing, overcharging by `+1.000000` payload bit/record; runner now keeps log-rank width | Future high-K refinements should use corrected sampling; not enough alone to prove uniform crossing |
| systematic response protocol | Scientific method for next lanes | H70: witness gaps need `1.677x-2.562x` effective choices/record; public lanes need d-choice thresholds; source rows need `c*` and `p_FF`; drift rows need tail caps | Future candidates must name the moved knob, paid currency, control, and stop rule before testing |
| finite-pass coverage frontier | Sharp roughly-all-data K bound | H71: at `90%` uniform coverage, max `>=1 bit/pass` is `K=0` for prefix/self-delimiting streams and `K=1` for the generous EOF one-shot bound; `>=2 bits/pass` gives `K=0` even with EOF | Structure-free maintained positive-rate recursion over arbitrary `P` is impossible unless a premise changes |
| public-Q / visible-state converse | Best-of/final-board/checksum selector audit | H72: for `n=16,S=4`, 16 free profiles cover `1.0` of inputs, but paid profiles return prefix coverage to `0.0625`; finite referees only buy finite uncharged profile bits | Final boards/profiles/checksums are valid only when their state identity is counted in output length or paid elsewhere |
| final-state entropy kernel | Egg-carton/position geometry priced | H73: `N=12,R=4,P=8` sparse ready+birth needs `20.951` hidden bits; `Q=N` occupancy has `8.951` bits, `Q=N*P` occupancy has `21.664` visible bits | Geometry can solve stateless placement, but arbitrary content-selected birth/open facts become visible coordinate entropy or supply loss |
| exact latent whole-cover Q | Strongest collective witness tested exactly | H74: exact domains show duplicate-cover gain `2.64-3.42` bits and favored fractions `0.036-0.255`, but uniform `Q` excess remains `+1.37` to `+6.80` bits and best raw/Q alpha is `0.00` | Latent whole-cover Q is the clean source-shaped witness language, not a structure-free uniform escape |
| rare-blowup coverage ledger | Statistical bad-tail loophole priced | H75: `c=0.90,P=64,s=1` needs losers to average `576` expansion bits and per-pass bad-tail `eps<=0.001645`, but prefix/EOF coverage bounds are only `5.421e-20` / `1.084e-19` | Rare blowups can pay mean length, not create enough short outputs; also violates Telomere bounded-loss when unbounded |
| randomized codebook ledger | Public/private randomness and compute priced | H76: for `90%` coverage at `P=64,s=1`, best-of needs about `2^63.848` prefix profiles, which costs `63.848` selector bits; paid coverage returns to `2^-64` | Randomness is either fixed public Q, paid selector state, or non-decodable private state |
| self-induced fertility | Internal public source-law test | H77: abstract `f=0.10,a=2` rows need `c*~0.145` and `p_FF~0.41`; exact H74 top-10% high-Q class needs `c*~0.508` and `p_FF~0.903`, while uniform starts at `0.10` | Telomere-output fertility is a possible source-shaped target, but not a structure-free all-data escape |
| master no-go audit | Unified theorem boundary | H78: after charging visible state, content-blind coverage obeys `c<=2^-S` prefix or `c<=2^(1-S)-2^-n` EOF; at `c=0.90,s=1`, max `K=0` prefix and `K=1` EOF | Maintained positive-rate arbitrary-pass recursion requires relaxing content-blindness or finding a public invariant outside the count |
| d-choice fertility conservation | Public-lane accounting split | H79: `r=0.10,d=23` gives apparent `+2.475` class-bias bits if witness fertility is charged at placement loss, but honest witness multiplicity gives `-1.914` bits | Public d-choice is still useful for position/salt geometry; it is not a free record-value fertility source |
| public-Q fertility lane | Exact finite source-shaped class sweep | H80: in exact `B=1,N=12,K=6,D=8`, uniform excess is `+1.814795` bits; `f=0.25` high-Q class has `Q(F)=0.7787` versus scaled-H7 `c*=0.7247`, with shuffled controls losing the lift | A gentler public high-Q source class is a sharper target for a real self-fertile rewrite rule, but it remains source-shaped rather than roughly-all uniform |
| output whitening vs fertility | Recurrence law after coding | H81: entropy-coded `Q` saves `1.365` bits but drops `top25` next membership to `0.25`; visible `Q`-shaping restores `0.7787` but costs `1.365` bits, net zero before record costs | The remaining target is native compact Telomere syntax that is already fertile, not entropy coding followed by paid reshaping |
| syntax support capacity | Native valid-subset check | H82: top25 has `Q(F)=0.7787`, support tax `2.000`, membership dividend `1.639`, net `-0.361`; `F_positive` net `-0.351` | Declaring fertile strings valid is not enough; a surviving syntax needs a full graded probability law over record strings |
| length-preserving relabeling | Native syntax permutation check | H83: for top25 and `F_positive`, identity already maximizes `Q(F)`; bottom/random classes can be made fertile only by choosing a different profile/class, e.g. `log2 C(4096,1024) ~= 3316.9` bits | Frozen relabeling is not the missing mechanism; the remaining target is a graded public record law |
| graded native law | One-shot versus invariant source law | H84: tilted `lambda=0.90` gives `Q->R` saving `0.216226` bits with `R(top25)=0.738867`, but invariant `R->R` saving is exactly `0` | Graded Q-family laws can transition but do not recurse; the next target is high-entropy fertility/value-count separation |
| entropy-budget fertility | Ideal value/count frontier | H85: under the uniform future-value tail, a `0.017703`-bit entropy budget can buy a `0.216226`-bit finite margin; `delta=1.365022` can buy lift `2.9626` | High-entropy fertility is mathematically plausible, but must be measured in native syntax with uniform controls |
| native value tail audit | Measured H80 fertility ROI | H86: measured H80 score needs only `0.005205` entropy bits to buy a `0.216226` future-value margin; H84 `R0.90` has `lift-delta=1.803832` | The soft-tail target is promising, but still needs a fixed parseable record language that emits it without hidden profile/selector/reshaping cost |
| native soft cycle ledger | Source cycle versus uniform startup | H87: tiny H58 threshold row `delta=0.005579` is canceled by `shape=0.005581`; stronger soft law `delta=1.158938` has `startup H58=1.450744` only if score lift becomes real witness savings | Soft-law cycles remain source-shaped targets; uniform all-data still needs an actual witness-saving theorem |
| frozen soft grammar overhead | Fixed public type-class parser | H88: public type class at `theta=1.05,m=32768` gives `bill=1.734528`, `lift=3.295267`, `eta=1.560740`; best `m<=512` is still negative | Parseability/profile cost can be made honest at large public block sizes, but this only validates the grammar channel, not second-pass compression |
| actual witness savings | Hard check of H88 value score | H89: `E_U paid_saving=-5.022461`, `E_Q paid_saving=-1.005994`; best finite score-law cycle `-2.530640`, best oracle-saving cycle `-2.397156` | `log2(Q/U)` is aligned with real witness savings but insufficient; the next target is actual witness-cost fertility, not another score proxy |
| witness Kraft variational bound | Public-law cap for fixed witnesses | H90: `sup_P E[S]-D(P||U)=log2 Z`; selected `Z=0.221606134` gives `-2.173930`, collective `Z=0.676912187` gives `-0.562959` | Better tilts cannot cross for a fixed witness family; the mechanism must increase honest Kraft mass or pay a new visible invariant |
| witness Kraft boost budget | Exact missing bits to cross | H91: selected needs `2.173930` flat bits/word or `1.086792` bits/record; collective needs `0.562959` flat bits/word or `0.277599` bits/record | Collective/all-description coding is the nearest constructive target; any claimed breakthrough must source about `0.28` honest bits/record in this toy |
| K/D witness Kraft sweep | Higher arity/deeper search lower-bound scout | H92: optimistic `K>5` extension crosses collectively; best lower-bound row `K=8,D=12` has `log2 Z_total=1.001339`, while best selected remains `-0.681489` | Higher arity/deeper search can move the frontier, but these crossings omit Lotus width metadata and are not paid codec results |
| paid extended-arity Lotus sweep | K/D anti-reward-hack check | H93: with fixed arity bits plus paid J3D1 width, all K/D crossings disappear; best paid collective row `K=12,D=12` has `log2 Z_total=-5.301885` | The H92 crossing was underpriced witness metadata; K/D alone does not solve the paid witness Kraft wall in this toy |
| normalized rank witness sweep | Custom arithmetic width/record coding check | H94: normalizing seed-width multiplicity removes the H92 crossing; best `custom_rank` `log2 Z_total=-2.188694`, best `custom_record=-1.781751` | Arithmetic rank coding is cheaper than Lotus but still pays the hidden width-class channel; better width coding alone is not enough |
| biased native expander conservation | Fixed public generator law check | H95: fertile-biased seed laws move mass toward future-fertile strings, but paid V1 total-cover `log2 Z=-11.885765` is identical for every tested law | Bias changes which strings win; it does not create new honest Kraft mass, so source-shape/recurrent-fertility still has to be paid or made invariant |
| neutral transfer operator | Visible genotype/fertility check | H96: exact `B=1,N=5,K=3,D=3` enumeration shows neutral choice gives `+5.659472` future lift over random same-length record strings, but best two-pass cycle is `-60.307024` and no word is positive | The DNA-like neutral-network signal is real but currently source/fertility-only; paid visible record strings do not produce all-data recursion |
| sampled neutral transfer sweep | Larger visible genotype search with controls | H97: sampled rows improve from `-60.307` to `-39.502` bits/word as `N/K/D` grow, but `log2(m)` net stays negative and best-of-same-budget random same-length controls beat selected genotypes in every row | Neutral-transfer search is not yet a public recurrent grammar; current lift looks like ordinary best-of-visible-string luck |
| partial slack refresh | Sparse +1/+2/+4 bloat refresh priced | H98: best unpaid row `v1_B8_K5,s0` has `mean log2 rho=-0.000706` but final fresh fraction `0`; best unpaid row with `>=10%` fresh has `+0.014129`; best H2 lower-bound paid row has `+0.007534`; best literal rewrite has `+0.346924` | The refresh lattice exists, but the alleged recursive gain disappears when readiness/carry state or literals are priced |
| partial-refresh Pareto frontier | Sweet spot isolated to width/boundary syntax | H110: parseable J3D1 best `q>=10%` row is `+0.524497` bits/atom, but local-width oracle best `q>=10%` row is `-0.111979` bits/atom; zero-arity oracle is `-1.472656` | The match lattice has enough option pressure; the current parseable payload-width/boundary bill spends it |
| collective width stream | Width histogram channel isolated | H111: local oracle `-0.118750`, counts-free enum `-0.073289`, but count-paid enum `+0.147041`, fixed-delta `+0.127344`, and J3D1 `+0.168652` bits/atom | Collective width coding improves J3D1, but the selected per-file width/delta law is still a hidden channel unless a public frozen model replaces it |
| frozen width/delta law | Public model check for H111 | H112: `B4_K16_D64,slack=4,q>=10%` held-out rows stay positive: global `+0.2531`, arity-bucket `+0.2907`, target+arity `+0.3163` bits/atom | A frozen public law does not replace the per-file histogram in the ordinary H2-charged branch |
| seed parity readiness | Paid seed-class channel | H99: even/odd is a legal two-epoch discriminator costing `1` bit/record; exact `64`-epoch birth classes cost `6` bits/record as seed-supply loss or residual ambiguity | Seed rejection can move readiness into seed grammar, but it is not a free many-pass birth/open channel |
| seed-class partial refresh | Parity replaces H2 only under finite age | H113: fixedD + two-epoch parity repeats at `B4_K32_D128,slack=2,q>=50%` with `+0.023438` bits/atom; local oracle is negative; 64-epoch parity fails | Visible seed class is a real stateless readiness channel, but only with mandatory old-cohort refresh/literalization |
| frozen delta + two-epoch parity | First paid partial-refresh target | H114: `B4_K32_D128,slack=4,global` held-out `-0.020876` bits/atom; 32/64 repeats across four seeds stay negative `-0.013144/-0.008421/-0.009607/-0.004403` | Promising custom target: no H2 map or per-file histogram, but requires a parseable record layer and strict two-epoch invariant |
| two-epoch record-layer audit | H114 age/length channel priced | H115: one-pass raw lower bound still `-0.005424`, but 4-pass `force_refresh` is `+0.020909` bits/atom/pass; invalid `no_expiry` is `-0.014058`; local oracle due-refresh is `-0.047175` | H114 underpriced heterogeneous record-layer due refresh; next target is a public width law for forced due-cohort refresh |
| public width-law search | H115 next target tested | H116: best focused public row `arity` at 128 atoms is `+0.023659` bits/atom/pass with `0.25` fail; hidden `target_lane_arity` public-lane diagnostic is still `+0.021842` | Simple public clocks and bucketed hidden target/age contexts do not recover the local-width oracle; next target must change the witness family or make interval composition public by a priced lane/board invariant |
| parseable width-symbol stream | Delta parser circularity priced | H117: honest `[arity][width][payload]` row `H114_raw_lower,lane_due_arity` is `+0.007218` bits/atom/pass at 128 atoms, but rewrites only `0.124` raw fraction; forcing `0.25` rewrite gives `+0.061297`, and `0.50` has no finite small-sweep path | Width symbols are parseable and near-flat only by doing little work; delta buckets remain optimistic unless target length is separately visible and paid |
| collective width amortization | Histogram loophole priced | H118: count-free scale-1 enum crosses at `-0.005928` bits/atom/pass, but scaling the same distribution to 1024 gives `+0.025875`; exact count-paid scale 1024 is `+0.026359` | The short-sequence count-free crossing is a hidden small-count artifact; large-file width entropy is still about `2.26` bits/selected record |
| public fixed-width lanes | Width made public/deterministic | H119: sparse global rows can show `-0.003906` bits/atom/pass while rewriting `<6%`; at `min_rewrite=0.25`, public exact/lane rows expand, best public-lane lower bound `+0.020833`, hidden target-size row `+0.023438` | Making width deterministic trades entropy for padding and match-supply loss; even hidden target-size buckets do not rescue fixed-width lanes |
| width-channel equivalence | Boundary hiding audited | H120: with H118 seed, scale-1024 enum/seed-class/referee converge around `5.34` bits/record; checksum64 covers only `~12` width decisions | Explicit width bits, seed-class supply loss, self-sync prefix syntax, and checksum ambiguity are the same currency unless the width distribution changes |
| public gap typed board | Public target length lower bound | H121: even with `T_pub=actual target length`, `min_rewrite=0.25` fails for gaps 1..16; at `0.10`, gap 4 expands `+0.007812`, gap 5 is flat with `0.50` fail | Public target length plus fixed gap is not enough; small gaps lack savings and large gaps lose due-refresh supply |
| public gap alphabet | Paid small gap class | H122: H114 rows miss; public-lane lower bound gets negative finite rows only with `0.75-0.84` fail; best wider alphabet is `+0.001674` bits/atom/pass with `0.125` fail | Gap alphabets improve supply versus fixed gaps, but gap bits, padding, and nonzero stale-failure risk still prevent a maintained-refresh crossing |
| self-consistent width law | Paid +1/+2 refresh sweet spot check | H132: public `arity` mini row `+0.024703` bits/atom/pass; public `lane_due_arity` focused row `+0.041360`; hidden `target_arity` diagnostic stays positive at `+0.017235` to `+0.026024` | Allowing small bloat and selecting with frozen width entropy refreshes due records, but the paid width stream still exceeds the lattice gain |
| common-cause batch witness | Shared-boundary batch audit | H133: honest `batch_only m=2` has `log2Z=-2.897549` vs base `-1.781751`; best valid mix chooses the base; `m=2,discount=2` crosses only with overfull `log2 symbol mass=2` | One base deriving many independent children is just Kraft convolution; boundary savings by fiat is hidden overfull code mass |
| modular readiness clocks | CRT/pass-clock audit | H134: `P=4096` best small CRT row uses `(8,19,27)` with cost `12.002815` bits vs ideal `12`; `P=2` parity costs exactly `1` bit | CRT/even-odd clocks can be efficient state labels, but they do not beat `log2(P)` unless a separate invariant bounds lifetime |
| recurrent transfer operator | Fertility-transfer harness | H135: exact `N=3,K=1,D=1` two-pass control has `fail=1.000000`; richer exact rows became expensive because pass two targets visible record strings | Endogenous transfer still needs a native visible language or transfer-matrix proof that keeps support while charging visible length |
| batch footprint mask DP | Egg-carton footprint audit | H136: valid `all_masks_normalized K=4` reaches only `log2Z=0`; `all_masks_free K=4` reaches `log2Z=21.656226` with invalid local mass `log2=7.857981` | Public non-contiguous footprints solve placement/order, but compression appears only when footprint choice is unpaid |
| bits-back salt flywheel | Posterior tape salting audit | H137: balanced `P=4096,gap=0.25,tape=salt=64,gamma=1` gives `net=-1024`; unbalanced `P=64,tape=64,salt=8` pays `3584` final settlement bits | Bits-back can make salt consumption stateless, but the reservoir is conserved; positive slope requires separate `gamma>1` fertility |
| bounded reset ratchet | Rare reset bounded-loss audit | H138: at `P=4096,eps=0.001,s=1`, net/pass is `0.236847` but half-rate probability only `0.128861`; 90% half-rate requires `eps<=5.144e-5` | Resets cap damage but destroy accumulated shrink; arbitrary-pass roughly-all savings require reset probability `O(1/P)` |
| reset/ratchet converse | Short-output support audit | H139: `P64_s1_c90` has prefix support `5.421e-20`; visible 64-bit state reduces charged saving to `0`; hidden `2^32` best-of returns to `5.421e-20` once paid | Reset, stop, and ratchet claims do not create high-coverage savings unless another mechanism supplies vanishing reset probability or real fertility |
| slack-refresh supply bound | +1/+2 option-pressure audit | H140: local-width oracle `B4,K5,s2` gives `q=0.999877`, but exact J3D1 `B4,K32,s2` gives `q=0.342932` with `H2/q=2.704901`; `q>=50%` is not reached by `K=4096` | The user's bundle-option multiplier is real, but parseable width/boundary syntax and ready/carry layout consume the apparent crossover |
| seed-boundary Kraft converse | Residue/self-delimiting width audit | H141: best seed-derived boundary collapses to a public fixed-width lane; `B4,K32,delta=-1` gives `q=0.393469` and `partial+H2=+0.954706`; `q>=0.90` needs `delta=+2` | Seed residues, trailing patterns, and canonical self-delimiting witnesses cannot recover the overfull local-width oracle |
| intrinsic boundary optimizer | Optimal width-class audit | H142: H120 pooled row needs width entropy `<=1.540537` bits/record to cross; optimal Kraft loss is `H(W)=5.341012`, and even a half-entropy `2.670506` profile still gives `+0.040829` bits/atom/pass | Hiding payload width in seed classes, residues, or terminators cannot beat the measured width entropy floor |
| near-total public-board bound | Public opening envelope | H143: exact J3D1 `slack<=2` tops out at `q=0.342932` vs required `q~=0.999`; `slack=8` reaches near-total but still expands, e.g. `B4,K128` total `+0.032630` bits/atom | Public board geometry solves status, not compression, unless a separate witness/fertility law makes near-total openings net-negative |
| non-greedy lookahead value | Superposition/future-fertility target | H144: easiest slack-8 rows require `mu=0.008625-0.040116` bits/atom/candidate of real future value to offset current bloat | Non-greedy search is live, but must be proven by recurrent transfer with same-budget random controls |
| unfold-depth stop ledger | Multi-step seed unfolding audit | H145: 90% coverage with `G` saved bits needs about `2^G*2.302585` stop candidates and `G+1.203254` stop bits if stored | Long unfolding trades compute for coverage only when stop depth is public or paid; stop/referee bits otherwise return the saving |
| slack superposition transfer | Exact non-greedy visible-genotype check | H146: full-cover tiny rows remain negative; `N6,K5,D7,s14` has future-vs-random `+0.621127` but two-pass total `-29.390338` bits/word | Non-greedy visible selection is real and not a side channel, but current bloat dominates in the exact tested family |
| upward detour collapse | Larger-intermediate counting bound | H147: fixed stateless paths collapse to final address count; 90% exact-length coverage at `G` saved bits needs `G+1.203254` branch bits if hidden branches are used | Upward paths are valid search, not free decode capacity; the good branch must be public, visible, or paid |
| two-pass selected stream | Actual recurrent support check | H148: `N4,K4,D7,slack12` has pass1 coverage `1.000000` but selected two-pass coverage `0.000000` | Replacing collective future score with a real selected second pass loses support in the exact toy; next target is a transfer-matrix/DP |
| decode-composition capacity | Fixed public multi-pass decoder audit | H149: `B1,K16,D4` has 476 valid top streams but only 3 two-pass-composable streams and 0 three-pass streams; `B1,K32,D3` drops 980 to 1 at two passes | The bottleneck is self-parse closure: intermediates must land back in the record language, or a branch/repair channel is being hidden |
| selected-stream min-plus DP | Exact non-greedy P=2 transfer without brute force | H150: `N4,K4,D7,slack12` reproduces pass2 coverage `0`; `slack20` reaches `0.625` support but mean final length is `29.1` bits for a 4-bit word | Future-fertility scoring must become cheap recurrent closure; support slack alone buys bloat, not compression |
| closure Kraft ledger | Parseable-intermediate support priced | H151: forcing intermediates into valid record streams costs multi-bit match-supply tax; `B1,K4,D7,t12` tax `5.415037`, `B4,K128,D16,t64` tax `10.019899` | Closure by subset restriction is too expensive; prefix-complete/literal repair buys support by raw-length bloat |
| superposition gap ledger | Non-greedy visible path versus hidden cloud | H152: `N6,K5,D7,slack18` gains `1.890625` bits over greedy, but explicit final stream is `41.593750` bits for 6 input bits and cloud gap is `7.868868` bits | Greedy wastes real option value, but discarded alternatives are a paid rank/arithmetic channel unless the final visible witness itself gets shorter |
| cloud Q conservation | Honest public arithmetic version of the cloud | H153: focused rows normalize to `Q` with uniform excess `+1.456567` to `+2.831486` bits; best raw/Q mixture has `alpha=0` | The cloud can guide search or serve source-shaped public Q, but it is not a free roughly-all uniform recursive compression channel |
| fixed-cell closure phase | Parseability by construction | H154: every output cell parses, but best grid row touches only `12.9149%` of cells and expects `111.468915` untouched cells out of 128; `C8,K128` expects `126.998037` untouched cells | Free closure spends the seed-address budget inside each cell; match rate starves before full cover can form |
| closed-lane non-greedy target | Public-lane base miss versus visible lift | H155: as a cross-domain target ledger, H152 `N6,K5,D7,s18` visible lift exceeds H105 `custom_record K6,D12` base gap by `0.108874` bits/word, but closure stress raises the miss to `+8.624339`; closure+width stress leaves best stacked row `+22.798591` bits/word | Best constructive signal so far: non-greedy lift is large enough to matter, but a real solution must internalize or make unnecessary width/closure bills without a hidden cloud or fixed-cell seed starvation |
| completion seed-mass tradeoff | Prefix completion/filler closure | H156: completion can cut parse tax to `0.142019` bits, but that row is `99.3534%` filler; `seed_closure_tax = completed_parse_tax + seed_preservation_tax` restores the H151 bill | Prefix completion is valid parse engineering, but it trades closure tax for seed thinning or literal/raw bloat rather than maintaining fresh match rate |
| recursive selected-stream DP | Closed seed-bearing recursion | H157: P2 can reach full support in tiny exact rows, but final streams are far longer; `N4,K4,D4,P2` stores `39.187500` bits for a 4-bit target, and loose `N3,K3,D3,P3` support is only `0.375000` with `117.000000` final bits | Lawful non-greedy recursion still expands in the tested closed language; the missing piece is a closed seed-bearing sublanguage with entropy rate below raw |
| opening referee scaling | Keep-what-decodes ambiguity measured | H158: in the Robin proof model, checksum winners are unique in tiny rows, but distinct pre-checksum outputs reach `180` at `N=4,T=4`, requiring `7.491853` referee bits before safety | Trial decode is a valid finite stateless rule; unbounded use needs a proof that ambiguity stays O(1) or an explicitly paid/refereed growth channel |
| seed-bearing closed core | Recurrent record-to-record language | H159: corrected H96 graph finds no recurrent SCC and no shorter predecessor; `K5,D3,cap28` has `21,387` nodes, `283` edges, `srcTax=11.895128`, `scc_nodes=0`, `shortF=0` | The tested seed-record language has sparse one-way closure, not a maintained recursive compression core; next version should use a prefix-safe transfer matrix |
| seed closure transfer matrix | Product-parser closure mass | H160: matches H159 closed counts (`K5,D3,cap28 -> 283`) and prices closure at `clFrac=0.000258`, `clTax=11.918435` bits, with `0` compressive closed paths and `bestG=-11` | H96 bit-level closure is both tiny and non-compressive; next viable closed-core test must be item-level, where records emit self-delimiting items rather than raw bits |
| item-level closure economics | SPEC-style item targets | H161: strict `seed_only` arity-2 rows show real local opportunity; `B8,K5,D80` has `hitMass=0.179325`, `accMass=0.000276`, `saveMass=0.000577`, `seqK=0.245625`; `mixed_all D40` reaches `saveMass=0.000991` but includes literals | Item-level closure is alive as a target, but accepted compressive mass is tiny and conditioned item syntax is not yet maintained full-cover compression |
| item-stream full-cover DP | Non-greedy exact current V1/J3D1 cover | H162: strict `seed_only K5,D80,N32` has support `0.310` and `gain/item=-4.110081`; `mixed_all K5,D80,N32` has support `0.384` and `gain/item=-3.472168` but spends literals | H161's local opportunity does not survive full-cover DP under current V1/J3D1 costs; the miss is several bits per item plus a support gap |
| extended-arity item DP | Paid higher-K record-only grammar | H163: `fixed` arity K8/K16/K32 worsens D80; `escape5 K16,D512,N32` reaches support `0.833` and `gain/item=-3.266563` | Higher K narrows support only at huge D and does not cross; the arity channel thickens the item grammar or pushes the DP back toward K5 behavior |
| fertility-selected superposition threshold | Non-greedy future-value target | H164: smallest strict miss is H162 `K5,D80,N32` at `8.361777` bits/selected-record; the equivalent ideal best-of-M count is `M ~= 329`; D512 narrows bits/item but raises the per-record bar above `11` bits | Fertility selection is the best remaining non-greedy value knob, but it must supply `8-11+` bits/record of measured future value or a public fertility score |
| fertility option DP | Same-cost neutral multiplicity upper bound | H165: optimistic same-cost option credit is only `0.20-0.25` bits/selected-record, equivalent to ideal best-of-M `M ~= 1.15-1.19`, while strict misses are `8.3-11.1` bits/record | Ordinary neutral seed multiplicity cannot pay H164; fertility selection needs a real public recurrent fertility law, not just same-cost alternatives |
| visible-selected conservation | Same-budget random control ledger | H166: same-class selected witnesses have zero expected lift over same-budget random; after H165 option credit the easiest strict row still has `8.112500` bits/record remaining; a 10% public class would need `11.683705` gross future bits/record | Fertility cannot live in untransmitted alternatives; it must be a public class/law or emitted-stream recurrence strong enough to beat the supply tax |
| emitted-stream recurrence | Selected visible stream versus same-budget controls | H167: content lift is `0` by exchangeability once visible class/cost is fixed; selected length/order control is nonpositive in tested rows (`B8,K5,D512` exact has `pass2|pass1=0.430556`, `final/i=-6.129032`, `orderLift/i=-0.173387`) | Pass-2 support can be bought with depth, but it does not create positive drift; the remaining target must be a public recurrent fertility law for the emitted record language |
| public fertility-law threshold | Class restriction versus population recurrence | H168: if `f=0.10` is enforced as a witness class, the easiest row needs `11.434428` future bits/record after H165 credit, or `11.683705` conservatively; if no restriction tax is paid and uniform start has `c0=f`, immediate positivity needs `a >= r/f = 81.125` bits/record, or a closed attractor with startup bloat | The remaining public-law route is precise: either pay class supply tax and prove large actual witness lift, or measure a real recurrent source/output population law; closed fertile outputs without supply tax are a hidden selector |
| visible-class savings scan | Public visible class paid-saving microscope | H169: in the exact H89 domain, best allowed public bit-shape class is `max_run<=5` with `net_after_tax=-4.955644` bits/word; even the disallowed post-hoc oracle ceiling is only `-3.041992` bits/word | Easy public visible classes do not provide the missing fertility law; next test must use native emitted-record classes or a new closed record language |
| native record-class scan | Public emitted-record class microscope | H170: in the H96 record-string domain, best allowed native class `bits_suffix3=101` has `net_after_tax=-43.208690` bits/record-string; even the disallowed future-saving oracle ceiling is `-41.091462` | Existing H96 emitted-record classes have visible fertility differences but remain far from positive after witness-mass tax; the record language itself would need to change |
| designed fertile sublanguage bound | Public fertile class by construction | H171: any boost `a` for a public fraction `f` spends Kraft mass `f*2^a`; restriction mode can at best repay `tax=-log2(f)`, leaving the `8.112500`-bit easiest gap unpaid; beating it needs `2^8.1125 = 276.761605` Kraft mass from F alone | Catalyst/fertility bits are not free recursive fuel; only a real no-tax population recurrence can use a rare fertile class |
| designed closed item-language bound | Fixed public closed grammar recurrence | H172: for item weights `W_a`, `F_n=sum W_a F_{n-a}` and positive drift requires `lambda>1`, which implies `sum W_a>1`; valid grammars with `sumW<=1` break even or lose | Public closure solves parseability but not uniform capacity; positive all-data drift in a fixed closed grammar is overfull hidden capacity |
| population concentration bound | No-tax population mode versus KL concentration cost | H173: for public class fraction `f`, values `a,b`, and population `c`, `c*a+(1-c)*b-D(c||f)=log2 Z-D(c||c_eq)`; Kraft-balanced laws have best net `0`, leaving the easiest post-H165 gap `-8.112500`; positive margin needs `Z>=2^r` | Population recurrence is not a free third channel for roughly-all data; biased `c_t` is paid as source KL unless it is genuine source bias |
| finite-state mixed-radix width | Public total-cover width/rank grammar | H176: strict depth-clamped bucket accounting finds no positive maintained row; nearest high-arity miss `B4,K128,D520,N128,r4,union:-1,2,P2` has `supportP=0.033333` and `packed gain/atom=-0.050781` | Public width grammar removes delimiter overhead but not the prefix/Kraft supply wall; bloat buys support and expands |
| Kraft cover bound | Total-cover prefix-code theorem | H177: `E_out <= 2^-s * sum_a 2^-ell(a)`; V1 arity Kraft is `0.875`, fixed complete arity is only critical at `s=0`, and strict paid savings are subcritical | More arity/search alone cannot maintain arbitrary-content total-cover compression; the next live route needs a real supply boost or source restriction |
| neutral option capacity | Near-equal witness lookahead | H178: V1 `K5,N128,s=-1` has `fantasy_net=-0.119706`; fixed `K8,N128,s=-1` has only `+0.000389` fantasy bits/record with support `0.709`, while support-repaired `s=-2` is `-0.161204` | Same-cost choice is real but conserved; it cannot by itself repay the slack/bloat needed for maintained support |
| reachable regime tax | Public developmental/generated surfaces | H179: `G=12,P=128,N=64` gives generated gain `8180` bits and reachable tax `8180` bits, uniform net `0` before headers | Developmental interpreters are valid source-shaped Telomere, not roughly-all-data compression unless source membership is free |
| cocycle canonical placement | Public coordinate/out-of-order decode geometry | H180: fixed `K8,N128,s=-1` baseline support `0.676`, observed `g=4` support `0.668`; `edge_zero g=4` support `0.000`; `paid_routes s=0,d=4` support `0.969` but paid gain/record `-2.000` | Zero-holonomy solves decode order, not match supply; conditioned coordinates and selected routes restore the H177 bill |
| forced two-epoch parity lane | Stateless readiness target | H100: with max record lifetime `<=1`, parity residual is `0`; current H7/H9/H12 parity nets are `-0.020716/-0.022079/-0.019183` bits/atom; hypothetical `+2` bits/record at H9 density gives `+0.009765` bits/atom | Real decode geometry, not current compression; needs `>1` paid bit/record base margin and mandatory old-cohort refresh |
| neutral parity discount | Seed-class cost refinement | H101: best discounted parity row `slack=1` has class loss `0.830905` bits/record but net `-0.027835` bits/atom; cheapest class row `slack=-12` has class loss `0.260736` but base margin `-5.346307` bits/record | Neutral multiplicity can discount readiness, but current slack width buys the discount at greater cost than it returns |
| public lane local class grammar | Stateless readiness without visible parity tax | H102: public lane + local class grammar crosses iff base margin `>0`; H9 still `-0.012314` bits/atom, but a hypothetical `+0.28` bits/record gives `+0.002800` bits/atom while visible one-bit parity remains negative | Best surviving spec shape: position/lane carries readiness, class-local rank carries fresh salt, separate witness mechanism must supply positive forced-rewrite margin |
| class-local Kraft check | Exact H102 sanity check | H103: in exact `B=1,N=12`, local class grammar has `0.000000` collective log2Z delta versus base; visible global class loses `-3.682516/-2.926359/-1.746973` in tested rows | Confirms local class is not hidden Kraft mass; it only works when readiness class is already public |
| SPEC_V1 decode scaling audit | Keep-what-decodes referee priced | H104: carried records have `S=T^R` possible readings in the arity-1 worst case; at `T=64`, fixed 64-bit checksum covers only `R<=10.667` records, or `R<=5.333` with 32 safety bits | Small proof round trips are valid finite decodes, not an unbounded birth/open channel |
| forced-rewrite collective target | Best current constructive target | H105: public-lane local grammar drops best honest target from `1.468557` visible-parity bits/record to `0.468557` bits/record; `custom_record K=6,D=12` still has `log2Z=-1.781751` | Public lanes materially help, but a paid collective witness family still needs about `0.47` honest bits/record |
| cover-sequence Kraft capacity | Arity reweighting no-go | H106: valid record-sequence grammar obeys `F_n=sum W_a F_{n-a}` with `sum W_a<=1`, so `F_n<=1`; equal `K=6,N=12` gives the H105 `-1.781751`, best valid divisor gives `0`, positive needs invalid `sum W_a>1` | The `0.468557` target cannot be closed by public arity-weight optimization alone |
| value-shape conservation | Biased seed grammar no-go for uniform data | H107: with fixed `W_a`, `uniform/zero/half/random` output laws all keep `log2Z=-1.781751`; uniform CE is raw or worse, and best raw/Q mixture chooses `alpha=0` | Value shaping only helps named source/fertility laws; it does not create content-blind witness margin |
| prefix record grammar converse | Exact underpricing detector | H108: exact Fraction audit gives `h92_lower log2 symbol mass=2.055381` and `log2Z=1.001339` invalid; valid `custom_record` has symbol mass `1` and `log2Z=-1.781751` | Confirms H92-style crossings are overfull-code artifacts; valid public grammars remain subprobability families |
| non-prefix referee capacity | Trial-decode/checksum pruning priced | H109: ambiguous length languages grow at rate `log2(lambda)`; a 64-bit referee covers only finite stream windows (`fib_1_2` 92 bits, `lotus_toy` 215 bits, `(8,9)` 569 bits); carried records have the same `T^R` ledger | Useful bounded engineering tool, but not an unbounded stateless birth/open channel unless a public invariant bounds survivor readings |
| original active goal audit | Blocked under stated premises | H17: Total-Cover decode solved; uniform/content-blind all-data recursive savings forbidden by H15/H2 | Next work must change a premise or find a flaw in the counting assumptions |
| public rank-residual coding | No | `B=8,K=64,D=120` truncated-geometric row: `-0.1115` bits/atom, missing `1.433` bits/record | Exact-rank entropy is almost the fixed width in the selected regimes |

## Free-Boundary Oracle

This mode charges arity plus the raw first-hit payload width. It is not a
parseable final codec by itself because the decoder still needs the witness
boundary, but it answers the first crossover question: the total-cover
order-statistic effect does cross positive.

Coarse grid, `atoms=64`, `trials=8`, coverage threshold `0.875`:

| B | K | first D | cover | gain/atom | gain/byte | rec/atom | avg arity | avg payload width |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 4 | 5 | 6 | 1.000 | 0.2285 | 0.4570 | 0.7109 | 1.41 | 3.27 |
| 4 | 16 | 17 | 1.000 | 0.0332 | 0.0664 | 0.2949 | 3.39 | 9.45 |
| 6 | 5 | 10 | 1.000 | 0.1660 | 0.2214 | 0.7578 | 1.32 | 5.69 |
| 8 | 5 | 14 | 1.000 | 0.1777 | 0.1777 | 0.7480 | 1.34 | 8.45 |
| 8 | 16 | 45 | 1.000 | 0.1797 | 0.1797 | 0.2949 | 3.39 | 22.52 |
| 12 | 8 | 41 | 1.000 | 0.1992 | 0.1328 | 0.4727 | 2.12 | 21.97 |
| 24 | 5 | 46 | 1.000 | 0.1699 | 0.0566 | 0.7637 | 1.31 | 29.20 |
| 24 | 8 | 184 | 1.000 | 0.6094 | 0.2031 | 0.2930 | 3.41 | 76.84 |

Answer to question 1: free-boundary/oracle flips positive at small finite `D`
for many rows. This validates the user's crossover intuition, but it is not a
paid parseable witness.

## Exact V1/J3D1

V1/J3D1 uses the current canonical arity alphabet and exact
`record_cost_for_payload_width(arity, payload_width)`. Since V1 arity is 1..5,
only `K=5` is meaningful here.

Coarse grid, `atoms=64`, `trials=8`, coverage threshold `0.875`:

| B | K | best D | cover | gain/atom | gain/byte | rec/atom | avg arity | avg payload width | missing bits/record |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 4 | 5 | 20 | 1.000 | -1.3145 | -2.6289 | 0.2637 | 3.79 | 11.30 | 4.985 |
| 6 | 5 | 30 | 1.000 | -1.3711 | -1.8281 | 0.2617 | 3.82 | 18.93 | 5.239 |
| 8 | 5 | 40 | 1.000 | -1.5723 | -1.5723 | 0.2734 | 3.66 | 25.16 | 5.750 |
| 12 | 5 | 60 | 1.000 | -1.5586 | -1.0391 | 0.2480 | 4.03 | 44.24 | 6.283 |
| 24 | 5 | 120 | 1.000 | -1.9746 | -0.6582 | 0.2285 | 4.38 | 101.90 | 8.641 |

Answer to question 2: exact V1/J3D1 did not flip positive in the tested grid.

## Custom Witness Modes

### Fixed Width And Small Width Classes

These modes are parseable: the layer has a global width or a small global set
of widths, and each record either uses that width or stores a small class id.
They cover, but they lose the order-statistic advantage.

Coarse sanity run, `atoms=64`, `trials=6`, coverage threshold `0.833`:

| Mode | B | K | D | cover | gain/atom | gain/byte | rec/atom | avg arity | missing bits/record |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| width_classes4_uniform | 24 | 64 | 1536 | 1.000 | -0.1458 | -0.0486 | 0.0182 | 54.86 | 8.000 |
| width_classes4_uniform | 8 | 64 | 512 | 1.000 | -0.1667 | -0.1667 | 0.0208 | 48.00 | 8.000 |
| width_classes4_uniform | 12 | 64 | 768 | 1.000 | -0.1875 | -0.1250 | 0.0234 | 42.67 | 8.000 |
| extended_j3d1_fixed_arity | 8 | 64 | 512 | 1.000 | -0.3099 | -0.3099 | 0.0312 | 32.00 | 9.917 |
| extended_j3d1_fixed_arity | 12 | 64 | 768 | 1.000 | -0.3646 | -0.2431 | 0.0312 | 32.00 | 11.667 |
| global_fixed_seed_width | 8 | 5 | 40 | 1.000 | -1.5026 | -1.5026 | 0.2214 | 4.52 | 6.788 |

### Arithmetic-Coded Selected Width/Rank Bins

This mode front-codes the selected `(arity,width)` stream, then stores local
payload bits. It is parseable: the decoder first decodes the arity/width stream
for the total cover, then reads exactly that many witness bits per record.
The coarse run produced positive rows, but the positives did not survive larger
refinement. The refined rows are the relevant result:

| Mode | B | K | D | atoms/trials | cover | gain/atom | gain/byte | rec/atom | avg arity | avg payload width | missing bits/record |
| --- | ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| arith_arity_width_lotus_payload | 12 | 5 | 57 | 256/48 | 1.000 | -0.4176 | -0.2784 | 0.6371 | 1.57 | 15.66 | 0.655 |
| arith_arity_width_lotus_payload | 24 | 8 | 164 | 256/48 | 1.000 | -0.4075 | -0.1358 | 0.6346 | 1.58 | 34.65 | 0.642 |
| arith_arity_width_lotus_payload | 8 | 64 | 65 | 256/48 | 1.000 | -0.4011 | -0.4011 | 0.6265 | 1.60 | 9.60 | 0.640 |
| whole_cover_local_payload_stream | 8 | 64 | 120 | 256/48 | 1.000 | -0.6180 | -0.6180 | 0.4930 | 2.03 | 12.41 | 1.253 |

Answer to question 3: no refined paid custom witness mode crossed positive.
The nearest stable miss is the arithmetic-coded selected `(arity,width)` stream,
short by about `0.64` bits per selected record.

### Paid Count And Public-Model Follow-Up

Continuation update, 2026-06-17: the optimistic arithmetic stream was split into
three stricter branches.

1. `paid_iid_counts_lotus_payload` and `paid_markov1_counts_lotus_payload` add
   the finite per-file symbol subset/count or transition subset/count costs.
   These are honest if the model is chosen from the file itself, but they do not
   cross. Representative `atoms=128`, `trials=24`, coverage `0.95` rows:

| Mode | B | K | D | cover | gain/atom | gain/byte | rec/atom | avg arity | avg payload width | missing bits/record |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| arith_arity_width_lotus_payload | 24 | 8 | 192 | 1.000 | -0.1961 | -0.0654 | 0.6475 | 1.54 | 33.90 | 0.303 |
| paid_iid_counts_lotus_payload | 24 | 8 | 52 | 1.000 | -1.8824 | -0.6275 | 0.7679 | 1.30 | 28.77 | 2.451 |
| paid_markov1_counts_lotus_payload | 24 | 8 | 27 | 1.000 | -3.8763 | -1.2921 | 1.0000 | 1.00 | 22.57 | 3.876 |
| paid_iid_counts_lotus_payload | 12 | 5 | 23 | 1.000 | -1.5420 | -1.0280 | 0.7627 | 1.31 | 13.25 | 2.022 |
| paid_iid_counts_lotus_payload | 8 | 64 | 16 | 1.000 | -1.9759 | -1.9759 | 0.7396 | 1.35 | 8.30 | 2.672 |

2. [total_cover_public_model_kernel.py](./total_cover_public_model_kernel.py)
   tests a public frozen arithmetic model learned only from independent
   uniform-law Total-Cover samples. No per-file counts are charged; this is
   honest only if the model is fixed by the codec profile for `(B,K,D,objective)`.
   The public iid model did not cross; public Markov over exact previous
   `(arity,width)` was worse because the transition state is too sparse.

| Model | Rank code | B | K | D | cover | gain/atom | gain/byte | rec/atom | avg arity | avg width | stream bits/record | missing bits/record |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| public iid | fixed | 24 | 8 | 192 | 1.000 | -0.1581 | -0.0527 | 0.1426 | 7.01 | 164.60 | 4.98 | 1.109 |
| public iid | fixed | 12 | 5 | 70 | 1.000 | -0.2371 | -0.1580 | 0.2240 | 4.46 | 50.45 | 4.24 | 1.058 |
| public iid | fixed | 8 | 64 | 120 | 1.000 | -0.1505 | -0.1505 | 0.0758 | 13.19 | 101.40 | 6.40 | 1.985 |
| public iid | fixed | 4 | 128 | 512 | 1.000 | -0.0595 | -0.1190 | 0.0092 | 108.74 | 432.34 | 43.87 | 6.471 |
| public markov1 | fixed | 24 | 8 | 184 | 1.000 | -0.5154 | -0.1718 | 0.1559 | 6.41 | 150.84 | 6.70 | 3.305 |

3. Public truncated-geometric rank coding was tested after the width bucket is
   decoded. It also did not cross. In the selected-cover regimes, the exact rank
   entropy is almost the fixed payload width; the suspected optimistic B=24
   rank-residual win does not survive public joint-cost accounting.

| Model | Rank code | B | K | D | cover | gain/atom | gain/byte | rec/atom | avg width | avg rank bits | stream bits/record | missing bits/record |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| public iid | truncated geometric | 24 | 8 | 184 | 1.000 | -0.1756 | -0.0585 | 0.1624 | 144.22 | 144.21 | 4.86 | 1.082 |
| public iid | truncated geometric | 12 | 5 | 70 | 1.000 | -0.2334 | -0.1556 | 0.2227 | 50.79 | 50.77 | 4.21 | 1.048 |
| public iid | truncated geometric | 8 | 64 | 120 | 1.000 | -0.1115 | -0.1115 | 0.0778 | 98.35 | 98.34 | 6.21 | 1.433 |
| public iid | truncated geometric | 4 | 128 | 512 | 1.000 | -0.0601 | -0.1203 | 0.0092 | 432.33 | 432.28 | 43.95 | 6.540 |

4. The best public-context follow-up was a factored model:

```text
symbol stream = arity under legal remaining-atom mask
              + width delta where delta = arity * B - payload_width
              + fixed/rank payload bits
context       = remaining_atoms bucket
```

This is decoder-derived: before each symbol, the decoder knows original atom
count, consumed atoms from previous arities, and the legal arity set. No
per-file counts are charged. It improved the high-arity target but still did
not cross.

| Model | Context | Rank code | B | K | D | cover | gain/atom | gain/byte | rec/atom | avg arity | avg width | stream bits/record | missing bits/record |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| factored arity+delta | remaining | fixed | 24 | 8 | 192 | 1.000 | -0.1368 | -0.0456 | 0.1442 | 6.94 | 162.84 | 4.84 | 0.949 |
| factored arity+delta | remaining | fixed | 8 | 64 | 120 | 1.000 | -0.0960 | -0.0960 | 0.0798 | 12.54 | 95.91 | 5.90 | 1.203 |
| factored arity+delta | remaining | fixed | 4 | 128 | 512 | 1.000 | -0.0313 | -0.0627 | 0.0089 | 112.22 | 446.75 | 35.30 | 3.518 |
| factored arity+delta | remaining_prev_coarse | fixed | 24 | 8 | 192 | 1.000 | -0.2092 | -0.0697 | 0.1487 | 6.73 | 157.87 | 5.44 | 1.407 |
| factored arity+delta | remaining | truncated geometric | 24 | 8 | 192 | 1.000 | -0.1395 | -0.0465 | 0.1450 | 6.90 | 161.83 | 4.92 | 0.962 |

The factored model confirms a useful engineering direction: avoid a sparse
joint `(arity,width)` alphabet, code only legal arities, and align widths as
target-relative deltas. But the best result is still a near-flat asymptote, not
a maintained positive crossover. Fewer records amortize the boundary bill over
many atoms, while each selected record still carries a positive
witness-language deficit.

### High-Arity Witness Split Follow-Up

Continuation update, 2026-06-17: the near-flat `B=4,K=128,D=512` branch was
split by field in
[`model_analysis/birth_channel_research/H5-total_cover_split_ledger.py`](./model_analysis/birth_channel_research/H5-total_cover_split_ledger.py)
and then tested with an exact suffix model in
[`model_analysis/birth_channel_research/H6-total_cover_suffix_partition.py`](./model_analysis/birth_channel_research/H6-total_cover_suffix_partition.py).
The follow-up parametric delta kernel
[`model_analysis/birth_channel_research/H7-total_cover_parametric_delta.py`](./model_analysis/birth_channel_research/H7-total_cover_parametric_delta.py)
then replaced sparse delta tables with public analytic/parametric laws.
Finally,
[`model_analysis/birth_channel_research/H8-total_cover_objective_beta.py`](./model_analysis/birth_channel_research/H8-total_cover_objective_beta.py)
and
[`model_analysis/birth_channel_research/H9-total_cover_fixed_slack.py`](./model_analysis/birth_channel_research/H9-total_cover_fixed_slack.py)
tested objective-tuned selected-delta temperature and fully decoder-derived
fixed witness widths.
[`model_analysis/birth_channel_research/H10-total_cover_tail_schedule.py`](./model_analysis/birth_channel_research/H10-total_cover_tail_schedule.py)
then tested the natural two-phase body/tail fixed-width schedule.
[`model_analysis/birth_channel_research/H11-total_cover_order_stat_delta.py`](./model_analysis/birth_channel_research/H11-total_cover_order_stat_delta.py)
then tested the public selected-order-statistic delta law.

H5 answers "which field is the bill?" by making individual fields free as a
diagnostic lower bound. H6 tests the concrete public witness language:

```text
P(arity | exact remaining atoms)
P(delta | exact remaining atoms, exact arity)
```

Representative bounded rows:

| Kernel | B | K | D | train/eval | paid gain/atom | free delta gain/atom | rank bits/rec | arity bits/rec | delta bits/rec | result |
| --- | ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: | --- |
| H5 current factored split | 4 | 128 | 512 | 32/16 | -0.0678 | +0.0088 | 334.98 | 5.61 | 6.53 | delta/slack is the tight field |
| H6 exact suffix, alpha=0.02 | 4 | 128 | 512 | 64/16 | -0.0400 | +0.0060 | 455.77 | 2.18 | 4.95 | suffix model improves but still misses |
| H7 raw first-hit delta law | 4 | 128 | 512 | 64/32 | -0.0119 | n/a | 453.54 | 0.52 | 2.41 | closest paid miss so far |
| H8 objective beta | 4 | 128 | 512 | 16/8 | -0.0163 | n/a | 406.45 | 1.57 | 3.25 | train-selected beta overfits held-out |
| H9 fixed slack 0 | 4 | 128 | 512 | 32/16 | -0.0123 | n/a | n/a | 1.26 | 0.00 | decoder-derived width nearly ties H7, still misses |
| H10 body/tail slack | 4 | 128 | 512 | 16/8 | -0.0273 | n/a | n/a | 2.92 | 0.00 | train-selected schedule overfits held-out |
| H11 selected-order m16 | 4 | 128 | 512 | 24/16 | -0.0178 | n/a | 225.80 | 3.44 | 2.55 | train-selected effective-choice law misses |
| H11 frozen m8 seed 9001 | 4 | 128 | 512 | 24/16 | -0.0180 | n/a | 251.81 | 2.59 | 2.75 | best diagnostic law did not survive independent seed |

`free_delta` is not a valid codec. It means that if payload width/slack were
somehow decoder-derived, the row would cross. In the paid model it remains a
real witness channel. H7 shows the public raw first-hit law prices it much more
cheaply than sparse suffix tables, but still leaves about `1.36` missing
bits/selected record. H8 did not improve that with one public selected-delta
temperature. H9 removed the delta stream entirely by deriving width from arity,
but the fixed-width padding and match-supply loss returned the bill.
H10's body-stricter/tail-relaxed schedules did not improve on scalar slack.
H11 corrected the effective-choice-count law to condition on the selected
minimum fitting `D`, not on every hidden draw already being legal; it still
missed and did not beat H7/H9 on an independent frozen-`m8` seed.
[`model_analysis/birth_channel_research/H12-neutral_fertility_capacity.py`](./model_analysis/birth_channel_research/H12-neutral_fertility_capacity.py)
then tested neutral seed multiplicity: choosing among multiple same-width
matching seeds to shape later layers without changing the current record size.
It is a valid stateless capacity source, but not an immediate saving. In the
stronger bounded row, even perfect one-for-one future credit stayed negative:

```text
H12 slack -8, train/eval=24/16
actual gain = -0.050155 bits/input atom
neutral capacity = 3.819 bits/record
perfect-credit gain = -0.008196 bits/input atom
residual = 0.746 bits/record
```
[`model_analysis/birth_channel_research/H13-joint_selected_cover_partition.py`](./model_analysis/birth_channel_research/H13-joint_selected_cover_partition.py)
then tested a normalized semi-Markov code over the whole selected cover shape,
still paying exact `width` bits for each seed residual. The H13 audit also
found and fixed a shared sampler issue: exact Lotus/J3D1 payload width is now
computed from integer rank as `ceil(log2(rank+3))-1`, not by the old
`ceil(log2(rank)-1)` approximation. Future sampled-width rows are stricter;
older rows using sampled `lotus_payload_width` should be treated as optimistic
unless rerun.

Post-fix H13 bounded row:

```text
N=128, train/eval=24/16
train-selected beta=0.5, record_bias=-10
gain = -0.013941 bits/input atom
missing = 1.586 bits/record
same-seed H7 raw = -0.012528 bits/input atom
same-seed H9 slack 0 = -0.026809 bits/input atom
```
[`model_analysis/birth_channel_research/H14-public_crf_cover_partition.py`](./model_analysis/birth_channel_research/H14-public_crf_cover_partition.py)
then trained a small frozen public CRF over selected-cover features using
independent uniform-law samples. The tiny first smoke was positive but
train-negative and collapsed under stronger checking. Bounded H14 rows:

```text
N=64, train/eval=16/8
gain = -0.019572 bits/input atom
missing = 1.253 bits/record

N=128, train/eval=8/4
gain = -0.015478 bits/input atom
missing = 1.981 bits/record
```
[`model_analysis/birth_channel_research/H15-recursive_counting_converse.py`](./model_analysis/birth_channel_research/H15-recursive_counting_converse.py)
then formalized the recursive pass-selection wall. Trying many passes gives at
most `log2(P)` apparent free bits if the pass selector is unpaid; once the
decoder-visible pass/profile/header channel is included, the final stream obeys
the same uniform-source bound:

```text
Pr_uniform[L(X) <= n - s] <= 2^-s
E_uniform[L(X)] >= n
Pr_uniform[L(X) <= (1-epsilon)n] <= 2^(-epsilon*n)
```

For example, with `n=1024`, `P=65536`, and target saving `s=32`, a free
selector gives a loose `1.5e-5` bound, but paying the 16 selector bits makes
the net 48-bit saving bound `3.55e-15`.
[`model_analysis/birth_channel_research/H16-prior_escape_ledger.py`](./model_analysis/birth_channel_research/H16-prior_escape_ledger.py)
then priced the remaining escape hatch: a public non-uniform interpreter or
source-shaped seed universe. If a source prior `Q` gives mass `c` to strings
that save `s` bits, then it must concentrate that mass on a set occupying at
most `2^-s` of uniform space:

```text
Q(A_s)/U(A_s) >= c * 2^s
n - H(Q) >= d2(c || 2^-s)
```

Representative H16 row:

```text
n=1024, s=128, c=0.90
uniform max coverage = 2.94e-39
average likelihood-ratio lift = 3.06e38
minimum entropy deficit = 114.731 bits
```

## Interpretation

Total-cover changes the problem in the right way. It correctly removes the
open/carry and birth-pass channels. The free-boundary model crosses positive,
so the overlap/order-statistic effect is real. The remaining paid channel is
not sparse metadata; it is the parseable seed witness boundary.

The exact V1/J3D1 format is too expensive by roughly `5` to `9` bits per
selected record. Global fixed-width and small width-class modes are honest but
discard too much early-rank luck. The optimistic empirical `(arity,width)` stream
preserves much of the order-statistic effect, but after the missing stream
model/count channel is made public or paid, the gap widens rather than closes.

The counting sanity check is now sharp: for uniform `N*B`-bit layers and any
public uniquely-decodable stream, the probability of saving `s` bits on an
arbitrary layer is at most `2^-s`. So a content-blind codec cannot compress
roughly all uniform layers by a linear amount forever. The remaining Telomere
crack is narrower: estimate the true entropy rate of the selected witness
process under public `(B,K,D,N)` dynamics, then see whether a fixed public model
can make a minority of layers positive without hidden per-file state.

H17 turns that into the original-goal audit: stateless decode is not the
blocker, and neither open/carry nor birth-pass entropy should be charged inside
Total-Cover. The blocker is the stronger requirement that the process keep
positive savings over arbitrary recursive passes on roughly all
uniform/content-blind data. Under the stated assumptions, that is one final
lossless code and is counting-forbidden.

The current counting addendum lives at
`model_analysis/birth_channel_research/findings/H2-total-cover-counting-bound.md`;
the runnable ledger is
`model_analysis/birth_channel_research/H2-uniform_counting_boundary.py`.
The original-goal audit lives at
`model_analysis/birth_channel_research/findings/H17-original-goal-audit.md`.

## Next Target

Most promising next target after the 2026-06-18 follow-up:

```text
B = 4 bits
K = 32
D = 128 payload-width frontier
witness mode = forced due-cohort refresh with a new witness family or priced public lane/board invariant
prior fixed-atom target = H114 visible parity + frozen delta law, -0.020876 bits/input atom
record-layer audit = H115 force_refresh goes positive at +0.020909 bits/atom/pass
invalid lower bound = H115 no_expiry stays negative at -0.014058 bits/atom/pass
oracle signal = H115 local-width force_refresh remains negative at -0.047175 bits/atom/pass
public-width search = H116 simple public clocks miss; best focused public arity row is +0.023659 bits/atom/pass
hidden diagnostic = H116 target/age bucket contexts also miss in this language
parseable width stream = H117 best honest row +0.007218 bits/atom/pass but only rewrites 0.124 raw fraction
maintained-refresh check = H117 min_rewrite 0.25 expands by +0.061297 bits/atom/pass; 0.50 has no finite small-sweep path
collective width check = H118 scale-1 count-free crosses but asymptotic/count-paid rows settle near +0.026 bits/atom/pass
width entropy target = H120 pooled equivalence shows selected widths need far less than ~5.34 bits/record or must become public by a real invariant
fixed-width lane check = H119 public deterministic W(context) misses at meaningful rewrite density, even with hidden target-size diagnostics
gap-board check = H121 public T_pub lower bound misses at maintained refresh; fixed gaps cannot keep supply
gap-alphabet check = H122 closes the small paid gap-class variant; nearest lower-bound row +0.001674 bits/atom/pass with nonzero fail
status = H114 was a fixed-atom lower-bound crossing, not a file-format proof
next proof = make selected gaps predictable from public geometry without losing high-gap supply, or change the search objective so selected intervals naturally concentrate in a low-entropy high-saving class
tested next = one-beta selected-delta tilt and scalar fixed slack both miss
tested next = monotone fixed-width tail schedule also misses
tested next = selected-order-statistic effective-choice law also misses
tested next = neutral seed-multiplicity capacity also misses under perfect credit
tested next = raw/tilted joint selected-cover partition code also misses
tested next = trained public CRF selected-cover code also misses
tested next = recursive best-of-pass/pass-count converse closes the uniform branch
tested next = priced non-uniform public interpreter/source-shaped prior is outside original claim
tested next = original-goal audit says this branch is blocked unless a premise changes
tested next = developmental neutral-fertility threshold needs gamma > 1.195
tested next = exact neutral ecology toy crosses only for source-shaped data
tested next = public position / active-lane schedule solves stateless salt/placement but costs log2(1/r) supply bits
tested next = orderless/confluent decode costs permutation entropy unless destinations are public
tested next = public fertility class criterion is value_lift > log2(1/f), with uniform controls negative
tested next = cover-equivalence Q(x) harvests duplicate covers but uniform average remains above raw
tested next = public reversible dither refreshes dice without per-record birth tags but preserves entropy
tested next = coset/syndrome repair returns to raw length or tiny coverage unless residual fertility has gamma > 1
tested next = bits-back latent reservoir conserves tape and only crosses with gamma > 1
tested next = de Bruijn/universal tape gives guaranteed matches but full coverage coordinate cost equals span entropy
tested next = XOR/fountain superposition makes decode order irrelevant but full coverage selector cost reaches raw entropy
tested next = confluent normal form permits out-of-order decode but arbitrary order/ready placement is paid
tested next = developmental attractor/canalization works as a public source prior, not a uniform all-data escape
tested next = d-choice self-routing lowers public-lane supply loss but still pays destination/order entropy
tested next = combined fertility-lane threshold shows d-choice lowers value-lift target but cannot beat uniform conservation
tested next = two-layer source-shaped fertility kernel crosses with uniform controls negative
tested next = EOF/non-prefix whole-file length coding gives a small final-file constant but does not compound
tested next = position/ready-prefix compaction is valid decode geometry but arbitrary sparse hit subsets cost log2 C(N,R)
tested next = systematic response-surface map identifies coverage epsilon, lane loss, witness gap, and value lift as the active axes
tested next = forced-rewrite/all-block target shows option-count dividend is real but current paid rows still miss by witness margin
tested next = normalized collective-cover Q harvests duplicate covers but uniform cross-entropy remains above raw
tested next = neutral-selection fertility is stateless but uniform best-of-M gains stay below the H18 gamma threshold
tested next = high-arity option-statistic bound shows H7 needs only 2.562x extra effective choices, but the selector/cover bill remains
tested next = frozen public residual-law calibration misses badly, so more public table shape is not enough without lower support entropy
tested next = seed-grammar arity embedding can derive arity, but parseable witness boundaries return the bill through seed thinning/J3D1 width
tested next = all-block renormalization confirms fresh dice over passes, but H7/H9 paid modes still have E[log rho] > 0 in the tested target
tested next = H50 corrected sweep gives K>=128 enough atoms; best paid row still misses at mean log2 rho +0.004884
tested next = normalized collective-cover Q removes selected-cover metadata but exact tiny uniform rows still have positive excess and escape alpha 0
tested next = fixed-slack percolation high-K scout improves closest strict paid gap to about +0.00366 mean log2 rho, still positive
tested next = paid global slack ladder keeps stateless decode, but selector-charged row misses at +0.004480 mean log2 rho
tested next = selector-referee checksum budget buys finite profile windows only; current H53 unpaid row still expands
tested next = Fibonacci/self-sync syntax can derive slack in tiny exact languages, but repeated-pass delimiter cost misses badly
tested next = normalized collective-cover Q at the H52/H53 frontier gives the closest log-rho miss, but expected bits remain above raw
tested next = frozen public-Q arity model lowers K384 expected excess to +0.229195 bits, still positive
tested next = raw/Q stop mixture either chooses raw-only or stays positive on held-out eval
tested next = EOF/non-prefix one-shot shrink needs recursive length-path ledger; exact fixed shrink covers exponentially small fraction
tested next = exact tiny selector ledger shows best-of profiles and checksum only help when selector/referee bits are unpriced or finite
tested next = scientific phase diagram ranks the closest honest misses and separates uniform-invariant targets from source-shaped fertility targets
tested next = source fertility phase shows atom-level H59/H58 misses can cross under modest public-class enrichment, while record gaps require much stronger concentration
tested next = recursive fertility invariant shows the nearest atom-level public-Q route needs `p_FF~0.414`, while record-gap source fertility needs `p_FF>0.95`
tested next = repeatable non-prefix path ledger separates the real one-shot EOF effect from recursive hidden length-path entropy
tested next = public invariant exhaustion reduces boards/permutations/lanes/profiles to visible-state capacity; apparent excess is hidden state or finite referee budget
tested next = all-block cover entropy bound shows high-arity option pressure is real but the chosen cover has up to ~1 bit/atom selector entropy
tested next = typical drift / rare blowup ledger shows negative mean log-rho still needs tail accounting over arbitrary pass counts
tested next = public-code martingale audit shows public Q/mixture rows keep `E[W]=1`; hidden best-of gains are selector bits
tested next = rank-width sampling bias fixed a +1 payload-bit/record overcharge for high-span rank-width samples
tested next = systematic response protocol turns future candidates into knob/prediction/currency/control/stop-rule cards
tested next = finite-pass coverage frontier gives max K=0 prefix and K=1 EOF at 90% coverage for >=1 bit/pass
tested next = public-Q/visible-state converse shows free profile/final-board/checksum multipliers cancel when paid
tested next = final-state entropy kernel keeps egg-carton geometry alive but prices ready/birth/order as visible state or supply loss
tested next = exact latent whole-cover Q shows duplicate-cover gains but uniform excess stays positive and raw/Q chooses raw-only
tested next = rare-blowup coverage ledger shows statistical bad tails cannot create short outputs and violate bounded-loss if unbounded
tested next = randomized codebook ledger shows public/private randomness and compute-as-best-of reduce to public Q or selector bits
tested next = self-induced fertility kernel shows exact H74 high-Q classes need strong source entry and p_FF~0.90 retention
tested next = master no-go audit unifies visible-state, Q, randomization, compute, EOF, and bad-tail bounds
next test = predeclare a public high-Q fertility class from H74/H59, measure c*, p_FF, and p_OF with uniform controls, or exhibit a public invariant beating H71-H73
```

This is not the most elegant codec target; it is the sharpest asymptotic probe.
Large arity can make the loss per atom small by spreading one negative record
over about `112` input atoms, but it has not made the expected record margin
negative. The next useful work is therefore not another empirical-count Markov
trick. It is one of:

- derive or approximate the entropy rate of selected covers as `N,K,D` grow,
  including the boundary/rank bill;
- test a joint enumerative selected-cover code that prices the whole cover as
  one canonical object rather than independent witness fields;
- avoid richer feature tables unless the profile is frozen before eval or its
  model-selection cost is explicitly paid;
- only revisit recursive fertility if a two-layer kernel can beat the H12
  neutral-capacity ceiling without exceeding one saved future bit per neutral
  choice bit;
- keep public phase/final-board lanes as the preferred stateless decode
  geometry, but require a value/count separation proof before treating them as
  compression;
- do not use multiset/canonical-sort decode for arbitrary streams unless the
  order entropy or seed-key supply loss is explicitly paid;
- test public fertility classes only with a uniform negative control and a
  predeclared class law; after-the-fact class/profile selection is metadata;
- keep cover-equivalence `Q(x)` as the strongest collective witness mode, but
  report it as a public prior/minority-win lane unless uniform raw escape
  mixture chooses nonzero collective weight and still averages below raw;
- use public reversible dither for freshness experiments only when the schedule
  is fixed or the transform selector is explicitly paid;
- treat syndrome/residual repair as a stateless fallback language, not as
  compression, unless residual bits produce measured future value above one bit
  per bit;
- bits-back cover reservoirs are allowed as an implementation of collective
  `Q(x)`, but salt tape consumption must be returned or charged unless a
  predeclared fertility law supplies `gamma > 1`;
- universal/de Bruijn tapes may be used as deterministic seed universes, but
  their coordinates must be charged as addresses; overlap is a source prior
  unless arbitrary order/path bits are paid;
- XOR/fountain records may be used as stateless, order-insensitive search
  primitives, but sparse support misses most targets and full coverage pays
  the recipe/selector entropy;
- confluent normal forms may be used for out-of-order decode, but arbitrary
  ready subsets and original stream order still require subset or
  linear-extension entropy unless placement is public;
- developmental attractors/canalized genotype maps are the strongest
  biology-shaped source-language target; require held-out source gains and
  negative uniform controls, not arbitrary-data claims;
- d-choice routing can lower the public-lane/fertility-class tax from
  `-log2(r)` to `-log2(1-(1-r)^d)`; it should be used as a threshold reducer,
  not as an arbitrary-order/coordinate channel;
- the combined H18/H37 threshold is
  `gamma_needed = gamma_no_lane + lane_loss/neutral_bits`; d-choice can reduce
  the added lane tax toward zero but cannot make uniform `gamma<=1` cross;
- a public two-layer fertility source can cross H38's reduced target while
  uniform controls stay negative; treat this as a source-language positive
  control, not a uniform all-data result;
- EOF/file length can support non-prefix whole-file codes with small constant
  savings, but fixed virtual boards do not compound, shrinking boards need an
  ordered length ledger, and storing original length/valid-bit count spends the
  constant unless those are public invariants;
- ready-prefix/position compaction should be treated as stateless decode
  geometry: it is free only for public selected sets, while content-selected
  sparse hits pay `log2 C(N,R)`; the constructive target is near-total cover
  where the exception ledger is genuinely small;
- future lanes should be plotted on the H42 response surface before testing:
  coverage exception rate, public lane fraction and d-choice count, paid
  witness gap, source/fertility value lift, decoder observation class, and the
  adversarial uniform control;
- forced-rewrite/all-block lanes must keep units straight: current high-arity
  rows have bits-per-record margins at low records/atom, while a true all-atom
  rewrite mechanism would need a paid bits-per-input-atom margin; do not use
  the looser atom-level exception threshold for the current H7/H9 rows;
- collective whole-cover coding should use normalized public `Q(x)` accounting:
  duplicate covers can reduce selected-cover cost and define a source prior,
  but the uniform average is `raw + KL(U||Q)`, not below raw;
- neutral/fertility selection is valid stateless machinery when same-cost seeds
  decode to the same current span, but the uniform tail only shifts by
  `log2(M)`; use it as a public developmental/source target, not a free
  uniform amplifier;
- stop treating richer public tables or recursive best-of-pass selection as a
  likely uniform-law escape; H15 reduces them to one paid final code;
- if continuing toward a breakthrough, change the premise by defining and
  pricing a non-uniform public interpreter/source-shaped seed universe, with
  H86 narrowing the target to a fixed native record language whose soft
  high-entropy output law buys future-value lift without a stored profile,
  hidden selector, or paid reshaping ledger; H87/H88 now narrow the next test
  further to an exact witness-savings kernel, because frozen soft grammars can
  be parseable; H89 shows the current `V=log2(Q/U)` lift is aligned but still
  misses by about `2.4` bits/word, so the next live target is actual
  witness-cost fertility rather than another normalized-`Q` score proxy; H90
  proves fixed-family public tilts are capped by `log2 Z`, and H91 identifies
  collective/all-description coding as the nearest target at `0.277599` missing
  bits/record in the exact toy domain; H92 shows higher `K/D` can cross only
  under an underpriced width oracle, H93 shows paid J3D1 extended arity
  removes those crossings, and H94 shows normalized arithmetic rank/record
  coding still pays the hidden width-class channel; H95 shows fixed biased
  native expanders can move mass toward fertile outputs but conserve total
  Kraft mass; H96 shows neutral genotype choice creates measurable future
  lift but remains paid-cycle negative in an exact tiny domain; H97 scales that
  probe with sampling and same-budget random controls, still negative; H98
  shows partial slack refresh can either barely shrink while freshness dies or
  keep freshness while expanding once ready/carry is paid; H99 keeps seed
  parity alive only as a paid bounded-epoch discriminator; H100 identifies the
  exact forced two-epoch target: stateless readiness is available after a
  separate mechanism supplies `>1` paid bit/record of base margin; H101 shows
  neutral multiplicity can discount that readiness class below `1` bit/record,
  but the tested slack width cost overwhelms the discount; H102 finds a cleaner
  stateless shape where public lanes carry readiness and class-local seed ranks
  avoid the visible parity tax, leaving the narrower target `base margin > 0`;
  H103 verifies that in the exact H74/H94 toy: local class grammar preserves
  base Kraft mass exactly while visible global parity loses mass; H104 reconciles
  the current SPEC_V1 keep-what-decodes proofs with scaling: fixed checksum
  trial decode is a finite referee, not an unbounded birth/open channel; H105
  turns this into the nearest target: `custom_record K=6,D=12` still needs
  `0.468557` honest bits/record after public-lane readiness is free; H106
  proves ordinary public arity reweighting can raise whole-cover mass only to
  `log2Z=0`, not positive, unless the record grammar violates Kraft; H107
  shows biased value/seed grammars conserve the same `log2Z` and only create
  source-shaped wins under non-uniform data; H108 verifies this exactly with
  rational symbol masses and flags H92 lower as overfull/invalid; H109 prices
  the non-prefix/trial-decode escape as finite checksum/referee capacity, with
  ambiguous syntax growing exponentially unless a public invariant bounds the
  survivor set; H110/H111 isolate partial-refresh slack to payload-boundary
  cost; H112 shows an ordinary H2-charged frozen law still misses; H113 shows
  visible seed parity can replace H2 only with a forced two-epoch age invariant;
  H114 is the first paid crossing in that geometry, but it still needs an exact
  record-layer codec proof and literal/bootstrap accounting; H115 performs that
  first record-layer audit and downgrades H114 to a fixed-atom lower-bound
  crossing: force-refresh due-cohort rows expand under the frozen law, while
  local-width oracle rows remain negative; H116 then tests public arity/lane
  clocks and hidden target/age bucket diagnostics, and none recover the oracle
  in the bucketed frozen-law language; H117 corrects the parser model by coding
  payload width directly, finding a sparse near-miss but expansion once
  meaningful rewrite fraction is required; H118 then prices collective width
  amortization and shows the scale-1 count-free crossing vanishes under
  scaling; H119/H120/H121 close the obvious width-hiding routes by pricing
  deterministic lanes, seed-class/self-sync/referee equivalence, and public
  gap-typed boards; H122 tests a paid small gap alphabet and finds only
  fragile lower-bound near misses, not a zero-failure maintained-refresh
  crossing; H123 freezes public gap tables and gets negative lower-bound
  held-out rows only with high failure rates; H124 repairs failures with raw
  fallback and shows the markerless raw-atom margin
  (`-0.014587` to `-0.023438` bits/atom/pass) is swamped by the hidden
  raw/record type stream (`0.157-0.194` as a bitmap, `0.261-0.303` as run
  boundaries); H125 fixed public raw lanes/runs are parseable but fail all
  meaningful `25%` rewrite rows; H126 paid raw segments show one/two free
  segments still expand at `atoms=128`, and boundary lists cost far more than
  the H124 margin; H127 then sweeps `1%-25%` rewrite and finds no paid sweet
  spot after type-stream pricing; H128 shows a near-total public board would
  need roughly `99.77%-99.94%` public opening under the measured margins; H129
  tests counted raw-prefix zones and misses by `+0.097` to `+0.122`
  bits/atom/pass in focused rows; H130 shows near-total exceptions raise,
  rather than lower, the required witness boost versus all-open; H131 tests a
  typed all-open board and shows public slot metadata solves parsing but
  positive gain loses roughly-all coverage under the uniform hash law; H132
  tests self-consistent width-aware refresh selection and still misses on
  held-out rows, including hidden target-arity diagnostics; H133 tests
  common-cause batch witnesses and finds only valid Kraft redistributions or
  invalid overfull-code crossings; H134 tests CRT/modular readiness clocks and
  finds they reach but do not beat the `log2(P)` epoch floor; H135 starts the
  exact recurrent fertility-transfer harness but the first bounded control
  fails support rather than crossing; H136 tests non-contiguous final-board
  footprints and finds valid geometry reaches at most zero margin while unpaid
  footprint choice creates invalid crossings; H137 tests bits-back posterior
  tape as salt and finds conservation/final-settlement costs unless a separate
  `gamma>1` fertility law exists; H138 tests bounded reset ratchets and finds
  arbitrary-pass roughly-all savings require reset probability to shrink like
  `O(1/P)`; H139 adds the converse that visible state and hidden best-of
  selectors erase reset savings when paid; H140 confirms the `+1/+2` slack
  bundle-option multiplier is real in the local-width oracle but exact J3D1
  parseability leaves `B4,K32,s2` at `q=0.342932` with a `2.705` bits/rewrite
  ready/carry bill; H141 shows seed-derived/self-delimiting boundary tricks
  collapse to a fixed-width Kraft lane, where `B4,K32,delta=-1` has
  `q=0.393469` and `partial+H2=+0.954706` bits/atom; H142 optimizes the
  intrinsic width channel and finds the H120 pooled row needs `<=1.540537`
  width bits/record while optimal Kraft loss remains `5.341012`; H143
  shows near-total public boards need exact J3D1 openings around `q~=0.999`
  but slack<=2 only reaches `0.342932`, while slack=8 near-total rows still
  expand; H144 makes the user's non-greedy slack idea concrete as a future
  value target needing `0.008625-0.040116` bits/atom/candidate in the easiest
  rows; H145 prices multi-step unfolding as a stop-time/referee channel; H146
  measures exact slack-superposition transfer and finds real but insufficient
  visible-fertility lift (`N6,K5,D7,s14` still `-29.390338` bits/word);
  H147 shows upward/downward detours collapse to final address count unless
  branch/stop selection is public, visible, or paid; H148 replaces collective
  future scoring with an actual selected second-pass stream and loses support
  in the default exact row (`N4,K4,D7,slack12` pass1 coverage 1.0, pass2
  coverage 0.0); H149 composes fixed public decoders directly and identifies
  self-parse closure as the next bottleneck (`B1,K16,D4` 476 valid streams
  shrink to 3 two-pass-composable and 0 three-pass streams); H150 implements
  the min-plus selected-stream DP and shows support slack buys bloat rather
  than compression (`N4,K4,D7,slack20` pass2 coverage 0.625, final 29.1 bits
  for a 4-bit word); H151 prices closure by valid-stream restriction and finds
  multi-bit match-supply tax (`B1,K4,D7,t12` costs 5.415037 bits); H152
  confirms non-greedy visible path choice has real value (`N6,K5,D7,s18`
  lifts 1.890625 bits over greedy) but still leaves the explicit final stream
  far too long (41.593750 bits for 6 input bits), while the larger cloud gain
  is a paid rank/arithmetic gap (7.868868 bits); H153 turns that cloud into an
  honest public `Q` and confirms conservation: focused normalized-Q rows expand
  uniform targets by +1.456567 to +2.831486 bits, and the raw/Q mixture chooses
  alpha=0; H154 tests fixed-cell free closure and finds seed-address starvation:
  the best grid row touches only 12.9149% of cells and expects 111.468915
  untouched cells in a 128-cell layer; H155 stacks the public-lane target with
  H152 visible lift as a cross-domain target ledger and finds the live signal:
  the best lift exceeds H105's base gap by 0.108874 bits/word, but closure
  stress moves it back to +8.624339 and
  closure+width stress leaves the best stacked row +22.798591 bits/word; H156
  tests prefix completion as a closure repair and finds the conservation law:
  completed parse tax can fall to 0.142019 bits, but the row is 99.3534%
  filler and seed preservation restores the seed-only closure bill; H157 tests
  exact recursive selected streams with every layer seed-bearing and still
  finds expansion (`N4,K4,D4,P2` final 39.187500 bits for 4 input bits; loose
  `N3,K3,D3,P3` support 0.375000 with 117.000000 final bits); H158 instruments
  the SPEC-style keep-what-decodes referee and measures distinct pre-checksum
  outputs up to 180 in tiny Robin rows, so fixed checksum use is finite unless
  survivor output count is proven bounded; H159 builds the corrected
  seed-bearing closed-core graph and finds no recurrent SCC and no shorter
  predecessor in exact H96 probes (`K5,D3,cap28`: 21,387 nodes, 283 edges,
  srcTax 11.895128, scc_nodes 0, shortF 0); H160 replaces that finite graph
  with a transfer-matrix closure count, confirms the same closed count
  (`K5,D3,cap28 -> 283`), prices closure at clFrac 0.000258 / clTax
  11.918435 bits, and finds zero compressive closed paths; H161 moves the
  closure test to SPEC-style item targets and reopens a local signal
  (`seed_only B8,K5,D80,a2`: hitMass 0.179325, accMass 0.000276, saveMass
  0.000577, seqK 0.245625), but accepted compressive mass is still tiny and
  this is not yet a maintained full-cover drift result; H162 runs that
  non-greedy full-cover item-stream DP under current exact V1/J3D1 costs and
  still expands (`seed_only K5,D80,N32`: support 0.310, gain/item -4.110081;
  `mixed_all K5,D80,N32`: support 0.384, gain/item -3.472168, with literals);
  H163 tests paid higher arity in the same DP and finds no crossover (`fixed`
  K8/K16/K32 worsens at D80; `escape5 K16,D512,N32` reaches support 0.833 but
  still has gain/item -3.266563); H164 prices the remaining fertility-selected
  superposition knob and shows the smallest strict current miss is 8.361777
  bits/selected-record, equivalent to ideal best-of-M M~=329, while deeper D raises
  the per-record bar above 11 bits; H165 measures the actual same-cost neutral
  multiplicity available to that knob and finds only 0.20-0.25 option
  bits/record, equivalent to ideal best-of-M M~=1.15-1.19, far below the H164
  bar; H166 shows same-class visible selection has zero expected lift over
  same-budget random and the easiest row still has 8.112500 bits/record
  remaining after the H165 option credit; H167 then tests the emitted record
  stream itself and finds content lift is 0 by exchangeability, while visible
  length/order controls are nonpositive (`B8,K5,D512` exact has pass2|pass1
  0.430556, final/i -6.129032, orderLift/i -0.173387); H168 splits the
  remaining public-law target into two paid contracts: class restriction at
  f=0.10 needs 11.434428 bits/record after H165 option credit
  (11.683705 conservatively), while
  no-restriction population mode needs 81.125 bits/record for immediate
  uniform-start positivity at f=0.10 or must account for closed-attractor
  startup bloat; H169 tests simple public visible classes against actual H89
  paid witness savings and finds the best allowed net after class tax is still
  negative (`max_run<=5`: -4.955644 bits/word), while even the disallowed
  post-hoc oracle ceiling is only -3.041992 bits/word; H170 moves the same
  scan to native H96 emitted record strings and witness-mass tax, where the
  best allowed row is still `bits_suffix3=101` at -43.208690 bits/record-string
  and the disallowed future-saving oracle ceiling is -41.091462; H171 prices
  designed fertile sublanguages and shows restriction mode can at best repay
  its own class tax, with the easiest gap requiring 276.761605 Kraft mass from
  the fertile class alone; H172 tests the explicit fixed closed item-language
  recurrence `F_n=sum W_a F_{n-a}` and shows positive drift requires
  `sum W_a>1`, i.e. an overfull grammar; H173 applies the variational bound to
  no-tax population mode and shows concentration `c_t` costs `D(c||f)`, so
  Kraft-balanced laws have best net 0 and still miss by 8.112500 bits/record;
  H176 implements the public finite-state width/mixed-radix total-cover branch
  with corrected depth-clamped Lotus bucket counts and finds no maintained
  positive row, with the nearest high-arity miss at
  `B4,K128,D520,N128,r4,union:-1,2,P2` (`supportP=0.033333`,
  `packed gain/atom=-0.050781`); H177 extracts the exact Kraft cover bound
  `E_out <= 2^-s * sum_a 2^-ell(a)`, explaining why V1 flat cover is already
  subcritical (`Kraft=0.875`) and complete fixed-arity cover is only critical
  at zero savings; H178 prices the near-equal neutral-option escape hatch and
  finds only a tiny fixed-code fantasy surplus at `s=-1` (`+0.000389`
  bits/record) with poor support, while support-repaired rows remain negative;
  H179 prices generated/developmental reachable regimes and shows the
  reachable-set source tax cancels root-vs-phenotype savings for arbitrary
  uniform data; H180 tests cocycle/canonical placement and confirms the split:
  public zero-holonomy coordinates can make decode path-independent, but
  observed coordinates do not lift support, conditioned coordinates thin supply,
  and selected routes only repair support by paying route bits; H181 tests
  finite checksum/referee survivor pruning and shows reliable unique stateless
  decode needs `c ~= log2(M)` referee bits plus safety, while an `E=9.36`
  structural filter only buys a finite knee (`T=65536` still leaves
  `6.654372` bits/record); H182 tests public recurrent population laws as
  weighted transfer matrices and finds all honest row-mass `<=1` laws have
  `rho<=1`, while positive rows are explicitly overfull or source/reachable
  restricted; H183 implements the generated/reachable positive control:
  stateless root unfolding gives strong inside-class savings (`G=16,P=6`
  pays 34 bits for a 4096-bit phenotype), but arbitrary uniform data pays the
  reachable-set tax and nets `-18` bits in that row; H184 shows quotient/coset
  witnesses either lose hidden member bits as supply, pay them as selector
  entropy, or become public width packing with no row-mass lift; H185 shows
  survivor coalescence is conserved by preimage residual or source membership
  and can maintain `90%` coverage for only `Pmax=1.520031` passes at
  `0.1 bits/pass`; H186 shows digest-tail/bits-back state is decode geometry
  unless a separate `gamma>1` fertility/source law is supplied; H187 shows
  shared macro-witnesses can amortize record/tier overhead but target-tuple
  supply remains bounded by the stored rank width (`m=16,T_i=32,W_i=16` saves
  131 record bits but has coverage log2 `-256`); H188 shows syndrome/residual
  witnesses either pay the omitted ambiguity for arbitrary data or become
  source-shaped low-volume residual classes (`n=256,c=128` has paid net 0;
  low-weight `n=256,t=8` still misses by `0.411656` bits); H189 shows
  non-prefix uniquely decodable grammars are parser engineering, not row-mass
  escapes, because Sardinas-Patterson-valid scans still obey Kraft `<=1` while
  overfull grammars are ambiguous and spend referee/checksum bits; H190 tests
  whole-layer canonical-minimum selection directly and finds the free-boundary
  oracle can gain tiny fractions of a bit (`N=16,Wmax=16`: `+0.008347`) only by
  omitting the raw-vs-witness syntax choice, while the paid one-bit parse mode
  is `-0.991653` bits; H191 tightens that bill with leftover Kraft raw fallback
  and finds the best nontrivial default miss at only `-0.007365` bits/layer but
  still negative; H192 tests the normalized arithmetic/bits-back mixture and
  shows the exact leftover point (`N=16,Wmax=16,lambda=q=0.076172`) has
  `gain=-0.063559`, while nonzero mixture weight approaches a tie only as the
  witness effect vanishes; H193 tests syntax-derived ready states and closed
  canonical partitions, finding public DFA state remains negative on arbitrary
  uniform targets (`N=16,Wmax=16,short,raw/canonpart`: `gainU=-0.000198`) and
  the closest closed-partition row (`N=16,Wmax=8,t=1`) reaches `gainU=-0.000113`
  only after support collapses to `9/65536`; H194 tests public finite-state
  language transforms and separates apparent syntax gain from real input gain:
  `maxrun2,N=8,m=11,W=4,semantic_reclaim` has `realGain=-0.000721` despite
  `appGain=2.999279`, while bounded balanced `primdyck4,N=8,m=18,W=16` reaches
  only `realGain=-0.000000013` by nearly turning witness mass off; H195 tests
  public paid salt-lane smoothing and reaches the sharp nonzero-witness miss
  `N=8,Wmax=8,lanes=4096,all` with `q=0.050781`, full support, and
  `gain=-0.000005239`, confirming that public lanes can flatten witness mass
  toward a tie but not below `N + D(U||Q)`; H196 tests recursive source-law
  resonance and shows the best case `P=Q` ties exactly (`N8,W8,L4096,beta1`
  apparent gain `+0.000005242`, source tax `+0.000005242`, paid net `0`);
  H197 tests hidden-lane/referee overfullness and finds the selector/referee
  bill dominates (`W8,L32` surplus `0.700440`, lane selector `5`, exact net
  `-4.299560`); H198 makes the generated positive branch Telomere-native:
  `G16,C8,B32,A5,P6` has inside generated gain `499965`, min per-pass step gain
  `59`, and optimistic arbitrary-uniform net `-19` (`-11` when pass count is a
  fixed public preset); H199 tests direct residual attachment to that generated
  tree and finds pair-count cancellation (`N16,G4,r8` full coverage but
  `ideal_net=-16.258676`; large H198 bound remains `G-paid=-11`); H200 tests
  high-coverage nearest-generated residuals and finds even the paid-index lower
  bound expands at 99% coverage (`+2.184448` Kraft-fallback delta), while native
  H198 fixed expands by `+13.070864`; H201 tests multi-root XOR generated
  residuals and finds sparse support ties only under paid selected-root rank
  while native records lose (`k4,N16` native net `-57.170277`), and full spans
  leave source gaps (`N500000,m16` rank bound `65536`, gap `434464`); H202
  tests H198 recombination/crossover and finds the same rank conservation:
  crossover points add reachable support and decoder rank together, leaving the
  large fixed H198 bound at `native_fixed_net=-21` for two parents and `-41`
  for four parents; H203 makes the crossover schedule decoder-derived, which
  removes the rank bill but also removes the support boost (`support_bound=32`
  for two H198 roots and `64` for four), leaving the same native losses; H204
  shows public orbit selection either thins support or pays an accepted-index
  rank; H205 gives a strong visible-population generated lineage
  (`M32,G16,A5,P6` pays 833 bits for 16,000,000 generated bits) but arbitrary
  uniform net remains `-321`; H206 optimizes that family and finds the best
  scanned arbitrary-uniform miss is `-7` bits overall, or `-8` for the
  high-growth `A=5` branch; H207 ideal packed roots close that miss only to
  a generated-only tie (`uniform_net=0` with no mode/fallback), while any
  parseable mode or raw fallback restores Kraft expansion; H208 converts the
  visible-population branch into a normalized prior with near-zero uniform
  overhead but source-shaped gains cancel after the `D(P||Q)` tax; H209 turns
  that visible-population branch into an explicit exact codec with raw escape:
  the tiny `N=8` row round-trips all outputs and the large
  `M32,G16,A5,P6,N16000000` row still gains `15999167` bits inside the
  generated class while arbitrary-uniform membership leaves `-321`; H210 prices
  final-board/position channels directly (`R1000,Q1111,rho0.9` occupancy is
  only `0.516089` bits/record, but `P64` birth labels need `6` bits/record and
  leave `5483.911082` residual bits); H211 enumerates the actual emitted stream
  law and shows self-induced bias can at best tie (`N8,W8` has
  `H_emit=8`, `mean=8.996094`, oracle `Q=P_emit` paid net `0`); H212 finds a
  legal non-greedy steering primitive because the stored seed carries its own
  digest tail (`B8,A1,W8,S2,credit2` zero-slack lookahead lifts tail success
  `0.512528 -> 0.578588`, while `slack=1` lifts to `0.637813` and pays
  `0.059226` bits), but the future fertility credit is still an external
  priced law;
- otherwise, under the original uniform/content-blind roughly-all-data premise,
  the recursive stateless branch is closed by H15/H16.

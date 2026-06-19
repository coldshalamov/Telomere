# Conjecture / Test / Mutation Log

Date started: 2026-06-18

Purpose: keep the active recursive Telomere search moving as a research loop,
not as a static verdict. Each entry must state a precise conjecture, the
smallest exact or symbolic model, the paid bill observed, and the next mutation.

## Current Contract

Find a deterministic, lossless, statelessly decodable Telomere recursion
mechanism that preserves useful exact-witness supply across many passes and
achieves negative paid length drift in at least one nontrivial recursive regime,
including a bounded or generated/reachable regime.

Every candidate separates:

```text
witness supply
naming cost
cover geometry
recursive drift
decoder-known state
exact bits in/out
bad tails and support
```

Total-cover rows do not charge sparse open/carry, birth-pass maps, hit maps,
final-position maps, or PCTB ledgers unless the mechanism reintroduces sparse
carried records.

## Ranked Live Directions

| Rank | Direction | Why It Is Live | Exact Next Kernel |
| ---: | --- | --- | --- |
| 1 | No-tax recurrent population law | H179 closes ordinary generated regimes for arbitrary data; H180 closes cocycle geometry as supply. Only a genuine recurrent population bias not paid as source KL could break H177. | Transfer-matrix population law with uniform controls. |
| 2 | Unknown non-prefix finite-referee law | H109/H158 show checksum/referee is finite; a live variant would need bounded survivor count with paid proof. | Survivor-growth capacity kernel. |
| 3 | Final-board dense/near-total geometry | H174 shows sparse boards are expensive per survivor, but dense boards can be under a 2-bit note only after actual survivor collapse. | Combine H174 with actual survivor collapse rows. |
| 4 | Cocycle / canonical placement | H180 solves decode geometry but not supply; keep as scaffold only. | Reuse only after a separate positive drift mechanism exists. |
| 5 | Equal-cost / near-equal witness lookahead | H178 shows neutral options are real but conserved; keep only as a component after another mechanism supplies support. | Use as auxiliary metric in future kernels. |

## H174 - Final-Board Salt Capacity

Conjecture:

```text
If R final survivors shrink enough, final positions stored once can amortize
birth/open/salt state better than a per-pass diary.
```

Small model:

```text
unordered occupancy = log2 C(Q,R)
ordered occupancy = log2 (Q)_R
valid arrangements = log2 |E_valid|
public lane counts = log2 product_p C(Q_p,r_p)
```

Result:

- Shrinking `R` makes the note cheap per original atom.
- Per survivor, sparse boards get expensive.
- `Q=N`, `R/Q=0.5` is about `2` bits/survivor; `R/Q=0.1` is `4.690`.
- Public lanes trade state entropy for match-supply loss.
- PCTB mechanics round-trip, but carry-only at `P=64` bloats to `21.867x` raw.

Bill:

```text
log2(valid final arrangements)
```

Mutation:

Dense/near-total board only. The next test must compare measured salted gain
per survivor against exact final-state cost per survivor.

## H175 - State-Carrying Digest-Tail Transducer

Conjecture:

```text
Every exact witness can emit q_next as unconstrained digest tail; the decoder
uses q_next as the next salt without storing salt or reducing match supply.
```

Small model:

```text
z = H(q_i, arity_i, seed_i)
x_i = z[:arity_i*B]
q_{i+1} = z[arity_i*B : arity_i*B+r]
record = [arity][J3D1 seed]
DP state = (position, q_i)
```

Result:

- Tail sanity validates observe-vs-condition:
  `D=10,r=4` gives observed conditioned ratio `0.064047` vs expected `0.0625`.
- Exact V1/J3D1 current-pass rows still expand:
  `B4,K5,D12,atoms8` best tested slack row has `out/in=1.438`.
- Bounded-slack two-pass lookahead is a real signal:
  `B4,K5,D8,atoms8` slack+4 improves exact two-pass cost in `3/4` trials with
  `2p delta=15.750` bits in the tiny beam run.
- The sampled recursive trellis extension keeps `B4,K5,D12,items16` pass-one
  support at `1.0`, but exact V1/J3D1 support collapses by two to three passes:
  the best `r=4,slack:4` row has `passes=2` complete support `0.05` and
  `passes=3` complete support `0.0`.

Bill:

```text
arity + J3D1 seed witness + any anchors/segments + layer framing
```

No bill for observing `q_next`; `r` bits are paid only if a tail class is
conditioned.

Mutation:

State-carrying salt is not enough. Combine it with:

```text
bounded-slack surface lookahead
public finite-state width grammar
whole-layer mixed-radix payload packing
higher-arity/custom total-cover witness language
```

The immediate bill is recursive surface fertility: emitted record-length/item
streams must remain coverable, not merely salted.

## Width Grammar / Mixed-Radix Packing

Conjecture:

```text
If witness widths are decoder-derived from public finite state, a layer can pack
payload ranks in one mixed-radix integer and avoid repeated Lotus delimiters.
```

Small model:

```text
w_i = W(q_i, position_i, arity_i, public layer facts)
record_i = [arity_i][payload_i exactly w_i bits]
payload layer cost = ceil(sum_i log2 M_i)
```

Known bill:

- If widths are content-selected, pay width entropy:
  `L_width >= log2 multinomial(width_counts)`.
- Prior width-channel rows measured `H(W)=5.341012 bits/record` while the
  break-even width entropy was only `1.540537`.

Mutation:

H176 implemented the strict inventory version and found no maintained positive
row. The nearest high-arity miss in the tested custom fixed-arity language was:

```text
B4,K128,D520,N128,r4,union_arity_margin:-1,2,P2
support1=0.133333, supportP=0.033333
inline gain/atom=-0.074219
packed gain/atom=-0.050781
```

The important correction was frontier bucket accounting:

```text
C_D(w) = min(count_le(w), 2^D) - min(count_le(w-1), 2^D)
```

At width `D`, the exact reachable bucket is not `2^D`.

Mutation:

Do not keep sweeping public width grammars blindly. H177 gives the general
reason strict savings lose support. Continue only with a mechanism that breaks
one H177 premise honestly: generated regime, paid public law, same-cost
lookahead option value, or canonical placement with charged exceptions.

## H177 - Kraft Cover Bound

Conjecture:

```text
In total-cover, if each record saves s paid bits and arity is prefix-free,
the cover graph has expected outgoing degree <= 2^-s.
```

Small model:

```text
candidate_count(a) <= 2^(target_bits - ell(a) - s)
P(edge_a) <= 2^-(ell(a)+s)
E_out <= 2^-s * sum_a 2^-ell(a)
```

Result:

- V1 arity has Kraft sum `0.875`, so even flat `s=0` is subcritical over long
  full-cover lines.
- A complete fixed arity code has Kraft sum `1`; flat cover is only critical.
- Strict paid savings `s>0` are subcritical for every valid prefix arity code.
- Bloat `s<0` is supercritical but expands; larger `K` only makes bloat per
  atom smaller by raising average arity.

Representative executable rows:

```text
v1 K5,N128,s=-1: support=0.266000, Eout=1.750000
v1 K5,N128,s=0:  support=0.000000, Eout=0.875000
v1 K5,N128,s=1:  support=0.000000, Eout=0.437500
fixed K8,N64,s=0: support=0.010000, Eout=1.000000
fixed K8,N64,s=1: support=0.000000, Eout=0.500000
```

Bill:

This is not an open/carry or salt bill. It is the arity/rank Kraft bill inside
the total-cover branch.

Mutation:

The strongest next attack is near-equal witness lookahead with an explicit
option-capacity ledger. If +b bits of current slack creates at most b bits of
usable collision-choice capacity, it cannot cross; if a structured reachable
surface gets more than b future savings, it becomes the first real wedge.

## H178 - Neutral Option Capacity

Conjecture:

```text
Free choice among same-cost witnesses carries at most log2(H) bits of future
steering, where H is the number of matching witnesses already represented by
the emitted seed.
```

Small model:

```text
lambda = Kraft(arity) * 2^(-s)
H ~ Poisson(lambda) conditioned on H>0
option = E[log2(H) | H>0]
fantasy_net = s + option
```

Result:

- V1 has no positive supercritical option row. `K5,N128,s=-1` has
  `path_support=0.307`, `option=0.880294`, and `fantasy_net=-0.119706`.
- Complete fixed arity has a tiny `s=-1` local fantasy surplus:
  `option=1.000389`, `fantasy_net=+0.000389`.
- That knife-edge fails support: `K8,N128` gives `path_support=0.709`;
  `K128,N128` gives `path_support=0.106`.
- Rows with support above about `0.95` are negative even before parser/fallback:
  fixed `K8,N128,s=-2` has `path_support=0.990` and
  `fantasy_net=-0.161204`; fixed `s=-8` has full support and
  `fantasy_net=-0.002818`.

Bill:

Non-emitted candidate clouds, future-score ranks, per-file profiles, and route
choices are selectors. The only free option is the identity of the seed that is
actually emitted.

Mutation:

Neutral lookahead alone is closed. Keep it as an auxiliary gain source only
inside a later mechanism that already supplies full-cover support without
large bloat.

## H179 - Reachable Regime Tax

Conjecture:

```text
A public developmental interpreter can compress its reachable/generated class,
but the reachable-set entropy tax cancels the saving for arbitrary data.
```

Small model:

```text
G root bits -> N*P phenotype bits
generated_gain = N*P - G - header
reachable_tax = N*P - G
uniform_net = -header
```

Result:

Example `G=12,P=128,N=64,header=0`:

```text
generated_gain=8180 bits
reachable_tax=8180 bits
uniform_net=0 bits
```

Bill:

The generated class fraction is at most `rho=2^(G-NP)`. If the source is not
known to come from that class, membership/source restriction costs `-log2(rho)`.

Mutation:

Developmental/DNA-like interpreters remain valid source-shaped Telomere
mechanisms. For the arbitrary-content goal, the live requirement is a no-tax
recurrent population law, not merely a rare generated subset.

## H180 - Cocycle / Canonical Placement

Conjecture:

```text
Zero-holonomy public coordinates can make decode path-independent, but they do
not create exact-witness supply.
```

Small model:

```text
baseline: H177 support
observed_coord: random digest-tail coordinate is observed
endpoint: final coordinate must be public zero
edge_zero: every edge is conditioned to zero coordinate
paid_routes: d route choices with log2(d) route bill
```

Result:

- Fixed `K8,N128,s=-1`: baseline support `0.676`; observed `g=4` support
  `0.668`; endpoint `g=4` support `0.691`; edge-zero `g=4` support `0.000`.
- Paid routes repair support by spending selector bits: fixed
  `K8,N128,s=0,d=4` has support `0.969` but paid gain/record `-2.000`.
- Public potentials pass diamond confluence at `1.0`; random edge labels pass
  zero holonomy at `0.067` for `g=4`, matching expected `2^-4=0.0625`.

Bill:

```text
E_out <= sum_a alpha(a) * 2^-(ell(a)+s) <= 2^-s
```

where public placement has `alpha<=1`; conditioned coordinates multiply supply
by `2^-g`; selected routes cost `log2(d)`.

Mutation:

Close cocycle placement as an independent supply source. Keep it as a decoder
scaffold only if another mechanism later supplies paid negative drift.

## H181 - Finite Referee / Survivor Capacity

Conjecture:

```text
A finite checksum/referee can prune hidden non-prefix or trial-decode readings
only by paying the entropy of those readings.
```

Small model:

```text
M hidden readings = b^(records*passes)
true reading always passes stored/root referee
each false reading survives with probability 2^-c
P(unique) ~= exp(-M/2^c)
```

Result:

- `b=2,R=8,P=1,c=8` gives `Efalse=1` and `p_unique=0.367879`.
- `b=2,R=8,P=1,c=16` gives `p_unique=0.996101` but pays
  `2.000000 bits/step` for a `1.000000 bits/step` hidden branch.
- `b=2,R=32,P=16` at 99% uniqueness needs `c_req=519`, or
  `1.013672 bits/step`, slightly more than the hidden branch entropy.
- `b=4,R=32,P=16` at 99% uniqueness needs `c_req=1031`, or
  `2.013672 bits/step`.
- Exact tiny check: `4096` candidates with `20` referee bits measured
  `p_unique=0.996000`, matching `0.996101`.

Bill:

Reliable stateless decode needs:

```text
c >= log2(M) - log2(-ln(target_unique))
```

The referee bill cancels the hidden branch entropy, and fixed small `c` fails
as records or passes grow.

Mutation:

Use finite referees only as bounded audit guards. The live attacks are now:
make branch choices public by construction, prove a no-tax recurrent population
law, or restrict to a generated/reachable regime and pay its membership tax.

## H182 - Transfer-Matrix Population Law

Conjecture:

```text
A public visible record/class population preserves witness supply across passes
only if its paid transfer matrix has spectral radius greater than one.
```

Small model:

```text
W_ij = paid witness/Kraft mass from visible class i to class j
asymptotic no-tax margin = log2 rho(W)
valid fixed public law has row sums <= 1
```

Result:

- Exact V1 flat law has `rho=0.875000`, `log2rho=-0.192645`.
- Complete fixed `K=8` flat law is critical only: `rho=1`, `log2rho=0`.
- Strict one-bit saving gives `rho=0.5`, `log2rho=-1`.
- Balanced rare fertility can concentrate the equality population at
  `80%` fertile, but `KL=1.966015` equals visible value `1.966015`, net `0`.
- Positive rows (`overfull_rare_rank_one` at `log2rho=0.765535`,
  `closed_fertile_overfull` at `log2rho=0.111031`) have row mass `>1`.
- Random substochastic controls: `1000` size-4 laws had
  `max_rho=0.912875`, `log2(max_rho)=-0.131511`.

Bill:

```text
max_i sum_j W_ij <= 1  =>  rho(W) <= 1
```

Any positive frozen public population law either spends overfull hidden mass or
requires real source bias/reachable-set tax.

Mutation:

Stop assigning fertility to visible classes unless the row-mass bound changes.
Next attacks should target a bounded generated regime with all tax charged, or
a genuinely non-Kraft witness inventory that remains statelessly parseable.

## H183 - Generated / Reachable Recursive Codec

Conjecture:

```text
A generated reachable regime can have real negative paid drift and stateless
recursive decode, but arbitrary-content use pays reachable-set membership.
```

Small model:

```text
[mode][arity=1 root witness][optional pass count]
public BLAKE2b counter expander unfolds root for P passes
```

The root witness uses exact V1/J3D1 record cost. Decode is deterministic and
stateless except for the fixed/root header.

Result:

- `G=8,P=2,out=64`: `paid=24`, `gain_inside=40`, `tax=56`,
  `uniform_net=-16`, `256/256` unique roots.
- `G=12,P=4,out=512`: `paid=28`, `gain_inside=484`, `tax=500`,
  `uniform_net=-16`, `4096/4096` unique roots.
- `G=16,P=6,out=4096`: `paid=34`, `gain_inside=4062`, `tax=4080`,
  `uniform_net=-18`, `65536/65536` unique roots.

Bill:

```text
inside_gain = N - paid_bits
reachable_tax = N - G
uniform_net = inside_gain - reachable_tax
```

Mutation:

This gives a clean source-shaped positive control. It does not solve arbitrary
content; the remaining arbitrary target must change the paid row-mass/Kraft
bound or make source membership explicit.

## H184 - Quotient / Coset Witness Language

Conjecture:

```text
Store [arity][coset id] and let public decode derive the exact seed member.
```

Small model:

```text
payload width W, hidden member bits q, records R
direct V1/J3D1 cost versus quotient cost plus selector/referee
```

Result:

- `W=32,q=16,R=32`: direct `42`, quotient `25`, selector `16`,
  local `41`, so only `1` tier bit is saved; checksum work is `2^512`.
- `W=128,q=64,R=128`: direct `140`, quotient `75`, selector `64`,
  local `139`; checksum work is `2^8192`.
- `W=508,q=64,R=128`: selector exactly returns to direct cost.
- Public width/layer-rank packing can save Lotus overhead
  (`W=128,R=128` saves `9.898438 bits/record`) but gives no supply boost.

Bill:

Deterministic coset representatives lose `q` bits of match supply. Noncanonical
members require `q` selector/referee bits per record, or exponential decode
over `2^(qR)` assignments.

Mutation:

Keep public width packing as a custom witness mode; close cosets as a free
row-mass escape.

## H185 - Variable-To-One Coalescence Capacity

Conjecture:

```text
Many current records collapse into fewer survivors, and survivor shrink itself
maintains stateless compression.
```

Small model:

```text
N-bit layer -> L=N-s bits over covered fraction f
residual >= max(0, s + log2(f))
source tax = -log2(f)
coverage ceiling without residual/source tax = 2^-s
```

Result:

- `N=4096,s=1,f=1`: residual `1`, paid net `0`, but coverage without
  residual/source channel is at most `0.5`.
- `N=4096,s=4,f=0.1`: residual `0.678072`, tax `3.321928`, paid net `0`,
  but coverage ceiling is `0.0625`.
- Tiny random coalescer `N=12,L=8` has mean preimage `16`, residual lower
  bound `4`, gain `4`, paid net lower bound `0`.
- Maintained saving `s/pass=0.1` can keep `90%` coverage for only
  `Pmax=1.520031` passes without paying residual/source tax.

Bill:

Coalescence is conserved by preimage entropy or source membership.

Mutation:

Keep coalescence as generated/final-board geometry only. It cannot supply
arbitrary-content drift without another paid row-mass breakthrough.

## H186 - State-Tail Conservation Certificate

Conjecture:

```text
Digest-tail or bits-back state can carry salt/fertility across passes for free.
```

Small model:

```text
observe state, condition state, select state, bits-back tape with gamma
base_mass = arity_kraft * 2^-saving
```

Result:

- V1 `s=0 observe`: rowMass `0.875000`, log2rho `-0.192645`.
- V1 `s=0 condition r=8`: rowMass `0.003418`, log2rho `-8.192645`.
- V1 `s=0 selected d=16`: rowMass `1.000000`, log2rho `0`, but paid gain
  `-4 bits/record`.
- Bits-back `gap=0.1,r=4,P=16,gamma=1` has net `-5.6`.
- Positive bits-back rows require `gamma>1`, e.g. `gamma=1.1` gives net
  `0.8` only by assuming separate fertility.

Bill:

Observed state is geometry; conditioned state costs supply; selected state
costs selector entropy; bits-back is conserved at `gamma=1`.

Mutation:

Digest-tail state remains a salting/decode scaffold. The live target is still a
separate honest `gamma>1` fertility or row-mass mechanism.

## H187 - Shared Macro-Witness / Batch Seed

Conjecture:

```text
One witness can carry many spans and amortize witness cost enough to maintain
recursive supply.
```

Small model:

```text
m spans, T_i target bits each, W_i rank bits each
independent V1 records vs public layer packing vs one joint seed
coverage log2 = W_total - T_total
```

Result:

- `m=4,T_i=16,W_i=8`: `T=64`, independent `64`, packed `48`, joint `42`,
  `saveJ=22`, but coverage log2 is `-32`.
- `m=8,T_i=16,W_i=16`: `T=128`, independent `200`, packed `153`,
  joint `140`, `saveJ=60`, coverage log2 `0`.
- `m=16,T_i=32,W_i=16`: `T=512`, independent `400`, packed `297`,
  joint `269`, `saveJ=131`, coverage log2 `-256`.

Bill:

A `W`-bit macro rank names at most `2^W` target tuples. Shared headers reduce
overhead, not target-tuple supply.

Mutation:

Keep macro witnesses as overhead amortization and generated-regime geometry,
not a row-mass escape.

## H188 - Syndrome / Algebraic Residual Ledger

Conjecture:

```text
A seed plus syndrome/parity equations can reconstruct arbitrary targets without
storing the full residual.
```

Small model:

```text
e = target xor expand(seed)
c-bit syndrome leaves n-c residual bits
low-volume residual class pays membership tax under uniform data
```

Result:

- `n=256,seed=0,c=128`: stored `128`, ambiguity `128`, paid unique `256`,
  net versus raw `0`.
- `n=1024,seed=32,c=256`: stored `288`, ambiguity `768`, paid unique `1056`,
  net versus raw `-32`.
- Low-weight `n=256,t=8`: inside gain `207`, class tax `207.411656`,
  uniform net `-0.411656`.
- Low-weight `n=1024,t=16`: inside gain `908`, class tax `908.397029`,
  uniform net `-0.397029`.

Bill:

Short syndromes are ambiguous; full residuals return to raw length; low-volume
residuals are source-shaped positives only.

Mutation:

Keep algebraic residuals as repair languages for explicit source classes, not
arbitrary all-content compression.

## H189 - Non-Prefix Uniquely-Decodable Kraft Check

Conjecture:

```text
Non-prefix/self-synchronizing grammars might exceed prefix Kraft mass while
remaining statelessly decodable.
```

Small model:

```text
Exhaust binary codebooks with word length <=4; test UD by Sardinas-Patterson.
```

Result:

- Size `2..5` scans found many non-prefix UD codebooks, but no UD Kraft sum
  above `1`.
- Best non-prefix UD Kraft reaches `1.000000` for sizes `3..5`.
- Overfull examples are non-UD, e.g. `0,1,00` has Kraft `1.25`.

Bill:

Kraft-McMillan applies to uniquely decodable non-prefix codes too.

Mutation:

Keep non-prefix grammar as parseability engineering only. It is not row-mass
fuel.

## Canonical Coupled Placement / Spatial Total-Cover

Conjecture:

```text
Canonical placement/peeling can make route choice public and reduce failure
tails for near-total forced rewrite.
```

Small model:

```text
interval witness -> d public candidate slots
decoder applies canonical orientation/peeling
exceptions and noncanonical route choices are charged
```

Known bill:

- Public route: free only if canonical.
- Encoder-selected route/list/fertility choice: selector/rank entropy.
- Public lane/list thinning: `-log2(1-(1-r)^d)`.
- The current strongest forced-rewrite witness target still needs about
  `0.468557 bits/record` of real witness/Kraft boost.

Mutation:

Implement H178 by fusing footprint accounting, canonical placement, and
forced-rewrite witness margins. Report peel failure/core size and charged
exceptions.

## H190 - Whole-Layer Minimum-Description Ledger

Conjecture:

```text
A whole-layer canonical minimum over many witness widths can use the shortest
available description plus raw fallback to cross on uniform targets.
```

Small model:

```text
enumerate all N-bit outputs
map exact V1/J3D1 witnesses up to Wmax into outputs
choose shortest witness or raw fallback
compare unparseable oracle against paid raw/witness mode bit
```

Result:

- `N=8,Wmax=16`: oracle gain `0.003906`, paid gain `-0.996094`.
- `N=12,Wmax=16`: oracle gain `0.011719`, paid gain `-0.988281`.
- `N=16,Wmax=16`: oracle gain `0.008347`, paid gain `-0.991653`.

Bill:

The oracle leaves the raw-vs-witness syntax choice outside the stream. A single
parse bit removes the gain and restores the uniform source-code bound.

Mutation:

Any future whole-layer macro/canonical-minimum claim must beat the paid ledger,
not only the free-boundary oracle.

## H191 - Kraft-Reserved Raw Fallback

Conjecture:

```text
The H190 one-bit raw/witness mode can be replaced by an optimal leftover-Kraft
raw fallback, perhaps recovering the missing bit.
```

Small model:

```text
enumerate all N-bit outputs and exact V1/J3D1 witnesses up to Wmax
witness syntax consumes Kraft mass q
raw fallback costs N - log2(1-q)
compare all syntactic aliases versus generous canonical shortest aliases
```

Result:

- `N=8,Wmax=16,canonical`: `q=0.007812`, `rawFrac=8.011315`,
  `gainFrac=-0.007365`.
- `N=16,Wmax=16,canonical`: `q=0.050766`, `rawFrac=16.075164`,
  `gainFrac=-0.066205`.
- `N=16,Wmax=16,all_syntax`: `q=0.076172`, `rawFrac=16.114304`,
  `gainFrac=-0.105041`.

Bill:

The mode bit shrinks to a fractional Kraft-reservation bill, but the fallback
alphabet lengthens for the rest of the uniform space.

Mutation:

Stop blaming the full one-bit mode. The tightened paid channel still misses;
next attacks must change recurrence/syntax, not local mode coding.

## H192 - Normalized Mixture / Bits-Back Ledger

Conjecture:

```text
Arithmetic coding, ANS, or bits-back can normalize raw and witness routes and
recover the H190 parse bill.
```

Small model:

```text
s_x = sum witness Kraft mass landing on output x
Q_lambda(x) = (1-lambda)U(x) + lambda*s_x/q
also test exact leftover point lambda=q, Q=(1-q)U+s
```

Result:

- `N=16,Wmax=16,lambda=q=0.076172`: `meanLen=16.063559`,
  `gain=-0.063559`.
- `N=16,Wmax=16,lambda=0.001`: `gain=-0.000247`.
- Best nonzero grid row: `N=8,Wmax=16,lambda=0.001` at
  `-0.000002682 bits/layer`.

Bill:

`E_U[-log2 Q(X)] = N + D(U||Q)`. The gap approaches zero only as
`lambda -> 0`, which also removes the witness effect.

Mutation:

Move to closed syntax / ready-set recurrence. Bits-back can implement a source
law, but it is not the source law.

## H193 - Syntax-Derived Ready-State Transfer

Conjecture:

```text
Decoded syntax can derive raw-ready versus witness-ready states, so the mode is
public and future witness supply remains alive across passes.
```

Small model:

```text
two-state public DFA over decoded N-bit outputs
state chooses raw / all-witness mixture / best-witness mixture / canonical
partition coding
next state is parity, covered, short-covered, or toggle-covered
closed partition C_{t+1}: canonical witness child remains in C_t
```

Result:

- Ready-state nearest default row:
  `N=16,Wmax=16,rule=short,raw/canonpart` has `gainU=-0.000198`,
  while its `inside_gain=0.000749` is source-shaped.
- Closed-partition nearest nonzero-support row:
  `N=16,Wmax=8,t=1` has `support=9/65536` and `gainU=-0.000113`.
- Further closure reaches support `0`, a tie only because no witness mechanism
  remains.

Bill:

`E_U[-log2 P_q(X)] = N + D(U||P_q)`. Public state is geometry unless it predicts
the next target; if it predicts by construction, the same KL appears as source
tax. Closed partitions trade the local bill for support collapse.

Mutation:

Move to finite-state reversible language/transform search: force all inputs
into public self-delimiting syntax, price `m-N`, then test whether witness
supply and closure improve after that honest transform tax.

## H194 - Finite-State Language Transform

Conjecture:

```text
A reversible public finite-state/self-delimiting language transform can force
all inputs into parseable syntax and preserve witness supply without hidden mode
bits or source restriction.
```

Small model:

```text
choose language L and minimal m with |L_m| >= 2^N
map raw rank 0..2^N-1 to the first 2^N accepted m-bit words
hash exact V1/J3D1 witnesses to m-bit words
price all_syntax and semantic_reclaim witness accounting
compare paid mean to original N and expanded syntax m
```

Result:

- Default nearest row:
  `maxrun2,N=8,m=11,W=4,semantic_reclaim` has `realGain=-0.000721`
  but `appGain=2.999279`.
- Bounded balanced edge:
  `primdyck4,N=8,m=18,W=16,semantic_reclaim` has
  `realGain=-0.000000013` and `appGain=10.000000`.

Bill:

The apparent syntax gain is the transform expansion. The real source has only
`N` bits, and for the selected transform image:

```text
E_U[-log2 Q(T(x))] = N + D(U_S || Q) - log2 Q(S) >= N
```

Mutation:

Finite-state transforms help parse geometry but do not make arbitrary-uniform
negative drift. The next useful target is not more surface syntax; it is a
mechanism that gives nonzero witness effect while keeping `D(U||Q)` near zero
and support from collapsing.

## H195 - Public Multi-Salt Witness-Mass Smoothing

Conjecture:

```text
Many public decoder-known salt lanes can preserve fresh exact-witness supply
and smooth witness mass enough that leftover raw fallback becomes negative on
arbitrary uniform layers.
```

Small model:

```text
output = H(public_lane, payload_width, rank) mod 2^N
length = record_cost_for_payload_width(1, payload_width) + ceil(log2 lanes)
s_x    = sum witness Kraft mass landing on x
Q(x)   = (1-q)/2^N + s_x
```

Result:

- Default nearest row:
  `N=8,Wmax=8,lanes=16,all` has `q=0.050781`, full support, and
  `gain=-0.000956`.
- Extended smoother:
  `N=8,Wmax=8,lanes=4096,all` keeps `q=0.050781`, full support, and reaches
  `gain=-0.000005239`.
- `N=12,Wmax=8,lanes=512,all` has full support and `gain=-0.000517`.
- `N=16,Wmax=8,lanes=256,all` reaches support `56594/65536` and
  `gain=-0.009580`.

Bill:

```text
E_U[-log2 Q(X)] = N + D(U || Q) >= N
```

Public lanes reduce the KL gap by making `s_x` flatter. With lane ids paid,
they approach equality only; without lane ids they overfill Kraft mass.

Mutation:

Do not spend more effort on independent public salt smoothing by itself. Reuse
it only as a component in a source/reachable regime or in a genuinely bounded
referee/ambiguity construction whose surplus survives its own bill.

## H196 - Self-Induced Source Law / Recursive Output-Law Ledger

Conjecture:

```text
Recursive Telomere output may become non-uniform in exactly the way the next
pass wants, creating maintained compression without external structure.
```

Small model:

```text
Q(x) = H195 paid public-lane witness/fallback distribution
P_beta(x) proportional to Q(x)^beta
apparent_gain = N - CE(P_beta,Q)
source_tax    = N - H(P_beta)
paid_net      = H(P_beta) - CE(P_beta,Q)
```

Result:

- `N=8,Wmax=8,lanes=4096,beta=0` reproduces H195:
  `paidNet=-0.000005239`.
- `N=8,Wmax=8,lanes=4096,beta=1` has apparent gain
  `+0.000005242`, but source tax `+0.000005242`, so `paidNet=0`.
- `N=12,Wmax=8,lanes=512,beta=1` has apparent gain and source tax
  `+0.000524`, so `paidNet=0`.
- More concentrated sources go negative by KL, e.g.
  `N=12,Wmax=8,lanes=512,beta=2` has `paidNet=-0.000547`.

Bill:

```text
paid_net = -D(P||Q) <= 0
```

Mutation:

Recursive output-law resonance can only tie for arbitrary data unless the
non-uniform law is a declared source/reachable class. Move next to bounded
overfull/referee surplus or a more Telomere-native generated/developmental
regime with explicit membership tax.

## H197 - Bounded Referee / Hidden-Lane Overfull Closure

Conjecture:

```text
Ambiguous overfull witness families can exceed Kraft locally, and a bounded
checksum/referee can cheaply prune candidate decodes.
```

Small model:

```text
coalescence: raw N bits -> visible K bits, missing selector N-K
hidden lanes: q_hidden = lanes * q_single, surplus = log2(q_hidden)
checksum uniqueness: c ~= log2(M) - log2(-ln u)
```

Result:

- Coalescence toy `raw=2,visible=1,R=32`: apparent gain `32`, selector bill
  `32`, exact net `0`; 99% checksum net is `-6.636612`.
- H195 hidden lanes `W=8,L=20`: `q_hidden=1.015625`, apparent surplus
  `0.022368`, lane bill `5`, exact net `-4.977632`.
- H195 hidden lanes `W=8,L=32`: apparent surplus `0.700440`, lane bill `5`,
  exact net `-4.299560`.
- Broad default best hidden-lane row: `W=16,L=256`, apparent surplus
  `4.285402`, lane bill `8`, exact net `-3.714598`.

Bill:

```text
exact selector entropy or checksum/referee bits
```

Mutation:

Bounded referees are closure machinery, not a maintained arbitrary-uniform
source of drift. Move next toward a more Telomere-native generated/reachable
developmental regime while keeping membership tax explicit.

## H198 - Telomere-Native Developmental Seed Tree

Conjecture:

```text
Make H183's generated positive control native to Telomere: a stored root record
recursively unfolds into a seed-bearing item tree, preserving exact-witness
supply across arbitrary passes without birth/open metadata.
```

Small model:

```text
root record = [arity=A][root witness width G]
child seed = H(parent_seed, depth, slot) truncated to C bits
leaf atom = H(leaf_seed, path) truncated to B bits
out_bits = B * A^P
```

Result:

- Strong sampled generated row:
  `G=16,C=8,B=32,A=5,P=6` has `out_bits=500000`, `paid_bits=35`,
  `inside_generated_gain=499965`, `min_per_pass_step_gain=59`, and
  `all_passes_shrink=True`.
- Fixed public pass-count variant:
  `G=16,C=8,B=32,A=5,P=6` has `paid_bits=27`,
  `inside_generated_gain=499973`, and optimistic `uniform_net=-11`.
- Exact support row:
  `G=8,C=8,B=16,A=3,P=2` has `unique=256/256`, `inside_gain=119`, and
  `observed_uniform_net=-17`.
- Collision sanity row:
  `G=8,C=8,B=16,A=2,P=2` has `unique=254/256`, so the observed arbitrary net is
  `-16.011315`, slightly worse than the optimistic `-16`.

Bill:

```text
uniform_net <= G - paid_bits
observed_uniform_net = gain_inside - (out_bits - log2(unique_phenotypes))
```

Mutation:

H198 solves maintained stateless recursion inside a declared generated class.
The remaining all-data question is whether arbitrary residuals can be attached
to the generated tree for less than reachable-set membership/preimage rank.

## H199 - Generated Tree Plus Residual Attachment

Conjecture:

```text
Encode arbitrary data as H198 generated phenotype(root) plus a residual; if the
residual is cheaper than reachable-set membership, H198 becomes roughly-all-data.
```

Small model:

```text
target = phenotype(root) XOR mask
mask in HammingBall(N,r)
ideal_net = log2(covered_targets) - paid_root_bits - log2(ball_size)
```

Result:

- `G=4,C=8,B=8,A=2,P=1,N=16,paid=17,r=0` has net `-13`.
- `r=4` covers `30470/65536` targets but net worsens to `-13.402388`.
- `r=8` covers all `65536` targets but net worsens to `-16.258676`.
- `r=16` is full raw residual and nets `-17`.
- Two-pass exact row `G=4,C=8,B=8,A=2,P=2,fixed_pass_count` has
  `unique=15/16`; its best net is `log2(15)-12 = -8.093109`.
- Large H198 bound `N=500000,G=16,paid=27` stays at `netBound=-11` for every
  residual radius before full coverage and cannot cross at full coverage.

Bill:

```text
support <= unique_roots * residual_count
net <= log2(unique_roots) - paid_root_bits
```

Mutation:

Direct arbitrary residuals cancel the reachable-set tax. The next only-live
variant would need the residual stream itself to be recursively generated and
decoded statelessly without becoming another reachable/source restriction.

## H200 - Nearest Generated-Cover Residual Ledger

Conjecture:

```text
Best-of-M generated roots plus a residual volume chosen for high coverage can
cover roughly all targets with negative paid drift.
```

Small model:

```text
s = log2(V) - (N-m)
coverage ~= 1 - exp(-2^s)
short_delta ~= root_cost - m + s
```

Result:

- At `N=500000,m=16,s=2.203` (`~99%` coverage):
  - `free_index` has `short_delta=-13.797` but is overfull/hidden selector.
  - `paid_index` lower bound has `Kraft_delta=+2.184448`.
  - `native_fixed` has `Kraft_delta=+13.070864`.
  - `native_stored` has `Kraft_delta=+20.990798`.
- Native H198 fixed-pass short deltas:
  `+10.471234` at 50% coverage, `+12.203254` at 90%,
  `+13.203254` at 99%, `+13.788217` at 99.9%.
- Default grid best valid paid Kraft-fallback row is still expansion:
  `native_fixed,m=16,s=-4,coverage=0.060587,Kraft_delta=+0.424750`.

Bill:

```text
selected-root bits cancel best-of-M residual shortening
```

Mutation:

The residual must itself have a new recursive/generated law. Plain nearest-root
coverage is closed for roughly-all data.

## H201 - Multi-Root Generated Superposition

Conjecture:

```text
Encode the residual itself as several H198 generated roots combined by XOR, or
as an arbitrary subset of a public generated codebook.
```

Small model:

```text
target = phenotype(root_1) XOR ... XOR phenotype(root_k)
paid_index_net = log2(xor_support) - log2 C(unique_roots,k)
native_net = log2(xor_support) - k * paid_H198_root_record
```

Result:

- One-pass exact row `G=4,C=8,B=8,A=2,P=1,N=16`:
  `k=4` has `xor_support=1820`, `xor_log2=10.829723`,
  `selection_log2=10.829723`, so `paid_index_net=0` and
  `native_net=-57.170277`.
- Same row `k=8`: `paid_index_net=-0.314381`,
  `native_net=-122.662657`.
- Full span of that codebook has `rank=15`, `bitmask_net=-1`.
- Two-pass exact row `G=4,C=8,B=8,A=2,P=2,N=32` has `rank=15`; full bitmask
  ties at `0` only inside a `2^15` support class, leaving a 17-bit source gap.
- Large H198 bound `N=500000,m=16,native_root_bits=27`:
  `k=128` has native tuple net `-1408`; full span has at most rank `65536`,
  leaving support gap `434464`.

Bill:

```text
selected-root entropy or public-codebook bitmask rank
```

Mutation:

Generated residual superposition closes unless a future scheme creates support
faster than selector rank, which reopens ambiguity/referee accounting.

## H202 - Recombination / Crossover Selector Ledger

Conjecture:

```text
Biology-like recombination of generated parent trees might create more useful
reachable phenotypes than XOR superposition while preserving stateless decode.
```

Small model:

```text
record = [mode][parent root records...][crossover rank]
grammar_bits = log2 C(L-1,t) + log2(p) + t*log2(p-1)
support_bits <= p*G + grammar_bits
```

Result:

- Exact tiny row `G=3,C=8,B=8,A=2,P=2,N=32,p=2,t=1` has
  `support=176`, `support_log2=7.459432`, `selection_bits=8.584963`,
  `paid_index_net=-1.125531`, and `native_net=-23.125531`.
- Exact tiny row `p=4,t=3` reaches `support=4096`, but still has
  `paid_index_net=-6.754888`, `native_net=-42.754888`, and a 20-bit support
  gap.
- Large H198 bound `N=500000,G=16,A=5,P=6,L=15625`:
  - `p=2,t=1` has `grammar=14.931476`, `support_bound=46.931476`,
    `native_fixed_net=-21`, `native_stored_net=-29`.
  - `p=2,t=32` has `grammar=329.098145`, `support_bound=361.098145`,
    but the same `native_fixed_net=-21`.
  - `p=4` rows stay at `native_fixed_net=-41` and `native_stored_net=-49`.

Bill:

```text
parent root identity + breakpoint rank + segment-parent rank
```

Extra crossover points add support and decoder rank in lockstep. Native H198
records then subtract the parent root overhead:

```text
native_fixed_net <= p*G - (1 + p*record_cost_for_payload_width(A,G))
```

Mutation:

Plain recombination is closed as an arbitrary-uniform residual mechanism. The
next biological mutation must derive the crossover schedule from already
visible decoder state, or explicitly declare a source/reachable population law
that pays for parent choice and crossover statistics.

## H203 - Decoder-Derived Crossover Schedule

Conjecture:

```text
Remove H202's crossover-rank bill by deriving the crossover schedule
deterministically from parent roots or digest-tail state.
```

Small model:

```text
(breakpoints, path) = H(parent_roots, public_params)
child = Recombine(parent_roots, breakpoints, path)
support_bits <= p*G
```

Result:

- Exact tiny row `G=3,C=8,B=8,A=2,P=2,N=32,p=2,t=1` has
  `parent_tuple_bits=6`, `support=61`, `support_log2=5.930737`,
  `paid_index_net=-0.069263`, and `native_fixed_net=-15.069263`.
- Exact tiny row `p=4,t=3` has `parent_tuple_bits=12`,
  `support_log2=10.768184`, `paid_index_net=-1.231816`, and
  `native_fixed_net=-30.231816`.
- Large H198 bound `N=500000,G=16,A=5,P=6` has `support_bound=32` and
  `native_fixed_net=-21` for `p=2`, and `support_bound=64` with
  `native_fixed_net=-41` for `p=4`, independent of `t`.

Bill:

```text
free deterministic schedule = one child per parent tuple
```

Removing the schedule rank also removes the extra address space. If the encoder
chooses among schedules, H202's selector bill returns.

Mutation:

Test public multi-child orbits with a visible decoder-derived accept/reject
law. The next question is whether canonical biological selection creates
recurrent fertility, or only thins the orbit and remains bounded by parent
tuple rank plus paid accepted-index/referee bits.

## H204 - Public Recombination Orbit With Visible Selection

Conjecture:

```text
A public orbit of crossover schedules plus a decoder-visible accept/reject law
might create biological selection without storing the accepted schedule.
```

Small model:

```text
candidate_j = Recombine(parent_tuple, schedule_j)
accept_j = visible F(candidate_j)
canonical = first accepted candidate
indexed = chosen accepted candidate, index/rank paid
```

Result:

- Exact tiny row `G=3,B=8,A=2,P=2,p=2,t=1,S=16,z=1` has
  `accepted_choices=523`, `tuples_with_accept=48`,
  `canonical_log2=5.459432`, `canonical_paid_net=-0.540568`,
  `indexed_log2=6.459432`, `indexed_selector_log2=9.030667`, and
  `indexed_paid_net=-2.571236`.
- Large H198 bound `N=500000,G=16,A=5,P=6,p=2,S=256,z=1` has
  `canonical_support_bound=32`, `native_canonical_net=-21`,
  `indexed_support_bound=39`, and `native_index_net=-22`.
- Four-parent canonical rows remain capped at support bound `64` with
  `native_canonical_net=-41`.

Bill:

```text
canonical visible selection = support thinning / at most one child per tuple
indexed selection = accepted-index entropy
```

Mutation:

Move recombination into an inherited visible population law: store the visible
final population and let decode deterministically derive parent choices,
crossover schedules, salts, and child seeds. This should be a generated
positive control with the arbitrary-uniform membership bill explicit.

## H205 - Visible Population / Neutral-Allele Generated Law

Conjecture:

```text
A visible final population of seed records can carry inherited parent choices,
crossover/salt state, and child seeds without selected-rank metadata.
```

Small model:

```text
stored = [mode][M root records]
paid = 1 + M*record_cost_for_payload_width(A,G)
out_bits = M*A^P*B
support_bits <= M*G
uniform_net_upper = M*G - paid
```

Result:

- Strong generated row `M=32,G=16,C=8,B=32,A=5,P=6` has
  `out_bits=16000000`, `paid_bits=833`, `inside_generated_gain=15999167`,
  `min_pass_step_gain=1888`, and `all_passes_shrink=True`.
- The same row has `reachable_tax_upper=15999488` and
  `uniform_net_upper=-321`, exactly `M*G - paid`.
- Smaller rows scale predictably: `M=1,G=16` has `uniform_net=-11`,
  `M=2,G=16` has `-21`, and `M=8,G=16` has `-81`.
- Neutral-tail control is multiplicity-limited:
  `lambda=1,S=16` gives `success=0.060587`, `miss_tax=4.044849`;
  `lambda=16,S=16` gives `success=0.632121`, `miss_tax=0.661728`.

Bill:

```text
arbitrary uniform membership tax = out_bits - M*G
neutral control tax = -log2(1-exp(-lambda/S)) unless multiplicity is present
```

Mutation:

H205 is the clean genetics-inspired generated positive control. It should be
used as a source-shaped / reachable benchmark, not claimed as roughly-all-data
compression unless an external source law pays the membership tax.

## H206 - Visible-Population Arbitrary-Uniform Overhead Bound

Conjecture:

```text
Tune M/G/A in the visible-population law until the arbitrary-uniform miss crosses.
```

Small model:

```text
support_bits <= M*G
paid_bits = 1 + M*record_cost_for_payload_width(A,G)
uniform_net_upper = M*G - paid_bits
```

Result:

- Best scanned arbitrary-uniform upper bound:
  `M=1,A=2,G=1,record=7,paid=8,support=1,uniform_net=-7`.
- Best high-growth `A=5` row:
  `M=1,A=5,G=1,record=8,paid=9,support=1,uniform_net=-8`,
  with `out=500000` and `inside_generated_gain=499991`.
- The H198/H205-style `M=1,A=5,G=16` row has `record=26`,
  `uniform_net=-11`, and `inside_generated_gain=499973`.

Bill:

```text
record_cost_for_payload_width(A,G) > G
uniform_net_upper = -1 - M*(record_bits-G) < 0
```

Mutation:

The visible-population family cannot cross arbitrary-uniform under current
V1/J3D1 root records by tuning. The nearest miss is 7 bits overall, or 8 bits
for the nontrivial high-growth `A=5` branch. The next attack must either change
the root-record language or supply a paid source/reachable membership law.

## H207 - Packed Root Population / Root-Record Language Attack

Conjecture:

```text
Remove the H206 root-record overhead by packing the visible population root
bits directly as M*G raw bits.
```

Small model:

```text
support_bits = M*G
packed_paid = support_bits + mode_bits
membership_tax = out_bits - support_bits
uniform_net_generated_only = -mode_bits
raw_fallback_length = out_bits - log2(1 - 2^-mode_bits)
```

Result:

- Generated-only no-mode rows tie after membership tax:
  `M=32,G=16,A=5,P=6` has `out=16000000`, `support=512`,
  `paid=512`, `inside_gain=15999488`, `membership_tax=15999488`, and
  `uniform_net_generated_only=0`.
- A one-bit mode gives `uniform_net_generated_only=-1` and raw-fallback
  delta `+1` bit under uniform data.
- A two-bit mode gives `uniform_net_generated_only=-2` and raw-fallback
  delta `+0.415037` bits.

Bill:

```text
mode/Kraft mass or missing support membership
```

Mutation:

Packed roots make the generated lineage cleaner but do not produce arbitrary
uniform negative drift. The remaining root-language attack would need a
non-Kraft uniquely decodable syntax, which H189/H108-style checks already make
suspect, or a declared source/reachable law.

## H208 - Public Ensemble / Source-Law Bridge

Conjecture:

```text
Use visible-population generated laws as a normalized Kraft prior with raw
fallback, or combine many public generated laws.
```

Small model:

```text
public ensemble support <= M*G + log2(E)
paid mode rank = log2(E)

q = 2^(s-c)
Q(reachable x) = 2^-c + (1-q)2^-N
Q(other x) = (1-q)2^-N
```

Result:

- Public ensembles do not change the sign: `E=65536,M=32,G=16,extra=1` has
  `support_bits=528`, `paid_bits=529`, `paid_net=-1`; the apparent
  `hidden_mode_net=+16` is the unpaid family selector.
- Normalized prior `H205-single-high-growth` (`M=1,A=5,G=16,N=500000,s=16,c=27`)
  has `raw_overhead=0.000704613` bits and generated-source threshold
  `alpha*=1.409e-9`.
- Normalized prior `H205-visible-population`
  (`M=32,A=5,G=16,N=16000000,s=512,c=833`) has `raw_overhead=3.377e-97` and
  `alpha*=2.111e-104`.
- At `alpha=1e-6`, `H205-visible-population` has apparent gain
  `+15.999167` bits/sample, source tax `+15.999467`, and paid net
  `-0.000300`.

Bill:

```text
paid_net_after_source_tax = H(P) - CE(P,Q) = -D(P||Q) <= 0
```

Mutation:

H208 is a strong universal-prior bridge with near-zero uniform downside and huge
generated-lineage upside. It still does not solve roughly-all uniform data. The
next attack must make the source law native/induced rather than external, or
find a mechanism that changes the uniform law premise without hiding a selector.

## H209 - Developmental Macro Codec

Conjecture:

```text
Turn the visible-population generated law into an explicit stateless codec:
generated roots unfold by public developmental rules, while non-reachable
outputs use a raw escape.
```

Small model:

```text
decode(generated) = public child law iterated P passes from M roots
decode(raw)       = literal N-bit output
generated_gain    = N - generatedBits
uniform_net       = generated_gain - (N - log2 support)
```

Result:

- Exact finite default `M=1,G=3,C=3,B=2,A=2,P=2,N=8` enumerates all `256`
  outputs and round-trips.  It has support `8/256`, packed generated length `4`,
  raw prefix length `9`, and generated packed gain `+4`, but uniform packed
  mean `8.843750` and net after membership `-1`.
- Large symbolic `native_v1_roots M=32,G=16,A=5,P=6,N=16000000` has
  `genBits=833`, generated gain `15999167`, uniform-after-membership `-321`,
  raw overhead `3.377e-97`, and source threshold `2.111e-104`.
- Ideal packed roots for that row have `genBits=513`, generated gain
  `15999487`, and uniform-after-membership `-1`.

Bill:

```text
generated source: pay only root macro bits
arbitrary uniform: pay membership tax N-log2(support), plus parseable mode/raw
```

Mutation:

H209 is the strongest fully parseable positive construction, but it is
generated/reachable.  The arbitrary-content branch still needs a real way to
make membership native or a bounded referee surplus that beats ambiguity.

## H210 - Position / Final-Board Channel Converse

Conjecture:

```text
Final positions, egg cartons, lanes, and modular boards can tell the decoder
salt/order/pass state only up to their counted arrangement entropy.
```

Small model:

```text
visible occupancy      = log2 C(Q,R)
ordered positions      = log2 (Q)_R
fixed lane arrangements= sum_t log2 C(Q_t,r_t)
birth labels           = R log2 P
```

Result:

- Dense `R=1000,Q=1111,rho=0.900,P=64` has cheap occupancy
  `0.516089` bits/record, but birth labels need `6` bits/record and residual
  ambiguity is `5483.911082` bits.
- Half-dense `R=1000,Q=2000,P=4` has `occ/R=1.994191`, barely inside a
  2-bit/record budget, with residual `5.808821` bits.
- Sparse `R=1000,Q=10000,P=16` has `occ/R=4.683723`; the board note itself
  costs more than the savings budget.

Bill:

```text
public lane thinning costs log2(P) bits/record
arrangement channel capacity <= log2(valid final states)
```

Mutation:

Keep final-board geometry as finite amortization/decode scaffolding.  Do not
treat it as a free many-pass salt channel; derive max finite `P` from the
remaining per-record margin.

## H211 - Honest Induced-Prior Conservation

Conjecture:

```text
If the recursive encoder creates a biased emitted stream, the best possible
decoder-known next prior over that exact stream can only tie after source tax.
```

Small model:

```text
uniform X -> deterministic lossless emitted token Y
P_emit = law(Y)
paid_net(Q) = H(P_emit) - CE(P_emit,Q) = -D(P_emit||Q)
```

Result:

- `N=8,Wmax=8` enumerates `256` cases, round-trips, and has
  `H_emit=8`, `mean_emit_bits=8.996094`, `support_witness=1`, `raw=255`.
  `actual_code` gives `paidNet=-0.001718`; `oracle_emit=P_emit` ties at `0`.
- `N=10,Wmax=9` has `H_emit=10`, `mean_emit_bits=10.993164`,
  `support_witness=5`; `actual_code` gives `paidNet=-0.008579`, and
  `oracle_emit` again ties.

Bill:

```text
apparent next-pass gain = emitted expansion/source shape
oracle prior            = tie
implementable mismatch  = KL loss
```

Mutation:

Close self-induced source bias as an arbitrary-uniform engine.  The next live
lookahead attack should instead test bounded-slack witness choice where the
stored seed itself carries the chosen next-state tail, and should charge slack
and miss probability explicitly.

## H212 - Bounded-Slack Witness Lookahead

Conjecture:

```text
Non-greedy equal-cost or near-equal witness choice can steer next-pass tail
state without a separate selector because the chosen seed is already stored.
```

Small model:

```text
candidate = exact witness with record cost c and digest tail q
greedy    = min c
lookahead = min(c - future_credit(q)) among c <= c_greedy + slack
```

Result:

- Default `B=8,A=1,Wmax=8,trials=512` covers `439/512` targets with
  `mean_candidates=2.266515`.
- Equal-cost choice has real zero-slack steering.  For `S=2,credit=2`,
  greedy tail rate is `0.512528`, lookahead tail rate is `0.578588`, slack
  paid is `0`, and two-pass option gain is `0.132118`.
- Near-equal slack buys more steering but pays record bits:
  `slack=1,S=2,credit=2` reaches lookahead tail rate `0.637813`, pays
  `0.059226` slack bits, and nets `0.191344` two-pass option gain under the
  assumed future credit.  Needed credit per newly steered tail is `0.472727`.
- For rarer state `S=16,credit=2`, `slack=1` reaches tail rate `0.107062`,
  pays `0.025057` slack bits, and nets `0.047836`; miss tax is `2.920502`.

Bill:

```text
same-cost choice is legal because selected seed is stored
near-equal choice pays slack
future credit is not created by the choice; it must be a real public fertility law
```

Mutation:

H212 is a live primitive, not a full arbitrary-uniform solution.  The next
experiment should attach it to an actually measured decoder-visible fertility
law or to a generated/reachable lineage where future credit is a source fact.

## H213 - Recursive Witness Closure / Upward Detour

Conjecture:

```text
A non-greedy recursive seed can generate a valid intermediate record token,
and that token can open to the final target.  The final seed names the
intermediate token, so no separate selector is stored.
```

Small model:

```text
pass2 seed -> pass1 token -> N-bit target
token length class bits are charged when multiple intermediate lengths exist
raw fallback = N + 1 bits
```

Result:

- Default `N=8,W1=8,W2=8` has recursive closure support
  (`final_token_hits=18`, `two_pass_support=13`) but no paid wins and mean
  paid delta `+0.992188`.
- Wider `N=16,W1=10,W2=12` produces real upward-detour wins:
  `two_pass_support=209`, `oracle_wins=8`, `paid_wins=1`,
  `mean_delta_paid=+0.983856`, and `best_paid_improvement=2`.
- `N=16,W1=12,W2=12` improves to `paid_wins=2`,
  `mean_delta_paid=+0.983841`, `hidden_length_bill=0.000305`, and
  support tax upper bound `7.955606`.

Bill:

```text
legal recursive naming, but tiny support and explicit token-length/boundary bits
```

Mutation:

H213 validates the upward-detour mechanism at finite depth.  Next: build a
multi-depth recursive closure kernel and measure support growth, mean paid
length, and bad tails after every length-class/fallback bill.

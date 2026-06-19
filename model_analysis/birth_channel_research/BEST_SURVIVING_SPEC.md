# Best Surviving Stateless Recursive Spec

## Status

No paid positive arbitrary-uniform recursive mechanism has been validated in the
current H1-H212 notebook.

The best fully paid positive construction is now the H209 developmental macro
codec, which makes the H205 visible-population law into an exact stateless
encode/decode mechanism with raw escape. It is deterministic, lossless for
members of its reachable class, recursively shrinkable in the large symbolic
rows, and statelessly decodable. Its limitation is explicit: arbitrary uniform
data pays the reachable-set membership tax plus parse/fallback cost, which
cancels or exceeds the root-vs-phenotype saving.

## Best Generated / Reachable Regime

Public preset:

```text
mode = H198_NATIVE_DEVELOPMENTAL_TREE
root_bits = G
internal_cell_bits = C
leaf_atom_bits = B
branch_arity = A in 1..5
pass_count = P, either fixed by preset or stored once in the header
child_seed = H(parent_seed, depth, slot) truncated to C bits
leaf_atom = H(leaf_seed, path) truncated to B bits
```

Encoded layer:

```text
[mode][optional Lotus(P)][arity=A][root witness]
```

The root witness is charged with the exact current V1/J3D1 cost:

```text
paid_bits = 1 + record_cost_for_payload_width(A, G) + optional Lotus(P)
```

Decode:

```text
visit(root, depth=0, path=[])
if depth < P:
    for slot in 0..A-1:
        child = H(parent_seed, depth, slot)[0..C]
        visit(child, depth+1, path+[slot])
else:
    emit H(leaf_seed, path)[0..B]
```

No carried records, sparse open/carry map, birth-pass map, hit map, final-board
map, or PCTB ledger is used. Pass salts are path/depth/parent-derived.

Representative paid row:

```text
G=16, C=8, B=32, A=5, P=6
output_bits = 500000
paid_bits = 35
inside_generated_gain = 499965
reachable_tax_upper = 499984
optimistic_uniform_net = -19
min_per_pass_step_gain = 59
all_passes_shrink = True
```

If `P=6` is fixed by the public preset, paid bits drop to `27`, inside gain
rises to `499973`, and the optimistic arbitrary-uniform net improves to `-11`.

Verdict:

```text
positive and recursively maintained inside the declared generated/reachable class
negative for arbitrary uniform data after membership tax
```

H183 remains the simpler opaque generated positive control. H198 is the best
surviving Telomere-native version because its internal layers are seed-bearing
records, not arbitrary developmental bytes.

## Nearest Arbitrary-Uniform Miss

H190 showed that the raw-vs-witness channel was the sharp local bill:

```text
N=16, Wmax=16
oracle gain = +0.008347 bits
paid gain   = -0.991653 bits
```

The oracle crosses only by omitting the raw-vs-witness parse channel. The paid
one-bit mode restores the uniform source-code bill.

H191 tightens the paid channel by using leftover Kraft mass for raw fallback:

```text
N=8, Wmax=4, canonical implicit mode
gain = -0.007365 bits/layer
```

H192 prices the arithmetic/bits-back version:

```text
N=16, Wmax=16, lambda=q=0.076172
gain = -0.063559 bits/layer
best nonzero grid row = -0.000002682 bits/layer at lambda=0.001
```

That last row is near zero only because the witness mixture is nearly turned
off.

H193 moves the target to public syntax-derived readiness:

```text
N=16, Wmax=16, rule=short, raw/canonpart
gainU = -0.000198 bits/layer

N=16, Wmax=8, closed partition t=1
gainU = -0.000113 bits/layer
support = 9 / 65536
```

The second row was the closest closed-partition miss at that point, but support
collapse means it is not maintained recursion.

H194 tests public finite-state language transforms:

```text
maxrun2, N=8, m=11, W=4, semantic_reclaim
realGain = -0.000721 bits/layer
appGain  =  2.999279 bits/layer

primdyck4, N=8, m=18, W=16, semantic_reclaim
realGain = -0.000000013 bits/layer
appGain  = 10.000000 bits/layer
```

The Dyck row is closer to zero, but only because the transform expands the
syntax surface heavily and leaves almost no useful witness effect.

H195 tests the opposite edge: keep nonzero witness effect and full support, then
smooth witness mass with many public paid salt lanes:

```text
N=8, Wmax=8, lanes=4096, mode=all
q       = 0.050781
support = 256 / 256
gain    = -0.000005239 bits/layer
```

This is the closest nonzero-witness arbitrary-uniform miss so far. Its limit is
a tie, not a positive row, because:

```text
E_U[-log2 Q(X)] = N + D(U || Q) >= N
```

Public lanes can drive `D(U||Q)` toward zero, but cannot make it negative.

H196 tests whether recursion can make the next layer non-uniform in exactly the
right way:

```text
N=8, Wmax=8, lanes=4096, beta=1
source law P = Q
apparent gain = +0.000005242 bits/layer
source tax    = +0.000005242 bits/layer
paid net      =  0
```

This is the best possible self-induced source resonance. It ties because:

```text
paid net = H(P) - E_P[-log2 Q(X)] = -D(P || Q) <= 0
```

Any stronger bias makes the apparent block gain larger and the source-law tax
larger still.

H197 tests whether bounded ambiguity/referee pruning can turn overfull witness
families into stateless decode savings:

```text
Wmax=8, lanes=32
hidden q = 1.625000
apparent surplus = 0.700440 bits
omitted lane selector = 5 bits
exact net = -4.299560 bits
99% checksum net = -10.936173 bits
```

The exact coalescence toy ties with a full selector and loses by `6.636612`
bits at 99% checksum uniqueness. Fixed referees buy finite toys, not maintained
recursive drift.

H198 strengthens the generated positive branch:

```text
G=16,C=8,B=32,A=5,P=6
inside_generated_gain = 499965
min_per_pass_step_gain = 59
optimistic_uniform_net = -19
fixed_pass_count_uniform_net = -11

G=8,C=8,B=16,A=3,P=2
unique phenotypes = 256/256
observed_uniform_net = -17.000000
```

The generated class has maintained fresh witness supply because every internal
parent is the public exact witness for its child bundle. The arbitrary-uniform
bill remains:

```text
uniform_net <= G - paid_bits
```

H199 tests the direct arbitrary-data attachment:

```text
target = generated_phenotype(root) XOR residual_mask
residual_mask in HammingBall(N,r)
```

Exact tiny rows:

```text
N=16,G=4,paid=17,r=8
coverage = 65536 / 65536
ideal_net = -16.258676

N=32,G=4,paid=12,P=2,fixed_pass_count,r=4
unique generated phenotypes = 15 / 16
ideal_net = -8.093109
```

Large H198 pair-count bound:

```text
N=500000,G=16,paid=27
netBound = G - paid = -11
```

Residual attachment grows support, but after residual rank is paid:

```text
support <= unique_roots * residual_count
net <= log2(unique_roots) - paid_root_bits
```

H200 tests the high-coverage nearest-root version:

```text
N=500000,m=16,coverage~=0.99

paid_index lower bound:
  Kraft_delta = +2.184448

native_fixed H198:
  Kraft_delta = +13.070864

native_stored H198:
  Kraft_delta = +20.990798
```

The diagnostic `free_index` row appears to win only because the selected root
index is not paid; it is an explicit hidden selector channel.

H201 tests generated residual superposition:

```text
target = phenotype(root_1) XOR ... XOR phenotype(root_k)
```

Exact tiny row:

```text
G=4,C=8,B=8,A=2,P=1,N=16,k=4
xor_support = 1820
xor_log2 = 10.829723
selection_log2 = 10.829723
paid_index_net = 0
native_net = -57.170277
```

Full span diagnostics:

```text
N=16, unique=16, rank=15
bitmask_net = -1

N=32, unique=15, rank=15
bitmask_net = 0, but support gap = 17 bits
```

Large H198 bound:

```text
N=500000,m=16
rank_bound = 65536
support_gap = 434464 bits
k=128 native_tuple_net = -1408
```

H202 tests biological-style recombination of H198 parent trees:

```text
record = [mode][parent root records...][crossover rank]
```

Exact tiny row:

```text
G=3,C=8,B=8,A=2,P=2,N=32,p=2,t=1
support_log2 = 7.459432
selection_bits = 8.584963
paid_index_net = -1.125531
native_net = -23.125531
```

Large H198 generous bound:

```text
N=500000,G=16,A=5,P=6,L=15625
p=2,t=32 support_bound = 361.098145, native_fixed_net = -21
p=4,t=32 support_bound = 444.816945, native_fixed_net = -41
```

The crossover rank grows with the reachable set, so extra breakpoints do not
change the paid sign. The native loss is the stored parent-root overhead:

```text
native_fixed_net <= p*G - (1 + p*record_cost_for_payload_width(A,G))
```

H203 removes H202's crossover-rank field by deriving the schedule from parent
roots:

```text
(breakpoints, path) = H(parent_roots, public_params)
child = Recombine(parent_roots, breakpoints, path)
```

That makes the schedule free, but it also removes its address space:

```text
support_bits <= p*G
```

Exact tiny row:

```text
G=3,C=8,B=8,A=2,P=2,N=32,p=2,t=1
parent_tuple_bits = 6
support_log2 = 5.930737
native_fixed_net = -15.069263
```

Large H198 bound:

```text
N=500000,G=16,A=5,P=6
p=2 support_bound = 32, native_fixed_net = -21
p=4 support_bound = 64, native_fixed_net = -41
```

H204 adds a public orbit of schedules plus a visible accept/reject rule:

```text
canonical = first accepted child, no index
indexed = chosen accepted child, accepted index/rank paid
```

Exact tiny row:

```text
G=3,B=8,A=2,P=2,p=2,t=1,S=16,z=1
canonical_paid_net = -0.540568
indexed_paid_net = -2.571236
```

Canonical selection thins support; indexed selection pays the index.

H205 then changes the claim boundary to an inherited visible population law:

```text
stored = [mode][M root records]
decode derives parent choices, crossover/salt state, and child seeds
```

Strong generated row:

```text
M=32,G=16,C=8,B=32,A=5,P=6
out_bits = 16000000
paid_bits = 833
inside_generated_gain = 15999167
min_pass_step_gain = 1888
all_passes_shrink = True
uniform_net_upper = -321
```

This is the strongest biology-shaped positive control so far. Its arbitrary
uniform bill remains:

```text
uniform_net_upper = M*G - paid_bits
```

H206 optimizes that arbitrary-uniform miss under exact current V1/J3D1 root
record costs:

```text
best scanned overall: M=1,A=2,G=1, uniform_net_upper=-7
best high-growth A=5: M=1,A=5,G=1, uniform_net_upper=-8
H198-style G=16,A=5: M=1, uniform_net_upper=-11
```

So the visible-population family has a finite nearest miss, not a hidden
tuning crossover.

H207 removes even that current-format root-record overhead by packing roots as
exactly `M*G` bits:

```text
M=32,G=16,A=5,P=6
out_bits = 16000000
packed_paid = 512
inside_gain = 15999488
membership_tax = 15999488
uniform_net_generated_only = 0
```

The result is a tie only for a generated-only public preset with no mode and no
fallback. A one-bit parse mode gives `uniform_net=-1`; raw fallback with that
mode has `+1` bit uniform mean expansion. So ideal root packing closes H206 to
a tie, not a crossing.

H208 turns the native visible-population family into a normalized universal
prior with raw escape:

```text
H205-single-high-growth:
  raw uniform overhead = 0.000704613 bits/sample
  generated-source threshold alpha = 1.409e-9

H205-visible-population:
  raw uniform overhead = 3.377e-97 bits/sample
  generated-source threshold alpha = 2.111e-104
```

This is the strongest source-shaped bridge so far: almost no uniform downside,
huge generated-lineage upside. After source entropy is charged, however:

```text
paid_net = H(P) - CE(P,Q) = -D(P||Q) <= 0
```

This makes the next target exact:

```text
find a recursive/generative residual mechanism that does not reduce to
root+residual pair counting, nearest-generated-cover selection, or multi-root
selected-root/bitmask/crossover rank, and does not lose the same rank when the
schedule is made deterministic; or define an explicit source/reachable law that
pays the visible-population membership tax; or change the root-record language
so self-description costs no more than support rank and still leaves a
parseable all-data fallback without Kraft expansion; or make the visible
population prior become the native induced source law rather than an external
source-shaped assumption
```

H209 implements that visible-population law as an exact codec:

```text
generated mode = read M roots, iterate public developmental law for P passes
raw mode       = read N-bit literal layer
```

Tiny exact row:

```text
M=1,G=3,C=3,B=2,A=2,P=2,N=8
roundtrip = True over all 256 outputs
support = 8/256
packedGen = 4
generatedGain(packed) = +4
uniformMean(packed) = 8.843750
netAfterMembership(packed) = -1
```

Large symbolic row:

```text
native_v1_roots M=32,G=16,A=5,P=6,N=16000000
genBits = 833
generated_gain = 15999167
uniform_after_membership = -321
rawOH = 3.377e-97
alpha* = 2.111e-104
```

H210 prices the strongest position/final-board salt channel:

```text
R=1000,Q=1111,rho=0.900,P=64
occupancy = 0.516089 bits/record
birth labels = 6 bits/record
residual after occupancy = 5483.911082 bits
```

Dense boards can carry finite notes cheaply, but they do not supply an
unbounded birth/salt ledger.

H211 tests whether the emitted stream can become its own next-pass source law:

```text
N=8,Wmax=8
H_emit = 8
mean_emit_bits = 8.996094
oracle Q=P_emit paid_net = 0
actual code paid_net = -0.001718
```

The best possible induced prior ties; implementable mismatches lose by KL.

H212 tests the strongest non-greedy witness-choice primitive:

```text
selected seed is stored
digest tail of selected seed is decoder-visible
equal-cost choice has no extra selector
near-equal choice pays its extra record bits
```

Default result:

```text
B=8,A=1,Wmax=8,trials=512
covered = 439/512
mean_candidates = 2.266515

S=2,credit=2,slack=0:
  greedy_tail_rate = 0.512528
  lookahead_tail_rate = 0.578588
  two_pass_option_gain = 0.132118

S=2,credit=2,slack=1:
  lookahead_tail_rate = 0.637813
  slack_paid = 0.059226
  two_pass_option_gain = 0.191344
```

This is a live steering primitive. It becomes compression only if the future
credit is supplied by an actual public fertility law or a generated/reachable
source fact.

No implemented candidate has done that yet.

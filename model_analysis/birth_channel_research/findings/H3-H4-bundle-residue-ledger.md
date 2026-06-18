# Avenue H3/H4 — finite-K bundles, residue, and cover-layout entropy

Author: Codex continuation with three read-only subagent checks. Date:
2026-06-17.
Status: current finite-K salted bundle addendum.

## HYPOTHESIS

Length-pinned bundles can buy a finite birth-pass window because wrong-pass
openings sometimes fail structurally. The open question was whether that finite
subsidy could become net-positive after replacing only some atoms, if the
uncovered residue is encoded more cleverly than one visible literal marker per
atom.

Expected optimistic route:

```text
bundle gross savings
- finite birth residual log2(1 + (P-1) * 2^-E)
- cheap residue / cover language
> 0 bits/input atom
```

## MECHANISM

Two runnable ledgers test this lane:

- `../H3-bundle_finite_k_ledger.py`
- `../H4-cover_layout_entropy.py`

H3 prices the false-positive-prone version:

```text
target_bits = arity * (B + literal_marker_bits)
birth_residual = log2(1 + (P - 1) * 2^-E_arity)
```

and then charges uncovered atoms as explicit literal records. This is the
marker-in-target grammar: the same marker bits that make the previous layer
parseable also provide the structural observations that reject wrong-pass
openings.

H4 is a friendlier upper-bound test. It keeps H3's optimistic hit model and
birth-pruning subsidy, but replaces the explicit literal-marker residue charge
with the minimum entropy of a fixed-arity non-overlapping interval cover:

```text
cover_count(N, a, m) = C(N - (a - 1) * m, m)

cover_bits_per_atom ~= (1 - (a - 1)r)
                       * H2(r / (1 - (a - 1)r))
```

where `r = selected bundle records / input atom`. This is cheaper than charging
3 bits on every uncovered atom. It is also only a lower bound for a real sparse
codec because it omits finite-file count headers, arithmetic-coder overhead,
literal token syntax, and extra salt/open costs.

## RESULT

`refuted-as-rescue(under-uniform-arbitrary-data)`

With `B=8`, arities `2..5`, V1/J3D1 record costs, and the finite-K pass sweep:

```text
H3 --min-raw-savings 1:
  best charged row = arity 3, P=301124
  gain = -1.51661 bits/input atom

H3 --min-raw-savings 2:
  best charged row = arity 3, P=301124
  gain = -1.51661 bits/input atom

H4 --min-raw-savings 1:
  best layout-only row = arity 5, P=64
  gain = -0.0000351769 bits/input atom

H4 --min-raw-savings 2:
  best layout-only row = arity 5, P=64
  gain = -0.0000175885 bits/input atom
```

The H4 numbers are the important ones: even when the residue channel is priced
as an ideal enumerative interval cover, the optimistic sparse bundle branch
does not cross positive. The nearest rows are only near zero because hit density
is so low that both gain and cover entropy are tiny.

## ACCOUNTING TRAP CLOSED

A tempting rescue is to remove literal markers from the target so matches are
against raw `arity * B` bits instead of `arity * (B + marker_bits)`. That raises
hit density sharply. But then the marker-derived structural rejection `E` is no
longer available. A wrong-pass opening also produces raw atoms, so the birth
residual must be recomputed with the new language's actual rejection power.
Borrowing `E` from the marker grammar while taking hit density from the raw
grammar spends the same parse bits twice.

Honest sparse-cover accounting has to use:

```text
gain/atom =
  r * (arity * B - record_bits
       - log2(1 + (P - 1) * 2^-E_language))
  - cover_bits/atom
```

where `E_language` belongs to the same parse language used for the targets and
residue.

## DECODER OBSERVATIONS

Open vs carry:

- H3/H4 are sparse mixed-cover branches, so the decoder must know which packed
  tokens are bundle records and which are literal residue.
- H3 makes this visible with literal markers.
- H4 charges the minimum enumerative cover layout instead.

Birth pass / salt:

- The finite subsidy comes only from length-pinned bundle structure.
- For arity `2..5`, the current ledger uses `E = 9.36, 12.59, 14.97, 18.20`
  bits respectively.
- Past `2^E` passes, residual ambiguity grows as `log2(P) - E`.

Refresh:

- Salting can refresh bundle match attempts.
- It does not make sparse decode stateless unless the open/birth coordinate is
  paid or structurally pruned.

Stored / derived / hidden info:

- H3 stores visible literal syntax on residue.
- H4 stores or arithmetically encodes cover layout entropy.
- Any canonical tie-break rule removes only tie metadata; it does not tell the
  decoder where the selected intervals are unless the layout is otherwise
  derivable.

## CURRENCY

This lane spends three finite currencies:

1. `hit density`: higher arity and marker-bearing targets are rare under the
   uniform hash law.
2. `birth residual`: structural bits buy only a finite pass window.
3. `cover entropy`: sparse interval placement is a compressed bitmap with
   asymptotic cost `~ r log2(1/r)` at low density.

The best sparse rows fail before finite headers and checksum/referee bits, so
there is no hidden positive margin to spend.

## NEXT

The constructive target remains Total-Cover, not sparse finite-K residue:

- Total-Cover removes the open/birth/cover-map bill by invariant.
- The remaining bill is the public parseable `[arity][seed witness]` stream.
- Current best honest row remains the high-arity public factored model:
  `B=4,K=128,D=512`, about `-0.0313 bits/input atom`.

If sparse bundles are revisited, the next kernel should jointly vary:

```text
mode A: internal markers
  target_bits = a * (B + marker_bits)
  E_language = measured marker rejection
  cover cost = marker/run/layout cost

mode B: external interval cover
  target_bits = a * B
  E_language = measured from that cover grammar, not borrowed
  cover cost = log2 legal covers

mode C: total cover
  cover cost = 0 by tiling invariant
  birth residual = 0 by all-open invariant
  bill = arity + witness entropy
```

The concrete mathematical target is therefore the high-arity Total-Cover
entropy-rate limit, not another sparse marker shuffle.

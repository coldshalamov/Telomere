#!/usr/bin/env python3
"""H42 - systematic response-surface map for maintained stateless Telomere.

This is not a compressor. It is a scientific map of the knobs the current
research program keeps touching:

* selected-set entropy: arbitrary content hits need a subset/permutation bill;
* public lane supply: public position/phase lanes are free to parse but lose
  hit supply;
* near-total cover: rare exceptions make the carry ledger small;
* paid Total-Cover witness: the current closest uniform rows need a small,
  specific bits/record improvement;
* source/fertility lift: the only constructive positive rows are those where
  future value exceeds the lane or witness tax.

The point is to learn the shape of the problem, not to run a lucky search.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


def h2(p: float) -> float:
    if p <= 0.0 or p >= 1.0:
        return 0.0
    return -(p * math.log2(p) + (1.0 - p) * math.log2(1.0 - p))


def lane_hit_fraction(active_fraction: float, choices: int) -> float:
    return 1.0 - (1.0 - active_fraction) ** choices


def lane_loss(active_fraction: float, choices: int) -> float:
    return -math.log2(lane_hit_fraction(active_fraction, choices))


def choices_needed(active_fraction: float, target_loss: float) -> int:
    target_hit = 2.0 ** (-target_loss)
    if target_hit >= 1.0:
        return math.inf  # type: ignore[return-value]
    return max(1, math.ceil(math.log(1.0 - target_hit) / math.log(1.0 - active_fraction)))


@dataclass(frozen=True)
class SelectionRow:
    r: float
    subset_bits_per_open: float
    single_lane_loss: float
    d4_loss: float
    d16_loss: float
    d64_loss: float


def selection_rows() -> list[SelectionRow]:
    rows: list[SelectionRow] = []
    for r in (0.001, 0.003, 0.01, 0.03, 0.10, 0.25, 0.50, 0.75, 0.90, 0.99):
        subset = h2(r) / r if r > 0 else math.inf
        rows.append(
            SelectionRow(
                r=r,
                subset_bits_per_open=subset,
                single_lane_loss=lane_loss(r, 1),
                d4_loss=lane_loss(r, 4),
                d16_loss=lane_loss(r, 16),
                d64_loss=lane_loss(r, 64),
            )
        )
    return rows


@dataclass(frozen=True)
class ExceptionRow:
    passes: int
    exception_fraction: float
    bits_per_atom: float
    bits_per_rewritten_atom: float
    net_if_two_bits_per_rewrite: float


def exception_rows() -> list[ExceptionRow]:
    rows: list[ExceptionRow] = []
    for passes in (8, 64, 256, 4096):
        for eps in (0.50, 0.25, 0.10, 0.03, 0.01, 0.003, 0.001):
            # Newest cohort has 1-eps. Exceptions are split across older
            # passes; this is the asymptotic multinomial entropy rate.
            old_pass_bits = eps * math.log2(max(1, passes - 1))
            bits_per_atom = h2(eps) + old_pass_bits
            rewritten = max(1e-12, 1.0 - eps)
            rows.append(
                ExceptionRow(
                    passes=passes,
                    exception_fraction=eps,
                    bits_per_atom=bits_per_atom,
                    bits_per_rewritten_atom=bits_per_atom / rewritten,
                    net_if_two_bits_per_rewrite=2.0 - bits_per_atom / rewritten,
                )
            )
    return rows


@dataclass(frozen=True)
class TotalCoverTarget:
    name: str
    gain_per_atom: float
    records_per_atom: float
    missing_bits_per_record: float

    @property
    def missing_bits_per_atom(self) -> float:
        return self.records_per_atom * self.missing_bits_per_record


TOTAL_COVER_TARGETS = [
    TotalCoverTarget(
        "H7 raw first-hit delta, B4 K128 D512",
        gain_per_atom=-0.011929,
        records_per_atom=0.008789,
        missing_bits_per_record=1.357,
    ),
    TotalCoverTarget(
        "H9 fixed slack 0, B4 K128 D512",
        gain_per_atom=-0.012314,
        records_per_atom=0.009765,  # approximate from miss/gain scale
        missing_bits_per_record=1.261,
    ),
    TotalCoverTarget(
        "H12 perfect-credit upper bound, slack -8",
        gain_per_atom=-0.008196,
        records_per_atom=0.010987,
        missing_bits_per_record=0.746,
    ),
]


@dataclass(frozen=True)
class RepeatedPassTarget:
    name: str
    mean_log2_rho: float
    selector_bits: float
    note: str


REPEATED_PASS_TARGETS = [
    RepeatedPassTarget(
        "H50 paid H9 slack0, B4 K128 D512",
        mean_log2_rho=0.004884,
        selector_bits=0.0,
        note="corrected high-arity sweep",
    ),
    RepeatedPassTarget(
        "H52 fixed slack0, B4 K192 D768",
        mean_log2_rho=0.003658,
        selector_bits=0.0,
        note="closest strict fixed-slack row",
    ),
    RepeatedPassTarget(
        "H52 fixed slack1, B4 K256 D1024",
        mean_log2_rho=0.003775,
        selector_bits=0.0,
        note="larger-K focused scout",
    ),
    RepeatedPassTarget(
        "H53 paid slack ladder, B4 K192 D768",
        mean_log2_rho=0.004480,
        selector_bits=math.log2(3.0),
        note="S={0,1,2}; selector charged",
    ),
    RepeatedPassTarget(
        "H53 unpaid slack ladder, B4 K192 D768",
        mean_log2_rho=0.001973,
        selector_bits=0.0,
        note="lower bound only; selector hidden",
    ),
    RepeatedPassTarget(
        "H56 fibonacci headerless, B4 K192 D768",
        mean_log2_rho=0.023081,
        selector_bits=0.0,
        note="syntax-derived slack, delimiter paid",
    ),
    RepeatedPassTarget(
        "H57 normalized Q, B4 K384 D1536",
        mean_log2_rho=0.000166,
        selector_bits=0.0,
        note="expected excess +1.426544 bits",
    ),
    RepeatedPassTarget(
        "H58 frozen bucket Q, B4 K384 D1536",
        mean_log2_rho=0.000215,
        selector_bits=0.0,
        note="expected excess +0.229195 bits",
    ),
    RepeatedPassTarget(
        "H59 raw/Q mix, B4 K384 D1536 T1",
        mean_log2_rho=0.000050,
        selector_bits=0.0,
        note="eval excess +0.053411 bits",
    ),
]


@dataclass(frozen=True)
class LaneValueTarget:
    r: float
    choices: int
    lane_loss_bits: float
    standalone_value_lift_needed: float
    total_cover_h7_value_lift_needed: float


def lane_value_targets() -> list[LaneValueTarget]:
    h7_missing = TOTAL_COVER_TARGETS[0].missing_bits_per_record
    rows: list[LaneValueTarget] = []
    for r in (0.01, 0.03, 0.10, 0.25, 0.50):
        for d in (1, 2, 4, 8, 16, 32, 64, 128):
            loss = lane_loss(r, d)
            rows.append(
                LaneValueTarget(
                    r=r,
                    choices=d,
                    lane_loss_bits=loss,
                    standalone_value_lift_needed=loss,
                    total_cover_h7_value_lift_needed=h7_missing + loss,
                )
            )
    return rows


def print_selection_surface() -> None:
    print("== selection / lane surface ==")
    print("Arbitrary content-selected readiness pays subset entropy. Public lanes")
    print("pay match-supply loss; d-choice routing lowers that loss but never below 0.")
    print(
        f"{'r':>7} {'subset/open':>13} {'lane d1':>9} "
        f"{'lane d4':>9} {'lane d16':>10} {'lane d64':>10}"
    )
    for row in selection_rows():
        print(
            f"{row.r:7.3f} {row.subset_bits_per_open:13.6f} "
            f"{row.single_lane_loss:9.3f} {row.d4_loss:9.3f} "
            f"{row.d16_loss:10.3f} {row.d64_loss:10.3f}"
        )
    print()


def print_exception_surface() -> None:
    print("== near-total exception surface ==")
    print("If every record opens except a small public/encoded exception set, the")
    print("carry/pass ledger becomes H(eps)+eps*log2(P-1) bits per atom.")
    print(
        f"{'P':>6} {'eps old':>9} {'bits/atom':>11} "
        f"{'bits/rewrite':>13} {'net@2b':>9}"
    )
    for row in exception_rows():
        if row.passes in (64, 256, 4096) and row.exception_fraction in (
            0.10,
            0.03,
            0.01,
            0.003,
            0.001,
        ):
            print(
                f"{row.passes:6d} {row.exception_fraction:9.3f} "
                f"{row.bits_per_atom:11.6f} {row.bits_per_rewritten_atom:13.6f} "
                f"{row.net_if_two_bits_per_rewrite:9.6f}"
            )
    print()


def print_total_cover_targets() -> None:
    print("== closest paid Total-Cover uniform targets ==")
    print("These are not new results; they are the response surface coordinates")
    print("to beat with a better witness or a real public fertility/source lift.")
    print(
        f"{'target':<42} {'gain/atom':>11} {'rec/atom':>10} "
        f"{'miss/rec':>9} {'miss/atom':>10}"
    )
    for row in TOTAL_COVER_TARGETS:
        print(
            f"{row.name:<42} {row.gain_per_atom:11.6f} "
            f"{row.records_per_atom:10.6f} {row.missing_bits_per_record:9.3f} "
            f"{row.missing_bits_per_atom:10.6f}"
        )
    print()


def print_repeated_pass_targets() -> None:
    print("== closest repeated-pass uniform targets ==")
    print("Sign convention: mean log2 rho < 0 is recursive shrinkage.")
    print("Paid selector rows must beat the fixed public baseline after charge.")
    print(
        f"{'target':<42} {'mean log2 rho':>14} "
        f"{'selector bits':>14} {'note':<34}"
    )
    for row in REPEATED_PASS_TARGETS:
        print(
            f"{row.name:<42} {row.mean_log2_rho:14.6f} "
            f"{row.selector_bits:14.3f} {row.note:<34}"
        )
    print()


def print_lane_value_targets() -> None:
    print("== value lift needed for public lanes ==")
    print("Standalone lane needs value_lift > lane_loss. If added on top of H7,")
    print("value_lift must also cover H7's remaining witness miss.")
    print(
        f"{'r':>6} {'d':>5} {'lane loss':>10} "
        f"{'standalone lift':>16} {'H7+lane lift':>14}"
    )
    for row in lane_value_targets():
        if row.r in (0.10, 0.25, 0.50) and row.choices in (1, 4, 16, 64, 128):
            print(
                f"{row.r:6.2f} {row.choices:5d} {row.lane_loss_bits:10.3f} "
                f"{row.standalone_value_lift_needed:16.3f} "
                f"{row.total_cover_h7_value_lift_needed:14.3f}"
            )
    print()


def print_choices_target_table() -> None:
    print("== d-choice needed to make a public lane cheap ==")
    print(
        f"{'r':>6} {'target loss':>12} {'d needed':>9} {'achieved':>10}"
    )
    for r in (0.01, 0.03, 0.10, 0.25):
        for target in (2.0, 1.0, 0.5, 0.25, 0.10):
            d = choices_needed(r, target)
            print(f"{r:6.2f} {target:12.3f} {d:9d} {lane_loss(r, d):10.3f}")
    print()


def print_scientific_protocol() -> None:
    print("== systematic protocol for the next lanes ==")
    print("For every candidate, record this row before any experiment:")
    print("  mechanism | changed knob | decoder observation | currency | formula")
    print("  predicted sign | adversarial control | finite K if any | next bottleneck")
    print()
    print("Current shape learned:")
    print("  1. If selection is content-dependent, the bill is subset/permutation entropy.")
    print("  2. If selection is public, the bill is match-supply loss.")
    print("  3. If coverage is total or near-total, open/carry entropy can become small.")
    print("  4. The closest expected-bit frontier is H58 frozen bucket Q at")
    print("     +0.229195 bits; H59 raw/Q mixture can reduce sample excess")
    print("     but not below raw on held-out data.")
    print("  5. Every adaptive knob needs a paired paid row and an unpaid lower bound.")
    print("  6. Syntax can derive some selectors, but delimiter/Kraft cost must be")
    print("     scored as record cost; H56 misses by far more than H52/H53.")
    print("  7. H60 is the roughly-all gate: paid S-bit savings can cover at most")
    print("     2^-S of uniform inputs; broader coverage needs source lift or a")
    print("     public invariant that fixes state paths without a selector.")
    print("  8. H61 ranks the nearest misses: H59 needs +0.000139 bits/atom")
    print("     of real source alignment; H58 needs +0.000597 bits/atom;")
    print("     H12/H7/H9 need paid witness-gap reductions.")
    print("  9. H62 makes the source-shaped target concrete: public class")
    print("     f=0.10,a=2 crosses H59/H58 at c*=0.1454/0.1458,")
    print("     but H7 witness with f=0.10,a=8 needs c*=0.6822.")
    print(" 10. H63 prices recursive maintenance: H59/H58 atom targets need")
    print("     p_FF=0.4122/0.4141 at p_OF=f=0.10; H7 witness needs 0.9534.")
    print(" 11. H64 reopens EOF/final boards and prices the hidden length path:")
    print("     n=128,P=64,s=1 gives stateless fraction 1.084e-19 vs")
    print("     path-free apparent 0.535193 with avg path bits 114.186748.")
    print(" 12. H65 exhausts public invariants as visible-state capacity:")
    print("     variable path apparent 0.989365 at n=16,P=4 returns to")
    print("     charged 0.124985 unless finite checksum bits are spent.")
    print(" 13. H66 prices high-arity all-block options: K=128 gives")
    print("     log2 M=13.011 local option bits, but cover-shape entropy")
    print("     is about 1 bit/atom and current misses are far smaller.")
    print(" 14. H67 guards log-rho claims: a=0.99,eps=0.01 gives")
    print("     Elog=-0.004427 but blowup probability 0.923685 by P=256.")
    print(" 15. H68 finite-domain martingale audit keeps E[W]=1 for")
    print("     public Q rows; hidden best-of shows 1.009249 selector bits.")
    print(" 16. H69 fixes high-span rank-width sampling: old 49..512-bit")
    print("     spans overcharged about +1 payload bit/record.")
    print(" 17. H70 turns the map into experiment cards: changed knob, prediction,")
    print("     paid currency, adversarial control, and stop rule.")
    print(" 18. H71 gives the sharp finite-pass roughly-all frontier:")
    print("     at 90% coverage, K=0 prefix and K=1 EOF for >=1 bit/pass.")
    print(" 19. H72 shows profile/final-board/checksum multipliers cancel")
    print("     when their visible state is counted in the output length.")
    print(" 20. H73 keeps egg-carton geometry alive but prices ready/birth/order")
    print("     as visible coordinate entropy or match-supply loss.")
    print(" 21. H74 exact latent-Q tests show duplicate-cover gains, but")
    print("     uniform excess stays positive and raw/Q chooses raw-only.")
    print(" 22. H75 prices rare-blowup claims: bad tails can balance means,")
    print("     but cannot create enough short outputs for roughly-all winners.")
    print(" 23. H76 prices randomness/compute: fixed public randomness is Q;")
    print("     per-file best-of profiles owe selector bits.")
    print(" 24. H77 tests self-induced fertility: exact H74 high-Q top 10%")
    print("     needs c*~0.508 and p_FF~0.903, while uniform starts at 0.10.")
    print(" 25. H78 unifies the no-go: charged visible state leaves only")
    print("     source/fertility law or a public invariant outside the count.")
    print(" 26. The smallest constructive source-shaped target is a public fertility")
    print("     lane with d-choice routing, e.g. r=0.10,d=16 needs >0.296 bits/record")
    print("     of real value lift, with uniform controls negative.")
    print(" 27. H79 separates placement d-choice from witness d-choice:")
    print("     r=0.10,d=23 has fake +2.475 class-bias bits if charged")
    print("     at placement loss, but honest witness multiplicity is -1.914 bits.")
    print(" 28. H80 sweeps exact public-Q class sizes: f=0.25 has")
    print("     Q(F)=0.7787 versus scaled-H7 c*=0.7247, while uniform")
    print("     still pays +1.814795 bits and shuffled classes lose the lift.")
    print(" 29. H81 shows the recurrence bottleneck: entropy-coded Q saves")
    print("     1.365 bits but whitens top25 to c=0.25; visible Q-shaping")
    print("     restores c=0.7787 but spends the same 1.365 bits.")
    print(" 30. H82 prices syntax-as-subset: top25 has Q(F)=0.7787,")
    print("     but support tax 2.000 minus membership dividend 1.639")
    print("     leaves -0.361 bits; valid/fertile membership alone cannot pay.")
    print(" 31. H83 prices length-preserving relabeling: for top25 and")
    print("     F_positive, identity already maximizes Q(F); making bottom/random")
    print("     classes fertile is a huge profile/class channel.")
    print(" 32. H84 finds a real one-shot graded-law row: lambda=0.90")
    print("     saves 0.216 bits and preserves top25, but invariant R->R")
    print("     saving is 0; repeatability needs high-entropy fertility.")
    print(" 33. H85 shows high-entropy fertility is mathematically plausible")
    print("     as an ideal tail target: a 0.017703-bit entropy budget can")
    print("     buy a 0.216226-bit finite margin, if a real syntax realizes it.")
    print(" 34. H86 measures that target on the exact H80 value tail:")
    print("     soft laws need only 0.005205 entropy bits for a 0.216226")
    print("     future-value margin, but still require a native parseable grammar.")
    print(" 35. H87 prices repeatable soft-law cycles: tiny threshold rows")
    print("     are canceled by uniform-to-P capacity, while strong soft laws")
    print("     remain source-shaped targets needing real witness savings.")
    print(" 36. H88 makes the frozen grammar concrete: public type classes")
    print("     survive finite overhead at large m, best scanned eta=1.560740,")
    print("     but the value score still must become actual Telomere savings.")
    print(" 37. H89 performs that hard check: Q-score soft laws align with")
    print("     actual witness savings, but best finite score-law cycle is")
    print("     -2.530640 bits/word; oracle actual-savings law is -2.397156.")
    print(" 38. H90 proves the fixed-family public-law cap: sup_P E[S]-D(P||U)")
    print("     equals log2 Z; selected Z gives -2.173930 and collective Z")
    print("     gives -0.562959 bits/word in the H89 domain.")
    print(" 39. H91 turns that into a constructive budget: selected needs")
    print("     1.086792 bits/record, while collective/all-description needs")
    print("     only 0.277599 honest bits/record to make Z cross 1.")
    print(" 40. H92 sweeps K/D and shows optimistic K>5 collective rows can")
    print("     cross when witness width is underpriced; best lower-bound")
    print("     row K=8,D=12 gives log2 Z_total=1.001339.")
    print(" 41. H93 reruns K/D with paid extended J3D1 witness widths; all")
    print("     crossings disappear, best paid collective log2 Z=-5.301885.")
    print(" 42. H94 tests custom arithmetic rank/record witness coding; after")
    print("     normalizing seed-width multiplicity, crossings still vanish")
    print("     (best custom_record log2 Z=-1.781751).")
    print(" 43. H95 tests fixed biased expander laws; they move mass toward")
    print("     fertile outputs, but total whole-cover Kraft mass is conserved")
    print("     (paid V1 toy log2 Z=-11.885765 for every tested law).")
    print(" 44. H96 tests visible neutral genotype transfer; it finds real")
    print("     next-pass fertility lift (+5.659 bits over random same-length")
    print("     strings) but a negative paid two-pass cycle (-60.307 bits/word).")
    print(" 45. H97 samples larger neutral-transfer rows; cycles improve with")
    print("     N/K/D but remain negative, and best-of-same-budget random")
    print("     same-length controls beat the selected genotypes.")
    print(" 46. H98 reopens partial +1/+2/+4 slack refresh: unpaid sparse")
    print("     rows can barely shrink only when final freshness dies; rows")
    print("     that keep >=10% fresh output expand, and H2/literal stateless")
    print("     accounting expands in every tested row.")
    print(" 47. H99 prices seed parity/rejection readiness: even/odd seeds are")
    print("     a paid two-epoch discriminator, but many-pass exact birth")
    print("     classes cost log2(P) bits/record as seed-supply loss or residual")
    print("     ambiguity.")
    print(" 48. H100 turns that into the forced two-epoch target: parity gives")
    print("     stateless open/carry if max record lifetime <=1 pass, but")
    print("     current H7/H9/H12 rows remain negative; a real mechanism needs")
    print("     >1 paid bit/record base margin before parity.")
    print(" 49. H101 discounts parity through neutral multiplicity: class loss")
    print("     can fall below 1 bit/record, but the slack/witness width bought")
    print("     to create that multiplicity overwhelms the discount in the")
    print("     tested H9 frontier.")
    print(" 50. H102 separates visible parity from public lane grammar: if lane")
    print("     position supplies the epoch class, a local class seed rank has no")
    print("     seed-supply tax; current rows still miss, but the target narrows")
    print("     to base forced-rewrite margin > 0.")
    print(" 51. H103 verifies that split in the exact H74/H94 Kraft toy: local")
    print("     class grammar preserves base log2Z exactly, while visible global")
    print("     class restrictions lose 1.75-3.68 collective log2Z in tested rows.")
    print(" 52. H104 reconciles SPEC_V1 keep-what-decodes with scaling: small")
    print("     checksum-refereed round trips are valid finite decodes, but carried")
    print("     records still create T^R readings in the arity-1 worst case.")
    print(" 53. H105 combines the surviving pieces: public-lane local grammar")
    print("     removes about 1 bit/record of readiness tax, but the best honest")
    print("     collective target still needs 0.468557 bits/record.")
    print(" 54. H106 closes ordinary arity reweighting: valid record-sequence")
    print("     grammars obey F_n=sum W_a F_{n-a} with sum W_a<=1, so whole-cover")
    print("     mass can reach log2Z=0 but cannot become positive.")
    print(" 55. H107 closes fixed-mass value shaping for uniform data: biased")
    print("     seed/output laws keep the same log2Z and raw/Q mixtures choose raw")
    print("     unless a non-uniform source or fertility cycle is named and paid.")
    print(" 56. H108 makes the converse exact: h92_lower crosses only with")
    print("     overfull symbol mass log2=2.055381, while valid custom_record")
    print("     exactly reproduces log2Z=-1.781751.")
    print(" 57. H109 prices non-prefix/trial-decode syntax: a fixed checksum")
    print("     is only a finite referee for ambiguous readings; lotus_toy")
    print("     exhausts 64 bits after about 215 stream bits, and carried")
    print("     records reproduce the same T^R survivor ledger.")
    print(" 58. H110 sharpens partial slack refresh: parseable J3D1 still")
    print("     misses at q>=10% by +0.524497 bits/atom, but a local-width")
    print("     oracle crosses at -0.111979, isolating payload-boundary cost.")
    print(" 59. H111 tests collective width streams: counts-free enum crosses")
    print("     at -0.073289 bits/atom, but count-paid enum is +0.147041,")
    print("     so the live target is a frozen public width/delta law.")
    print(" 60. H112 freezes that public width/delta law for the ordinary")
    print("     H2-charged partial-refresh branch; held-out rows stay positive")
    print("     at +0.2531 to +0.3163 bits/atom.")
    print(" 61. H113 lets visible seed parity replace H2 only under a forced")
    print("     two-epoch age invariant; fixedD parity narrows the miss to")
    print("     +0.023438 bits/atom, while many-epoch parity aliases.")
    print(" 62. H114 combines two-epoch parity with a frozen public delta law")
    print("     and crosses in the toy kernel: B4,K32,D128,slack4 gives")
    print("     -0.020876 held-out bits/atom and 32/64 repeats stay negative.")
    print(" 63. H115 converts H114 to a variable-length record-layer audit:")
    print("     no_expiry stays negative, but force_refresh due-cohort rows")
    print("     expand at +0.020909 bits/atom/pass; local-width oracle remains")
    print("     negative, so the next target is a heterogeneous public width law.")
    print(" 64. H116 tests that next target: public arity/start/lane clocks")
    print("     still expand, best focused public row +0.023659 bits/atom/pass;")
    print("     hidden target/age bucket diagnostics also miss, so bucketed")
    print("     frozen laws are not enough for heterogeneous due refresh.")
    print(" 65. H117 prices the parser correction: code payload width directly,")
    print("     not delta against hidden target length. Best honest row is")
    print("     +0.007218 bits/atom/pass but rewrites only 12.4%; forcing")
    print("     25% rewrite expands by +0.061297 bits/atom/pass.")
    print(" 66. H118 prices collective width amortization: count-free scale-1")
    print("     crosses at -0.005928, but scaled/asymptotic entropy returns")
    print("     to about +0.026 bits/atom/pass, with ~2.26 width bits/record.")
    print(" 67. H119 tests public fixed-width lanes: sparse global rows can")
    print("     look negative, but at 25% rewrite public lanes expand and")
    print("     even hidden target-size fixed-width diagnostics miss.")
    print(" 68. H120 proves width-channel equivalence: explicit width, seed")
    print("     class supply loss, self-sync prefix cost, and checksum ambiguity")
    print("     converge around 5.34 bits/record on the H118 selected widths.")
    print(" 69. H121 tests an optimistic public-gap typed board with T_pub free;")
    print("     25% rewrite fails for gaps 1..16, and 10% rows expand or are")
    print("     fragile, so fixed public gaps do not maintain refresh.")
    print(" 70. H122 tests paid public gap alphabets. They improve supply, but")
    print("     negative lower-bound rows have 75-84% fail; the best wider")
    print("     alphabet is +0.001674 bits/atom/pass with nonzero fail.")
    print(" 71. H123 freezes public gap tables. Held-out lower-bound rows can")
    print("     go negative, e.g. public_lane_raw lane_exact_arity q=0.10")
    print("     at -0.010851 bits/atom/pass, but fail 43.75% of trials.")
    print(" 72. H124 repairs those failures with raw fallback. Markerless raw")
    print("     atoms give -0.014587 to -0.023438 bits/atom/pass, but the")
    print("     hidden type stream costs 0.157-0.194 as a bitmap or")
    print("     0.261-0.303 as raw-run boundaries.")
    print(" 73. H125 makes raw fallback public with fixed raw lanes/runs.")
    print("     Periodic lanes are parseable but all tested meaningful rows")
    print("     fail, including period 8 raw_run 7 at 25% rewrite.")
    print(" 74. H126 tests paid raw segments. One/two free segments still")
    print("     expand at atoms=128; exact boundary lists add 0.08-0.15")
    print("     bits/atom/pass, far above the H124 margin.")
    print(" 75. H127 sweeps the user's partial-rewrite sweet spot. Raw")
    print("     lower-bound deltas stay negative from 1%-25% rewrite, but")
    print("     bitmap-priced nets are +0.143 to +0.168 bits/atom/pass.")
    print(" 76. H128 quantifies the near-total public-board target: H124")
    print("     margins require roughly 99.77%-99.94% public opening as P")
    print("     grows from 2 to 4096 passes.")
    print(" 77. H129 tests counted raw-prefix zones. Parseable zones miss:")
    print("     zone=32 gives +0.121578 bits/atom/pass at 25% rewrite,")
    print("     and zone=128 fails outright in the focused row.")
    print(" 78. H130 combines near-total exceptions with witness margin.")
    print("     Exceptions always raise the required boost over all-open;")
    print("     H105 custom_record moves from 0.468557 to 0.542498")
    print("     bits/record at eps=0.001,P=4096,F=0.")
    print(" 79. H131 tests typed all-open public boards. Public slot types")
    print("     solve parsing, but positive gain limits coverage; saving 1 bit")
    print("     covers only 39.35% per pass, while 90% final survival over")
    print("     4096 passes requires about 3.40 bits of bloat.")
    print(" 80. H132 tests self-consistent width-aware selection for the")
    print("     partial-refresh sweet spot. Public arity/lane laws still")
    print("     expand, and even hidden target-arity diagnostics stay positive")
    print("     at +0.017 to +0.026 bits/atom/pass in the focused rows.")
    print(" 81. H133 tests common-cause batch witnesses. Honest batch")
    print("     convolutions are valid but worse than the base custom_record")
    print("     row; positive-looking discounted batches are overfull, e.g.")
    print("     m=2,discount=2 gives log2Z=1.220990 with log2 symbol mass=2.")
    print(" 82. H134 tests CRT/modular readiness clocks. Best clocks reach")
    print("     the log2(P) floor but do not beat it; P=4096 costs")
    print("     12.002815 bits in the small CRT sweep, so clocks only help")
    print("     after a separate invariant bounds record lifetime.")
    print(" 83. H135 starts an exact recurrent transfer harness. The tiny")
    print("     N=3,K=1,D=1 two-pass control has no zero-failure row; richer")
    print("     exact rows get expensive because pass two targets visible")
    print("     record strings, not small raw words.")
    print(" 84. H136 tests non-contiguous batch footprints over an uncovered")
    print("     board. Valid normalized footprint grammars reach log2Z=0 at")
    print("     best; free all-mask footprints cross only with local overfull")
    print("     mass, e.g. K=4 log2Z=21.656226 and max local log2=7.857981.")
    print(" 85. H137 tests bits-back salt flywheels. Balanced posterior tape")
    print("     with gamma=1 is conserved; P=4096,gap=0.25,tape=salt=64")
    print("     has net=-1024 bits, while unbalanced tape pays huge final")
    print("     settlement. Positive slope needs gamma>1 fertility.")
    print(" 86. H138 tests bounded reset ratchets. Resets cap damage but")
    print("     destroy accumulated shrink; for half-rate 90% survival,")
    print("     eps must fall from 0.003287 at P=64 to 5.144e-5 at P=4096.")
    print(" 87. H139 adds the reset/ratchet converse ledger. A P64,s=1,")
    print("     90% coverage claim has prefix support 5.421e-20; visible")
    print("     64-bit state cancels the saving, and hidden 2^32 best-of")
    print("     returns to the raw bound once the selector is paid.")
    print(" 88. H140 prices +1/+2 slack refresh supply. The local-width")
    print("     oracle has real option pressure, e.g. B4,K5,s2 q=0.999877,")
    print("     but exact J3D1 B4,K32,s2 gives q=0.342932 with H2/q=2.705")
    print("     bits per rewritten atom; q>=50% is not reached by K=4096.")
    print(" 89. H141 closes seed-derived boundary tricks by Kraft. The best")
    print("     self-delimiting seed language at fixed delta is a public")
    print("     fixed-width lane; B4,K32,delta=-1 gives q=0.393469 but")
    print("     partial+H2=+0.954706 bits/atom, and q>=0.90 needs +2 bits.")
    print(" 90. H142 optimizes intrinsic boundary classes directly. On the")
    print("     H120 pooled ledger, break-even width entropy is 1.540537")
    print("     bits/record, while optimal Kraft loss is H(W)=5.341012;")
    print("     even half entropy at 2.670506 still expands.")
    print(" 91. H143 gives a generous near-total public-board bound. Exact")
    print("     J3D1 slack<=2 tops out at q=0.342932 versus required")
    print("     q~=0.999; slack=8 reaches q~=1 but still expands, e.g.")
    print("     B4,K128 total +0.032630 bits/atom.")
    print(" 92. H144 reframes non-greedy slack as future-value selection.")
    print("     The easiest slack-8 rows need only 0.008625-0.040116")
    print("     bits/atom/candidate of real future value, making recurrent")
    print("     transfer measurement the next live target.")
    print(" 93. H145 prices upward unfolding depth. Fixed depth gives one")
    print("     output per seed; stop among T states gives coverage but costs")
    print("     log2(T), so 90% coverage at G saved bits stores back G+1.203")
    print("     stop bits unless a public invariant derives the stop.")
    print(" 94. H146 tests slack superposition directly. Exact B=1 rows")
    print("     show real future-fertility lift over some random controls,")
    print("     e.g. N6,K5,D7,s14 has +0.621127 future-vs-random,")
    print("     but full-cover two-pass total remains -29.390338 bits/word.")
    print(" 95. H147 collapses upward/downward detours to final address")
    print("     count under fixed stateless decode. Hidden branches raise")
    print("     coverage only by paying log2(T); 90% exact-length coverage")
    print("     costs G+1.203254 branch bits for G saved bits.")
    print(" 96. H148 replaces H146's collective future score with an")
    print("     actual selected second-pass stream. In the default exact")
    print("     N4,K4,D7 row, pass1 coverage reaches 1.0 at slack12 but")
    print("     two-pass selected-stream coverage remains 0.0.")
    print(" 97. H149 composes the fixed public decoder directly. In a")
    print("     high-arity K16,D4 toy, 476 valid top streams become only")
    print("     3 two-pass-composable streams and 0 three-pass streams;")
    print("     K32,D3 similarly drops to 1 two-pass stream.")
    print(" 98. H150 replaces H148 brute force with an online min-plus")
    print("     selected-stream DP. N4,K4,D7 reproduces pass2 coverage 0")
    print("     at slack12; slack20 reaches 0.625 support but final length")
    print("     averages 29.1 bits for a 4-bit word.")
    print(" 99. H151 prices closure directly. Forcing intermediates into")
    print("     the valid record-stream subset costs about 5-10 bits in")
    print("     tested rows; B1,K4,D7,t12 has tax 5.415037, and many")
    print("     high-arity exact lengths have zero valid streams.")
    print("100. H152 separates non-greedy visible paths from cloud mass.")
    print("     Visible superposition lift is real, reaching 1.890625 bits")
    print("     in N6,K5,D7,s18, but the explicit final stream still")
    print("     averages 41.593750 bits for 6 input bits; the unselected")
    print("     cloud advantage hides a 7.868868-bit rank/arithmetic gap.")
    print("101. H153 turns that cloud into an honest public Q distribution.")
    print("     Uniform targets expand by KL(U||Q): focused rows have")
    print("     +1.456567 to +2.831486 bits excess, and the raw/Q mixture")
    print("     chooses alpha=0. The cloud is source/rank-shaped, not free.")
    print("102. H154 tests fixed-cell closure where every output cell parses.")
    print("     Closure is free, but C-bit cells leave only C-ceil(log2 K)")
    print("     seed bits; best grid row touches only 12.9% of cells and")
    print("     expects 111.47 untouched cells out of 128.")
    print("103. H155 stacks the public-lane target with non-greedy lift.")
    print("     H152 lift exceeds H105's best base gap by 0.108874")
    print("     bits/word as a target transfer; closure stress raises")
    print("     the miss to +8.624339, and width stress leaves the")
    print("     best stacked row +22.798591.")
    print("104. H156 prices prefix-completion filler closure. Completed")
    print("     parse tax can fall to 0.142019 bits, but filler fraction")
    print("     is 0.993534; seed preservation tax restores the seed-only")
    print("     closure bill by seedTax = compTax + preservationTax.")
    print("105. H157 extends selected-stream DP to recursive seed-bearing")
    print("     layers. In exact tiny rows P2 can reach full coverage,")
    print("     but final streams are much longer, e.g. N4,K4,D4 has")
    print("     P2 final 39.187500 bits for 4 input bits; P3 support")
    print("     appears only with larger caps and is still deeply negative.")
    print("106. H158 instruments keep-what-decodes referee scaling. Tiny")
    print("     Robin rows keep a unique checksum-winning output, but")
    print("     pre-checksum distinct outputs reach 180 at N4,T4,")
    print("     requiring 7.491853 referee bits before safety.")
    print("107. H159 builds the seed-bearing closed-core graph directly.")
    print("     Corrected edges describe whole visible seed streams. Exact")
    print("     H96 rows find no recurrent SCC and no shorter predecessor;")
    print("     K5,D3,cap28 has 21,387 nodes, 283 edges, srcTax")
    print("     11.895128 bits, scc_nodes=0, shortF=0.")
    print("108. H160 replaces H159 target-node enumeration with a closure")
    print("     transfer matrix. It matches H159 closed counts (K5,D3,")
    print("     cap28 -> 283) and prices closure mass at clFrac=0.000258")
    print("     / clTax=11.918435 bits, with zero compressive closed paths.")
    print("109. H161 moves closure to SPEC-style item streams. Strict")
    print("     seed-only arity-2 rows show real local opportunity, e.g.")
    print("     B8,K5,D80 has hitMass=0.179325, accMass=0.000276,")
    print("     and saveMass=0.000577, but the accepted mass is far too")
    print("     small and conditioned item syntax is not a maintained")
    print("     all-data compression proof.")
    print("110. H162 runs the non-greedy full-cover item-stream DP.")
    print("     Exact V1/J3D1 K5 seed-only D80,N32 has support=0.310")
    print("     and gain/item=-4.110081; mixed_all D80,N32 improves")
    print("     to support=0.384 and gain/item=-3.472168 but spends")
    print("     literals, so H161's local signal does not become drift.")
    print("111. H163 prices higher arity in the same item DP. Fixed")
    print("     arity codes worsen K8/K16/K32 at D80; escape5 K16")
    print("     reaches support=0.833 and gain/item=-3.266563 at")
    print("     D512, narrowing but not crossing the H162 miss.")
    print("112. H164 turns fertility-selected superposition into a")
    print("     threshold: the smallest strict current miss is 8.361777")
    print("     bits/selected-record (ideal best-of-M equivalent M~=329);")
    print("     deeper D narrows bits/item but raises the per-record bar.")
    print("113. H165 measures same-cost witness multiplicity in the")
    print("     fertility-option DP. Optimistic option credit is only")
    print("     about 0.20-0.25 bits/record (ideal M~=1.15-1.19),")
    print("     far below the H164 8.36-bit requirement.")
    print("114. H166 prices visible-selected fertility conservation.")
    print("     Same-class selection has zero expected lift over")
    print("     same-budget random; the easiest strict row still has")
    print("     8.112500 bits/record remaining after H165 option credit.")
    print("115. H167 tests emitted-stream recurrence directly. Same-cost")
    print("     content lift is 0 by exchangeability; visible length/order")
    print("     control rows are nonpositive, e.g. B8,K5,D512 exact has")
    print("     pass2|pass1=0.430556 but final/i=-6.129032 and")
    print("     orderLift/i=-0.173387.")
    print("116. H168 splits public recurrent fertility into two honest")
    print("     ledgers. Restricting to a public class pays -log2(f),")
    print("     so the easiest f=0.10 post-H165 row needs 11.434428")
    print("     bits/record. Without restriction tax, uniform-start")
    print("     population mode needs a >= gap/f, i.e. 81.125")
    print("     bits/record at f=0.10, or a closed attractor plus")
    print("     startup-bloat accounting.")
    print("117. H169 scans simple public visible classes against actual")
    print("     H89 paid witness savings. The best allowed row,")
    print("     max_run<=5, has net_after_tax=-4.955644 bits/word;")
    print("     even the disallowed oracle-top paid-saving ceiling is")
    print("     only -3.041992 bits/word. Easy visible bit-shape")
    print("     classes do not supply the public fertility law.")
    print("118. H170 moves the class scan to H96 emitted record")
    print("     strings and prices class fraction by current witness")
    print("     mass. The best allowed native class, bits_suffix3=101,")
    print("     has net_after_tax=-43.208690 bits/record-string;")
    print("     the disallowed future-saving oracle ceiling is")
    print("     -41.091462. Existing H96 record classes do not cross.")
    print("119. H171 prices a designed fertile sublanguage. A boost")
    print("     a for public fraction f spends Kraft mass f*2^a,")
    print("     so restriction mode can at best repay tax=-log2(f).")
    print("     Beating the easiest 8.112500-bit gap would need")
    print("     276.761605 Kraft mass from F alone.")
    print("120. H172 tests the explicit fixed closed item-language")
    print("     recurrence F_n=sum W_a F_{n-a}. Valid grammars have")
    print("     sum W_a<=1 and lambda<=1; positive all-data drift")
    print("     appears only in overfull invalid rows such as")
    print("     slightly_overfull_K5 with sumW=1.2 and log2lambda=0.089529.")
    print("121. H173 closes the no-tax population-concentration")
    print("     loophole for roughly-all uniform data. For class fraction")
    print("     f, values a,b, and population c, the paid net is")
    print("     c*a+(1-c)*b-D(c||f)=log2Z-D(c||c_eq). Kraft-balanced")
    print("     laws have best net 0, leaving the easiest gap -8.112500.")
    print("122. H174 reopens final boards under optimal end-state entropy.")
    print("     Shrinking R can make final positions cheap per original atom,")
    print("     but per survivor they are <2 bits only for dense boards")
    print("     (roughly R/Q>=0.5); public lane classes trade state entropy")
    print("     against match-supply loss, and PCTB needs real survivor collapse.")
    print("123. H175 tests state-carrying digest-tail salts. Observing q_next")
    print("     is free while conditioning it costs 2^-r; exact V1/J3D1")
    print("     B4,K5,D12 still expands at out/in 1.438, but bounded-slack")
    print("     surface lookahead improves exact two-pass cost in tiny rows;")
    print("     sampled recursive support still collapses by passes 2-3.")
    print("124. H176 tests public finite-state width grammar plus")
    print("     mixed-radix rank packing. Correct depth-clamped Lotus")
    print("     bucket accounting removes the frontier overcount; no")
    print("     maintained positive row crosses. Best high-arity miss:")
    print("     B4,K128,D520,N128,r4,union:-1,2 has supportP=0.033333")
    print("     and packed gain/atom=-0.050781.")
    print("125. H177 extracts the total-cover Kraft bound:")
    print("     E_out <= 2^-s * sum_a 2^-ell(a). V1 arity has")
    print("     Kraft=0.875, fixed complete arity is only critical at")
    print("     s=0, and strict paid savings are subcritical unless a")
    print("     separate honest supply boost or source restriction is added.")
    print("126. H178 prices neutral same-cost / near-equal lookahead.")
    print("     Same-cost seed choice is real but option-bounded. V1")
    print("     K5,N128,s=-1 has fantasy_net=-0.119706; fixed K8")
    print("     s=-1 has only +0.000389 bits/record and path support")
    print("     0.709, while support-repaired s=-2 is negative.")
    print("127. H179 prices public generated/reachable regimes.")
    print("     Developmental roots can compress generated data, e.g.")
    print("     G12->64*128 saves 8180 bits inside the class, but the")
    print("     reachable-set tax is also 8180 bits for arbitrary data.")
    print("128. H180 tests cocycle/canonical placement. Public observed")
    print("     coordinates solve decode geometry but do not lift support;")
    print("     fixed K8,N128,s=-1 baseline support 0.676 vs observed")
    print("     g4 support 0.668. Conditioning g4 gives support 0.000,")
    print("     while route d4 at s0 repairs support to 0.969 only by")
    print("     paying -2.000 bits/record.")
    print("129. H181 tests finite checksum/referee survivor pruning.")
    print("     Reliable unique stateless decode needs c ~= log2(M)")
    print("     plus safety bits. A structural E=9.36-bit filter buys")
    print("     only a finite knee: T=64 leaves 0.132082 bits/record,")
    print("     while T=65536 leaves 6.654372 bits/record.")
    print("130. H182 tests public recurrent population laws as weighted")
    print("     transfer matrices. V1 flat has rho=0.875, fixed K8 flat")
    print("     is only critical, and positive rows cross only by")
    print("     overfull row mass or source/reachable restriction.")
    print("131. H183 implements the generated/reachable positive control.")
    print("     Stateless root unfolding compresses inside the generated")
    print("     class, e.g. G16,P6 pays 34 bits for a 4096-bit phenotype,")
    print("     but the reachable-set tax leaves arbitrary-uniform net -18.")
    print("132. H184 tests quotient/coset witnesses. Hidden coset bits")
    print("     either reduce seed supply, return as selector/referee bits,")
    print("     or become public width packing; W128,q64,R128 saves only")
    print("     one Lotus tier bit locally and checksum decode hides 2^8192")
    print("     low-bit assignments.")
    print("133. H185 tests many-to-one coalescence. Preimage residual or")
    print("     source membership cancels survivor shrink; N12->L8 has")
    print("     mean preimage 16, residual 4, gain 4, paid net 0.")
    print("134. H186 tests digest-tail/bits-back state. Observed state")
    print("     is free geometry, conditioning costs supply, selected tails")
    print("     pay selector entropy, and bits-back is positive only with")
    print("     a separate gamma>1 fertility/source law.")
    print("135. H187 tests shared macro-witnesses. Batch rank packing")
    print("     amortizes parse/tier overhead, e.g. m16,T32,W16 saves")
    print("     131 record bits, but its target-tuple coverage log2 is")
    print("     still -256, so arbitrary supply is not lifted.")
    print("136. H188 tests algebraic syndrome residuals. Full syndrome")
    print("     mode pays the omitted ambiguity back; n256,c128 stores")
    print("     128 bits but needs 128 residual bits for unique arbitrary")
    print("     decode. Low-weight residual rows are source-shaped and")
    print("     still miss after integer index cost, e.g. n256,t8 by 0.411656.")
    print("137. H189 tests non-prefix uniquely-decodable grammars with")
    print("     Sardinas-Patterson. Small exhaustive scans find non-prefix")
    print("     UD examples but Kraft<=1; overfull rows such as Kraft 1.25")
    print("     are not uniquely decodable and spend referee/checksum bits.")
    print("138. H190 tests whole-layer canonical minimum-description")
    print("     selection over every small N-bit output and exact V1/J3D1")
    print("     witness widths. The oracle gains tiny bits by omitting")
    print("     raw-vs-witness syntax, but the paid one-bit mode stays")
    print("     negative, e.g. N16,W16 gainP=-0.991653.")
    print("139. H191 replaces the one-bit mode with optimal leftover-Kraft")
    print("     raw fallback. The mode bill shrinks sharply, with the")
    print("     best nontrivial default miss at -0.007365 bits/layer,")
    print("     but fallback length N-log2(1-q) still keeps uniform gain <=0.")
    print("140. H192 tests the arithmetic/ANS/bits-back normalized mixture.")
    print("     The exact leftover point N16,W16,lambda=q=0.076172 gives")
    print("     gain=-0.063559; nonzero lambda approaches a tie only as")
    print("     lambda approaches zero and the witness effect disappears.")
    print("141. H193 tests syntax-derived ready states and closed partitions.")
    print("     Public DFA state remains a KL/source bill on arbitrary targets")
    print("     (N16,W16,short,raw/canonpart gainU=-0.000198).")
    print("     Closed partition N16,W8,t1 reaches -0.000113 only after")
    print("     support collapses to 9/65536, so it is a finite knee.")
    print("142. H194 tests public finite-state language transforms.")
    print("     Surface syntax can show large apparent gain versus expanded")
    print("     m-bit words, but real input gain stays negative: maxrun2")
    print("     N8,m11,W4 semantic_reclaim has realGain=-0.000721,")
    print("     and primdyck4 N8,m18,W16 reaches only -1.305e-08.")
    print("143. H195 tests public multi-salt witness-mass smoothing.")
    print("     Paid public lanes preserve nonzero witness mass and fill")
    print("     support, e.g. N8,W8,L4096 has q=0.050781 and full support,")
    print("     but only reaches gain=-5.239e-06 because normalized Q gives")
    print("     E_U[-log2 Q]=N+D(U||Q)>=N.")
    print("144. H196 tests recursive self-induced source laws.")
    print("     Biasing the next layer toward Q creates apparent gain,")
    print("     but the source-law tax cancels it: N8,W8,L4096,beta1")
    print("     appGain=+5.242e-06, srcTax=+5.242e-06, paidNet=0.")
    print("145. H197 tests bounded referee / hidden-lane overfullness.")
    print("     Hidden lanes can make q overfull, e.g. W8,L32 surplus")
    print("     0.700440 bits, but the omitted lane selector is 5 bits")
    print("     and a 99% checksum adds another 6.636612-bit margin.")
    print("146. H198 makes the generated positive control Telomere-native.")
    print("     Rooted seed trees shrink at every pass inside the reachable")
    print("     class: G16,C8,B32,A5,P6 gains 499965 bits with min")
    print("     step gain 59, while arbitrary-uniform net remains -19")
    print("     or -11 when P is fixed by public preset.")
    print("147. H199 tests arbitrary residual attachment to H198 trees.")
    print("     Exact root+Hamming residual support never beats the")
    print("     pair-count bill: N16,G4,r8 reaches full coverage but")
    print("     nets -16.258676; large H198 bound remains G-paid=-11.")
    print("148. H200 tests nearest generated-cover residuals at high coverage.")
    print("     At N500000,m16,99% coverage, paid-index lower bound still")
    print("     expands by +2.184448 with Kraft fallback; native fixed H198")
    print("     expands by +13.070864. Free-index wins are hidden selectors.")
    print("149. H201 tests multi-root generated XOR superposition.")
    print("     Sparse XORs tie only under paid selected-root rank and lose")
    print("     natively; full spans need bitmasks and still leave support")
    print("     gaps, e.g. N500000,m16 rank bound leaves 434464 bits.")
    print("150. H202 tests biological recombination/crossover of H198 trees.")
    print("     Crossover points increase support only by the same stored")
    print("     rank the decoder needs; H198 G16,A5,P6 stays at fixed")
    print("     native net -21 for two parents and -41 for four parents.")
    print("151. H203 makes the crossover schedule decoder-derived.")
    print("     Removing crossover rank removes the added address space:")
    print("     support is bounded by pG; exact p2,t1 reaches logSupp")
    print("     5.930737 under a 6-bit tuple but still loses natively.")
    print("152. H204 tests public orbit selection.")
    print("     Canonical visible selection is free but support-thinning;")
    print("     indexed selection uses the orbit only by paying rank.")
    print("153. H205 builds the visible-population generated law.")
    print("     M32,G16,A5,P6 pays 833 bits for 16,000,000 generated")
    print("     bits with min step gain 1888, but arbitrary-uniform")
    print("     upper net remains -321 = M*G - paid.")
    print("154. H206 optimizes that arbitrary-uniform overhead.")
    print("     Exact V1/J3D1 root records never have cost <= support")
    print("     rank: best scanned miss is -7 bits overall, and -8")
    print("     bits for the high-growth A5 branch.")
    print("155. H207 packs visible root populations directly.")
    print("     Ideal packed roots tie at zero only with no mode/fallback")
    print("     and tiny support; any parse mode or raw fallback restores")
    print("     Kraft/fallback expansion under uniform data.")
    print("156. H208 turns visible populations into a normalized prior.")
    print("     Uniform overhead can be tiny (3.377e-97 bits in M32),")
    print("     but source-shaped gains are exactly balanced by source")
    print("     entropy tax: paid net = -D(P||Q) <= 0.")
    print("157. H209 makes the visible-population branch an exact codec.")
    print("     The tiny finite codec round-trips all N8 outputs; packed roots")
    print("     gain 4 bits inside the reachable class but lose 1 bit after")
    print("     membership/raw accounting. Large M32,G16 still gains 15999167")
    print("     generated bits natively, with arbitrary net -321.")
    print("158. H210 prices final-board / position-derived salt channels.")
    print("     Dense boards can amortize finite notes (rho 0.9 has occ/R")
    print("     0.516089), but P64 birth labels need 6 bits/record and")
    print("     leave 5483.911082 residual bits at R1000,Q1111.")
    print("159. H211 enumerates the actual self-induced emitted prior.")
    print("     N8,W8 has H_emit=8 and mean emitted length 8.996094;")
    print("     oracle Q=P_emit only ties at paidNet=0, while the actual")
    print("     code prior loses by KL (-0.001718 bits).")
    print("160. H212 tests bounded-slack non-greedy witness lookahead.")
    print("     Stored seeds can legally steer digest-tail state: with")
    print("     B8,A1,W8,S2,credit2, zero slack lifts tail rate from")
    print("     0.512528 to 0.578588. Slack1 lifts it to 0.637813 but")
    print("     pays 0.059226 bits, so the future fertility law must be real.")


def main() -> None:
    print_selection_surface()
    print_exception_surface()
    print_total_cover_targets()
    print_repeated_pass_targets()
    print_lane_value_targets()
    print_choices_target_table()
    print_scientific_protocol()


if __name__ == "__main__":
    main()

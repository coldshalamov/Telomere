"""v-next proof kernel: LITERAL_RUN, BIT_LITERAL singles, position-salted
expansion, k-XOR (meet-in-the-middle) records, jumpstarter profiles, and
dual window semantics (entry-aligned + aB-bit grid).

ADDITIVE module: the audited v1/BIT_LITERAL lane in ``entry_state.py`` is
untouched. Expectation-level exact counting on ``costs.py`` arithmetic under
the single empirical assumption P(match) = 2^-S per (seed-tuple, content,
position) trial.

LAYER MODEL. A layer is a self-delimiting entry stream:

  seed record    [arity codeword][Lotus(s_1)]..[Lotus(s_k)]
  single literal [single codeword][block_bits raw]            (BIT_LITERAL)
  literal run    [run codeword][Lotus(payload_bit_len)][payload raw bits]

Decoding layer t+1 reproduces layer t's bitstream: expand records, copy
literals, concatenate; termination is out-of-band by payload_bit_len
(FORMAT_CANONICAL.md section 6). Two decodable expansion-length rules:

  ENTRY mode: the expansion is parsed self-delimitingly until ``a`` entries
      complete (records-over-records; the audited lane's semantics).
      Window = a consecutive entries; content = budget = their encoded bits.
  GRID mode: the expansion is exactly ``a * block_bits`` bits at any bit
      offset (length is decoder-known; no alignment requirement).
      Window = aB bits anywhere; clean/dirty/interior split priced by an
      exact walk DP over the entry mix (clipping a record mid-bits forces
      the remnant into a new charged run header).

Which arities use which mode is a decoder-public alphabet constant.

LITERAL_RUN is the legal rechunk: the dead bit-rechunk lanes failed for
lack of a charged record/chunk discriminator; here the discriminator is the
prefix-free codeword plus the charged Lotus run-length header.

FRESHNESS (computed, never assumed):
  position_salt = LAYER-MASKED expansion: expand(seed) XOR
      mask(layer_index, output_bit_offset), mask a fixed public schedule.
      Zero metadata; every window re-rolls every pass (fresh = 1); the seed
      table stays unsalted and shared. NOTE: salting by position alone
      DEADLOCKS (pre-first-accept emission replicates the previous layer, so
      queries repeat) — caught by freshness_law_validation.py; the layer
      index is what breaks it.
  permutation   3 charged bits/pass; multi-entry windows fresh, arity-1
      entry windows fresh only via cascade; grid interiors stale.
  none          cascade only.

k-XOR RECORDS: decoder XORs k expansions (profile constant k). M_k by exact
convolution of the per-field cost distribution, divided by k! (unordered).
Compute (reported separately, never inside size): 2-list MitM 2^(D/2) time
and memory; Wagner 4-tree ~2^(D/3); with position salt only seed #1 is
salted so shared tables survive across positions and passes.

HARD GATES: every header bit charged in its emitting layer; no passthrough;
greedy deterministic selection (oracle labeled); salt metadata 0;
permutation 3 bits/pass.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from functools import lru_cache

from costs import (
    lotus_cost_for_value,
    lotus_width_for_value,
    max_payload_width_for_j_bits,
    payload_width_count_le,
    seed_count_for_depth_bits,
)
from superposition_model import SuperpositionConfig, retained_variant_stats

LN2 = math.log(2.0)


# ---------------------------------------------------------------------------
# Alphabets: codeword assignment is a decoder-public profile constant
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Alphabet:
    name: str
    entry_arities: tuple[tuple[int, int], ...]  # ((arity, codeword_bits), ...)
    grid_arities: tuple[tuple[int, int], ...]
    single_marker_bits: int | None
    run_marker_bits: int | None
    # RUN_FIXED: [codeword][fixed_run_blocks * block_bits raw] — NO length
    # field (profile constant), self-delimiting like BIT_LITERAL with a
    # larger payload. Zero length-metadata literal grouping.
    fixed_run_marker_bits: int | None = None
    fixed_run_blocks: int = 0

    def kraft(self) -> float:
        total = sum(2.0 ** -b for _, b in self.entry_arities)
        total += sum(2.0 ** -b for _, b in self.grid_arities)
        if self.single_marker_bits is not None:
            total += 2.0 ** -self.single_marker_bits
        if self.run_marker_bits is not None:
            total += 2.0 ** -self.run_marker_bits
        if self.fixed_run_marker_bits is not None:
            total += 2.0 ** -self.fixed_run_marker_bits
        return total


ALPHABETS: dict[str, Alphabet] = {
    # audited BIT_LITERAL alphabet: entry arities 1..5 + 3-bit single (111)
    "audited_equiv": Alphabet(
        "audited_equiv", ((1, 2), (2, 2), (3, 3), (4, 3), (5, 3)), (), 3, None
    ),
    # entry arities 1..4 + single (110) + run (111)
    "entry_singles_run": Alphabet(
        "entry_singles_run", ((1, 2), (2, 2), (3, 3), (4, 3)), (), 3, 3
    ),
    # entry 1..3 + one grid arity + single + run
    "grid_mix": Alphabet(
        "grid_mix", ((1, 2), (2, 2), (3, 3)), ((4, 3),), 3, 3
    ),
    # entry 1..2 + grid 3..4 + single + run
    "grid_heavy": Alphabet(
        "grid_heavy", ((1, 2), (2, 2)), ((3, 3), (4, 3)), 3, 3
    ),
    # no singles: entry 1..2 + grid 3..5 + run (pure run carriage)
    "runs_only_grid": Alphabet(
        "runs_only_grid", ((1, 2), (2, 2)), ((3, 3), (4, 3), (5, 3)), None, 3
    ),
    # cheap-literal pass-1 alphabet: single = 2 bits
    "single_cheap": Alphabet(
        "single_cheap", ((1, 2), (2, 3), (3, 3), (4, 3)), (), 2, 3
    ),
    # fixed-run alphabets: RUN_FIXED(m0) costs only its codeword (no Lotus
    # length field); variable runs (111) remain for remnants/fragments.
    "fixedrun2_singles": Alphabet(
        "fixedrun2_singles", ((1, 2), (2, 2), (3, 3)), (), 3, 3,
        fixed_run_marker_bits=3, fixed_run_blocks=2,
    ),
    "fixedrun3_singles": Alphabet(
        "fixedrun3_singles", ((1, 2), (2, 2), (3, 3)), (), 3, 3,
        fixed_run_marker_bits=3, fixed_run_blocks=3,
    ),
    "fixedrun4_singles": Alphabet(
        "fixedrun4_singles", ((1, 2), (2, 2), (3, 3)), (), 3, 3,
        fixed_run_marker_bits=3, fixed_run_blocks=4,
    ),
    "fixedrun2_grid": Alphabet(
        "fixedrun2_grid", ((1, 2), (2, 2)), ((3, 3),), 3, 3,
        fixed_run_marker_bits=3, fixed_run_blocks=2,
    ),
    "fixedrun4_grid": Alphabet(
        "fixedrun4_grid", ((1, 2), (2, 2)), ((3, 3),), 3, 3,
        fixed_run_marker_bits=3, fixed_run_blocks=4,
    ),
}

for _a in ALPHABETS.values():
    if abs(_a.kraft() - 1.0) > 1e-12:
        raise AssertionError(f"alphabet {_a.name} not Kraft-complete: {_a.kraft()}")


# ---------------------------------------------------------------------------
# k-XOR record counting
# ---------------------------------------------------------------------------


@lru_cache(maxsize=None)
def _field_cost_counts(depth_bits: int, j_bits: int, max_cost: int) -> tuple[float, ...]:
    counts = [0.0] * (max_cost + 1)
    cap_width = max_payload_width_for_j_bits(j_bits)
    depth_cap = seed_count_for_depth_bits(depth_bits)
    for pw in range(1, cap_width + 1):
        cost = j_bits + lotus_width_for_value(pw) + pw
        if cost > max_cost:
            if pw > max_cost:
                break
            continue
        le_w = min(payload_width_count_le(pw), depth_cap)
        le_p = min(payload_width_count_le(pw - 1), depth_cap)
        cnt = max(0, le_w - le_p)
        if cnt:
            counts[cost] += float(cnt)
    return tuple(counts)


@lru_cache(maxsize=None)
def _k_field_cumulative(k: int, depth_bits: int, j_bits: int, max_cost: int) -> tuple[float, ...]:
    base = _field_cost_counts(depth_bits, j_bits, max_cost)
    acc = [0.0] * (max_cost + 1)
    acc[0] = 1.0
    for _ in range(k):
        nxt = [0.0] * (max_cost + 1)
        for c1, n1 in enumerate(acc):
            if n1 <= 0.0:
                continue
            for c2 in range(0, max_cost - c1 + 1):
                n2 = base[c2]
                if n2 > 0.0:
                    nxt[c1 + c2] += n1 * n2
        acc = nxt
    out, run = [], 0.0
    for c in range(max_cost + 1):
        run += acc[c]
        out.append(run)
    return tuple(out)


@lru_cache(maxsize=None)
def m_records(arity_codeword_bits: int, record_budget_bits: int, depth_bits: int,
              j_bits: int = 3, k_xor: int = 1) -> float:
    field_budget = record_budget_bits - arity_codeword_bits
    if field_budget < k_xor * (j_bits + 2):
        return 0.0
    cum = _k_field_cumulative(k_xor, depth_bits, j_bits, min(field_budget, 700))
    return cum[min(field_budget, len(cum) - 1)] / math.factorial(k_xor)


def min_record_bits_v(arity_codeword_bits: int, j_bits: int, k_xor: int) -> int:
    return arity_codeword_bits + k_xor * (j_bits + 2)


def _poissonized(log_expected: float) -> float:
    if log_expected > 36.0:
        return 1.0
    if log_expected < -36.0:
        return math.exp(log_expected)
    return -math.expm1(-math.exp(log_expected))


@lru_cache(maxsize=None)
def hit_and_gain(content_bits: int, budget_bits: int, arity_codeword_bits: int,
                 depth_bits: int, j_bits: int, k_xor: int,
                 multiplier: float = 1.0) -> tuple[float, float]:
    """(P(hit), unconditional E[gain]) for records with cost <= budget.

    gain = (budget+1) - record_cost; E[gain] = sum_{b=floor..budget} P(min<=b).
    """

    floor = min_record_bits_v(arity_codeword_bits, j_bits, k_xor)
    if budget_bits < floor or content_bits <= 0 or multiplier <= 0:
        return 0.0, 0.0
    log_c = content_bits * LN2
    m_top = m_records(arity_codeword_bits, budget_bits, depth_bits, j_bits, k_xor)
    if m_top <= 0:
        return 0.0, 0.0
    hit = _poissonized(math.log(m_top * multiplier) - log_c)
    egain = 0.0
    for budget in range(floor, budget_bits + 1):
        m = m_records(arity_codeword_bits, budget, depth_bits, j_bits, k_xor)
        if m > 0:
            egain += _poissonized(math.log(m * multiplier) - log_c)
    return hit, egain


# ---------------------------------------------------------------------------
# Freshness (computed)
# ---------------------------------------------------------------------------


def salted_fresh_fraction(accepted_prev: float) -> float:
    a = max(0.0, accepted_prev)
    if a <= 1e-12:
        return 0.0
    if a > 700.0:
        return 1.0 - 1.0 / a
    return 1.0 - (1.0 - math.exp(-a)) / a


# ---------------------------------------------------------------------------
# Walk DP for grid windows
# ---------------------------------------------------------------------------


def _junction_walk(span_bits: int, rho_rec: float,
                   rec_pmf: tuple[tuple[int, float], ...],
                   avg_run_payload_bits: int = 1 << 30) -> tuple[float, float, float]:
    """(P_clean, E[entries consumed | clean], E[entry bits consumed | clean]).

    From a junction, with ``remaining`` window bits:
    - next is a run (prob 1-rho_rec), modeled at the fixed average payload
      length: if payload >= remaining the window ends inside it -> CLEAN
      stop (run shortens from the front, no split); otherwise the window
      consumes the WHOLE short run (its header vanishes — bonus uncredited,
      conservative on gain) and the walk continues past it;
    - next is an entry of length L: L < remaining -> consume, continue;
      L == remaining -> clean exact; L > remaining -> DIRTY (mid-entry clip:
      the remnant is re-carried under a new charged header).

    Short runs therefore no longer launder dirty mass as clean: the walk
    keeps going and prices whatever the far edge actually lands on.
    """

    if span_bits <= 0:
        return 1.0, 0.0, 0.0
    if not rec_pmf:
        rho_rec = 0.0
    run_step = max(1, int(avg_run_payload_bits))

    @lru_cache(maxsize=None)
    def go(remaining: int) -> tuple[float, float, float]:
        if remaining <= 0:
            return 1.0, 0.0, 0.0
        p_clean = 0.0
        e_n = 0.0
        e_b = 0.0
        w_run = 1.0 - rho_rec
        if w_run > 0.0:
            if run_step >= remaining:
                p_clean += w_run  # clean stop inside the run
            else:
                s_p, s_n, s_b = go(remaining - run_step)
                p_clean += w_run * s_p
                e_n += w_run * s_n
                e_b += w_run * s_b
        if rho_rec > 0.0:
            for length, prob in rec_pmf:
                w = rho_rec * prob
                if w <= 1e-15:
                    continue
                if length < remaining:
                    s_p, s_n, s_b = go(remaining - length)
                    p_clean += w * s_p
                    e_n += w * (s_p + s_n)
                    e_b += w * (s_p * length + s_b)
                elif length == remaining:
                    p_clean += w
                    e_n += w
                    e_b += w * length
        return p_clean, e_n, e_b

    p, en, eb = go(span_bits)
    go.cache_clear()
    if p <= 0.0:
        return 0.0, 0.0, 0.0
    return p, en / p, eb / p


# ---------------------------------------------------------------------------
# Config / state / ledger row
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class VConfig:
    name: str = "vnext"
    block_bits: int = 8
    input_blocks: int = 1_000_000
    depth_schedule_bits: tuple[int, ...] = (96,)
    j_bits: int = 3
    k_xor: int = 1
    alphabet_schedule: tuple[str, ...] = ("audited_equiv",)
    refresh: str = "position_salt"  # position_salt | affine_epoch | permutation | none
    singles_fraction: float = 1.0  # phi: pass-1 mass exposed as singles
    fixed_run_fraction: float = 0.0  # share of the (1-phi) mass in FIXED runs
    initial_segments: int = 1  # S0: run count for the variable-run mass
    superposition: SuperpositionConfig = field(
        default_factory=lambda: SuperpositionConfig(16, 4, True, True)
    )
    include_interior_channel: bool = True
    oracle: bool = False

    def alphabet_for_pass(self, i: int) -> Alphabet:
        return ALPHABETS[self.alphabet_schedule[min(i, len(self.alphabet_schedule) - 1)]]

    def depth_for_pass(self, i: int) -> int:
        return self.depth_schedule_bits[min(i, len(self.depth_schedule_bits) - 1)]


@dataclass
class VState:
    raw_bits: float
    run_payload_bits: float
    segments: float
    entries: dict[int, float]  # encoded length -> count (records + singles)
    pass_index: int = 0
    metadata_bits: float = 0.0
    accepted_prev: float = 0.0
    changed_fraction: float = 1.0

    @property
    def entry_count(self) -> float:
        return sum(self.entries.values())

    @property
    def entry_bits(self) -> float:
        return sum(l * c for l, c in self.entries.items())

    def run_header_bits(self, alpha: Alphabet, j_bits: int) -> float:
        if self.segments <= 0 or self.run_payload_bits <= 0 or alpha.run_marker_bits is None:
            return 0.0
        avg = max(1, round(self.run_payload_bits / self.segments))
        return self.segments * (alpha.run_marker_bits + lotus_cost_for_value(avg, j_bits))

    def layer_bits(self, alpha: Alphabet, j_bits: int) -> float:
        return (self.entry_bits + self.run_payload_bits
                + self.run_header_bits(alpha, j_bits) + self.metadata_bits)


@dataclass(frozen=True)
class VRow:
    pass_index: int
    depth_bits: int
    alphabet: str
    refresh_rule: str
    bits_before: float
    bits_after: float
    metadata_bits_pass: float
    net_delta_pct_current: float
    net_delta_pct_raw: float
    fresh_entry1: float
    fresh_multi: float
    fresh_grid: float
    entry_windows: float
    grid_junction_windows: float
    grid_interior_windows: float
    accepted_entry: float
    accepted_grid_clean: float
    accepted_grid_dirty: float
    accepted_grid_interior: float
    accepted_windows: float
    expected_gain_bits: float
    header_delta_bits: float
    segments: float
    entry_count: float
    entry_bits: float
    run_payload_bits: float
    run_header_bits: float
    avg_variants: float
    window_multiplier: float
    final_over_raw: float
    uncharged_passthrough: bool = False


def initial_state(cfg: VConfig) -> VState:
    alpha = cfg.alphabet_for_pass(0)
    raw = float(cfg.input_blocks * cfg.block_bits)
    phi = max(0.0, min(1.0, cfg.singles_fraction))
    entries: dict[int, float] = {}
    singles_blocks = phi * cfg.input_blocks
    if singles_blocks > 0:
        if alpha.single_marker_bits is None:
            raise ValueError(f"alphabet {alpha.name} has no single codeword; set phi=0")
        entries[alpha.single_marker_bits + cfg.block_bits] = singles_blocks
    run_mass_bits = (1.0 - phi) * raw
    segments = 0.0
    if run_mass_bits > 0:
        fix_share = max(0.0, min(1.0, cfg.fixed_run_fraction))
        if alpha.fixed_run_marker_bits is not None and alpha.fixed_run_blocks > 0 and fix_share > 0:
            # FIXED runs: entries of marker + m0*B bits, zero length metadata.
            m0 = alpha.fixed_run_blocks
            fixed_bits = run_mass_bits * fix_share
            count = fixed_bits / (m0 * cfg.block_bits)
            length = alpha.fixed_run_marker_bits + m0 * cfg.block_bits
            entries[length] = entries.get(length, 0.0) + count
            run_mass_bits -= fixed_bits
        if run_mass_bits > 1e-9:
            if alpha.run_marker_bits is None:
                raise ValueError(f"alphabet {alpha.name} has no variable-run codeword")
            segments = float(max(1, min(cfg.initial_segments, int(run_mass_bits))))
        else:
            run_mass_bits = 0.0
    return VState(raw_bits=raw, run_payload_bits=run_mass_bits, segments=segments,
                  entries=entries)


def _conservative_multiplier(score: float, arity: int) -> float:
    if score <= 1.0 or arity <= 1:
        return max(1.0, score)
    per = score ** (1.0 / arity)
    return 1.0 + arity * (per - 1.0)


def run_pass(state: VState, cfg: VConfig) -> tuple[VState, VRow]:
    alpha = cfg.alphabet_for_pass(state.pass_index)
    depth = cfg.depth_for_pass(state.pass_index)
    b = cfg.block_bits
    bits_before = state.layer_bits(alpha, cfg.j_bits)

    # ---- freshness ----------------------------------------------------------
    if state.pass_index == 0:
        fresh_e1 = fresh_multi = fresh_grid = 1.0
    elif cfg.refresh == "position_salt":
        # LAYER-MASKED expansion: expand(seed) XOR mask(layer_index, offset).
        # Both inputs are decoder-known; the mask schedule is a fixed protocol
        # constant => zero metadata and EVERY window re-rolls every pass.
        # (Position-only salting deadlocks: until the first accept of a pass
        # the emission replicates the previous layer, so queries repeat and
        # re-miss — measured dead by pass 3 in freshness_law_validation.py.)
        fresh_e1 = fresh_multi = fresh_grid = 1.0
    elif cfg.refresh == "affine_epoch":
        # COMPARISON LANE (handoff v2): pass-indexed affine permutation +
        # per-epoch expansion salts; bundles recover their epoch by stride
        # inference with a charged 1-bit escape at ~pass_index/N collision
        # rate. Under the uniform law its per-window trial statistics equal
        # the layer-masked lane; it differs only in charges (escape ledger)
        # and decode compute (T stride tests per bundle, reported in the
        # compute estimate). Kept as the fallback if masking ever fails.
        fresh_e1 = fresh_multi = fresh_grid = 1.0
    elif cfg.refresh == "permutation":
        fresh_e1 = max(0.0, min(1.0, state.changed_fraction))
        fresh_multi = 1.0
        fresh_grid = 0.0  # permutation does not refresh run-interior content
    else:
        u = max(0.0, min(1.0, state.changed_fraction))
        fresh_e1 = u
        fresh_multi = 1.0 - (1.0 - u) ** 2
        fresh_grid = 0.0
    metadata_pass = 3.0 if cfg.refresh == "permutation" else 0.0

    # ---- superposition multiplier (earned, conservative) ---------------------
    n_e = state.entry_count
    avg_variants = 1.0
    score = 1.0
    if n_e > 0:
        score = 0.0
        avg_variants = 0.0
        for length, count in state.entries.items():
            stat = retained_variant_stats(int(length), depth, cfg.superposition)
            w = count / n_e
            score += w * stat.weighted_score
            avg_variants += w * stat.avg_variants
        score = max(1.0, score)

    new_entries: dict[int, float] = {}
    accepted_entry = 0.0
    accepted_clean = 0.0
    accepted_dirty = 0.0
    accepted_interior = 0.0
    gain_bits = 0.0
    header_delta_bits = 0.0
    coverage_entry_count = 0.0
    coverage_entry_bits = 0.0
    coverage_run_bits = 0.0
    max_mult = 1.0

    # ---- ENTRY-mode windows ---------------------------------------------------
    # entry pmf includes runs as entries (encoded length; long runs simply
    # never hit, which is the depth gate operating as designed)
    pmf: dict[int, float] = {}
    total_stream_entries = n_e + state.segments
    if total_stream_entries > 0:
        for length, count in state.entries.items():
            pmf[length] = pmf.get(length, 0.0) + count / total_stream_entries
        if state.segments > 0 and alpha.run_marker_bits is not None:
            avg = max(1, round(state.run_payload_bits / state.segments))
            run_len = alpha.run_marker_bits + lotus_cost_for_value(avg, cfg.j_bits) + avg
            pmf[run_len] = pmf.get(run_len, 0.0) + state.segments / total_stream_entries

    run_entry_len = None
    if state.segments > 0 and alpha.run_marker_bits is not None:
        avg = max(1, round(state.run_payload_bits / state.segments))
        run_entry_len = alpha.run_marker_bits + lotus_cost_for_value(avg, cfg.j_bits) + avg

    current = dict(pmf)
    for arity, a_bits in alpha.entry_arities:
        if arity > 1:
            nxt: dict[int, float] = {}
            for l1, p1 in current.items():
                for l2, p2 in pmf.items():
                    pp = p1 * p2
                    if pp > 1e-14:
                        nxt[l1 + l2] = nxt.get(l1 + l2, 0.0) + pp
            current = nxt
        f = fresh_e1 if arity == 1 else fresh_multi
        if f <= 0 or total_stream_entries < arity:
            continue
        windows = total_stream_entries - arity + 1.0
        mult = math.floor(_conservative_multiplier(score, arity) * 1000.0) / 1000.0
        max_mult = max(max_mult, mult)
        for span, prob in current.items():
            if prob <= 1e-14:
                continue
            hit, egain = hit_and_gain(span, span - 1, a_bits, depth, cfg.j_bits, cfg.k_xor, mult)
            hit_f = hit * f
            if hit_f <= 0:
                continue
            raw_mass = windows * prob * hit_f
            if not cfg.oracle:
                density = (windows * hit_f) * arity / max(total_stream_entries, 1.0)
                raw_mass *= 1.0 / (1.0 + max(0.0, arity - 1) * density)
            gain_per = egain / hit
            floor_bits = min_record_bits_v(a_bits, cfg.j_bits, cfg.k_xor)
            rec_len = max(floor_bits, round(span - gain_per))
            new_entries[rec_len] = new_entries.get(rec_len, 0.0) + raw_mass
            accepted_entry += raw_mass
            gain_bits += raw_mass * gain_per
            coverage_entry_count += raw_mass * arity
            coverage_entry_bits += raw_mass * span

    # ---- GRID-mode windows ------------------------------------------------------
    junctions = total_stream_entries  # alternating boundaries (+/- 1)
    interior_offsets = max(0.0, state.run_payload_bits - 2.0 * state.segments * b)
    avg_seg_len = state.run_payload_bits / state.segments if state.segments else 0.0
    frag_header = 0
    if alpha.run_marker_bits is not None:
        frag_header = alpha.run_marker_bits + lotus_cost_for_value(
            max(1, round(avg_seg_len / 2) if avg_seg_len >= 2 else 1), cfg.j_bits
        )
    remnant_header = (alpha.run_marker_bits or 3) + lotus_cost_for_value(max(1, b), cfg.j_bits)
    rho_rec = n_e / max(junctions, 1.0)
    rec_pmf_t = tuple(
        (length, count / n_e) for length, count in sorted(state.entries.items())
    ) if n_e > 0 else ()

    for arity, a_bits in alpha.grid_arities:
        span = arity * b
        mult = math.floor(_conservative_multiplier(score, arity) * 1000.0) / 1000.0
        max_mult = max(max_mult, mult)
        p_clean, e_n_clean, e_b_clean = _junction_walk(
            span, rho_rec, rec_pmf_t,
            int(avg_seg_len) if avg_seg_len > 0 else (1 << 30))
        clean_w = 2.0 * junctions * p_clean
        dirty_w = 2.0 * junctions * (1.0 - p_clean)
        hit_c, egain_c = hit_and_gain(span, span - 1, a_bits, depth, cfg.j_bits, cfg.k_xor, mult)
        hit_d, egain_d = hit_and_gain(span, span - 1 - remnant_header, a_bits, depth,
                                      cfg.j_bits, cfg.k_xor, mult)
        hit_i, egain_i = (0.0, 0.0)
        if cfg.include_interior_channel and interior_offsets > 0 and frag_header:
            hit_i, egain_i = hit_and_gain(span, span - 1 - frag_header, a_bits, depth,
                                          cfg.j_bits, cfg.k_xor, mult)
        for w_count, hit, egain, channel in (
            (clean_w, hit_c, egain_c, "clean"),
            (dirty_w, hit_d, egain_d, "dirty"),
            (interior_offsets, hit_i, egain_i, "interior"),
        ):
            f = fresh_grid
            hit_f = hit * f
            if hit_f <= 0 or w_count <= 0:
                continue
            raw_mass = w_count * hit_f
            if not cfg.oracle:
                density = raw_mass * span / max(bits_before, 1.0)
                raw_mass *= 1.0 / (1.0 + density)
            gain_per = egain / hit
            floor_bits = min_record_bits_v(a_bits, cfg.j_bits, cfg.k_xor)
            rec_len = max(floor_bits, round(span - gain_per))
            new_entries[rec_len] = new_entries.get(rec_len, 0.0) + raw_mass
            gain_bits += raw_mass * gain_per
            if channel == "interior":
                accepted_interior += raw_mass
                header_delta_bits += raw_mass * frag_header
                coverage_run_bits += raw_mass * span
            elif channel == "dirty":
                accepted_dirty += raw_mass
                header_delta_bits += raw_mass * remnant_header
                coverage_run_bits += raw_mass * span * (1.0 - rho_rec)
                coverage_entry_bits += raw_mass * span * rho_rec
            else:
                accepted_clean += raw_mass
                coverage_entry_count += raw_mass * e_n_clean
                coverage_entry_bits += raw_mass * e_b_clean
                coverage_run_bits += raw_mass * max(0.0, span - e_b_clean)

    accepted_total = accepted_entry + accepted_clean + accepted_dirty + accepted_interior
    if cfg.refresh == "affine_epoch":
        # stride-collision escape ledger: 1 bit per multi-entry accept at
        # ~pass_index/N rate, plus 1 bit per bundle whose stride test is
        # ambiguous at decode. Expectation-level charge:
        n_total = max(1.0, n_e + state.segments)
        escape_bits = accepted_total * min(1.0, (state.pass_index + 1) / n_total)
        metadata_pass += escape_bits

    # coverage sanity cap (greedy non-overlap)
    cover = coverage_entry_bits + coverage_run_bits
    if cover > 0.6 * bits_before:
        s = 0.6 * bits_before / cover
        for d in (new_entries,):
            for k in list(d):
                d[k] *= s
        accepted_entry *= s; accepted_clean *= s; accepted_dirty *= s
        accepted_interior *= s; accepted_total *= s; gain_bits *= s
        header_delta_bits *= s; coverage_entry_count *= s
        coverage_entry_bits *= s; coverage_run_bits *= s

    # ---- apply ---------------------------------------------------------------
    entries = dict(state.entries)
    # entry-channel + clean-grid coverage removes whole entries; the pmf used
    # for selection included runs, so split removal between entries and runs
    # by their share of the covered span mass.
    total_pmf_bits = state.entry_bits + (state.run_payload_bits +
        (state.run_header_bits(alpha, cfg.j_bits)))
    entry_share = state.entry_bits / total_pmf_bits if total_pmf_bits > 0 else 0.0
    remove_entry_bits = min(state.entry_bits, coverage_entry_bits * entry_share)
    removed_run_via_entry = coverage_entry_bits - remove_entry_bits
    if remove_entry_bits > 0 and state.entry_bits > 0:
        frac = min(0.98, remove_entry_bits / state.entry_bits)
        entries = {k: v * (1.0 - frac) for k, v in entries.items()}
    # Run-entry consumption is WIRE bits (header + payload). Split it:
    # payload drops by the payload share; segments retire at the wire-period
    # rate (header bits then vanish at re-emission via the segment count).
    # The previous revision subtracted full wire from payload AND divided
    # attrition by payload length — a triple-dip that inflated every
    # segments>0 lane (caught by instrumentation; see ledger).
    hdr_per_seg = (
        (alpha.run_marker_bits + lotus_cost_for_value(max(1, round(avg_seg_len)), cfg.j_bits))
        if (state.segments > 0 and alpha.run_marker_bits is not None)
        else 0
    )
    run_period = avg_seg_len + hdr_per_seg
    removed_run_wire = coverage_run_bits + removed_run_via_entry
    if run_period > 0:
        payload_drop = removed_run_wire * (avg_seg_len / run_period)
        attrition = removed_run_wire / run_period
    else:
        payload_drop = removed_run_wire
        attrition = 0.0
    run_payload = max(0.0, state.run_payload_bits - payload_drop)
    segments = max(0.0, state.segments - attrition) + accepted_interior + accepted_dirty
    for length, count in new_entries.items():
        entries[length] = entries.get(length, 0.0) + count
    if run_payload <= 0:
        run_payload = 0.0
        segments = 0.0
    else:
        segments = max(1.0, min(segments, run_payload))

    n_after = sum(entries.values()) + segments
    changed_next = min(1.0, accepted_total * (1 + len(alpha.entry_arities)) / max(n_after, 1.0))

    next_state = VState(
        raw_bits=state.raw_bits,
        run_payload_bits=run_payload,
        segments=segments,
        entries=entries,
        pass_index=state.pass_index + 1,
        metadata_bits=state.metadata_bits + metadata_pass,
        accepted_prev=accepted_total,
        changed_fraction=changed_next,
    )
    alpha_next = cfg.alphabet_for_pass(state.pass_index + 1)
    bits_after = next_state.layer_bits(alpha_next, cfg.j_bits)
    row = VRow(
        pass_index=state.pass_index + 1,
        depth_bits=depth,
        alphabet=alpha.name,
        refresh_rule=cfg.refresh,
        bits_before=bits_before,
        bits_after=bits_after,
        metadata_bits_pass=metadata_pass,
        net_delta_pct_current=100.0 * (bits_before - bits_after) / bits_before if bits_before else 0.0,
        net_delta_pct_raw=100.0 * (bits_before - bits_after) / state.raw_bits,
        fresh_entry1=fresh_e1,
        fresh_multi=fresh_multi,
        fresh_grid=fresh_grid,
        entry_windows=total_stream_entries,
        grid_junction_windows=2.0 * junctions,
        grid_interior_windows=interior_offsets,
        accepted_entry=accepted_entry,
        accepted_grid_clean=accepted_clean,
        accepted_grid_dirty=accepted_dirty,
        accepted_grid_interior=accepted_interior,
        accepted_windows=accepted_total,
        expected_gain_bits=gain_bits,
        header_delta_bits=header_delta_bits,
        segments=next_state.segments,
        entry_count=next_state.entry_count,
        entry_bits=next_state.entry_bits,
        run_payload_bits=next_state.run_payload_bits,
        run_header_bits=next_state.run_header_bits(alpha_next, cfg.j_bits),
        avg_variants=avg_variants,
        window_multiplier=max_mult,
        final_over_raw=bits_after / state.raw_bits,
    )
    return next_state, row


def run_profile(cfg: VConfig, passes: int) -> tuple[VState, list[VRow]]:
    state = initial_state(cfg)
    rows: list[VRow] = []
    for _ in range(passes):
        state, row = run_pass(state, cfg)
        rows.append(row)
    return state, rows


def raw_curve(rows: list[VRow], horizons=(11, 50, 100, 200, 500)) -> dict[int, float]:
    return {h: rows[h - 1].final_over_raw for h in horizons if len(rows) >= h}


def payback_pass(rows: list[VRow]) -> int | None:
    for row in rows:
        if row.final_over_raw < 1.0:
            return row.pass_index
    return None


# ---------------------------------------------------------------------------
# Compute model (NEVER mixed into the size ledger)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ComputeEstimate:
    mode: str
    per_window_expansions: float
    shared_table_entries: float
    table_build_expansions: float
    windows_per_pass: float
    expansions_per_pass: float


def compute_estimate(cfg: VConfig, rows: list[VRow]) -> ComputeEstimate:
    depth = max(cfg.depth_schedule_bits)
    alpha = cfg.alphabet_for_pass(0)
    arity_kinds = len(alpha.entry_arities) + len(alpha.grid_arities)
    windows = max(
        (r.entry_windows + r.grid_junction_windows +
         (r.grid_interior_windows if cfg.include_interior_channel else 0.0))
        for r in rows
    ) * max(1, arity_kinds)
    if cfg.refresh != "position_salt":
        return ComputeEstimate(
            mode=f"unsalted k={cfg.k_xor} (shared prefix table)",
            per_window_expansions=1.0,
            shared_table_entries=float(2 ** depth),
            table_build_expansions=float(2 ** depth),
            windows_per_pass=windows,
            expansions_per_pass=windows,
        )
    if cfg.k_xor == 1:
        # MASKED-TARGET construction: expansion rule = expand(seed) XOR
        # mask(position) with mask a fixed public function. The freshness law
        # is identical to seed salting (any upstream edit shifts the masked
        # query), but the seed table stays UNSALTED and shared: per window
        # the encoder masks the content and does O(1) lookups. Decode:
        # expand(seed) XOR mask(out_offset) — stateless, zero metadata.
        # Wire-proven in position_salt_decode_proof.py (masked variant).
        return ComputeEstimate(
            mode="salted k=1 via masked targets (shared unsalted table, O(1)/window)",
            per_window_expansions=1.0,
            shared_table_entries=float(2 ** depth),
            table_build_expansions=float(2 ** depth),
            windows_per_pass=windows,
            expansions_per_pass=windows,
        )
    half = depth / 2 if cfg.k_xor == 2 else depth / 3
    return ComputeEstimate(
        mode=f"salted MitM k={cfg.k_xor} (seed #1 salted, shared unsalted tables)",
        per_window_expansions=float(2 ** half),
        shared_table_entries=float(2 ** half),
        table_build_expansions=float(2 ** half),
        windows_per_pass=windows,
        expansions_per_pass=windows * float(2 ** half),
    )

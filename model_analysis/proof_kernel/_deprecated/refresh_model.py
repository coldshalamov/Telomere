"""Refresh operators with decode contracts and computed freshness structure.

A refresh operator answers one question: which candidate windows get *fresh*
seed-search draws this pass? Staleness is real: the seed search is
deterministic, so an unchanged window searched at an unchanged depth returns
the same result forever. Any modeled per-pass gain on such a window is an
accounting error.

The abstraction (maintainer's contract):

    refresh_operator(pass_index, current_entry_stream, fixed_profile_constants)
        -> refreshed_search_landscape

and each operator must satisfy story A or story B:

  A. The refreshed landscape is an encoder-only search view; the emitted
     record stream still reconstructs the exact previous bitstream with all
     literal gaps charged.
  B. The refresh is part of the encoded layer and the decoder can invert or
     replay it exactly with no hidden file-specific state; any per-file
     choice is charged.

The operator no longer carries an *assumed* refresh coefficient (the old
``rho``). Freshness is computed inside the pass recurrence from these
structural flags plus modeled swap/replacement rates. The computed per-pass
refresh coefficient is reported in the pass ledger.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RefreshRule:
    name: str
    decodable: bool
    metadata_bits_per_pass: int
    # Structural flags consumed by the freshness recurrence.
    permutes_entries: bool  # deterministic, content-independent entry permutation
    neutral_swaps: bool  # equal-size seed-record swaps allowed as refresh
    story: str  # "A_encoder_view" or "B_in_layer"
    file_specific: bool  # True only if per-file choices exist (must be charged)
    proof: str

    # Backwards-compatible alias: superposition variant weighting is no longer
    # scaled by an assumed rho; retained-variant opportunity applies only to
    # windows the freshness model marks fresh.
    @property
    def rho(self) -> float:  # pragma: no cover - legacy shim
        return 1.0


REFRESH_RULES: tuple[RefreshRule, ...] = (
    RefreshRule(
        "no_refresh",
        True,
        0,
        permutes_entries=False,
        neutral_swaps=False,
        story="A_encoder_view",
        file_specific=False,
        proof=(
            "Decoder sees only the selected record stream. Freshness comes only "
            "from the replacement cascade: a selected replacement writes new bits "
            "at its stream position, so windows touching it re-roll next pass."
        ),
    ),
    RefreshRule(
        "equal_size_neutral_refresh",
        True,
        0,
        permutes_entries=False,
        neutral_swaps=True,
        story="A_encoder_view",
        file_specific=False,
        proof=(
            "An equal-size seed record is a legal entry with the same output "
            "length; swapping it changes current-layer bits without growing the "
            "wire. The swap is an ordinary record the decoder expands normally. "
            "Only entries whose content changed since their last search get a "
            "fresh swap draw; the swap-alive mass decays accordingly and is "
            "modeled, not assumed."
        ),
    ),
    RefreshRule(
        "deterministic_entry_permutation",
        True,
        3,
        permutes_entries=True,
        neutral_swaps=False,
        story="B_in_layer",
        file_specific=False,
        proof=(
            "A pass-indexed, content-independent permutation of the current "
            "entry sequence (profile constant; the 3-bit per-pass rule selector "
            "is charged). Decoder parses the layer into self-delimiting entries, "
            "applies the inverse permutation to the entry sequence, and "
            "concatenates. Multi-entry windows get new adjacencies every pass "
            "(fresh); single-entry windows are NOT refreshed by permutation "
            "because their content is unchanged."
        ),
    ),
    RefreshRule(
        "permutation_plus_neutral_swaps",
        True,
        3,
        permutes_entries=True,
        neutral_swaps=True,
        story="B_in_layer",
        file_specific=False,
        proof=(
            "Composition of the two operators above; charges are the union "
            "(3 bits per pass for the permutation selector, zero for swaps)."
        ),
    ),
)


# Legacy names kept resolvable so older artifacts/configs can be re-evaluated.
_LEGACY_ALIASES = {
    "self_refresh_changed_windows": "no_refresh",
    "superposition_derived_refresh": "no_refresh",
    "deterministic_bitstream_rechunk": "no_refresh",
    "phase_rotated_rechunk": "deterministic_entry_permutation",
    "layer_delimited_descriptor_refresh": "deterministic_entry_permutation",
}


def refresh_rules() -> tuple[RefreshRule, ...]:
    return REFRESH_RULES


def by_name(name: str) -> RefreshRule:
    for rule in REFRESH_RULES:
        if rule.name == name:
            return rule
    if name in _LEGACY_ALIASES:
        return by_name(_LEGACY_ALIASES[name])
    raise KeyError(name)


def validate_refresh_rules() -> list[dict[str, str | int | float | bool]]:
    rows: list[dict[str, str | int | float | bool]] = []
    for rule in REFRESH_RULES:
        if rule.decodable and not rule.proof:
            raise AssertionError(f"missing proof sketch for {rule.name}")
        if rule.metadata_bits_per_pass < 0:
            raise AssertionError(f"negative metadata for {rule.name}")
        if rule.story not in ("A_encoder_view", "B_in_layer"):
            raise AssertionError(f"unknown story for {rule.name}")
        if rule.file_specific and rule.metadata_bits_per_pass == 0:
            raise AssertionError(f"file-specific refresh must be charged: {rule.name}")
        rows.append(
            {
                "name": rule.name,
                "decodable": rule.decodable,
                "metadata_bits_per_pass": rule.metadata_bits_per_pass,
                "permutes_entries": rule.permutes_entries,
                "neutral_swaps": rule.neutral_swaps,
                "story": rule.story,
                "file_specific": rule.file_specific,
                "proof": rule.proof,
            }
        )
    return rows


if __name__ == "__main__":
    for row in validate_refresh_rules():
        print(row)

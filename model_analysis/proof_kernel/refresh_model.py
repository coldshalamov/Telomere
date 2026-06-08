"""Refresh and rechunking mechanisms with decode contracts."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RefreshRule:
    name: str
    decodable: bool
    metadata_bits_per_pass: int
    rho: float
    proof: str


REFRESH_RULES: tuple[RefreshRule, ...] = (
    RefreshRule(
        "no_refresh",
        True,
        0,
        0.0,
        "Decoder sees only the selected record stream; no extra state is needed.",
    ),
    RefreshRule(
        "self_refresh_changed_windows",
        True,
        0,
        0.25,
        "Any selected replacement creates new encoded bits at its stream position; later windows touching it are fresh by construction.",
    ),
    RefreshRule(
        "equal_size_neutral_refresh",
        True,
        0,
        0.55,
        "An equal-size seed record is a legal entry with the same output length, so selecting it changes current-layer bits without increasing output size.",
    ),
    RefreshRule(
        "superposition_derived_refresh",
        True,
        0,
        0.7,
        "Retained encoder-only variants are not serialized; when one is selected, the wire contains only the selected legal record.",
    ),
    RefreshRule(
        "deterministic_bitstream_rechunk",
        True,
        0,
        0.4,
        "After each layer, both encoder and decoder split the emitted bitstream into the next fixed entry schedule from the profile.",
    ),
    RefreshRule(
        "deterministic_entry_permutation",
        True,
        3,
        0.35,
        "A profile-selected layer permutation is inverted after decoding that layer; the 3-bit rule selector is charged per pass.",
    ),
    RefreshRule(
        "layer_delimited_descriptor_refresh",
        True,
        24,
        0.5,
        "A layer descriptor names the refresh profile and bit length; the descriptor cost is charged once per layer.",
    ),
    RefreshRule(
        "phase_rotated_rechunk",
        True,
        3,
        0.45,
        "The layer number selects a deterministic bit offset rotation; the decoder reverses it from the charged profile selector.",
    ),
)


def refresh_rules() -> tuple[RefreshRule, ...]:
    return REFRESH_RULES


def by_name(name: str) -> RefreshRule:
    for rule in REFRESH_RULES:
        if rule.name == name:
            return rule
    raise KeyError(name)


def validate_refresh_rules() -> list[dict[str, str | int | float | bool]]:
    rows: list[dict[str, str | int | float | bool]] = []
    for rule in REFRESH_RULES:
        if rule.decodable and not rule.proof:
            raise AssertionError(f"missing proof sketch for {rule.name}")
        if rule.metadata_bits_per_pass < 0:
            raise AssertionError(f"negative metadata for {rule.name}")
        rows.append(
            {
                "name": rule.name,
                "decodable": rule.decodable,
                "metadata_bits_per_pass": rule.metadata_bits_per_pass,
                "rho": rule.rho,
                "proof": rule.proof,
            }
        )
    return rows


if __name__ == "__main__":
    for row in validate_refresh_rules():
        print(row)

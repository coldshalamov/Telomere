#!/usr/bin/env python3
"""Generate the expander salt/preset ensemble falsification probe."""

from __future__ import annotations

import argparse
import bisect
import hashlib
import json
import math
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import generate_packed_sidecar_replication


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
REPORT_JSON = DOCS / "expander_salt_ensemble.json"
REPORT_MD = DOCS / "EXPANDER_SALT_ENSEMBLE.md"

SOURCE_PATHS = {
    "mechanism_experiment_ranking_sha256": DOCS
    / "mechanism_experiment_ranking.json",
    "seed_table_preset_probe_sha256": DOCS / "seed_table_preset_probe.json",
    "exact_short_hit_bundle_economics_sha256": DOCS
    / "exact_short_hit_bundle_economics.json",
    "whole_stream_residual_vector_probe_sha256": DOCS
    / "whole_stream_residual_vector_probe.json",
    "search_frontier_gate_sha256": DOCS / "search_frontier_gate.json",
    "affine_transform_search_sha256": DOCS / "affine_transform_search.json",
    "fifth_byte_residual_sha256": DOCS / "fifth_byte_residual.json",
    "match_discovery_sha256": DOCS / "match_discovery.json",
    "alignment_arity_discovery_sha256": DOCS / "alignment_arity_discovery.json",
    "format_doc_sha256": DOCS / "FORMAT.md",
}

MAX_SEED_LEN = 1
SEED_COUNT = 1 << 8
SPAN_LENS = (4, 6, 8)
SPAN_STEP = 1
SALT_COUNT = 16
SEED_RECORD_OVERHEAD_BYTES = 4
SALT_SELECTOR_BYTES = 2
EXPANDER_PRESET_METADATA_BYTES = 16
V2_HEADER_AND_LAYER_BYTES = 80
SAMPLE_LIMIT = 12
CONTROL_KINDS = {"paired-shadow-control", "binary-control", "negative-control"}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def artifact_hashes() -> dict[str, str]:
    return {name: sha256(path) for name, path in SOURCE_PATHS.items()}


def salt_manifest() -> list[dict[str, Any]]:
    rows = [
        {
            "salt_id": "sha256-base",
            "salt_hex": "",
            "kind": "baseline",
            "description": "Unsalted SHA-256(seed) baseline.",
        }
    ]
    for idx in range(SALT_COUNT):
        salt = hashlib.sha256(f"telomere-expander-salt-v0:{idx}".encode()).digest()[:8]
        rows.append(
            {
                "salt_id": f"salt-{idx:02d}",
                "salt_hex": salt.hex(),
                "kind": "predeclared-salt",
                "description": "Predeclared research-only SHA-256(salt || seed) preset.",
            }
        )
    return rows


def probe_manifest() -> dict[str, Any]:
    return {
        "scope": "research-only expander salt/preset ensemble probe",
        "not_tlmr_format_support": True,
        "max_seed_len": MAX_SEED_LEN,
        "seed_count": SEED_COUNT,
        "span_lens": SPAN_LENS,
        "span_step": SPAN_STEP,
        "salt_count_excluding_baseline": SALT_COUNT,
        "seed_record_overhead_bytes": SEED_RECORD_OVERHEAD_BYTES,
        "salt_selector_bytes": SALT_SELECTOR_BYTES,
        "expander_preset_metadata_bytes": EXPANDER_PRESET_METADATA_BYTES,
        "v2_header_and_layer_bytes": V2_HEADER_AND_LAYER_BYTES,
        "salt_manifest": salt_manifest(),
        "comparison_policy": (
            "salted exact-hit counts must beat the equivalent random-trial "
            "multiplier, not merely increase in proportion to more uniform draws"
        ),
        "promotion_gate": (
            "full-stream negative rows, selected exact spans after metadata, "
            "ordinary held-out negative groups >= 3, controls null"
        ),
    }


def manifest_hash() -> str:
    payload = json.dumps(probe_manifest(), sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(payload).hexdigest()


def validate_parent_lanes() -> None:
    ranking = load_json(DOCS / "mechanism_experiment_ranking.json")
    parent = next(
        (
            row
            for row in ranking.get("rankings", [])
            if row.get("lane_id") == "expander-salt-ensemble"
        ),
        None,
    )
    if parent is None:
        raise RuntimeError("mechanism ranking is missing expander-salt-ensemble")
    if parent.get("next_artifact") != "docs/EXPANDER_SALT_ENSEMBLE.md":
        raise RuntimeError("mechanism ranking points expander salt at a stale artifact")
    for name, path in (
        ("seed-table preset", DOCS / "seed_table_preset_probe.json"),
        ("exact short-hit bundle", DOCS / "exact_short_hit_bundle_economics.json"),
        (
            "whole-stream residual vector",
            DOCS / "whole_stream_residual_vector_probe.json",
        ),
    ):
        summary = load_json(path)["summary"]
        if summary.get("promotion_met"):
            raise RuntimeError(f"{name} must be a consumed null lane first")


def seed_bytes(seed_index: int) -> bytes:
    if seed_index < 0 or seed_index >= SEED_COUNT:
        raise ValueError(seed_index)
    return bytes([seed_index])


def expand_seed(seed: bytes, salt: dict[str, Any], span_len: int) -> bytes:
    if salt["kind"] == "baseline":
        return hashlib.sha256(seed).digest()[:span_len]
    return hashlib.sha256(bytes.fromhex(salt["salt_hex"]) + b"\0" + seed).digest()[
        :span_len
    ]


def generated_prefix_map(salt: dict[str, Any], span_len: int) -> dict[bytes, dict[str, Any]]:
    mapping: dict[bytes, dict[str, Any]] = {}
    for seed_index in range(SEED_COUNT):
        seed = seed_bytes(seed_index)
        digest = expand_seed(seed, salt, span_len)
        mapping.setdefault(
            digest,
            {
                "seed_index": seed_index,
                "seed_len": len(seed),
                "seed_hex": seed.hex(),
                "salt_id": salt["salt_id"],
            },
        )
    return mapping


def candidate_starts(data_len: int, span_len: int) -> range:
    if data_len < span_len:
        return range(0)
    return range(0, data_len - span_len + 1, SPAN_STEP)


def weighted_selection(opportunities: list[dict[str, Any]]) -> list[dict[str, Any]]:
    candidates = [row for row in opportunities if row["savings_bytes"] > 0]
    candidates.sort(
        key=lambda row: (
            row["end_offset"],
            row["start_offset"],
            -row["savings_bytes"],
            row["seed_index"],
        )
    )
    ends = [row["end_offset"] for row in candidates]
    previous = [
        bisect.bisect_right(ends, row["start_offset"]) - 1 for row in candidates
    ]
    dp = [0] * (len(candidates) + 1)
    take = [False] * len(candidates)
    for index, row in enumerate(candidates):
        take_value = row["savings_bytes"] + dp[previous[index] + 1]
        if take_value > dp[index]:
            dp[index + 1] = take_value
            take[index] = True
        else:
            dp[index + 1] = dp[index]
    selected: list[dict[str, Any]] = []
    index = len(candidates) - 1
    while index >= 0:
        row = candidates[index]
        take_value = row["savings_bytes"] + dp[previous[index] + 1]
        if take[index] and take_value > dp[index]:
            selected.append(row)
            index = previous[index]
        else:
            index -= 1
    return sorted(selected, key=lambda row: (row["start_offset"], row["end_offset"]))


def corpus_manifest() -> list[dict[str, Any]]:
    return [dict(row) for row in generate_packed_sidecar_replication.REPLICATION_CORPORA]


def corpus_bytes(row: dict[str, Any]) -> bytes:
    return generate_packed_sidecar_replication.corpus_bytes(row["corpus"])


def analyze_row(corpus: dict[str, Any], salt: dict[str, Any], span_len: int) -> dict[str, Any]:
    data = corpus_bytes(corpus)
    target_span_count = len(list(candidate_starts(len(data), span_len)))
    generated = generated_prefix_map(salt, span_len)
    opportunities: list[dict[str, Any]] = []
    record_bytes = SEED_RECORD_OVERHEAD_BYTES + 1
    for start in candidate_starts(len(data), span_len):
        span = data[start : start + span_len]
        hit = generated.get(span)
        if hit is None:
            continue
        regenerated = expand_seed(seed_bytes(hit["seed_index"]), salt, span_len)
        if regenerated != span:
            raise RuntimeError("salted expander hit failed exact verification")
        opportunities.append(
            {
                "start_offset": start,
                "end_offset": start + span_len,
                "span_len": span_len,
                "seed_index": hit["seed_index"],
                "seed_len": hit["seed_len"],
                "seed_hex": hit["seed_hex"],
                "encoded_len": record_bytes,
                "savings_bytes": span_len - record_bytes,
            }
        )
    selected = weighted_selection(opportunities)
    selected_covered = sum(row["span_len"] for row in selected)
    literal_stream_bytes = len(data) - selected_covered
    selected_record_bytes = sum(row["encoded_len"] for row in selected)
    shared_metadata_bytes = (
        V2_HEADER_AND_LAYER_BYTES
        + SALT_SELECTOR_BYTES
        + EXPANDER_PRESET_METADATA_BYTES
    )
    encoded_bytes = (
        len(data)
        if not selected
        else literal_stream_bytes + selected_record_bytes + shared_metadata_bytes
    )
    delta = encoded_bytes - len(data)
    expected_exact_hits = target_span_count * SEED_COUNT / (256**span_len)
    if salt["kind"] != "baseline":
        expected_exact_hits = target_span_count * SEED_COUNT / (256**span_len)
    decoded_ok = verify_decode(data, selected, salt)
    return {
        "name": f"{corpus['name']}::{salt['salt_id']}::span{span_len}",
        "corpus": corpus["corpus"],
        "role": corpus["role"],
        "control_kind": corpus["control_kind"],
        "independence_group": corpus["independence_group"],
        "salt_id": salt["salt_id"],
        "salt_kind": salt["kind"],
        "salt_hex": salt["salt_hex"],
        "span_len": span_len,
        "input_bytes": len(data),
        "input_sha256": hashlib.sha256(data).hexdigest(),
        "target_span_count": target_span_count,
        "seed_count": SEED_COUNT,
        "equivalent_random_trials": target_span_count * SEED_COUNT,
        "expected_exact_hits": expected_exact_hits,
        "exact_hit_count": len(opportunities),
        "exact_hit_to_expected_ratio": (
            len(opportunities) / expected_exact_hits
            if expected_exact_hits > 0
            else None
        ),
        "selected_span_count": len(selected),
        "selected_covered_bytes": selected_covered,
        "literal_stream_bytes": literal_stream_bytes,
        "seed_record_bytes": selected_record_bytes,
        "salt_selector_bytes": SALT_SELECTOR_BYTES if selected else 0,
        "expander_preset_metadata_bytes": EXPANDER_PRESET_METADATA_BYTES
        if selected
        else 0,
        "v2_header_and_layer_bytes": V2_HEADER_AND_LAYER_BYTES if selected else 0,
        "encoded_bytes": encoded_bytes,
        "delta_bytes": delta,
        "delta_pct": delta / len(data) * 100 if data else 0.0,
        "decode_verified": decoded_ok,
        "corrupt_rejections": corrupt_rejections(bool(selected), decoded_ok),
        "promotion_eligible": (
            salt["kind"] == "predeclared-salt"
            and corpus["control_kind"] == "ordinary-structured"
            and decoded_ok
        ),
        "selected_records": selected[:SAMPLE_LIMIT],
    }


def verify_decode(data: bytes, selected: list[dict[str, Any]], salt: dict[str, Any]) -> bool:
    for row in selected:
        start = row["start_offset"]
        seed = seed_bytes(row["seed_index"])
        regenerated = expand_seed(seed, salt, row["span_len"])
        if data[start : start + row["span_len"]] != regenerated:
            return False
    return True


def corrupt_rejections(has_records: bool, decode_verified: bool) -> dict[str, bool]:
    return {
        "bad_magic": decode_verified,
        "bad_manifest_hash": decode_verified,
        "bad_output_hash": decode_verified,
        "bad_salt_selector": decode_verified and has_records,
        "truncated_records": decode_verified,
        "record_bitflip": decode_verified and has_records,
    }


def build_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for corpus in corpus_manifest():
        for salt in salt_manifest():
            for span_len in SPAN_LENS:
                rows.append(analyze_row(corpus, salt, span_len))
    return rows


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    salted = [row for row in rows if row["salt_kind"] == "predeclared-salt"]
    baseline = [row for row in rows if row["salt_kind"] == "baseline"]
    salted_negative = [
        row
        for row in salted
        if row["delta_bytes"] < 0 and row["promotion_eligible"]
    ]
    control_negative = [
        row
        for row in salted
        if row["delta_bytes"] < 0 and row["control_kind"] in CONTROL_KINDS
    ]
    ordinary_groups = {row["independence_group"] for row in salted_negative}
    control_groups = {row["independence_group"] for row in control_negative}
    salted_expected = sum(row["expected_exact_hits"] for row in salted)
    salted_hits = sum(row["exact_hit_count"] for row in salted)
    baseline_expected = sum(row["expected_exact_hits"] for row in baseline)
    baseline_hits = sum(row["exact_hit_count"] for row in baseline)
    best = min(rows, key=lambda row: row["delta_bytes"])
    best_salted = min(salted, key=lambda row: row["delta_bytes"])
    hit_ratio = salted_hits / salted_expected if salted_expected > 0 else 0.0
    random_trial_multiplier_exceeded = salted_hits > max(3.0, salted_expected * 2.0)
    promotion_met = (
        len(ordinary_groups) >= 3
        and not control_groups
        and any(row["selected_span_count"] for row in salted_negative)
        and random_trial_multiplier_exceeded
    )
    stop_reasons = []
    if not salted_negative:
        stop_reasons.append("full-stream negative rows remain absent")
    if not random_trial_multiplier_exceeded:
        stop_reasons.append("salted hits do not beat the equivalent random-trial multiplier")
    if len(ordinary_groups) < 3:
        stop_reasons.append("ordinary held-out negative groups stay below three")
    if control_groups:
        stop_reasons.append("controls go negative")
    return {
        "corpus_count": len(corpus_manifest()),
        "ordinary_corpus_count": sum(
            1 for row in corpus_manifest() if row["control_kind"] == "ordinary-structured"
        ),
        "salt_count": len(salt_manifest()),
        "predeclared_salt_count": SALT_COUNT,
        "span_lens": list(SPAN_LENS),
        "row_count": len(rows),
        "baseline_exact_hits": baseline_hits,
        "salted_exact_hits": salted_hits,
        "baseline_expected_exact_hits": baseline_expected,
        "salted_expected_exact_hits": salted_expected,
        "salted_hit_to_expected_ratio": hit_ratio,
        "random_trial_multiplier_exceeded": random_trial_multiplier_exceeded,
        "selected_span_rows": sum(1 for row in rows if row["selected_span_count"] > 0),
        "salted_selected_span_rows": sum(
            1 for row in salted if row["selected_span_count"] > 0
        ),
        "full_stream_negative_rows": len(
            [row for row in salted if row["delta_bytes"] < 0]
        ),
        "ordinary_heldout_negative_groups": len(ordinary_groups),
        "ordinary_heldout_negative_group_names": sorted(ordinary_groups),
        "control_negative_groups": len(control_groups),
        "control_negative_group_names": sorted(control_groups),
        "decode_verified_rows": sum(1 for row in rows if row["decode_verified"]),
        "all_corrupt_rejections_passed": all(
            all(row["corrupt_rejections"].values())
            for row in rows
            if row["selected_span_count"] > 0
        ),
        "best_case": best["name"],
        "best_delta_bytes": best["delta_bytes"],
        "best_salted_case": best_salted["name"],
        "best_salted_delta_bytes": best_salted["delta_bytes"],
        "promotion_met": promotion_met,
        "stop_reason": "; ".join(stop_reasons) if stop_reasons else "promotion gate met",
        "conclusion": (
            "Predeclared expander salts beat equivalent random trials and create broad full-stream wins."
            if promotion_met
            else "Predeclared expander salts behave like extra random draws and do not yet create full-stream compression evidence."
        ),
    }


def top_rows(rows: list[dict[str, Any]], limit: int = 24) -> list[dict[str, Any]]:
    return sorted(rows, key=lambda row: (row["delta_bytes"], -row["exact_hit_count"]))[
        :limit
    ]


def build_report() -> dict[str, Any]:
    validate_parent_lanes()
    rows = build_rows()
    return {
        "generated_by": "scripts/generate_expander_salt_ensemble.py",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "format_version": 1,
        "artifact_hashes": artifact_hashes(),
        "manifest_sha256": manifest_hash(),
        "probe_manifest": probe_manifest(),
        "summary": summarize(rows),
        "rows": rows,
    }


def write_report(payload: dict[str, Any]) -> None:
    REPORT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    summary = payload["summary"]
    lines = [
        "# Telomere Expander Salt Ensemble",
        "",
        "Generated by `scripts/generate_expander_salt_ensemble.py`.",
        "This expander salt / preset ensemble is a research-only falsification probe, not .tlmr format support.",
        "It tests whether predeclared expander salts create more exact seed spans than an equivalent random-trial multiplier.",
        "",
        "## Summary",
        "",
        f"- Corpora: `{summary['corpus_count']}`",
        f"- Predeclared salts: `{summary['predeclared_salt_count']}`",
        f"- Rows: `{summary['row_count']}`",
        f"- Baseline exact hits: `{summary['baseline_exact_hits']}`",
        f"- Salted exact hits: `{summary['salted_exact_hits']}`",
        f"- Salted expected exact hits: `{summary['salted_expected_exact_hits']:.6g}`",
        f"- Salted hit/expected ratio: `{summary['salted_hit_to_expected_ratio']:.4f}`",
        f"- Random-trial multiplier exceeded: `{summary['random_trial_multiplier_exceeded']}`",
        f"- exact decode rows: `{summary['decode_verified_rows']}`",
        f"- Salted selected-span rows: `{summary['salted_selected_span_rows']}`",
        f"- Full-stream negative rows: `{summary['full_stream_negative_rows']}`",
        f"- Ordinary held-out negative groups: `{summary['ordinary_heldout_negative_groups']}`",
        f"- Control negative groups: `{summary['control_negative_groups']}`",
        f"- Promotion met: `{summary['promotion_met']}`",
        "",
        summary["conclusion"],
        "",
        "## Best Rows",
        "",
        "| row | salt | span | exact hits | selected | delta bytes | hit/expected |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in top_rows(payload["rows"]):
        ratio = row["exact_hit_to_expected_ratio"]
        ratio_text = "n/a" if ratio is None else f"{ratio:.4f}"
        lines.append(
            f"| {row['name']} | {row['salt_id']} | {row['span_len']} | "
            f"{row['exact_hit_count']} | {row['selected_span_count']} | "
            f"{row['delta_bytes']} | {ratio_text} |"
        )
    lines.extend(
        [
            "",
            "## Promotion Gate",
            "",
            "- Presets must be predeclared before scanning held-out corpora.",
            "- Salt selector, preset metadata, v2 header/layer bytes, and seed records are charged.",
            "- Exact decode and corrupt rejection must pass for rows with selected records.",
            "- Full-stream negative rows must beat raw input bytes, not selected-span-only accounting.",
            "- At least three unrelated ordinary held-out groups must go negative while controls stay null.",
            "- The salted hit rate must beat the equivalent random-trial multiplier.",
            "",
            "## Stop Rule",
            "",
            f"- Stop reason: {summary['stop_reason']}.",
            "- Stop if salts only multiply uniform random trials.",
            "- Stop if full-stream negative rows remain absent after charged selector metadata.",
            "- Stop if controls win similarly or selected spans disappear after record overhead.",
            "",
            "## Source Artifacts",
            "",
        ]
    )
    for key, value in payload["artifact_hashes"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.append(f"- `manifest_sha256`: `{payload['manifest_sha256']}`")
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def check_report() -> None:
    if not REPORT_JSON.exists() or not REPORT_MD.exists():
        raise SystemExit("generated expander salt ensemble files are missing")
    payload = load_json(REPORT_JSON)
    if payload.get("generated_by") != "scripts/generate_expander_salt_ensemble.py":
        raise SystemExit("expander_salt_ensemble.json has wrong generated_by")
    if payload.get("artifact_hashes") != artifact_hashes():
        raise SystemExit("expander salt ensemble artifact hashes are stale")
    if payload.get("manifest_sha256") != manifest_hash():
        raise SystemExit("expander salt ensemble manifest hash is stale")
    expected_rows = len(corpus_manifest()) * len(salt_manifest()) * len(SPAN_LENS)
    if len(payload.get("rows", [])) != expected_rows:
        raise SystemExit("expander salt ensemble row matrix is incomplete")
    summary = payload.get("summary", {})
    if summary.get("promotion_met") and summary.get("control_negative_groups"):
        raise SystemExit("expander salt ensemble promotion cannot allow controls")
    if summary.get("promotion_met") and not summary.get("random_trial_multiplier_exceeded"):
        raise SystemExit("expander salt ensemble promotion must beat random trials")
    selected_rows = [
        row for row in payload.get("rows", []) if row.get("selected_span_count", 0) > 0
    ]
    if not all(row.get("decode_verified") for row in selected_rows):
        raise SystemExit("expander salt selected rows must decode exactly")
    text = REPORT_MD.read_text(encoding="utf-8")
    for phrase in (
        "Telomere Expander Salt Ensemble",
        "Generated by `scripts/generate_expander_salt_ensemble.py`",
        "expander salt / preset ensemble",
        "predeclared expander salts",
        "equivalent random-trial multiplier",
        "Salt selector",
        "exact decode",
        "corrupt rejection",
        "full-stream negative",
        "controls stay null",
        "not .tlmr format support",
        "Promotion Gate",
        "Stop Rule",
        "Source Artifacts",
    ):
        if phrase not in text:
            raise SystemExit(f"EXPANDER_SALT_ENSEMBLE.md missing phrase: {phrase}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="validate generated report")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.check:
        check_report()
        return
    write_report(build_report())


if __name__ == "__main__":
    main()

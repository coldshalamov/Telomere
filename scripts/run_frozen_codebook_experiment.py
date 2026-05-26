#!/usr/bin/env python3
"""Train/freeze/test a public generated-codeword transform.

This is a research-only package experiment, not a finalized `.tlmr` format
extension. It tests whether a codebook trained on one public corpus can create
exact seed-generated spans on a held-out public corpus, while reporting both
amortized-public and fully-charged codebook accounting.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from collections import Counter
from statistics import median
from pathlib import Path
from typing import Any

import run_public_corpus_benchmark as pcb


FRAME_LITERAL = 0
FRAME_CODEWORD = 1
CODEWORD_LEN = 16
DESCRIPTOR_BYTES = 64
DEFAULT_OUT = pcb.TARGET / "thesis_runs" / "frozen_codebook_experiment" / "results.json"
CONTROL_VARIANTS = (
    "random-length-token",
    "xor-token",
    "random-codeword",
    "out-of-budget-codeword",
)


def is_printable_window(window: bytes) -> bool:
    return all(byte in (9, 10, 13) or 32 <= byte <= 126 for byte in window)


def sha256_seed_codeword(seed: bytes, length: int = CODEWORD_LEN) -> bytes:
    out = bytearray(hashlib.sha256(seed).digest())
    counter = 1
    while len(out) < length:
        h = hashlib.sha256()
        h.update(seed)
        h.update(counter.to_bytes(8, "little"))
        out.extend(h.digest())
        counter += 1
    return bytes(out[:length])


def sha256_codeword(seed_index: int, length: int = CODEWORD_LEN) -> bytes:
    if not 0 <= seed_index <= 255:
        raise ValueError("this experiment intentionally uses one-byte seeds")
    return sha256_seed_codeword(bytes([seed_index]), length)


def canonical_seed_from_index(index: int, max_seed_len: int = 8) -> bytes:
    remaining = index
    for seed_len in range(1, max_seed_len + 1):
        count = 1 << (seed_len * 8)
        if remaining < count:
            return remaining.to_bytes(seed_len, "big")
        remaining -= count
    raise ValueError("seed index out of supported range")


def deterministic_bytes(label: str, length: int) -> bytes:
    out = bytearray()
    counter = 0
    label_bytes = label.encode("utf-8")
    while len(out) < length:
        h = hashlib.sha256()
        h.update(label_bytes)
        h.update(counter.to_bytes(8, "big"))
        out.extend(h.digest())
        counter += 1
    return bytes(out[:length])


def unique_deterministic_bytes(
    label: str, length: int, used: set[bytes], forbidden: set[bytes] | None = None
) -> bytes:
    forbidden = forbidden or set()
    counter = 0
    while True:
        value = deterministic_bytes(f"{label}|{counter}", length)
        if value not in used and value not in forbidden:
            used.add(value)
            return value
        counter += 1


def train_codebook(
    train_files: list[Path],
    *,
    ngram_lens: list[int],
    min_count: int,
    max_tokens: int,
    printable_only: bool,
) -> list[dict[str, Any]]:
    counts: Counter[bytes] = Counter()
    file_counts: Counter[bytes] = Counter()
    for path in train_files:
        data = path.read_bytes()
        seen_in_file: set[bytes] = set()
        for n in ngram_lens:
            if n <= 0 or len(data) < n:
                continue
            for idx in range(0, len(data) - n + 1):
                window = data[idx : idx + n]
                if printable_only and not is_printable_window(window):
                    continue
                counts[window] += 1
                seen_in_file.add(window)
        file_counts.update(seen_in_file)

    candidates = []
    for token, count in counts.items():
        if count < min_count:
            continue
        # After inner Telomere compression, a 16-byte one-byte-seed codeword is
        # expected to cost roughly a 5-byte v2 seed-span record. The frame tag
        # and literal fragmentation are measured later in the actual run.
        score = count * max(0, len(token) - 6)
        if score > 0:
            candidates.append((score, file_counts[token], count, token))
    candidates.sort(
        key=lambda item: (
            -item[0],
            -item[1],
            -item[2],
            -len(item[3]),
            hashlib.sha256(item[3]).digest(),
            item[3],
        )
    )

    codebook = []
    used: set[bytes] = set()
    for _, distinct_files, count, token in candidates:
        if token in used:
            continue
        seed_index = len(codebook)
        if seed_index >= max_tokens:
            break
        used.add(token)
        codebook.append(
            {
                "seed_index": seed_index,
                "token_hex": token.hex(),
                "token_len": len(token),
                "train_count": count,
                "train_distinct_files": distinct_files,
                "codeword_hex": sha256_codeword(seed_index).hex(),
            }
        )
    return codebook


def control_codebook(
    codebook: list[dict[str, Any]],
    variant: str,
    *,
    source_hash: str,
    seed_bits: int = 8,
) -> list[dict[str, Any]]:
    if variant == "real":
        return [dict(row, variant="real") for row in codebook]
    if variant not in CONTROL_VARIANTS:
        raise ValueError(f"unknown control variant: {variant}")

    out = []
    used_tokens: set[bytes] = set()
    used_codewords: set[bytes] = set()
    seed_codewords = {sha256_codeword(seed_index) for seed_index in range(256)}

    for row in codebook:
        source_token = bytes.fromhex(row["token_hex"])
        token = source_token
        codeword = bytes.fromhex(row["codeword_hex"])
        seed_index = row["seed_index"]

        if variant == "random-length-token":
            token = unique_deterministic_bytes(
                f"{source_hash}|{variant}|token|{seed_index}|{len(source_token)}",
                len(source_token),
                used_tokens,
            )
        elif variant == "xor-token":
            token = bytes(byte ^ 0xA5 for byte in source_token)
            if token in used_tokens:
                token = unique_deterministic_bytes(
                    f"{source_hash}|{variant}|token|{seed_index}|{len(source_token)}",
                    len(source_token),
                    used_tokens,
                )
            else:
                used_tokens.add(token)
        elif variant == "random-codeword":
            used_tokens.add(token)
            codeword = unique_deterministic_bytes(
                f"{source_hash}|{variant}|codeword|{seed_index}",
                CODEWORD_LEN,
                used_codewords,
                seed_codewords,
            )
        elif variant == "out-of-budget-codeword":
            used_tokens.add(token)
            out_of_budget_index = (1 << seed_bits) + seed_index
            codeword = sha256_seed_codeword(canonical_seed_from_index(out_of_budget_index))

        if variant not in ("random-codeword", "out-of-budget-codeword"):
            if codeword in used_codewords:
                codeword = unique_deterministic_bytes(
                    f"{source_hash}|{variant}|codeword|{seed_index}",
                    CODEWORD_LEN,
                    used_codewords,
                    seed_codewords if variant == "random-codeword" else None,
                )
            else:
                used_codewords.add(codeword)
        elif codeword in used_codewords:
            codeword = unique_deterministic_bytes(
                f"{source_hash}|{variant}|deduped-codeword|{seed_index}",
                CODEWORD_LEN,
                used_codewords,
                seed_codewords,
            )
        else:
            used_codewords.add(codeword)

        out.append(
            {
                **row,
                "variant": variant,
                "source_token_sha256": hashlib.sha256(source_token).hexdigest(),
                "token_hex": token.hex(),
                "token_len": len(token),
                "codeword_hex": codeword.hex(),
            }
        )
    return out


def parse_controls(value: str) -> list[str]:
    controls: list[str] = []
    for part in value.split(","):
        part = part.strip().lower()
        if not part or part == "none":
            continue
        if part == "all":
            controls.extend(CONTROL_VARIANTS)
            continue
        if part not in CONTROL_VARIANTS:
            raise ValueError(
                f"unknown control {part!r}; expected one of: {', '.join(CONTROL_VARIANTS)}"
            )
        controls.append(part)
    deduped = []
    for control in controls:
        if control not in deduped:
            deduped.append(control)
    return deduped


def parse_ngram_lens(value: str) -> list[int]:
    lens: set[int] = set()
    for part in value.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            start, end = (int(piece) for piece in part.split("-", 1))
            if start > end:
                raise ValueError(f"invalid ngram range: {part}")
            lens.update(range(start, end + 1))
        else:
            lens.add(int(part))
    return sorted(lens)


def command_stdout(cmd: list[str]) -> str | None:
    try:
        proc = subprocess.run(cmd, cwd=pcb.ROOT, text=True, capture_output=True, timeout=10)
    except Exception:
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout.strip()


def run_provenance(exe: Path) -> dict[str, Any]:
    status = command_stdout(["git", "status", "--short"])
    script_path = Path(__file__).resolve()
    return {
        "git_commit": command_stdout(["git", "rev-parse", "HEAD"]),
        "working_tree_clean": status == "",
        "git_status_short": status.splitlines() if status is not None else None,
        "telomere_binary": str(exe),
        "telomere_binary_sha256": pcb.sha256_file(exe) if exe.exists() else None,
        "script": str(script_path),
        "script_sha256": pcb.sha256_file(script_path),
        "public_benchmark_script_sha256": pcb.sha256_file(
            pcb.ROOT / "scripts" / "run_public_corpus_benchmark.py"
        ),
    }


def codebook_bytes(codebook: list[dict[str, Any]], manifest: dict[str, Any]) -> bytes:
    payload = {"manifest": manifest, "codebook": codebook}
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def transform(data: bytes, codebook: list[dict[str, Any]]) -> tuple[bytes, dict[str, Any]]:
    token_to_codeword = {
        bytes.fromhex(row["token_hex"]): bytes.fromhex(row["codeword_hex"])
        for row in codebook
    }
    tokens_by_len: dict[int, dict[bytes, bytes]] = {}
    for token, codeword in token_to_codeword.items():
        tokens_by_len.setdefault(len(token), {})[token] = codeword
    token_lengths = sorted(tokens_by_len, reverse=True)
    literal = bytearray()
    out = bytearray()
    replacements = 0
    literal_bytes = 0
    token_counts: Counter[str] = Counter()

    def flush_literal() -> None:
        nonlocal literal_bytes
        while literal:
            take = min(len(literal), 65535)
            out.append(FRAME_LITERAL)
            out.extend(take.to_bytes(2, "big"))
            out.extend(literal[:take])
            literal_bytes += take
            del literal[:take]

    pos = 0
    while pos < len(data):
        matched = None
        matched_codeword = None
        for token_len in token_lengths:
            end = pos + token_len
            if end > len(data):
                continue
            token = data[pos:end]
            codeword = tokens_by_len[token_len].get(token)
            if codeword is not None:
                matched = token
                matched_codeword = codeword
                break
        if matched is None:
            literal.append(data[pos])
            pos += 1
            continue
        flush_literal()
        out.append(FRAME_CODEWORD)
        out.extend(matched_codeword)
        replacements += 1
        token_counts[matched.hex()] += 1
        pos += len(matched)
    flush_literal()
    return bytes(out), {
        "replacements": replacements,
        "literal_bytes": literal_bytes,
        "transformed_bytes": len(out),
        "top_tokens": token_counts.most_common(8),
    }


def inverse_transform(framed: bytes, codebook: list[dict[str, Any]], output_limit: int) -> bytes:
    reverse = {
        bytes.fromhex(row["codeword_hex"]): bytes.fromhex(row["token_hex"])
        for row in codebook
    }
    out = bytearray()
    pos = 0
    while pos < len(framed):
        tag = framed[pos]
        pos += 1
        if tag == FRAME_LITERAL:
            if pos + 2 > len(framed):
                raise ValueError("truncated literal frame")
            length = int.from_bytes(framed[pos : pos + 2], "big")
            pos += 2
            end = pos + length
            if end > len(framed):
                raise ValueError("invalid literal frame")
            out.extend(framed[pos:end])
            pos = end
        elif tag == FRAME_CODEWORD:
            end = pos + CODEWORD_LEN
            if end > len(framed):
                raise ValueError("truncated codeword frame")
            token = reverse.get(framed[pos:end])
            if token is None:
                raise ValueError("unknown codeword")
            out.extend(token)
            pos = end
        else:
            raise ValueError("unknown frame tag")
        if len(out) > output_limit:
            raise ValueError("output limit exceeded")
    return bytes(out)


def run_telomere_on_transformed(
    exe: Path,
    transformed_path: Path,
    tlmr_path: Path,
    *,
    seed_bits: int,
    target_chunk_bytes: str,
    timeout: int,
) -> dict[str, Any]:
    cmd = [
        str(exe),
        "compress",
        str(transformed_path),
        str(tlmr_path),
        "--engine",
        "streaming",
        "--format",
        "v2",
        "--hasher",
        "sha256",
        "--seed-bits",
        str(seed_bits),
        "--max-span-len",
        str(CODEWORD_LEN),
        "--block-size",
        "4",
        "--span-step",
        "1",
        "--passes",
        "1",
        "--json",
        "--verify",
        "--force",
        "--telemetry-limit",
        "8",
        "--target-chunk-bytes",
        target_chunk_bytes,
    ]
    return pcb.run_command(cmd, timeout)


def evaluate_file(
    exe: Path,
    path: Path,
    codebook: list[dict[str, Any]],
    out_dir: Path,
    *,
    corpus_root: Path,
    seed_bits: int,
    target_chunk_bytes: str,
    timeout: int,
    codebook_size: int,
    transform_only: bool,
) -> dict[str, Any]:
    data = path.read_bytes()
    rel = path.relative_to(corpus_root)
    safe_name = "__".join(rel.parts)
    transformed, transform_stats = transform(data, codebook)
    recovered = inverse_transform(transformed, codebook, len(data))
    inverse_ok = recovered == data

    transformed_path = out_dir / f"{safe_name}.framed.bin"
    tlmr_path = out_dir / f"{safe_name}.inner.tlmr"
    transformed_path.write_bytes(transformed)
    row: dict[str, Any] = {
        "file": str(rel).replace("\\", "/"),
        "input_bytes": len(data),
        "sha256": pcb.sha256_bytes(data),
        "zlib": [pcb.zlib_result(data, 1), pcb.zlib_result(data, 9)],
        "transform": transform_stats,
        "inverse_ok": inverse_ok,
        "framed_delta_bytes": len(transformed) - len(data),
        "framed_ratio": round(len(transformed) / len(data), 6) if data else 0,
    }
    if transform_only:
        row["telomere_returncode"] = None
        row["telomere_elapsed_s"] = 0.0
        return row

    run = run_telomere_on_transformed(
        exe,
        transformed_path,
        tlmr_path,
        seed_bits=seed_bits,
        target_chunk_bytes=target_chunk_bytes,
        timeout=timeout,
    )
    row["telomere_returncode"] = run["returncode"]
    row["telomere_elapsed_s"] = run["elapsed_s"]
    if run["returncode"] != 0:
        row["stderr_tail"] = run["stderr"][-2000:]
        return row

    payload = json.loads(run["stdout"])
    telemetry = payload.get("engine_telemetry", {})
    layer = (telemetry.get("layers") or [{}])[0]
    inner_bytes = tlmr_path.stat().st_size
    row.update(
        {
            "inner_tlmr_bytes": inner_bytes,
            "amortized_public_package_bytes": inner_bytes + DESCRIPTOR_BYTES,
            "fully_charged_package_bytes": inner_bytes + DESCRIPTOR_BYTES + codebook_size,
            "amortized_delta_bytes": inner_bytes + DESCRIPTOR_BYTES - len(data),
            "fully_charged_delta_bytes": inner_bytes + DESCRIPTOR_BYTES + codebook_size - len(data),
            "candidate_count": layer.get("candidate_count"),
            "selected_count": layer.get("selected_count"),
            "literal_bytes": layer.get("literal_bytes"),
            "seed_len_counts": layer.get("seed_len_counts"),
            "seeds_scanned": layer.get("seeds_scanned"),
            "first_selected_spans": layer.get("selected_spans", []),
        }
    )
    return row


def evaluate_raw_file(
    exe: Path,
    path: Path,
    out_dir: Path,
    *,
    corpus_root: Path,
    seed_bits: int,
    target_chunk_bytes: str,
    timeout: int,
) -> dict[str, Any]:
    data = path.read_bytes()
    rel = path.relative_to(corpus_root)
    safe_name = "__".join(rel.parts)
    tlmr_path = out_dir / f"{safe_name}.raw.tlmr"
    run = run_telomere_on_transformed(
        exe,
        path,
        tlmr_path,
        seed_bits=seed_bits,
        target_chunk_bytes=target_chunk_bytes,
        timeout=timeout,
    )
    row: dict[str, Any] = {
        "file": str(rel).replace("\\", "/"),
        "input_bytes": len(data),
        "sha256": pcb.sha256_bytes(data),
        "zlib": [pcb.zlib_result(data, 1), pcb.zlib_result(data, 9)],
        "telomere_returncode": run["returncode"],
        "telomere_elapsed_s": run["elapsed_s"],
    }
    if run["returncode"] != 0:
        row["stderr_tail"] = run["stderr"][-2000:]
        return row

    payload = json.loads(run["stdout"])
    telemetry = payload.get("engine_telemetry", {})
    layer = (telemetry.get("layers") or [{}])[0]
    raw_tlmr_bytes = tlmr_path.stat().st_size
    row.update(
        {
            "raw_tlmr_bytes": raw_tlmr_bytes,
            "raw_delta_bytes": raw_tlmr_bytes - len(data),
            "raw_ratio": round(raw_tlmr_bytes / len(data), 6) if data else 0,
            "candidate_count": layer.get("candidate_count"),
            "selected_count": layer.get("selected_count"),
            "literal_bytes": layer.get("literal_bytes"),
            "seed_len_counts": layer.get("seed_len_counts"),
            "seeds_scanned": layer.get("seeds_scanned"),
            "first_selected_spans": layer.get("selected_spans", []),
        }
    )
    return row


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    total_input = sum(row["input_bytes"] for row in rows)
    amortized_ratios = [
        row["amortized_public_package_bytes"] / row["input_bytes"]
        for row in rows
        if "amortized_public_package_bytes" in row and row["input_bytes"]
    ]
    fully_charged_ratios = [
        row["fully_charged_package_bytes"] / row["input_bytes"]
        for row in rows
        if "fully_charged_package_bytes" in row and row["input_bytes"]
    ]
    summary: dict[str, Any] = {
        "files": len(rows),
        "input_bytes": total_input,
        "inverse_failures": sum(1 for row in rows if not row["inverse_ok"]),
        "telomere_failures": sum(
            1 for row in rows if row.get("telomere_returncode") not in (0, None)
        ),
        "token_replacements": sum(row["transform"]["replacements"] for row in rows),
        "framed_bytes": sum(row["transform"]["transformed_bytes"] for row in rows),
        "framed_delta_bytes": sum(row["transform"]["transformed_bytes"] for row in rows)
        - total_input,
        "framed_ratio": round(
            sum(row["transform"]["transformed_bytes"] for row in rows) / total_input, 6
        )
        if total_input
        else 0,
        "selected_count": sum(row.get("selected_count", 0) or 0 for row in rows),
        "amortized_file_wins": sum(
            1 for row in rows if row.get("amortized_delta_bytes", 1) < 0
        ),
        "fully_charged_file_wins": sum(
            1 for row in rows if row.get("fully_charged_delta_bytes", 1) < 0
        ),
        "amortized_median_ratio": round(median(amortized_ratios), 6)
        if amortized_ratios
        else None,
        "fully_charged_median_ratio": round(median(fully_charged_ratios), 6)
        if fully_charged_ratios
        else None,
        "zlib_1_bytes": sum(row["zlib"][0]["bytes"] for row in rows),
        "zlib_9_bytes": sum(row["zlib"][1]["bytes"] for row in rows),
    }
    for key in ("inner_tlmr_bytes", "amortized_public_package_bytes", "fully_charged_package_bytes"):
        if any(key not in row for row in rows):
            summary[key] = None
            continue
        value = sum(row[key] for row in rows)
        summary[key] = value
        summary[key.replace("_bytes", "_delta_bytes")] = value - total_input
        summary[key.replace("_bytes", "_ratio")] = round(value / total_input, 6) if total_input else 0
    for key in ("zlib_1_bytes", "zlib_9_bytes"):
        value = summary[key]
        summary[key.replace("_bytes", "_delta_bytes")] = value - total_input
        summary[key.replace("_bytes", "_ratio")] = round(value / total_input, 6) if total_input else 0
    return summary


def summarize_raw(rows: list[dict[str, Any]]) -> dict[str, Any]:
    total_input = sum(row["input_bytes"] for row in rows)
    total_raw = None if any("raw_tlmr_bytes" not in row for row in rows) else sum(
        row["raw_tlmr_bytes"] for row in rows
    )
    summary: dict[str, Any] = {
        "files": len(rows),
        "input_bytes": total_input,
        "telomere_failures": sum(1 for row in rows if row["telomere_returncode"] != 0),
        "selected_count": sum(row.get("selected_count", 0) or 0 for row in rows),
        "zlib_1_bytes": sum(row["zlib"][0]["bytes"] for row in rows),
        "zlib_9_bytes": sum(row["zlib"][1]["bytes"] for row in rows),
        "raw_tlmr_bytes": total_raw,
    }
    if total_raw is not None:
        summary["raw_delta_bytes"] = total_raw - total_input
        summary["raw_ratio"] = round(total_raw / total_input, 6) if total_input else 0
    for key in ("zlib_1_bytes", "zlib_9_bytes"):
        value = summary[key]
        summary[key.replace("_bytes", "_delta_bytes")] = value - total_input
        summary[key.replace("_bytes", "_ratio")] = round(value / total_input, 6) if total_input else 0
    return summary


def compact_variant_summary(
    variant_payload: dict[str, Any], raw_summary: dict[str, Any] | None
) -> dict[str, Any]:
    summary = variant_payload["summary"]
    replacements = summary.get("token_replacements") or 0
    telomere_measured = summary.get("inner_tlmr_bytes") is not None
    selected = summary.get("selected_count") if telomere_measured else None
    out = {
        "variant": variant_payload["variant"],
        "telomere_measured": telomere_measured,
        "token_replacements": replacements,
        "selected_count": selected,
        "selected_per_replacement": round(selected / replacements, 6)
        if replacements and selected is not None
        else None,
        "amortized_delta_bytes": summary.get("amortized_public_package_delta_bytes"),
        "amortized_ratio": summary.get("amortized_public_package_ratio"),
        "fully_charged_delta_bytes": summary.get("fully_charged_package_delta_bytes"),
        "fully_charged_ratio": summary.get("fully_charged_package_ratio"),
    }
    if raw_summary and raw_summary.get("raw_tlmr_bytes") is not None:
        raw_bytes = raw_summary["raw_tlmr_bytes"]
        amortized_bytes = summary.get("amortized_public_package_bytes")
        fully_charged_bytes = summary.get("fully_charged_package_bytes")
        if amortized_bytes is not None:
            out["amortized_vs_raw_tlmr_delta_bytes"] = amortized_bytes - raw_bytes
        if fully_charged_bytes is not None:
            out["fully_charged_vs_raw_tlmr_delta_bytes"] = fully_charged_bytes - raw_bytes
    return out


def seed_alignment_control_deltas(variants: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Compare the real seed-codeword run against same-position non-seed controls."""
    if not variants:
        return []
    real = variants[0]["summary"]
    if variants[0]["variant"] != "real":
        return []
    output = []
    for control in variants[1:]:
        summary = control["summary"]
        row: dict[str, Any] = {
            "control_variant": control["variant"],
            "meaning": (
                "negative byte deltas mean the real seed-generated codewords "
                "were smaller than this same-token control after full Telomere accounting"
            ),
        }
        for key in (
            "inner_tlmr_bytes",
            "amortized_public_package_bytes",
            "fully_charged_package_bytes",
            "selected_count",
        ):
            real_value = real.get(key)
            control_value = summary.get(key)
            if real_value is None or control_value is None:
                row[f"real_minus_control_{key}"] = None
            else:
                row[f"real_minus_control_{key}"] = real_value - control_value
        output.append(row)
    return output


def evaluate_raw_baseline(
    *,
    exe: Path,
    output_root: Path,
    eval_files: list[Path],
    eval_root: Path,
    seed_bits: int,
    target_chunk_bytes: str,
    timeout: int,
) -> dict[str, Any]:
    raw_dir = output_root / "raw-baseline"
    raw_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for path in eval_files:
        row = evaluate_raw_file(
            exe,
            path,
            raw_dir,
            corpus_root=eval_root,
            seed_bits=seed_bits,
            target_chunk_bytes=target_chunk_bytes,
            timeout=timeout,
        )
        rows.append(row)
        print(
            json.dumps(
                {
                    "variant": "raw-baseline",
                    "file": row["file"],
                    "input_bytes": row["input_bytes"],
                    "selected_count": row.get("selected_count"),
                    "raw_tlmr_bytes": row.get("raw_tlmr_bytes"),
                    "zlib_9_bytes": row["zlib"][1]["bytes"],
                },
                sort_keys=True,
            )
        )
    return {"summary": summarize_raw(rows), "rows": rows}


def evaluate_codebook_variant(
    *,
    variant: str,
    exe: Path,
    codebook: list[dict[str, Any]],
    manifest: dict[str, Any],
    output_root: Path,
    eval_files: list[Path],
    eval_root: Path,
    seed_bits: int,
    target_chunk_bytes: str,
    timeout: int,
    transform_only: bool,
) -> dict[str, Any]:
    variant_dir = output_root / variant
    variant_dir.mkdir(parents=True, exist_ok=True)
    frozen_codebook_bytes = codebook_bytes(codebook, manifest)
    codebook_hash = hashlib.sha256(frozen_codebook_bytes).hexdigest()
    codebook_path = variant_dir / "frozen_codebook.json"
    codebook_path.write_bytes(frozen_codebook_bytes)

    rows = []
    for path in eval_files:
        row = evaluate_file(
            exe,
            path,
            codebook,
            variant_dir,
            corpus_root=eval_root,
            seed_bits=seed_bits,
            target_chunk_bytes=target_chunk_bytes,
            timeout=timeout,
            codebook_size=len(frozen_codebook_bytes),
            transform_only=transform_only,
        )
        rows.append(row)
        print(
            json.dumps(
                {
                    "variant": variant,
                    "file": row["file"],
                    "input_bytes": row["input_bytes"],
                    "replacements": row["transform"]["replacements"],
                    "selected_count": row.get("selected_count"),
                    "amortized_bytes": row.get("amortized_public_package_bytes"),
                    "fully_charged_bytes": row.get("fully_charged_package_bytes"),
                    "zlib_9_bytes": row["zlib"][1]["bytes"],
                },
                sort_keys=True,
            )
        )

    return {
        "variant": variant,
        "manifest": manifest,
        "codebook": {
            "path": str(codebook_path),
            "sha256": codebook_hash,
            "bytes_json_compact": len(frozen_codebook_bytes),
            "token_count": len(codebook),
            "tokens": codebook,
        },
        "summary": summarize(rows),
        "rows": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--train-corpus", choices=sorted(pcb.CORPORA), default="calgary")
    parser.add_argument("--eval-corpus", choices=sorted(pcb.CORPORA), default="canterbury")
    parser.add_argument("--ngram-lens", default="13,16,24,32,48,64")
    parser.add_argument("--min-count", type=int, default=2)
    parser.add_argument("--max-tokens", type=int, default=128)
    parser.add_argument("--printable-only", action="store_true")
    parser.add_argument("--seed-bits", type=int, default=8)
    parser.add_argument("--max-files", type=int, default=0)
    parser.add_argument("--max-file-bytes", type=int, default=0)
    parser.add_argument("--target-chunk-bytes", default="64MB")
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument(
        "--transform-only",
        action="store_true",
        help="measure the frozen transform and controls without invoking Telomere",
    )
    parser.add_argument("--skip-raw-baseline", action="store_true")
    parser.add_argument(
        "--controls",
        default="",
        help=(
            "comma-separated null controls: random-length-token,xor-token,"
            "random-codeword,out-of-budget-codeword,all,none"
        ),
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    if args.max_tokens > 256:
        raise SystemExit("--max-tokens cannot exceed 256 for one-byte seed codewords")
    ngram_lens = parse_ngram_lens(args.ngram_lens)
    if not ngram_lens:
        raise SystemExit("--ngram-lens cannot be empty")
    try:
        controls = parse_controls(args.controls)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    exe = pcb.telomere_exe()
    train_meta, train_files = pcb.corpus_files(args.train_corpus)
    eval_meta, eval_files = pcb.corpus_files(args.eval_corpus)
    if args.max_file_bytes:
        eval_files = [path for path in eval_files if path.stat().st_size <= args.max_file_bytes]
    if args.max_files:
        eval_files = eval_files[: args.max_files]

    train_manifest = {
        "train_corpus": train_meta,
        "ngram_lens": ngram_lens,
        "min_count": args.min_count,
        "max_tokens": args.max_tokens,
        "printable_only": args.printable_only,
        "codeword_len": CODEWORD_LEN,
        "seed_kind": "one-byte canonical seed index",
        "split_role": "train",
        "files": [
            {
                "path": str(path.relative_to(pcb.TARGET / "public_corpora" / args.train_corpus / "files")).replace("\\", "/"),
                "bytes": path.stat().st_size,
                "sha256": pcb.sha256_file(path),
            }
            for path in train_files
        ],
    }
    started = time.perf_counter()
    codebook = train_codebook(
        train_files,
        ngram_lens=ngram_lens,
        min_count=args.min_count,
        max_tokens=args.max_tokens,
        printable_only=args.printable_only,
    )
    training_elapsed = time.perf_counter() - started
    real_codebook = control_codebook(codebook, "real", source_hash="")

    out_dir = args.output.parent / f"{args.train_corpus}_to_{args.eval_corpus}"
    out_dir.mkdir(parents=True, exist_ok=True)
    eval_root = pcb.TARGET / "public_corpora" / args.eval_corpus / "files"

    real_manifest = {
        **train_manifest,
        "variant": "real",
        "control_role": "positive mechanism candidate",
    }
    variants = [
        evaluate_codebook_variant(
            variant="real",
            exe=exe,
            codebook=real_codebook,
            manifest=real_manifest,
            output_root=out_dir,
            eval_files=eval_files,
            eval_root=eval_root,
            seed_bits=args.seed_bits,
            target_chunk_bytes=args.target_chunk_bytes,
            timeout=args.timeout,
            transform_only=args.transform_only,
        )
    ]
    source_codebook_hash = variants[0]["codebook"]["sha256"]
    for control in controls:
        control_manifest = {
            **train_manifest,
            "variant": control,
            "control_role": "null control",
            "source_codebook_sha256": source_codebook_hash,
        }
        control_rows = control_codebook(real_codebook, control, source_hash=source_codebook_hash)
        variants.append(
            evaluate_codebook_variant(
                variant=control,
                exe=exe,
                codebook=control_rows,
                manifest=control_manifest,
                output_root=out_dir,
                eval_files=eval_files,
                eval_root=eval_root,
                seed_bits=args.seed_bits,
                target_chunk_bytes=args.target_chunk_bytes,
                timeout=args.timeout,
                transform_only=args.transform_only,
            )
        )

    real_variant = variants[0]
    raw_baseline = None
    if not args.skip_raw_baseline and not args.transform_only:
        raw_baseline = evaluate_raw_baseline(
            exe=exe,
            output_root=out_dir,
            eval_files=eval_files,
            eval_root=eval_root,
            seed_bits=args.seed_bits,
            target_chunk_bytes=args.target_chunk_bytes,
            timeout=args.timeout,
        )

    variant_comparison = [
        compact_variant_summary(
            variant,
            raw_baseline["summary"] if raw_baseline is not None else None,
        )
        for variant in variants
    ]

    payload = {
        "generated_by": "scripts/run_frozen_codebook_experiment.py",
        "format_status": "external_transform_research_package_not_final_tlmr",
        "codec_status": (
            "experimental harness; rerun after the repository Lotus codec is "
            "confirmed faithful to the canonical lotus implementation"
        ),
        "control_descriptions": {
            "random-length-token": (
                "same token length multiset and seed-generated codewords, but "
                "tokens are deterministic random bytes"
            ),
            "xor-token": (
                "same codewords, but tokens are bytewise XOR shadows of the "
                "trained tokens"
            ),
            "random-codeword": (
                "same trained tokens and replacement positions, but codewords "
                "are deterministic non-seed random bytes"
            ),
            "out-of-budget-codeword": (
                "same trained tokens, but codewords are generated from canonical "
                "seed indices just beyond the configured seed_bits budget"
            ),
        },
        "run_provenance": run_provenance(exe),
        "train": train_manifest,
        "eval_corpus": {
            **eval_meta,
            "split_role": "validation" if args.eval_corpus == "canterbury" else "heldout",
        },
        "params": {
            "seed_bits": args.seed_bits,
            "target_chunk_bytes": args.target_chunk_bytes,
            "timeout": args.timeout,
            "max_files": args.max_files,
            "max_file_bytes": args.max_file_bytes,
            "transform_only": args.transform_only,
            "skip_raw_baseline": args.skip_raw_baseline,
            "controls": controls,
        },
        "codebook": {
            **real_variant["codebook"],
            "token_count": len(codebook),
            "training_elapsed_s": round(training_elapsed, 6),
        },
        "summary": real_variant["summary"],
        "rows": real_variant["rows"],
        "controls": variants[1:],
        "variants": variants,
        "raw_baseline": raw_baseline,
        "variant_comparison": variant_comparison,
        "seed_alignment_control_deltas": seed_alignment_control_deltas(variants),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(f"WROTE {args.output}")
    print(json.dumps(payload["summary"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())

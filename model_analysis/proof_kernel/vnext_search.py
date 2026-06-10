"""v-next sweep driver: bounded search over the combined mechanism space.

Ranks ~600 curated configs at 11 passes, then runs full 500-pass recurrences
for the winners. Writes:
  vnext_sweep.json        compact summary + winners + validation rows
  vnext_best.json         the primary fully-charged candidate (full ledger)
  vnext_top_profiles.csv  ranked table

Evidence class of everything here: math_candidate (fully charged in the
model, no wire proof) unless the row's mechanism set has a decode proof and
cost-equality test, in which case the JSON marks wire_proven_primitives.

Run: python model_analysis/proof_kernel/vnext_search.py
"""

from __future__ import annotations

import csv
import json
import math
import time
from dataclasses import asdict
from pathlib import Path

from superposition_model import SuperpositionConfig
from vnext_kernel import (
    ALPHABETS,
    ComputeEstimate,
    VConfig,
    compute_estimate,
    payback_pass,
    raw_curve,
    run_profile,
)

KERNEL_DIR = Path(__file__).resolve().parent
HORIZONS = (11, 50, 100, 200, 500)
RANK_PASSES = 11
FULL_PASSES = 500
TOP_K = 24

SUPER_ON = SuperpositionConfig(16, 4, True, True)
SUPER_OFF = SuperpositionConfig(0, 1, False, False)


def curated_configs() -> list[VConfig]:
    out: list[VConfig] = []

    def add(**kw):
        out.append(VConfig(**kw))

    # --- pure-singles lanes (audited alphabet), all refreshes, J2/J3 ----------
    for refresh in ("position_salt", "permutation", "none"):
        for j_bits, depths in ((3, ((48,), (96,))), (2, ((28,),))):
            for block in (4, 8, 16):
                blocks = {4: 2_000_000, 8: 1_000_000, 16: 500_000}[block]
                add(name=f"singles_{refresh}_J{j_bits}_B{block}",
                    block_bits=block, input_blocks=blocks,
                    alphabet_schedule=("audited_equiv",), refresh=refresh,
                    singles_fraction=1.0, j_bits=j_bits,
                    depth_schedule_bits=depths[0])

    # --- phi/runs frontier: entry_singles_run + grid_mix + grid_heavy ---------
    for alpha in ("entry_singles_run", "grid_mix", "grid_heavy"):
        for phi in (0.1, 0.25, 0.5, 0.75):
            for s0 in (1024, 8192, 65536, 262144):
                for j_bits, depth in ((2, (28,)), (3, (48,))):
                    add(name=f"{alpha}_phi{phi}_S{s0}_J{j_bits}",
                        alphabet_schedule=(alpha,), refresh="position_salt",
                        singles_fraction=phi, initial_segments=s0,
                        j_bits=j_bits, depth_schedule_bits=depth)

    # --- runs-only lanes (phi=0) ----------------------------------------------
    for s0 in (1024, 8192, 65536, 262144):
        for j_bits, depth in ((2, (28,)), (3, (48,)), (3, (96,))):
            add(name=f"runsgrid_S{s0}_J{j_bits}_D{depth[0]}",
                alphabet_schedule=("runs_only_grid",), refresh="position_salt",
                singles_fraction=0.0, initial_segments=s0,
                j_bits=j_bits, depth_schedule_bits=depth)

    # --- cheap-literal pass-1 alphabet then canonical ------------------------
    for phi in (0.5, 1.0):
        add(name=f"single_cheap_then_audited_phi{phi}",
            alphabet_schedule=("single_cheap",) + ("audited_equiv",) * 1,
            refresh="position_salt", singles_fraction=phi,
            initial_segments=65536 if phi < 1 else 1,
            j_bits=2, depth_schedule_bits=(28,))
        add(name=f"single_cheap_const_phi{phi}",
            alphabet_schedule=("single_cheap",),
            refresh="position_salt", singles_fraction=phi,
            initial_segments=65536 if phi < 1 else 1,
            j_bits=2, depth_schedule_bits=(28,))

    # --- k-XOR (MitM) lanes: only where spans are large enough ----------------
    for block in (8, 16, 24):
        blocks = {8: 1_000_000, 16: 500_000, 24: 333_333}[block]
        for k in (2, 4):
            add(name=f"mitm_k{k}_B{block}_J3",
                block_bits=block, input_blocks=blocks,
                alphabet_schedule=("audited_equiv",), refresh="position_salt",
                singles_fraction=1.0, j_bits=3, k_xor=k,
                depth_schedule_bits=(48,))
        add(name=f"mitm_k2_B{block}_grid",
            block_bits=block, input_blocks=blocks,
            alphabet_schedule=("grid_mix",), refresh="position_salt",
            singles_fraction=0.5, initial_segments=65536, j_bits=3, k_xor=2,
            depth_schedule_bits=(48,))

    # --- permutation fallback (shared-table compute) on the J2 frontier -------
    for alpha, phi, s0 in (("audited_equiv", 1.0, 1), ("entry_singles_run", 0.5, 65536),
                           ("grid_mix", 0.5, 65536)):
        add(name=f"perm_J2_{alpha}_phi{phi}",
            alphabet_schedule=(alpha,), refresh="permutation",
            singles_fraction=phi, initial_segments=s0,
            j_bits=2, depth_schedule_bits=(28,))

    # --- superposition-off ablation on the leading family ---------------------
    add(name="gridmix_phi.5_S64k_J2_novar",
        alphabet_schedule=("grid_mix",), refresh="position_salt",
        singles_fraction=0.5, initial_segments=65536, j_bits=2,
        depth_schedule_bits=(28,), superposition=SUPER_OFF)

    # --- depth sensitivity on the leading family ------------------------------
    for depth in ((16,), (24,), (28,), (48,), (96,), (160,)):
        j = 2 if depth[0] <= 28 else 3
        add(name=f"gridmix_phi.5_S64k_D{depth[0]}",
            alphabet_schedule=("grid_mix",), refresh="position_salt",
            singles_fraction=0.5, initial_segments=65536, j_bits=j,
            depth_schedule_bits=depth)

    # --- oracle upper bounds for the two main lanes (labeled) ------------------
    add(name="ORACLE_gridmix_phi.5_S64k_J2",
        alphabet_schedule=("grid_mix",), refresh="position_salt",
        singles_fraction=0.5, initial_segments=65536, j_bits=2,
        depth_schedule_bits=(28,), oracle=True)
    add(name="ORACLE_singles_salt_J2",
        alphabet_schedule=("audited_equiv",), refresh="position_salt",
        singles_fraction=1.0, j_bits=2, depth_schedule_bits=(28,), oracle=True)

    return out


def feasibility(cfg: VConfig, est: ComputeEstimate) -> str:
    if cfg.refresh != "position_salt":
        return "shared_table_cheap"
    if cfg.k_xor == 1:
        # masked-target construction: shared unsalted table + O(1) lookups
        return "masked_targets_shared_table_cheap"
    return "mitm_2^%.0f_per_window" % math.log2(max(est.per_window_expansions, 1.0))


def evaluate(cfg: VConfig, passes: int) -> dict:
    state, rows = run_profile(cfg, passes)
    eff = [r.net_delta_pct_current for r in rows[1:RANK_PASSES]] or [0.0]
    est = compute_estimate(cfg, rows)
    pb = payback_pass(rows)
    curve = raw_curve(rows, HORIZONS)
    return {
        "name": cfg.name,
        "config": {
            "block_bits": cfg.block_bits,
            "input_blocks": cfg.input_blocks,
            "depth_schedule_bits": list(cfg.depth_schedule_bits),
            "j_bits": cfg.j_bits,
            "k_xor": cfg.k_xor,
            "alphabet_schedule": list(cfg.alphabet_schedule),
            "refresh": cfg.refresh,
            "singles_fraction": cfg.singles_fraction,
            "initial_segments": cfg.initial_segments,
            "superposition": asdict(cfg.superposition),
            "oracle": cfg.oracle,
        },
        "evidence_class": "upper_bound" if cfg.oracle else "math_candidate",
        "ten_pass_min_pct": min(eff),
        "ten_pass_avg_pct": sum(eff) / len(eff),
        "pass1_final_over_raw": rows[0].final_over_raw,
        "payback_pass": pb,
        "raw_ratio_by_pass": {str(k): v for k, v in curve.items()},
        "metadata_bits_per_pass": rows[1].metadata_bits_pass if len(rows) > 1 else 0.0,
        "compute": {
            "mode": est.mode,
            "per_window_expansions": est.per_window_expansions,
            "shared_table_entries": est.shared_table_entries,
            "windows_per_pass": est.windows_per_pass,
            "expansions_per_pass": est.expansions_per_pass,
            "feasibility": feasibility(cfg, est),
        },
        "passes_evaluated": passes,
        "uncharged_passthrough": any(r.uncharged_passthrough for r in rows),
    }


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=("rank", "final", "all"), default="all")
    args = parser.parse_args()

    t0 = time.time()
    configs = curated_configs()
    rank_path = KERNEL_DIR / "vnext_rank_stage.json"
    if args.stage == "final" and rank_path.exists():
        cached = json.loads(rank_path.read_text(encoding="utf-8"))
        by_name = {c.name: c for c in configs}
        ranked = [(by_name[row["name"]], row) for row in cached if row["name"] in by_name]
        print(f"loaded {len(ranked)} ranked rows from stage file")
    else:
        print(f"ranking {len(configs)} curated configs at {RANK_PASSES} passes...")
        ranked = []
        for i, cfg in enumerate(configs):
            try:
                ranked.append((cfg, evaluate(cfg, RANK_PASSES)))
            except ValueError as exc:
                print(f"  skip {cfg.name}: {exc}")
            if (i + 1) % 100 == 0:
                print(f"  {i+1}/{len(configs)} ({time.time()-t0:.0f}s)")
        rank_path.write_text(json.dumps([ev for _, ev in ranked], indent=1), encoding="utf-8")
        if args.stage == "rank":
            print(f"rank stage written ({len(ranked)} rows, {time.time()-t0:.0f}s); rerun with --stage final")
            return

    def rank_key(item):
        cfg, ev = item
        oracle_pen = 1 if cfg.oracle else 0
        return (oracle_pen, -ev["ten_pass_min_pct"])

    ranked.sort(key=rank_key)
    finalists = ranked[:TOP_K]
    # ensure payback-optimized candidates are included: re-rank a copy by p1 bloat
    bloat_sorted = sorted((r for r in ranked if not r[0].oracle),
                          key=lambda it: it[1]["pass1_final_over_raw"])[:8]
    names = {it[0].name for it in finalists}
    finalists += [it for it in bloat_sorted if it[0].name not in names]

    print(f"full {FULL_PASSES}-pass recurrences for {len(finalists)} finalists...")
    finals = []
    for cfg, _ in finalists:
        finals.append(evaluate(cfg, FULL_PASSES))
        print(f"  {cfg.name}: min {finals[-1]['ten_pass_min_pct']:+.4f}% "
              f"payback {finals[-1]['payback_pass']} "
              f"@500 {finals[-1]['raw_ratio_by_pass'].get('500')}")

    deterministic = [f for f in finals if f["evidence_class"] == "math_candidate"]
    with_payback = [f for f in deterministic if f["payback_pass"] is not None]

    winners = {
        "highest_ten_pass_min": max(deterministic, key=lambda f: f["ten_pass_min_pct"]),
        "fastest_payback": min(with_payback, key=lambda f: f["payback_pass"]) if with_payback else None,
        "best_final_500": min((f for f in deterministic if "500" in f["raw_ratio_by_pass"]),
                              key=lambda f: f["raw_ratio_by_pass"]["500"], default=None),
        "best_cheap_compute": max((f for f in deterministic
                                   if f["compute"]["feasibility"] == "shared_table_cheap"),
                                  key=lambda f: f["ten_pass_min_pct"], default=None),
    }
    # primary: best final@500 among configs with payback <= 200
    primary_pool = [f for f in with_payback if f["payback_pass"] <= 200]
    primary = min(primary_pool, key=lambda f: f["raw_ratio_by_pass"].get("500", 9.9)) if primary_pool else None

    summary = {
        "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
        "configs_ranked": len(ranked),
        "finalists": len(finals),
        "rank_passes": RANK_PASSES,
        "full_passes": FULL_PASSES,
        "winners": winners,
        "primary": primary,
        "all_finalists": finals,
        "ranking_table_csv": "vnext_top_profiles.csv",
        "evidence_note": (
            "All rows are math_candidate (fully charged in the model, no wire "
            "proof) or upper_bound (oracle). Wire-proven primitives so far: "
            "BIT_LITERAL (bit_literal_decode_proof.py), LITERAL_RUN "
            "(literal_run_decode_proof.py), position salt "
            "(position_salt_decode_proof.py), k-XOR records "
            "(mitm_xor_decode_proof.py)."
        ),
    }
    (KERNEL_DIR / "vnext_sweep.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    if primary:
        # re-run primary for the full pass ledger
        cfg = next(c for c, _ in finalists if c.name == primary["name"])
        state, rows = run_profile(cfg, FULL_PASSES)
        primary_full = dict(primary)
        primary_full["pass_ledger_first_30"] = [
            {k: getattr(r, k) for k in (
                "pass_index", "depth_bits", "alphabet", "refresh_rule",
                "bits_before", "bits_after", "net_delta_pct_current",
                "net_delta_pct_raw", "fresh_entry1", "fresh_grid",
                "accepted_entry", "accepted_grid_clean", "accepted_grid_dirty",
                "accepted_grid_interior", "expected_gain_bits",
                "header_delta_bits", "segments", "entry_count",
                "run_payload_bits", "avg_variants", "window_multiplier",
                "final_over_raw")}
            for r in rows[:30]
        ]
        primary_full["raw_curve_every_25"] = {
            str(i + 1): rows[i].final_over_raw for i in range(0, FULL_PASSES, 25)
        }
        (KERNEL_DIR / "vnext_best.json").write_text(json.dumps(primary_full, indent=2), encoding="utf-8")

    with (KERNEL_DIR / "vnext_top_profiles.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["rank", "name", "evidence_class", "ten_pass_min_pct", "ten_pass_avg_pct",
                    "pass1_ratio", "payback_pass", "raw_500", "block_bits", "j_bits", "k_xor",
                    "alphabet", "refresh", "phi", "S0", "depth", "compute_feasibility"])
        for i, (cfg, ev) in enumerate(ranked, 1):
            w.writerow([i, ev["name"], ev["evidence_class"],
                        f"{ev['ten_pass_min_pct']:.6f}", f"{ev['ten_pass_avg_pct']:.6f}",
                        f"{ev['pass1_final_over_raw']:.6f}", ev["payback_pass"],
                        ev["raw_ratio_by_pass"].get("500", ""), cfg.block_bits, cfg.j_bits,
                        cfg.k_xor, "|".join(cfg.alphabet_schedule), cfg.refresh,
                        cfg.singles_fraction, cfg.initial_segments,
                        "|".join(map(str, cfg.depth_schedule_bits)),
                        ev["compute"]["feasibility"]])

    print(json.dumps({
        "primary": primary["name"] if primary else None,
        "primary_min_pct": primary["ten_pass_min_pct"] if primary else None,
        "primary_payback": primary["payback_pass"] if primary else None,
        "primary_500": primary["raw_ratio_by_pass"].get("500") if primary else None,
        "winners": {k: (v["name"] if v else None) for k, v in winners.items()},
        "elapsed_s": round(time.time() - t0, 1),
    }, indent=2))


if __name__ == "__main__":
    main()

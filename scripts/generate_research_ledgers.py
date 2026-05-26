#!/usr/bin/env python3
"""Regenerate or check the top-level Telomere research ledgers in dependency order."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class LedgerStep:
    name: str
    script: str
    reason: str


PIPELINE = [
    LedgerStep(
        "UI workflow smoke",
        "scripts/generate_ui_workflow_smoke.py",
        "viability, scorecard, and goal audit all record this artifact hash",
    ),
    LedgerStep(
        "viability",
        "scripts/generate_viability.py",
        "research scorecard and goal audit consume the viability ledger",
    ),
    LedgerStep(
        "research scorecard",
        "scripts/generate_research_scorecard.py",
        "goal audit consumes the scorecard ledger",
    ),
    LedgerStep(
        "goal audit",
        "scripts/generate_goal_audit.py",
        "experiment queue consumes the goal audit ledger",
    ),
    LedgerStep(
        "experiment queue",
        "scripts/generate_experiment_queue.py",
        "research decision consumes the queue state",
    ),
    LedgerStep(
        "research decision",
        "scripts/generate_research_decision.py",
        "research frontier consumes the current go/no-go decision",
    ),
    LedgerStep(
        "research frontier",
        "scripts/generate_research_frontier.py",
        "natural/prod proof matrices and team protocol consume the frontier gate state",
    ),
    LedgerStep(
        "natural corpus proof matrix",
        "scripts/generate_natural_corpus_proof_matrix.py",
        "completion audit consumes natural-corpus viability blockers",
    ),
    LedgerStep(
        "production proof matrix",
        "scripts/generate_production_proof_matrix.py",
        "completion audit consumes production-readiness blockers",
    ),
    LedgerStep(
        "research team protocol",
        "scripts/generate_research_team_protocol.py",
        "completion audit consumes the parallel-team protocol",
    ),
    LedgerStep(
        "goal completion audit",
        "scripts/generate_goal_completion_audit.py",
        "blocked-requirement dispatch consumes completion blockers",
    ),
    LedgerStep(
        "blocked requirement dispatch",
        "scripts/generate_blocked_requirement_dispatch.py",
        "final maintenance-only dispatch boundary for blocked requirements",
    ),
]


def run_step(step: LedgerStep, check: bool) -> dict[str, object]:
    command = [sys.executable, str(ROOT / step.script)]
    if check:
        command.append("--check")
    started = datetime.now(timezone.utc)
    completed = subprocess.run(command, cwd=ROOT, check=False)
    finished = datetime.now(timezone.utc)
    return {
        "name": step.name,
        "script": step.script,
        "mode": "check" if check else "generate",
        "returncode": completed.returncode,
        "started_at": started.isoformat(),
        "finished_at": finished.isoformat(),
    }


def print_plan() -> None:
    for index, step in enumerate(PIPELINE, start=1):
        print(f"{index}. {step.name}: {step.script}")
        print(f"   {step.reason}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="run every ledger generator in check mode instead of rewriting artifacts",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="emit a JSON execution report",
    )
    parser.add_argument(
        "--print-plan",
        action="store_true",
        help="print the dependency order without running commands",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.print_plan:
        if args.json:
            print(json.dumps([asdict(step) for step in PIPELINE], indent=2))
        else:
            print_plan()
        return

    report = []
    for step in PIPELINE:
        result = run_step(step, args.check)
        report.append(result)
        if result["returncode"] != 0:
            if args.json:
                print(json.dumps(report, indent=2))
            raise SystemExit(
                f"{step.script} failed in {result['mode']} mode "
                f"with exit code {result['returncode']}"
            )

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        mode = "check" if args.check else "generate"
        print(f"Research ledger {mode} pipeline passed ({len(report)} steps).")


if __name__ == "__main__":
    main()

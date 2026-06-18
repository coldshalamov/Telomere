#!/usr/bin/env python3
"""H159 - seed-bearing closed-core graph.

H157 tested recursive selected streams by dynamic programming. This kernel
asks whether the underlying closed language exists:

    visible seed-record stream y  --decodes to-->  visible seed-record stream x

Nodes are concrete H96 seed-record streams up to a cap. An edge ``y -> x``
exists when ``y`` is an actual bounded H96 description of the full visible
bitstring ``x`` and both endpoints are nodes. This is the recursive
record-to-record question; it does not use filler completion, cloud mass,
hidden ranks, stop selectors, or raw repair.

If a finite recurrent closed core exists, it appears as a nontrivial strongly
connected component. Any finite decode cycle has zero total length drift by
telescoping, so positive maintained compression would need either a one-way
basin that eventually stops helping, or an unbounded/public state space whose
syntax is paid.
"""

from __future__ import annotations

import argparse
import importlib.util
import math
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from statistics import mean


HERE = Path(__file__).resolve().parent
H96_PATH = HERE / "H96-neutral_transfer_operator.py"
H96_SPEC = importlib.util.spec_from_file_location("h96_for_h159", H96_PATH)
if H96_SPEC is None or H96_SPEC.loader is None:
    raise RuntimeError(f"cannot load {H96_PATH}")
h96 = importlib.util.module_from_spec(H96_SPEC)
sys.modules[H96_SPEC.name] = h96
H96_SPEC.loader.exec_module(h96)


@dataclass(frozen=True)
class Node:
    bits: str
    record_count: int

    @property
    def visible_len(self) -> int:
        return len(self.bits)


@dataclass(frozen=True)
class GraphRow:
    max_arity: int
    depth_bits: int
    cap_bits: int
    node_count: int
    capped: bool
    duplicate_streams: int
    edges: int
    source_nodes: int
    target_nodes: int
    edge_density: float
    source_mass_tax: float
    nontrivial_sccs: int
    scc_nodes: int
    largest_scc: int
    compressive_edges: int
    nodes_with_shorter_parent: int
    shorter_parent_fraction: float
    shorter_parent_mass_tax: float
    best_edge_gain: int
    mean_edge_gain: float
    best_scc_edge_gain: int
    best_density_len: int
    best_density_log2: float
    best_source_len: int
    best_source_fraction_by_len: float


def flat_records(max_arity: int, depth_bits: int, seed: int) -> tuple[list[h96.Record], list[list[list[h96.Record]]]]:
    by_value, _edge_weights, _edge_maxes = h96.build_record_family(
        block_bits=1,
        max_arity=max_arity,
        depth_bits=depth_bits,
        seed=seed,
    )
    records: list[h96.Record] = []
    for arity in range(1, max_arity + 1):
        for bucket in by_value[arity]:
            records.extend(bucket)
    return (
        sorted(records, key=lambda item: (len(item.bits), item.arity, item.rank, item.bits)),
        by_value,
    )


def enumerate_nodes(
    *,
    max_arity: int,
    depth_bits: int,
    cap_bits: int,
    seed: int,
    max_nodes: int,
) -> tuple[list[Node], int, bool, list[list[list[h96.Record]]]]:
    records, by_value = flat_records(max_arity, depth_bits, seed)
    nodes: list[Node] = []
    seen: set[str] = set()
    duplicates = 0
    capped = False

    def rec(bits: str, record_count: int) -> None:
        nonlocal duplicates, capped
        for record in records:
            next_bits = bits + record.bits
            if len(next_bits) > cap_bits:
                continue
            if next_bits in seen:
                duplicates += 1
            else:
                seen.add(next_bits)
                nodes.append(Node(bits=next_bits, record_count=record_count + 1))
                if len(nodes) >= max_nodes:
                    capped = True
                    return
                rec(next_bits, record_count + 1)
                if capped:
                    return

    rec("", 0)
    return nodes, duplicates, capped, by_value


def span_value(bits: str, pos: int, arity: int) -> int:
    return int(bits[pos : pos + arity], 2) if arity else 0


def bounded_descriptions(
    bits: str,
    *,
    max_arity: int,
    by_value: list[list[list[h96.Record]]],
    cap_bits: int,
    stop_set: set[str],
) -> set[str]:
    """Return visible descriptions of ``bits`` that are also in ``stop_set``."""

    found: set[str] = set()

    def rec(pos: int, out_bits: str, cost: int) -> None:
        if cost > cap_bits:
            return
        if pos == len(bits):
            if out_bits in stop_set:
                found.add(out_bits)
            return
        for arity in range(1, min(max_arity, len(bits) - pos) + 1):
            value = span_value(bits, pos, arity)
            for record in by_value[arity][value]:
                next_cost = cost + len(record.bits)
                if next_cost <= cap_bits:
                    rec(pos + arity, out_bits + record.bits, next_cost)

    rec(0, "", 0)
    return found


def tarjan_scc(edges: list[set[int]]) -> list[list[int]]:
    index = 0
    stack: list[int] = []
    on_stack: set[int] = set()
    indices: dict[int, int] = {}
    lowlink: dict[int, int] = {}
    components: list[list[int]] = []

    def strongconnect(node: int) -> None:
        nonlocal index
        indices[node] = index
        lowlink[node] = index
        index += 1
        stack.append(node)
        on_stack.add(node)

        for target in edges[node]:
            if target not in indices:
                strongconnect(target)
                lowlink[node] = min(lowlink[node], lowlink[target])
            elif target in on_stack:
                lowlink[node] = min(lowlink[node], indices[target])

        if lowlink[node] == indices[node]:
            component: list[int] = []
            while True:
                item = stack.pop()
                on_stack.remove(item)
                component.append(item)
                if item == node:
                    break
            components.append(component)

    for node in range(len(edges)):
        if node not in indices:
            strongconnect(node)
    return components


def log2_density(count: int, length: int) -> float:
    if count <= 0:
        return float("-inf")
    return math.log2(count) - length


def row_for(max_arity: int, depth_bits: int, cap_bits: int, seed: int, max_nodes: int) -> GraphRow:
    nodes, duplicates, capped, by_value = enumerate_nodes(
        max_arity=max_arity,
        depth_bits=depth_bits,
        cap_bits=cap_bits,
        seed=seed,
        max_nodes=max_nodes,
    )
    by_bits = {node.bits: index for index, node in enumerate(nodes)}
    node_bits = set(by_bits)
    edges: list[set[int]] = [set() for _ in nodes]

    for target_index, target in enumerate(nodes):
        for source_bits in bounded_descriptions(
            target.bits,
            max_arity=max_arity,
            by_value=by_value,
            cap_bits=cap_bits,
            stop_set=node_bits,
        ):
            source_index = by_bits[source_bits]
            edges[source_index].add(target_index)

    edge_pairs = [
        (source, target)
        for source, targets in enumerate(edges)
        for target in targets
    ]
    edge_gains = [
        nodes[target].visible_len - nodes[source].visible_len
        for source, target in edge_pairs
    ]
    source_nodes = {source for source, _target in edge_pairs}
    target_nodes = {target for _source, target in edge_pairs}
    incoming_shorter = {
        target
        for source, target in edge_pairs
        if nodes[source].visible_len < nodes[target].visible_len
    }
    valid_mass = sum(2.0 ** (-node.visible_len) for node in nodes)
    source_mass = sum(2.0 ** (-nodes[node].visible_len) for node in source_nodes)
    shorter_target_mass = sum(2.0 ** (-nodes[node].visible_len) for node in incoming_shorter)

    def mass_tax(part: float) -> float:
        if valid_mass <= 0.0 or part <= 0.0:
            return float("inf")
        return -math.log2(part / valid_mass)

    components = tarjan_scc(edges)
    nontrivial = [
        comp
        for comp in components
        if len(comp) > 1 or (len(comp) == 1 and comp[0] in edges[comp[0]])
    ]
    scc_node_set = {node for comp in nontrivial for node in comp}
    scc_edge_gains = [
        nodes[target].visible_len - nodes[source].visible_len
        for source, target in edge_pairs
        if source in scc_node_set and target in scc_node_set
    ]

    counts_by_len = Counter(node.visible_len for node in nodes)
    sources_by_len = Counter(nodes[source].visible_len for source in source_nodes)
    if counts_by_len:
        best_density_len, best_density_count = max(
            counts_by_len.items(),
            key=lambda item: (log2_density(item[1], item[0]), -item[0]),
        )
        best_source_len, best_source_count = max(
            counts_by_len.items(),
            key=lambda item: (
                sources_by_len[item[0]] / item[1] if item[1] else 0.0,
                -item[0],
            ),
        )
        best_source_fraction = sources_by_len[best_source_len] / best_source_count
    else:
        best_density_len = 0
        best_density_count = 0
        best_source_len = 0
        best_source_fraction = 0.0

    return GraphRow(
        max_arity=max_arity,
        depth_bits=depth_bits,
        cap_bits=cap_bits,
        node_count=len(nodes),
        capped=capped,
        duplicate_streams=duplicates,
        edges=len(edge_pairs),
        source_nodes=len(source_nodes),
        target_nodes=len(target_nodes),
        edge_density=(len(edge_pairs) / len(nodes) if nodes else 0.0),
        source_mass_tax=mass_tax(source_mass),
        nontrivial_sccs=len(nontrivial),
        scc_nodes=len(scc_node_set),
        largest_scc=max((len(comp) for comp in nontrivial), default=0),
        compressive_edges=sum(1 for gain in edge_gains if gain > 0),
        nodes_with_shorter_parent=len(incoming_shorter),
        shorter_parent_fraction=(len(incoming_shorter) / len(nodes) if nodes else 0.0),
        shorter_parent_mass_tax=mass_tax(shorter_target_mass),
        best_edge_gain=max(edge_gains) if edge_gains else 0,
        mean_edge_gain=mean(edge_gains) if edge_gains else float("-inf"),
        best_scc_edge_gain=max(scc_edge_gains) if scc_edge_gains else 0,
        best_density_len=best_density_len,
        best_density_log2=log2_density(best_density_count, best_density_len),
        best_source_len=best_source_len,
        best_source_fraction_by_len=best_source_fraction,
    )


def fmt(value: float) -> str:
    if value == float("inf"):
        return "inf"
    if value == float("-inf"):
        return "-inf"
    if abs(value) >= 1000.0 or (0.0 < abs(value) < 0.0001):
        return f"{value:.3e}"
    return f"{value:.6f}"


def print_rows(rows: list[GraphRow]) -> None:
    print("== seed-bearing closed-core graph ==")
    print("Nodes are H96 seed-record streams; edges are bounded H96 descriptions of nodes.")
    print(
        f"{'K':>2} {'D':>2} {'cap':>3} {'nodes':>8} {'edges':>8} "
        f"{'src':>6} {'tgt':>6} {'srcTax':>8} {'e/node':>8} {'scc':>5} "
        f"{'sccN':>5} {'big':>5} {'cmpE':>6} {'shortIn':>7} "
        f"{'shortF':>8} {'shortTax':>8} {'bestG':>6} {'meanG':>8} {'sccG':>6} {'densL':>5} "
        f"{'logDens':>9} {'srcL':>5} {'srcFrac':>8} {'dup':>5} {'cap?':>5}"
    )
    for row in rows:
        print(
            f"{row.max_arity:2d} {row.depth_bits:2d} {row.cap_bits:3d} "
            f"{row.node_count:8d} {row.edges:8d} {row.source_nodes:6d} "
            f"{row.target_nodes:6d} {fmt(row.source_mass_tax):>8} "
            f"{fmt(row.edge_density):>8} "
            f"{row.nontrivial_sccs:5d} {row.scc_nodes:5d} "
            f"{row.largest_scc:5d} {row.compressive_edges:6d} "
            f"{row.nodes_with_shorter_parent:7d} "
            f"{fmt(row.shorter_parent_fraction):>8} "
            f"{fmt(row.shorter_parent_mass_tax):>8} "
            f"{row.best_edge_gain:6d} "
            f"{fmt(row.mean_edge_gain):>8} {row.best_scc_edge_gain:6d} "
            f"{row.best_density_len:5d} {fmt(row.best_density_log2):>9} "
            f"{row.best_source_len:5d} {fmt(row.best_source_fraction_by_len):>8} "
            f"{row.duplicate_streams:5d} {str(row.capped):>5}"
        )
    print()


def print_reading(rows: list[GraphRow]) -> None:
    print("== reading ==")
    if not rows:
        print("No rows.")
        return
    best_core = max(rows, key=lambda row: (row.scc_nodes, row.source_nodes, row.edges))
    best_gain = max(rows, key=lambda row: row.best_edge_gain)
    print(
        f"Largest recurrent core row: K={best_core.max_arity},D={best_core.depth_bits},"
        f"cap={best_core.cap_bits}; scc_nodes={best_core.scc_nodes}, "
        f"largest_scc={best_core.largest_scc}, source_nodes={best_core.source_nodes}."
    )
    print(
        f"Best one-step edge gain: K={best_gain.max_arity},D={best_gain.depth_bits},"
        f"cap={best_gain.cap_bits}; gain={best_gain.best_edge_gain} bits "
        "(positive means the visible description is shorter than the target node)."
    )
    if best_core.scc_nodes == 0:
        print(
            "No finite recurrent seed-bearing core appeared in these exact rows. "
            "Edges exist only as one-way descriptions, so they do not maintain "
            "fresh recursive closure indefinitely."
        )
    else:
        print(
            "A finite recurrent core exists in at least one row, but any cycle "
            "inside a finite graph has zero total length drift by telescoping. "
            "It can contain compressive edges only if other edges pay them back."
        )
    if any(row.duplicate_streams for row in rows):
        print(
            "Duplicate visible streams occurred in the H96 surrogate. They are "
            "reported as syntax stress; production Lotus syntax would need its "
            "own exact parser audit."
        )


def parse_job(raw: str) -> tuple[int, int, int]:
    parts = raw.split(",")
    if len(parts) != 3:
        raise ValueError("--job must be K,D,cap")
    return tuple(int(part) for part in parts)  # type: ignore[return-value]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--job", action="append", default=[], help="K,D,cap")
    parser.add_argument("--seed", type=int, default=146146)
    parser.add_argument("--max-nodes", type=int, default=80_000)
    args = parser.parse_args()

    jobs = [parse_job(item) for item in args.job] if args.job else [
        (2, 2, 24),
        (3, 3, 21),
        (3, 3, 24),
        (4, 3, 24),
    ]
    rows = [
        row_for(max_arity, depth_bits, cap_bits, args.seed, args.max_nodes)
        for max_arity, depth_bits, cap_bits in jobs
    ]
    print_rows(rows)
    print_reading(rows)


if __name__ == "__main__":
    main()

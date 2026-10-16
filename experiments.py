from __future__ import annotations

import argparse
import csv
import os
import random
from statistics import mean

from puzzle.board import random_state, scramble
from puzzle.solvers import ALGORITHMS, astar_manhattan

DEPTHS = list(range(6, 27, 2))
OUT_DIR = "results"

SHORT = {
    "A* (манхеттенська відстань)": "A* h2",
    "A* (плитки не на місці)": "A* h1",
    "Жадібний (манхеттенська відстань)": "Greedy",
    "BFS (пошук у ширину)": "BFS",
}


def collect_instances(depths, per_depth, rng):
    buckets = {d: [] for d in depths}
    tries = 0
    while any(len(b) < per_depth for b in buckets.values()):
        tries += 1
        if tries > 500_000:
            raise RuntimeError("Не вдалося підібрати задачі - зменшіть --per-depth")
        need = [d for d in depths if len(buckets[d]) < per_depth]
        target = rng.choice(need)
        if target < 20:
            state = scramble(rng.randint(target, target * 3), rng)
        else:
            state = random_state(rng)
        depth = astar_manhattan(state).moves
        bucket = buckets.get(depth)
        if bucket is not None and len(bucket) < per_depth and state not in bucket:
            bucket.append(state)
    return buckets


def branching_factor(nodes, depth):
    if depth == 0:
        return float("nan")
    lo, hi = 1.0, 10.0
    for _ in range(60):
        b = (lo + hi) / 2
        total = sum(b ** i for i in range(depth + 1))
        if total < nodes + 1:
            lo = b
        else:
            hi = b
    return (lo + hi) / 2


def run(per_depth, seed):
    rng = random.Random(seed)
    print(f"Підбираю задачі: {len(DEPTHS)} глибин x {per_depth} шт...")
    buckets = collect_instances(DEPTHS, per_depth, rng)

    rows = []
    for depth in DEPTHS:
        for state in buckets[depth]:
            for name, solver in ALGORITHMS.items():
                r = solver(state)
                rows.append({
                    "depth": depth,
                    "algorithm": SHORT[name],
                    "state": "".join(map(str, state)),
                    "moves": r.moves,
                    "expanded": r.expanded,
                    "generated": r.generated,
                    "max_frontier": r.max_frontier,
                    "ms": round(r.seconds * 1000, 3),
                })
        print(f"  глибина {depth:2d}: готово")
    return rows


def summarize(rows):
    algs = list(SHORT.values())
    table = {}
    for depth in DEPTHS:
        for alg in algs:
            sel = [r for r in rows if r["depth"] == depth and r["algorithm"] == alg]
            table[depth, alg] = {
                "expanded": mean(r["expanded"] for r in sel),
                "ms": mean(r["ms"] for r in sel),
                "moves": mean(r["moves"] for r in sel),
                "frontier": mean(r["max_frontier"] for r in sel),
            }
    return algs, table


def fmt(x, digits=0):
    if digits == 0:
        return f"{x:,.0f}".replace(",", " ")
    return f"{x:.{digits}f}"


def write_summary(algs, table, per_depth, path):
    lines = [f"# Результати експериментів ({per_depth} задач на кожну глибину)", ""]

    lines += ["## Середня кількість розкритих вузлів", ""]
    lines += ["| d | " + " | ".join(algs) + " |", "|---" * (len(algs) + 1) + "|"]
    for d in DEPTHS:
        lines.append(f"| {d} | " + " | ".join(fmt(table[d, a]["expanded"]) for a in algs) + " |")

    lines += ["", "## Ефективний коефіцієнт розгалуження b*", ""]
    opt = ["BFS", "A* h1", "A* h2"]
    lines += ["| d | " + " | ".join(opt) + " |", "|---" * (len(opt) + 1) + "|"]
    for d in DEPTHS:
        lines.append(f"| {d} | " + " | ".join(
            fmt(branching_factor(table[d, a]["expanded"], d), 2) for a in opt) + " |")

    lines += ["", "## Середній час пошуку, мс", ""]
    lines += ["| d | " + " | ".join(algs) + " |", "|---" * (len(algs) + 1) + "|"]
    for d in DEPTHS:
        lines.append(f"| {d} | " + " | ".join(fmt(table[d, a]["ms"], 2) for a in algs) + " |")

    lines += ["", "## Довжина розв'язку жадібного пошуку (оптимум = d)", ""]
    lines += ["| d | Greedy | перевищення |", "|---|---|---|"]
    for d in DEPTHS:
        g = table[d, "Greedy"]["moves"]
        lines.append(f"| {d} | {fmt(g, 1)} | {fmt((g / d - 1) * 100, 0)}% |")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def plot(algs, table, path):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib не встановлено - графік пропущено (pip install matplotlib)")
        return

    colors = {"A* h2": "#2a78d6", "A* h1": "#eb6834", "Greedy": "#1baf7a", "BFS": "#c98500"}
    ink, muted, grid = "#2d2a32", "#6b6670", "#e4e1da"
    fig, ax = plt.subplots(figsize=(8, 4.6), dpi=200)
    for alg in algs:
        ys = [table[d, alg]["expanded"] for d in DEPTHS]
        ax.plot(DEPTHS, ys, color=colors[alg], linewidth=2, marker="o", markersize=5,
                markeredgecolor="white", markeredgewidth=1, label=alg)
        ax.annotate(alg, (DEPTHS[-1], ys[-1]), xytext=(8, 0), textcoords="offset points",
                    va="center", fontsize=9, color=ink)
    ax.set_yscale("log")
    ax.set_xlabel("Довжина оптимального розв'язку d, ходів", color=muted)
    ax.set_ylabel("Розкрито вузлів (лог. шкала)", color=muted)
    ax.set_xticks(DEPTHS)
    ax.set_xlim(DEPTHS[0] - 1, DEPTHS[-1] + 4)
    ax.grid(True, which="major", color=grid, linewidth=0.8)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(grid)
    ax.tick_params(colors=muted, labelsize=9)
    ax.legend(frameon=False, fontsize=9, loc="upper left", labelcolor=ink)
    ax.set_title("Скільки вузлів розкриває кожен алгоритм", loc="left", color=ink, fontsize=12)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description="Експерименти з алгоритмами для 8-puzzle")
    parser.add_argument("--per-depth", type=int, default=20)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    os.makedirs(OUT_DIR, exist_ok=True)
    rows = run(args.per_depth, args.seed)

    with open(os.path.join(OUT_DIR, "results.csv"), "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    algs, table = summarize(rows)
    write_summary(algs, table, args.per_depth, os.path.join(OUT_DIR, "summary.md"))
    plot(algs, table, os.path.join(OUT_DIR, "expanded_nodes.png"))

    print()
    print(f"{'d':>3} " + " ".join(f"{a:>10}" for a in algs))
    for d in DEPTHS:
        print(f"{d:>3} " + " ".join(f"{table[d, a]['expanded']:>10.0f}" for a in algs))
    print(f"\nГотово: {OUT_DIR}/summary.md, {OUT_DIR}/results.csv")


if __name__ == "__main__":
    main()

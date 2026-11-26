from __future__ import annotations

import heapq
import itertools
import time
from collections import deque
from dataclasses import dataclass, field

from .board import goal, is_solvable, neighbors, size_of
from .heuristics import manhattan, misplaced

# Скільки вузлів можна розкрити, поки пошук не здасться. Для 3x3 ліміт ніколи не
# досягається (усього 181 440 станів), а на 4x4 він не дає забрати всю пам'ять.
NODE_LIMIT = 500_000


class SearchLimitError(RuntimeError):
    pass


class SearchStopped(RuntimeError):
    pass


@dataclass
class SearchResult:
    algorithm: str
    path: list = field(default_factory=list)
    expanded: int = 0
    generated: int = 0
    max_frontier: int = 0
    seconds: float = 0.0

    @property
    def moves(self):
        return len(self.path) - 1


def _build_path(parent, state):
    path = []
    while state is not None:
        path.append(state)
        state = parent[state]
    path.reverse()
    return path


def _check(start):
    if not is_solvable(start):
        raise ValueError("Ця розстановка не має розв'язку")


def _guard(expanded, limit, stop):
    if expanded > limit:
        raise SearchLimitError(
            f"Пошук перевищив ліміт у {limit:,} розкритих вузлів".replace(",", " "))
    if stop is not None and expanded % 1000 == 0 and stop.is_set():
        raise SearchStopped("Пошук зупинено")


def bfs(start, limit=NODE_LIMIT, stop=None):
    _check(start)
    target = goal(size_of(start))
    t0 = time.perf_counter()
    parent = {start: None}
    queue = deque([start])
    expanded = 0
    max_frontier = 1
    goal_state = start if start == target else None

    while queue and goal_state is None:
        state = queue.popleft()
        expanded += 1
        _guard(expanded, limit, stop)
        for _, nxt in neighbors(state):
            if nxt in parent:
                continue
            parent[nxt] = state
            if nxt == target:
                goal_state = nxt
                break
            queue.append(nxt)
        max_frontier = max(max_frontier, len(queue))

    return SearchResult(
        algorithm="BFS (пошук у ширину)",
        path=_build_path(parent, goal_state),
        expanded=expanded,
        generated=len(parent),
        max_frontier=max_frontier,
        seconds=time.perf_counter() - t0,
    )


def best_first(start, h, g_weight=1, name="A*", limit=NODE_LIMIT, stop=None):
    _check(start)
    target = goal(size_of(start))
    t0 = time.perf_counter()
    counter = itertools.count()
    h0 = h(start)
    frontier = [(h0, h0, next(counter), start)]
    g = {start: 0}
    parent = {start: None}
    closed = set()
    expanded = 0
    max_frontier = 1
    found = None

    while frontier:
        _, _, _, state = heapq.heappop(frontier)
        if state in closed:
            continue
        if state == target:
            found = state
            break
        closed.add(state)
        expanded += 1
        _guard(expanded, limit, stop)
        for _, nxt in neighbors(state):
            new_g = g[state] + 1
            if nxt not in g or new_g < g[nxt]:
                g[nxt] = new_g
                parent[nxt] = state
                h_val = h(nxt)
                heapq.heappush(frontier, (g_weight * new_g + h_val, h_val, next(counter), nxt))
        max_frontier = max(max_frontier, len(frontier))

    return SearchResult(
        algorithm=name,
        path=_build_path(parent, found),
        expanded=expanded,
        generated=len(g),
        max_frontier=max_frontier,
        seconds=time.perf_counter() - t0,
    )


def astar_manhattan(start, limit=NODE_LIMIT, stop=None):
    return best_first(start, manhattan, 1, "A* (манхеттенська відстань)", limit, stop)


def astar_misplaced(start, limit=NODE_LIMIT, stop=None):
    return best_first(start, misplaced, 1, "A* (плитки не на місці)", limit, stop)


def greedy_manhattan(start, limit=NODE_LIMIT, stop=None):
    return best_first(start, manhattan, 0, "Жадібний (манхеттенська відстань)", limit, stop)


ALGORITHMS = {
    "A* (манхеттенська відстань)": astar_manhattan,
    "A* (плитки не на місці)": astar_misplaced,
    "Жадібний (манхеттенська відстань)": greedy_manhattan,
    "BFS (пошук у ширину)": bfs,
}


def solve(start, algorithm="A* (манхеттенська відстань)", limit=NODE_LIMIT, stop=None):
    return ALGORITHMS[algorithm](start, limit, stop)


def hint(state, limit=NODE_LIMIT, stop=None):
    result = astar_manhattan(state, limit, stop)
    return result.path[1] if result.moves > 0 else None

from __future__ import annotations

import heapq
import itertools
import time
from collections import deque
from dataclasses import dataclass, field

from .board import GOAL, is_solvable, neighbors
from .heuristics import manhattan, misplaced


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


def bfs(start):
    _check(start)
    t0 = time.perf_counter()
    parent = {start: None}
    queue = deque([start])
    expanded = 0
    max_frontier = 1
    goal_state = start if start == GOAL else None

    while queue and goal_state is None:
        state = queue.popleft()
        expanded += 1
        for _, nxt in neighbors(state):
            if nxt in parent:
                continue
            parent[nxt] = state
            if nxt == GOAL:
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


def best_first(start, h, g_weight=1, name="A*"):
    _check(start)
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
        if state == GOAL:
            found = state
            break
        closed.add(state)
        expanded += 1
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


def astar_manhattan(start):
    return best_first(start, manhattan, 1, "A* (манхеттенська відстань)")


def astar_misplaced(start):
    return best_first(start, misplaced, 1, "A* (плитки не на місці)")


def greedy_manhattan(start):
    return best_first(start, manhattan, 0, "Жадібний (манхеттенська відстань)")


ALGORITHMS = {
    "A* (манхеттенська відстань)": astar_manhattan,
    "A* (плитки не на місці)": astar_misplaced,
    "Жадібний (манхеттенська відстань)": greedy_manhattan,
    "BFS (пошук у ширину)": bfs,
}


def solve(start, algorithm="A* (манхеттенська відстань)"):
    return ALGORITHMS[algorithm](start)


def hint(state):
    result = astar_manhattan(state)
    return result.path[1] if result.moves > 0 else None

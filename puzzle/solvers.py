"""Алгоритми пошуку розв'язку для 8-puzzle."""
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
    path: list = field(default_factory=list)  # стани від початкового до цілі
    expanded: int = 0        # скільки вузлів розкрито (взято з черги)
    generated: int = 0       # скільки різних станів побачено
    max_frontier: int = 0    # найбільший розмір черги (пам'ять)
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
    """Пошук у ширину: неінформований, знаходить найкоротший розв'язок."""
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
        algorithm="BFS",
        path=_build_path(parent, goal_state),
        expanded=expanded,
        generated=len(parent),
        max_frontier=max_frontier,
        seconds=time.perf_counter() - t0,
    )


def best_first(start, h, g_weight=1, name="A*"):
    """Пошук «спочатку найкращий» з пріоритетом f(n) = g_weight * g(n) + h(n).

    g_weight = 1 -> A*: f = g + h, оптимальний при допустимій евристиці.
    g_weight = 0 -> жадібний пошук: f = h, швидкий, але не гарантує
                    найкоротшого розв'язку.
    """
    _check(start)
    t0 = time.perf_counter()
    counter = itertools.count()      # щоб heapq не порівнював самі стани
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
            continue                 # застарілий запис у черзі
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


# порядок - від найкращого для гри до найпростішого
ALGORITHMS = {
    "A* (манхеттенська відстань)": astar_manhattan,
    "A* (плитки не на місці)": astar_misplaced,
    "Жадібний (манхеттенська відстань)": greedy_manhattan,
    "BFS (пошук у ширину)": bfs,
}


def solve(start, algorithm="A* (манхеттенська відстань)"):
    return ALGORITHMS[algorithm](start)


def hint(state):
    """Наступний оптимальний хід (стан після нього) або None, якщо вже зібрано."""
    result = astar_manhattan(state)
    return result.path[1] if result.moves > 0 else None

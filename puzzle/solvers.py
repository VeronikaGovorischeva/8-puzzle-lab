"""Алгоритми пошуку розв'язку для 8-puzzle."""
from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field

from .board import GOAL, is_solvable, neighbors


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

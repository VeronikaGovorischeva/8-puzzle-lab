"""Евристики для інформованого пошуку.

Обидві евристики допустимі (ніколи не переоцінюють справжню кількість ходів)
і монотонні, тому A* з ними знаходить оптимальний розв'язок.
"""
from __future__ import annotations

from .board import GOAL, SIZE

GOAL_POS = {tile: divmod(i, SIZE) for i, tile in enumerate(GOAL)}

DIST = {}
for _tile, (_gr, _gc) in GOAL_POS.items():
    DIST[_tile] = [abs(i // SIZE - _gr) + abs(i % SIZE - _gc) for i in range(SIZE * SIZE)]


def misplaced(state):
    """h1: кількість плиток не на своєму місці (порожню не рахуємо)."""
    return sum(1 for i, tile in enumerate(state) if tile and tile != GOAL[i])


def manhattan(state):
    """h2: сума манхеттенських відстаней плиток до їхніх цільових позицій."""
    return sum(DIST[tile][i] for i, tile in enumerate(state) if tile)


def zero(state):
    """h = 0: з нею A* перетворюється на пошук за рівномірною ціною."""
    return 0

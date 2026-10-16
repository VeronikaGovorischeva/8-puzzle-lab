from __future__ import annotations

from .board import GOAL, SIZE

GOAL_POS = {tile: divmod(i, SIZE) for i, tile in enumerate(GOAL)}

DIST = {}
for _tile, (_gr, _gc) in GOAL_POS.items():
    DIST[_tile] = [abs(i // SIZE - _gr) + abs(i % SIZE - _gc) for i in range(SIZE * SIZE)]


def misplaced(state):
    return sum(1 for i, tile in enumerate(state) if tile and tile != GOAL[i])


def manhattan(state):
    return sum(DIST[tile][i] for i, tile in enumerate(state) if tile)


def zero(state):
    return 0

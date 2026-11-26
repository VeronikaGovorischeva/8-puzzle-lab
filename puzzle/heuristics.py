from __future__ import annotations

from functools import lru_cache

from .board import goal, size_of


@lru_cache(maxsize=None)
def _distances(size):
    target = goal(size)
    table = {}
    for g, tile in enumerate(target):
        gr, gc = divmod(g, size)
        table[tile] = tuple(abs(i // size - gr) + abs(i % size - gc) for i in range(size * size))
    return table


def misplaced(state):
    target = goal(size_of(state))
    return sum(1 for i, tile in enumerate(state) if tile and tile != target[i])


def manhattan(state):
    dist = _distances(size_of(state))
    return sum(dist[tile][i] for i, tile in enumerate(state) if tile)


def zero(state):
    return 0

from __future__ import annotations

import random
from functools import lru_cache
from math import isqrt

SIZES = (3, 4)
SIZE = 3

MOVES = {
    "U": (-1, 0),
    "D": (1, 0),
    "L": (0, -1),
    "R": (0, 1),
}


def goal(size=SIZE):
    return tuple(range(1, size * size)) + (0,)


GOAL = goal(3)


def size_of(state):
    return isqrt(len(state))


@lru_cache(maxsize=None)
def adjacency(size):
    result = []
    for i in range(size * size):
        r, c = divmod(i, size)
        near = []
        for name, (dr, dc) in MOVES.items():
            nr, nc = r + dr, c + dc
            if 0 <= nr < size and 0 <= nc < size:
                near.append((name, nr * size + nc))
        result.append(tuple(near))
    return tuple(result)


ADJACENT = adjacency(3)


def swap(state, i, j):
    s = list(state)
    s[i], s[j] = s[j], s[i]
    return tuple(s)


def neighbors(state):
    zero = state.index(0)
    return [(move, swap(state, zero, j)) for move, j in adjacency(size_of(state))[zero]]


def apply_move(state, move):
    zero = state.index(0)
    for name, j in adjacency(size_of(state))[zero]:
        if name == move:
            return swap(state, zero, j)
    return None


def move_tile(state, index):
    zero = state.index(0)
    for _, j in adjacency(size_of(state))[zero]:
        if j == index:
            return swap(state, zero, index)
    return None


def moved_tile(before, after):
    return after[before.index(0)]


def is_goal(state):
    return state == goal(size_of(state))


def inversions(state):
    tiles = [t for t in state if t != 0]
    count = 0
    for i in range(len(tiles)):
        for j in range(i + 1, len(tiles)):
            if tiles[i] > tiles[j]:
                count += 1
    return count


def blank_row_from_bottom(state):
    size = size_of(state)
    return size - state.index(0) // size


def is_solvable(state):
    # Непарна ширина (3x3): кожен хід зберігає парність інверсій.
    # Парна ширина (4x4): вертикальний хід міняє і парність інверсій, і рядок порожньої
    # клітинки, тому зберігається парність суми "інверсії + рядок порожньої знизу".
    # У цільовому стані інверсій 0, порожня в 1-му рядку знизу, сума непарна.
    if size_of(state) % 2 == 1:
        return inversions(state) % 2 == 0
    return (inversions(state) + blank_row_from_bottom(state)) % 2 == 1


def random_state(rng=None, size=SIZE):
    rng = rng or random
    target = goal(size)
    tiles = list(target)
    while True:
        rng.shuffle(tiles)
        state = tuple(tiles)
        if is_solvable(state) and state != target:
            return state


def scramble(steps, rng=None, size=SIZE):
    rng = rng or random
    state, prev = goal(size), None
    for _ in range(steps):
        options = [s for _, s in neighbors(state) if s != prev]
        prev, state = state, rng.choice(options)
    return state


def parse_state(text, size=SIZE):
    n = size * size
    cleaned = text.replace("_", "0").replace(",", " ").replace(";", " ")
    parts = cleaned.split()
    if len(parts) == 1 and size == 3:
        parts = list(parts[0])
    try:
        values = tuple(int(p) for p in parts)
    except ValueError:
        raise ValueError(f"Стан має містити лише числа 0-{n - 1}") from None
    if sorted(values) != list(range(n)):
        hint = "через пробіл, " if size > 3 else ""
        raise ValueError(f"Потрібно {n} різних чисел від 0 до {n - 1}, {hint}0 або _ - порожня клітинка")
    return values


def format_state(state):
    size = size_of(state)
    width = len(str(size * size - 1))
    rows = []
    for r in range(size):
        row = state[r * size:(r + 1) * size]
        rows.append(" ".join((str(t) if t else "_").rjust(width) for t in row))
    return "\n".join(rows)

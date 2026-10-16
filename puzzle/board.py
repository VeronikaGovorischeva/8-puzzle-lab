"""Логіка гри 8-puzzle (п'ятнашки 3x3).

Стан поля - кортеж із 9 чисел, записаних по рядках, 0 - порожня клітинка.
Цільовий стан:

    1 2 3
    4 5 6
    7 8 _
"""
from __future__ import annotations

import random

SIZE = 3
GOAL = (1, 2, 3, 4, 5, 6, 7, 8, 0)

MOVES = {
    "U": (-1, 0),
    "D": (1, 0),
    "L": (0, -1),
    "R": (0, 1),
}


def _build_adjacency():
    """Для кожної позиції 0..8 - список (хід, сусідня позиція)."""
    adjacency = []
    for i in range(SIZE * SIZE):
        r, c = divmod(i, SIZE)
        near = []
        for name, (dr, dc) in MOVES.items():
            nr, nc = r + dr, c + dc
            if 0 <= nr < SIZE and 0 <= nc < SIZE:
                near.append((name, nr * SIZE + nc))
        adjacency.append(near)
    return adjacency


ADJACENT = _build_adjacency()


def swap(state, i, j):
    s = list(state)
    s[i], s[j] = s[j], s[i]
    return tuple(s)


def neighbors(state):
    """Усі стани, у які можна перейти за один хід: список пар (хід, стан)."""
    zero = state.index(0)
    return [(move, swap(state, zero, j)) for move, j in ADJACENT[zero]]


def apply_move(state, move):
    """Виконує хід порожньої клітинки ('U', 'D', 'L', 'R') або повертає None."""
    zero = state.index(0)
    for name, j in ADJACENT[zero]:
        if name == move:
            return swap(state, zero, j)
    return None


def move_tile(state, index):
    """Пересуває плитку з позиції index у порожню клітинку, якщо вони сусідні."""
    zero = state.index(0)
    for _, j in ADJACENT[zero]:
        if j == index:
            return swap(state, zero, index)
    return None


def moved_tile(before, after):
    """Номер плитки, яку пересунули між двома сусідніми станами."""
    return after[before.index(0)]


def is_goal(state):
    return state == GOAL


def inversions(state):
    """Кількість пар плиток, що стоять у «неправильному» порядку."""
    tiles = [t for t in state if t != 0]
    count = 0
    for i in range(len(tiles)):
        for j in range(i + 1, len(tiles)):
            if tiles[i] > tiles[j]:
                count += 1
    return count


def is_solvable(state):
    """Для поля непарної ширини (3x3) хід не змінює парність кількості інверсій,
    тому стан розв'язний тоді й лише тоді, коли інверсій парна кількість
    (у цільовому стані їх 0)."""
    return inversions(state) % 2 == 0


def random_state(rng=None):
    """Випадкова розв'язна розстановка (рівномірно серед усіх 181 440)."""
    rng = rng or random
    tiles = list(GOAL)
    while True:
        rng.shuffle(tiles)
        state = tuple(tiles)
        if is_solvable(state) and state != GOAL:
            return state


def scramble(steps, rng=None):
    """Випадкове блукання від цілі на steps ходів (без повернення назад)."""
    rng = rng or random
    state, prev = GOAL, None
    for _ in range(steps):
        options = [s for _, s in neighbors(state) if s != prev]
        prev, state = state, rng.choice(options)
    return state


def parse_state(text):
    """Розбирає рядок на зразок '1 2 3 4 5 6 7 8 0', '12345678_' або '1,2,3,...'."""
    cleaned = text.replace("_", "0").replace(",", " ").replace(";", " ")
    parts = cleaned.split()
    if len(parts) == 1:
        parts = list(parts[0])
    try:
        values = tuple(int(p) for p in parts)
    except ValueError:
        raise ValueError("Стан має містити лише цифри 0-8") from None
    if sorted(values) != list(range(SIZE * SIZE)):
        raise ValueError("Потрібно 9 різних чисел від 0 до 8 (0 або _ - порожня клітинка)")
    return values


def format_state(state):
    rows = []
    for r in range(SIZE):
        row = state[r * SIZE:(r + 1) * SIZE]
        rows.append(" ".join(str(t) if t else "_" for t in row))
    return "\n".join(rows)

import random
import unittest

from puzzle.board import (
    GOAL, inversions, is_solvable, move_tile, moved_tile, neighbors,
    parse_state, random_state, scramble, swap,
)
from puzzle.heuristics import manhattan, misplaced
from puzzle.solvers import ALGORITHMS, astar_manhattan, bfs, greedy_manhattan, hint

HARDEST = (8, 6, 7, 2, 5, 4, 3, 0, 1)  # одна з найважчих розстановок, 31 хід


def is_valid_path(path):
    if not path or path[-1] != GOAL:
        return False
    for a, b in zip(path, path[1:]):
        if b not in [s for _, s in neighbors(a)]:
            return False
    return True


class BoardTest(unittest.TestCase):
    def test_neighbors_count(self):
        self.assertEqual(len(neighbors(GOAL)), 2)                         # кут
        self.assertEqual(len(neighbors((1, 2, 3, 4, 0, 5, 6, 7, 8))), 4)  # центр
        self.assertEqual(len(neighbors((1, 0, 2, 3, 4, 5, 6, 7, 8))), 3)  # край

    def test_solvability(self):
        self.assertTrue(is_solvable(GOAL))
        self.assertFalse(is_solvable(swap(GOAL, 0, 1)))  # обмін двох плиток
        self.assertEqual(inversions((2, 1, 3, 4, 5, 6, 7, 8, 0)), 1)

    def test_scramble_is_solvable(self):
        rng = random.Random(1)
        for _ in range(50):
            self.assertTrue(is_solvable(scramble(rng.randint(1, 60), rng)))

    def test_move_tile(self):
        self.assertEqual(move_tile(GOAL, 7), (1, 2, 3, 4, 5, 6, 7, 0, 8))
        self.assertIsNone(move_tile(GOAL, 0))  # плитка 1 не поруч з порожньою
        after = move_tile(GOAL, 5)
        self.assertEqual(moved_tile(GOAL, after), 6)

    def test_parse_state(self):
        self.assertEqual(parse_state("1 2 3 4 5 6 7 8 0"), GOAL)
        self.assertEqual(parse_state("12345678_"), GOAL)
        self.assertEqual(parse_state("1,2,3,4,5,6,7,8,0"), GOAL)
        with self.assertRaises(ValueError):
            parse_state("1 2 3")
        with self.assertRaises(ValueError):
            parse_state("1 1 2 3 4 5 6 7 8")


class HeuristicsTest(unittest.TestCase):
    def test_zero_at_goal(self):
        self.assertEqual(misplaced(GOAL), 0)
        self.assertEqual(manhattan(GOAL), 0)

    def test_known_values(self):
        state = (1, 2, 3, 4, 5, 6, 0, 7, 8)
        self.assertEqual(misplaced(state), 2)
        self.assertEqual(manhattan(state), 2)

    def test_manhattan_dominates_and_admissible(self):
        rng = random.Random(2)
        for _ in range(20):
            s = random_state(rng)
            optimal = astar_manhattan(s).moves
            self.assertLessEqual(misplaced(s), manhattan(s))
            self.assertLessEqual(manhattan(s), optimal)


class SolversTest(unittest.TestCase):
    def test_goal_needs_no_moves(self):
        for solver in ALGORITHMS.values():
            self.assertEqual(solver(GOAL).moves, 0)

    def test_paths_are_valid(self):
        rng = random.Random(3)
        for _ in range(10):
            s = random_state(rng)
            for solver in ALGORITHMS.values():
                result = solver(s)
                self.assertEqual(result.path[0], s)
                self.assertTrue(is_valid_path(result.path))

    def test_astar_is_optimal(self):
        rng = random.Random(4)
        for _ in range(15):
            s = random_state(rng)
            best = bfs(s).moves
            for name, solver in ALGORITHMS.items():
                if name.startswith("A*"):
                    self.assertEqual(solver(s).moves, best, name)
            self.assertGreaterEqual(greedy_manhattan(s).moves, best)

    def test_hardest_state(self):
        self.assertEqual(astar_manhattan(HARDEST).moves, 31)

    def test_unsolvable_raises(self):
        bad = swap(GOAL, 0, 1)
        for solver in ALGORITHMS.values():
            with self.assertRaises(ValueError):
                solver(bad)

    def test_hint(self):
        self.assertIsNone(hint(GOAL))
        state = (1, 2, 3, 4, 5, 6, 7, 0, 8)
        self.assertEqual(hint(state), GOAL)


if __name__ == "__main__":
    unittest.main()

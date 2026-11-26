import random
import threading
import unittest

from puzzle.board import (
    GOAL, apply_move, goal, inversions, is_solvable, move_tile, moved_tile, neighbors,
    parse_state, random_state, scramble, size_of, swap,
)
from puzzle.heuristics import manhattan, misplaced
from puzzle.solvers import (
    ALGORITHMS, WEIGHT, SearchLimitError, SearchStopped, astar_manhattan, astar_misplaced, bfs,
    greedy_manhattan, hint, weighted_astar_manhattan,
)

HARDEST = (8, 6, 7, 2, 5, 4, 3, 0, 1)
GOAL4 = goal(4)


def is_valid_path(path):
    if not path or path[-1] != goal(size_of(path[0])):
        return False
    for a, b in zip(path, path[1:]):
        if b not in [s for _, s in neighbors(a)]:
            return False
    return True


class BoardTest(unittest.TestCase):
    def test_neighbors_count(self):
        self.assertEqual(len(neighbors(GOAL)), 2)
        self.assertEqual(len(neighbors((1, 2, 3, 4, 0, 5, 6, 7, 8))), 4)
        self.assertEqual(len(neighbors((1, 0, 2, 3, 4, 5, 6, 7, 8))), 3)

    def test_solvability(self):
        self.assertTrue(is_solvable(GOAL))
        self.assertFalse(is_solvable(swap(GOAL, 0, 1)))
        self.assertEqual(inversions((2, 1, 3, 4, 5, 6, 7, 8, 0)), 1)

    def test_scramble_is_solvable(self):
        rng = random.Random(1)
        for _ in range(50):
            self.assertTrue(is_solvable(scramble(rng.randint(1, 60), rng)))

    def test_move_tile(self):
        self.assertEqual(move_tile(GOAL, 7), (1, 2, 3, 4, 5, 6, 7, 0, 8))
        self.assertIsNone(move_tile(GOAL, 0))
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
            weighted = weighted_astar_manhattan(s).moves
            self.assertGreaterEqual(weighted, best)
            self.assertLessEqual(weighted, WEIGHT * best)

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


class Board4x4Test(unittest.TestCase):
    def test_goal_and_neighbors(self):
        self.assertEqual(GOAL4, tuple(range(1, 16)) + (0,))
        self.assertEqual(len(neighbors(GOAL4)), 2)
        middle = swap(GOAL4, 15, 5)
        self.assertEqual(len(neighbors(middle)), 4)

    def test_solvability_rule(self):
        self.assertTrue(is_solvable(GOAL4))
        # вертикальний хід міняє парність інверсій, але розстановка лишається розв'язною
        up = apply_move(GOAL4, "U")
        self.assertEqual(inversions(up) % 2, 1)
        self.assertTrue(is_solvable(up))
        # обмін двох плиток робить розстановку нерозв'язною
        self.assertFalse(is_solvable(swap(GOAL4, 0, 1)))

    def test_parity_matches_reachability(self):
        rng = random.Random(5)
        for _ in range(100):
            s = scramble(rng.randint(1, 80), rng, size=4)
            self.assertTrue(is_solvable(s))
            i, j = rng.sample([k for k in range(16) if s[k]], 2)
            self.assertFalse(is_solvable(swap(s, i, j)))

    def test_random_state(self):
        rng = random.Random(6)
        for _ in range(30):
            s = random_state(rng, size=4)
            self.assertEqual(sorted(s), list(range(16)))
            self.assertTrue(is_solvable(s))

    def test_parse_state(self):
        text = "1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 0"
        self.assertEqual(parse_state(text, 4), GOAL4)
        self.assertEqual(parse_state(text.replace(" 0", " _"), 4), GOAL4)
        with self.assertRaises(ValueError):
            parse_state("1 2 3 4 5 6 7 8 0", 4)
        with self.assertRaises(ValueError):
            parse_state("123456789101112131415_", 4)

    def test_heuristics(self):
        self.assertEqual(manhattan(GOAL4), 0)
        self.assertEqual(misplaced(GOAL4), 0)
        state = apply_move(apply_move(GOAL4, "L"), "U")
        self.assertEqual(manhattan(state), 2)
        self.assertEqual(misplaced(state), 2)


class Solvers4x4Test(unittest.TestCase):
    def test_astar_optimal_and_paths_valid(self):
        rng = random.Random(7)
        for _ in range(8):
            s = scramble(rng.randint(10, 18), rng, size=4)
            best = astar_misplaced(s)
            h2 = astar_manhattan(s)
            greedy = greedy_manhattan(s)
            self.assertEqual(h2.moves, best.moves)
            self.assertLessEqual(manhattan(s), h2.moves)
            self.assertGreaterEqual(greedy.moves, best.moves)
            for r in (best, h2, greedy):
                self.assertEqual(r.path[0], s)
                self.assertTrue(is_valid_path(r.path))

    def test_bfs_small(self):
        s = scramble(8, random.Random(8), size=4)
        self.assertEqual(bfs(s).moves, astar_manhattan(s).moves)

    def test_harder_scramble(self):
        s = scramble(60, random.Random(7), size=4)
        result = astar_manhattan(s)
        self.assertEqual(result.moves, 34)
        self.assertTrue(is_valid_path(result.path))

    def test_hint(self):
        state = apply_move(GOAL4, "L")
        self.assertEqual(hint(state), GOAL4)

    def test_node_limit(self):
        s = scramble(60, random.Random(7), size=4)
        with self.assertRaises(SearchLimitError):
            bfs(s, limit=1000)

    def test_weighted_astar_solves_random(self):
        rng = random.Random(11)
        for _ in range(3):
            s = random_state(rng, size=4)
            result = weighted_astar_manhattan(s)
            self.assertEqual(result.path[0], s)
            self.assertTrue(is_valid_path(result.path))
            self.assertLessEqual(manhattan(s), result.moves)

    def test_weighted_astar_bound(self):
        rng = random.Random(12)
        for _ in range(8):
            s = scramble(rng.randint(10, 18), rng, size=4)
            best = astar_manhattan(s).moves
            self.assertLessEqual(weighted_astar_manhattan(s).moves, WEIGHT * best)

    def test_stop(self):
        s = scramble(60, random.Random(7), size=4)
        stop = threading.Event()
        stop.set()
        with self.assertRaises(SearchStopped):
            astar_misplaced(s, stop=stop)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import queue
import threading
import tkinter as tk
from tkinter import font as tkfont
from tkinter import messagebox, ttk

from .board import (
    GOAL, SIZE, apply_move, inversions, is_solvable, move_tile, moved_tile,
    parse_state, random_state, scramble,
)
from .solvers import ALGORITHMS, astar_manhattan

BG = "#f5f1e8"
TEXT = "#2d2a32"
MUTED = "#7a7480"
BOARD = "#2d2a32"
TILE = "#fbf8f1"
TILE_SHADOW = "#1c1a20"
TILE_OK = "#2a9d8f"
ACCENT = "#e76f51"
BUTTON = "#e9e3d5"

SHORT_NAMES = {
    "A* (манхеттенська відстань)": "A* + манхеттен",
    "A* (плитки не на місці)": "A* + не на місці",
    "Жадібний (манхеттенська відстань)": "Жадібний + манхеттен",
    "BFS (пошук у ширину)": "BFS",
}

DIFFICULTY = {
    "Легка": lambda: scramble(8),
    "Середня": lambda: scramble(20),
    "Складна": random_state,
}


def moves_text(n):
    if n % 10 == 1 and n % 100 != 11:
        return f"{n} хід"
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return f"{n} ходи"
    return f"{n} ходів"


def pick_font(root):
    families = set(tkfont.families(root))
    for name in ("Segoe UI", "Helvetica Neue", "Inter", "DejaVu Sans", "Arial"):
        if name in families:
            return name
    return "TkDefaultFont"


def rounded_rect(canvas, x1, y1, x2, y2, r, **kw):
    points = [
        x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r,
        x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2,
        x1, y2, x1, y2 - r, x1, y1 + r, x1, y1,
    ]
    return canvas.create_polygon(points, smooth=True, **kw)


class PuzzleApp:
    def __init__(self, root):
        self.root = root
        self.state = GOAL
        self.moves_made = 0
        self.animating = False
        self.busy = False
        self.stop_requested = False
        self.solution = []
        self.results = queue.Queue()

        self.k = max(1.0, root.winfo_fpixels("1i") / 96)
        self.tile = int(104 * self.k)
        self.gap = int(8 * self.k)
        self.pad = int(12 * self.k)
        self.board_px = 2 * self.pad + SIZE * self.tile + (SIZE - 1) * self.gap

        self.family = pick_font(root)
        self._setup_style()
        self._build_ui()
        self.draw_board()

    def _setup_style(self):
        self.root.configure(bg=BG)
        style = ttk.Style(self.root)
        style.theme_use("clam")
        f = self.family
        style.configure("TFrame", background=BG)
        style.configure("TLabel", background=BG, foreground=TEXT, font=(f, 10))
        style.configure("Title.TLabel", font=(f, 20, "bold"))
        style.configure("Sub.TLabel", foreground=MUTED, font=(f, 10))
        style.configure("Section.TLabel", font=(f, 11, "bold"))
        style.configure("Counter.TLabel", font=(f, 26, "bold"))
        style.configure("Status.TLabel", foreground=MUTED, font=(f, 10))
        style.configure(
            "TButton", font=(f, 10), padding=(12, 7), background=BUTTON,
            foreground=TEXT, borderwidth=0, focuscolor=BUTTON,
        )
        style.map("TButton", background=[("disabled", "#efebe2"), ("active", "#ddd5c3")],
                  foreground=[("disabled", "#b5afa6")])
        style.configure("TCombobox", padding=4)
        style.configure("Accent.TButton", background=ACCENT, foreground="white", font=(f, 10, "bold"))
        style.map("Accent.TButton", background=[("disabled", "#eebcae"), ("active", "#d65a3c")],
                  foreground=[("disabled", "white")])
        style.configure("Stat.TLabel", foreground=MUTED)
        style.configure("StatValue.TLabel", font=(f, 10, "bold"))
        style.configure("TScale", background=BG)

    def _build_ui(self):
        outer = ttk.Frame(self.root, padding=int(20 * self.k))
        outer.pack(fill="both", expand=True)

        ttk.Label(outer, text="П'ятнашки 3×3", style="Title.TLabel").grid(row=0, column=0, columnspan=2, sticky="w")
        ttk.Label(outer, text="Зберіть плитки по порядку: 1-8, порожня клітинка внизу праворуч",
                  style="Sub.TLabel").grid(row=1, column=0, columnspan=2, sticky="w", pady=(0, 14))

        self.canvas = tk.Canvas(outer, width=self.board_px, height=self.board_px,
                                bg=BG, highlightthickness=0)
        self.canvas.grid(row=2, column=0, sticky="n")
        self.canvas.bind("<Button-1>", self.on_click)
        self._build_custom_section(outer)

        self.panel = ttk.Frame(outer, padding=(int(20 * self.k), 0, 0, 0))
        self.panel.grid(row=2, column=1, rowspan=2, sticky="n")
        self._build_game_section(self.panel)
        self._build_ai_section(self.panel)
        self._build_stats_section(self.panel)

        self.status = ttk.Label(outer, text="Клікніть на плитку поруч із порожньою клітинкою або використовуйте стрілки",
                                style="Status.TLabel")
        self.status.grid(row=4, column=0, columnspan=2, sticky="w", pady=(14, 0))

        for key, move in (("<Up>", "D"), ("<Down>", "U"), ("<Left>", "R"), ("<Right>", "L")):
            self.root.bind(key, lambda e, m=move: self.on_key(m))

    def _build_game_section(self, parent):
        ttk.Label(parent, text="Гра", style="Section.TLabel").pack(anchor="w")
        row = ttk.Frame(parent)
        row.pack(anchor="w", fill="x", pady=(2, 8))
        ttk.Label(row, text="Ходів:").pack(side="left", anchor="s", pady=(0, 6))
        self.counter = ttk.Label(row, text="0", style="Counter.TLabel")
        self.counter.pack(side="left", padx=(8, 0))

        row = ttk.Frame(parent)
        row.pack(anchor="w", fill="x", pady=(0, 6))
        ttk.Label(row, text="Складність:").pack(side="left")
        self.difficulty = ttk.Combobox(row, values=list(DIFFICULTY), state="readonly", width=10)
        self.difficulty.set("Середня")
        self.difficulty.pack(side="left", padx=(8, 0))

        row = ttk.Frame(parent)
        row.pack(anchor="w", fill="x")
        self.btn_shuffle = ttk.Button(row, text="Перемішати", command=self.on_shuffle)
        self.btn_shuffle.pack(side="left")
        self.btn_reset = ttk.Button(row, text="Скинути", command=self.on_reset)
        self.btn_reset.pack(side="left", padx=(8, 0))

    def _build_custom_section(self, parent):
        box = ttk.Frame(parent)
        box.grid(row=3, column=0, sticky="nw", pady=(14, 0))
        ttk.Label(box, text="Своя розстановка (по рядках, 0 - порожня):", style="Stat.TLabel").pack(anchor="w")
        row = ttk.Frame(box)
        row.pack(anchor="w", pady=(4, 0))
        self.custom = ttk.Entry(row, width=22, font=(self.family, 11))
        self.custom.insert(0, "8 6 7 2 5 4 3 0 1")
        self.custom.pack(side="left", ipady=3)
        self.custom.bind("<Return>", lambda e: self.on_custom())
        self.btn_custom = ttk.Button(row, text="Задати", command=self.on_custom)
        self.btn_custom.pack(side="left", padx=(8, 0))

        legend = ttk.Frame(box)
        legend.pack(anchor="w", pady=(10, 0))
        sq = tk.Canvas(legend, width=14, height=14, bg=BG, highlightthickness=0)
        sq.create_rectangle(1, 1, 13, 13, fill=TILE_OK, outline="")
        sq.pack(side="left")
        ttk.Label(legend, text=" - плитка вже на своєму місці", style="Stat.TLabel").pack(side="left")

    def _build_ai_section(self, parent):
        ttk.Separator(parent).pack(fill="x", pady=14)
        ttk.Label(parent, text="Штучний інтелект", style="Section.TLabel").pack(anchor="w", pady=(0, 6))
        self.algorithm = ttk.Combobox(parent, values=list(ALGORITHMS), state="readonly", width=34)
        self.algorithm.set(next(iter(ALGORITHMS)))
        self.algorithm.pack(anchor="w", fill="x")

        row = ttk.Frame(parent)
        row.pack(anchor="w", fill="x", pady=(8, 0))
        self.btn_solve = ttk.Button(row, text="Розв'язати", style="Accent.TButton", command=self.on_solve)
        self.btn_solve.pack(side="left")
        self.btn_hint = ttk.Button(row, text="Підказка", command=self.on_hint)
        self.btn_hint.pack(side="left", padx=(8, 0))
        self.btn_stop = ttk.Button(row, text="Стоп", command=self.on_stop, state="disabled")
        self.btn_stop.pack(side="left", padx=(8, 0))

        row = ttk.Frame(parent)
        row.pack(anchor="w", fill="x", pady=(10, 0))
        ttk.Label(row, text="Швидкість:").pack(side="left")
        self.speed = tk.IntVar(value=5)
        ttk.Scale(row, from_=1, to=10, variable=self.speed, length=int(160 * self.k)).pack(side="left", padx=(8, 0))

    def _build_stats_section(self, parent):
        ttk.Separator(parent).pack(fill="x", pady=14)
        ttk.Label(parent, text="Статистика пошуку", style="Section.TLabel").pack(anchor="w", pady=(0, 4))
        grid = ttk.Frame(parent)
        grid.pack(anchor="w", fill="x")
        self.stats = {}
        rows = [
            ("algorithm", "Алгоритм"),
            ("moves", "Довжина розв'язку"),
            ("expanded", "Розкрито вузлів"),
            ("generated", "Згенеровано станів"),
            ("frontier", "Макс. розмір черги"),
            ("time", "Час пошуку"),
            ("optimal", "Гарантує оптимальність"),
        ]
        for r, (key, title) in enumerate(rows):
            ttk.Label(grid, text=title, style="Stat.TLabel").grid(row=r, column=0, sticky="w", pady=1)
            var = tk.StringVar(value="-")
            ttk.Label(grid, textvariable=var, style="StatValue.TLabel").grid(row=r, column=1, sticky="w", padx=(12, 0))
            self.stats[key] = var

    def cell_xy(self, index):
        r, c = divmod(index, SIZE)
        x = self.pad + c * (self.tile + self.gap)
        y = self.pad + r * (self.tile + self.gap)
        return x, y

    def draw_board(self):
        cv = self.canvas
        cv.delete("all")
        rounded_rect(cv, 0, 0, self.board_px, self.board_px, int(18 * self.k), fill=BOARD)
        for i, tile in enumerate(self.state):
            if tile:
                self.draw_tile(tile, i)

    def draw_tile(self, tile, index):
        cv = self.canvas
        x, y = self.cell_xy(index)
        t = self.tile
        tag = f"t{tile}"
        ok = GOAL[index] == tile
        s = int(4 * self.k)
        rounded_rect(cv, x, y + s, x + t, y + t + s, int(14 * self.k), fill=TILE_SHADOW, tags=(tag, "tile"))
        rounded_rect(cv, x, y, x + t, y + t, int(14 * self.k),
                     fill=TILE_OK if ok else TILE, tags=(tag, "tile", f"{tag}body"))
        cv.create_text(x + t / 2, y + t / 2, text=str(tile), font=(self.family, 30, "bold"),
                       fill="white" if ok else TEXT, tags=(tag, "tile", f"{tag}text"))

    def animate(self, tile, src, dst, duration, on_done=None):
        self.animating = True
        x1, y1 = self.cell_xy(src)
        x2, y2 = self.cell_xy(dst)
        steps = max(1, duration // 15)
        dx, dy = (x2 - x1) / steps, (y2 - y1) / steps
        tag = f"t{tile}"

        def step(i):
            if i < steps:
                self.canvas.move(tag, dx, dy)
                self.root.after(15, step, i + 1)
            else:
                self.canvas.delete(tag)
                self.draw_tile(tile, dst)
                self.animating = False
                if on_done:
                    on_done()

        step(0)

    def set_state(self, state):
        self.state = state
        self.moves_made = 0
        self.counter.configure(text="0")
        self.draw_board()

    def do_move(self, new_state, duration=120, on_done=None):
        tile = moved_tile(self.state, new_state)
        src = self.state.index(tile)
        dst = self.state.index(0)
        self.state = new_state
        self.moves_made += 1
        self.counter.configure(text=str(self.moves_made))
        self.animate(tile, src, dst, duration, on_done)

    def user_move(self, new_state):
        if new_state is None or self.animating or self.busy:
            return
        self.do_move(new_state, on_done=self.check_solved)

    def check_solved(self):
        if self.state == GOAL and self.moves_made:
            self.set_status(f"Зібрано за {moves_text(self.moves_made)}!")

    def set_status(self, text):
        self.status.configure(text=text)

    def on_click(self, event):
        for i in range(SIZE * SIZE):
            x, y = self.cell_xy(i)
            if x <= event.x <= x + self.tile and y <= event.y <= y + self.tile:
                self.user_move(move_tile(self.state, i))
                return

    def on_key(self, move):
        self.user_move(apply_move(self.state, move))

    def on_shuffle(self):
        if self.animating or self.busy:
            return
        state = GOAL
        while state == GOAL:
            state = DIFFICULTY[self.difficulty.get()]()
        self.set_state(state)
        self.set_status("Поле перемішано. Удачі!")

    def on_reset(self):
        if self.animating or self.busy:
            return
        self.set_state(GOAL)
        self.set_status("Поле скинуто до цільового стану")


    def on_custom(self):
        if self.animating or self.busy:
            return
        try:
            state = parse_state(self.custom.get())
        except ValueError as e:
            messagebox.showerror("Неправильний формат", str(e))
            return
        if not is_solvable(state):
            messagebox.showwarning(
                "Немає розв'язку",
                f"Кількість інверсій: {inversions(state)} - непарна.\n\n"
                "Кожен хід зберігає парність інверсій, а в цільовому стані їх 0, "
                "тому таку розстановку неможливо зібрати.",
            )
            return
        self.set_state(state)
        self.set_status(f"Задано розстановку, інверсій: {inversions(state)} (парна) - розв'язок існує")

    def on_hint(self):
        if self.animating or self.busy:
            return
        if self.state == GOAL:
            self.set_status("Поле вже зібране")
            return
        result = astar_manhattan(self.state)
        tile = moved_tile(self.state, result.path[1])
        self.canvas.itemconfigure(f"t{tile}body", outline=ACCENT, width=int(4 * self.k))
        self.root.after(1500, lambda: self.canvas.itemconfigure(f"t{tile}body", outline="", width=1))
        self.set_status(f"Підказка: пересуньте плитку {tile} (оптимальний розв'язок - {moves_text(result.moves)})")

    def set_busy(self, busy):
        self.busy = busy
        normal = "disabled" if busy else "normal"
        for btn in (self.btn_shuffle, self.btn_reset, self.btn_solve, self.btn_hint, self.btn_custom):
            btn.configure(state=normal)
        self.algorithm.configure(state="disabled" if busy else "readonly")
        self.difficulty.configure(state="disabled" if busy else "readonly")
        self.btn_stop.configure(state="normal" if busy else "disabled")

    def on_solve(self):
        if self.busy or self.animating:
            return
        if self.state == GOAL:
            self.set_status("Поле вже зібране - перемішайте його")
            return
        name = self.algorithm.get()
        self.set_busy(True)
        self.stop_requested = False
        self.set_status(f"ШІ шукає розв'язок: {name}...")
        threading.Thread(target=self._solver_worker, args=(self.state, name), daemon=True).start()
        self.root.after(50, self._poll_solver)

    def _solver_worker(self, state, name):
        try:
            self.results.put(ALGORITHMS[name](state))
        except Exception as e:
            self.results.put(e)

    def _poll_solver(self):
        try:
            result = self.results.get_nowait()
        except queue.Empty:
            self.root.after(50, self._poll_solver)
            return
        if isinstance(result, Exception):
            self.set_busy(False)
            self.set_status(f"Помилка: {result}")
            return
        self.show_stats(result)
        if self.stop_requested:
            self.set_busy(False)
            self.set_status("Пошук зупинено")
            return
        self.solution = result.path[1:]
        self.moves_made = 0
        self.counter.configure(text="0")
        self.set_status(f"Знайдено розв'язок за {moves_text(result.moves)}, показую...")
        self.play_next()

    def show_stats(self, result):
        self.stats["algorithm"].set(SHORT_NAMES.get(result.algorithm, result.algorithm))
        self.stats["moves"].set(moves_text(result.moves))
        self.stats["expanded"].set(f"{result.expanded:,}".replace(",", " "))
        self.stats["generated"].set(f"{result.generated:,}".replace(",", " "))
        self.stats["frontier"].set(f"{result.max_frontier:,}".replace(",", " "))
        self.stats["time"].set(f"{result.seconds * 1000:.1f} мс")
        self.stats["optimal"].set("ні" if result.algorithm.startswith("Жадібний") else "так")

    def play_next(self):
        if self.stop_requested or not self.solution:
            self.set_busy(False)
            if self.state == GOAL:
                self.set_status(f"ШІ зібрав поле за {moves_text(self.moves_made)}")
            else:
                self.set_status("Показ зупинено - можна продовжити вручну")
            return
        speed = self.speed.get()
        duration = 330 - 28 * speed
        pause = 300 - 28 * speed
        nxt = self.solution.pop(0)
        self.do_move(nxt, duration, on_done=lambda: self.root.after(pause, self.play_next))

    def on_stop(self):
        self.stop_requested = True


def enable_dpi_awareness():
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass


def run():
    enable_dpi_awareness()
    root = tk.Tk()
    root.title("П'ятнашки 3×3 - ШІ-розв'язувач")
    root.resizable(False, False)
    PuzzleApp(root)
    root.mainloop()

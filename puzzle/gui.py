"""Графічний інтерфейс гри на Tkinter."""
from __future__ import annotations

import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk

from .board import GOAL, SIZE, apply_move, move_tile, moved_tile, random_state, scramble

# --- кольори ---
BG = "#f5f1e8"
TEXT = "#2d2a32"
MUTED = "#7a7480"
BOARD = "#2d2a32"
TILE = "#fbf8f1"
TILE_SHADOW = "#1c1a20"
TILE_OK = "#2a9d8f"      # плитка на своєму місці
ACCENT = "#e76f51"
BUTTON = "#e9e3d5"

DIFFICULTY = {
    "Легка": lambda: scramble(8),
    "Середня": lambda: scramble(20),
    "Складна": random_state,
}


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

        # масштаб для екранів з високою роздільною здатністю
        self.k = max(1.0, root.winfo_fpixels("1i") / 96)
        self.tile = int(104 * self.k)
        self.gap = int(8 * self.k)
        self.pad = int(12 * self.k)
        self.board_px = 2 * self.pad + SIZE * self.tile + (SIZE - 1) * self.gap

        self.family = pick_font(root)
        self._setup_style()
        self._build_ui()
        self.draw_board()

    # ---------- інтерфейс ----------
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

        self.panel = ttk.Frame(outer, padding=(int(20 * self.k), 0, 0, 0))
        self.panel.grid(row=2, column=1, sticky="ns")
        self._build_game_section(self.panel)

        self.status = ttk.Label(outer, text="Клікніть на плитку поруч із порожньою клітинкою або використовуйте стрілки",
                                style="Status.TLabel")
        self.status.grid(row=3, column=0, columnspan=2, sticky="w", pady=(14, 0))

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

    # ---------- малювання ----------
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

    def recolor(self, tile):
        ok = GOAL[self.state.index(tile)] == tile
        self.canvas.itemconfigure(f"t{tile}body", fill=TILE_OK if ok else TILE)
        self.canvas.itemconfigure(f"t{tile}text", fill="white" if ok else TEXT)

    def animate(self, tile, src, dst, duration, on_done=None):
        """Плавно пересуває плитку з клітинки src у клітинку dst."""
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
                # прибираємо накопичену похибку округлення
                self.canvas.delete(tag)
                self.draw_tile(tile, dst)
                self.animating = False
                if on_done:
                    on_done()

        step(0)

    # ---------- логіка ----------
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
        if new_state is None or self.animating:
            return
        self.do_move(new_state, on_done=self.check_solved)

    def check_solved(self):
        if self.state == GOAL and self.moves_made:
            self.set_status(f"Зібрано за {self.moves_made} ходів!")

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
        if self.animating:
            return
        state = GOAL
        while state == GOAL:
            state = DIFFICULTY[self.difficulty.get()]()
        self.set_state(state)
        self.set_status("Поле перемішано. Удачі!")

    def on_reset(self):
        if self.animating:
            return
        self.set_state(GOAL)
        self.set_status("Поле скинуто до цільового стану")


def enable_dpi_awareness():
    """На Windows без цього вікно розмите на екранах з масштабуванням."""
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

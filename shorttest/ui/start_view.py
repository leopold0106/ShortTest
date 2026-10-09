"""시작 화면: 시험 시작 / 설정 / 최근 파일 / 도움말."""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import ttk
from typing import TYPE_CHECKING

from shorttest import APP_NAME, __version__
from shorttest.ui import theme as T
from shorttest.ui.dialogs import HelpWindow, save_template

if TYPE_CHECKING:
    from shorttest.ui.app import App


class StartView(tk.Frame):
    def __init__(self, parent: tk.Misc, app: "App"):
        super().__init__(parent, bg=T.BG, padx=40, pady=32)
        self.app = app
        f = app.fonts

        # 머리
        head = tk.Frame(self, bg=T.BG)
        head.pack(fill="x", pady=(0, 20))
        badge = tk.Label(head, text="✓", bg=T.ACCENT, fg="#FFFFFF", font=f.heading, width=3, height=1)
        badge.pack(side="left", padx=(0, 12), ipady=4)
        titles = tk.Frame(head, bg=T.BG)
        titles.pack(side="left")
        T.label(titles, APP_NAME, font=f.title).pack(anchor="w")
        T.label(titles, "문제지와 정답지를 열고 문제를 풀면 자동으로 채점합니다.", fg=T.MUTED).pack(anchor="w")

        grid = tk.Frame(self, bg=T.BG)
        grid.pack(fill="both", expand=True)
        grid.columnconfigure((0, 1), weight=1, uniform="col")
        grid.rowconfigure(1, weight=1)

        # 왼쪽 위: 시험 시작
        start = T.card(grid, padx=22, pady=20)
        start.outer.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=(0, 16))
        T.label(start, "시험 시작", font=f.heading).pack(anchor="w", pady=(0, 10))
        ttk.Button(start, text="문제지 열기…", style="Primary.TButton", command=app.open_dialog).pack(fill="x", ipady=4)
        hint = tk.Frame(start, bg=T.CARD)
        hint.pack(anchor="w", pady=(8, 0))
        T.label(hint, "같은 폴더의 ", fg=T.MUTED, font=f.small).pack(side="left")
        tk.Label(hint, text="이름.answers.txt", font=f.mono, bg=T.BG, fg=T.TEXT, padx=5).pack(side="left")
        T.label(hint, " 정답지를 자동으로 찾습니다.", fg=T.MUTED, font=f.small).pack(side="left")

        # 왼쪽 아래: 설정
        settings = T.card(grid, padx=22, pady=20)
        settings.outer.grid(row=1, column=0, sticky="nsew", padx=(0, 10))
        T.label(settings, "설정", font=f.heading).pack(anchor="w", pady=(0, 8))
        self.var_ignore_spaces = tk.BooleanVar(value=app.settings.ignore_inner_spaces)
        self.var_always_checkbox = tk.BooleanVar(value=app.settings.always_checkbox)
        self._setting(settings, "단답형 채점 시 띄어쓰기 무시", "'엽록 체'와 '엽록체'를 같은 답으로 봅니다", self.var_ignore_spaces)
        self._setting(settings, "객관식은 항상 체크 상자로 표시", "복수 정답 여부를 응시자에게 숨깁니다", self.var_always_checkbox)

        # 오른쪽 위: 최근 파일
        recent = T.card(grid, padx=22, pady=20)
        recent.outer.grid(row=0, column=1, rowspan=2, sticky="nsew", padx=(10, 0))
        recent.rowconfigure(1, weight=1)
        recent.columnconfigure(0, weight=1)
        rhead = tk.Frame(recent, bg=T.CARD)
        rhead.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        T.label(rhead, "최근 파일", font=f.heading).pack(side="left")
        T.label(rhead, "더블클릭하면 엽니다", fg=T.MUTED, font=f.small).pack(side="right")
        self.recent_list = tk.Frame(recent, bg=T.CARD)
        self.recent_list.grid(row=1, column=0, sticky="nsew")
        self.recent_hint = T.label(recent, "", fg=T.MUTED, font=f.small)
        self.recent_hint.grid(row=2, column=0, sticky="ew")

        # 오른쪽 아래: 처음 만드시나요
        helpcard = T.card(grid, padx=22, pady=16)
        helpcard.outer.grid(row=2, column=1, sticky="nsew", padx=(10, 0), pady=(16, 0))
        T.label(helpcard, "처음 만드시나요?", font=f.bold).pack(anchor="w")
        T.label(helpcard, "빈 문제지·정답지 한 쌍을 만들어 메모장으로 고치세요.", fg=T.MUTED, font=f.small).pack(anchor="w", pady=(0, 8))
        btns = tk.Frame(helpcard, bg=T.CARD)
        btns.pack(anchor="w")
        ttk.Button(btns, text="작성법 (F1)", style="Secondary.TButton", command=lambda: HelpWindow.show(self)).pack(side="left")
        ttk.Button(btns, text="템플릿 만들기…", style="Outline.TButton", command=lambda: save_template(self)).pack(side="left", padx=(8, 0))

        T.label(self, f"버전 {__version__}", fg=T.FAINT, font=f.small, anchor="e").pack(fill="x", pady=(12, 0))
        self.refresh()

    def _setting(self, parent: tk.Misc, title: str, desc: str, var: tk.BooleanVar) -> None:
        row = tk.Frame(parent, bg=T.CARD)
        row.pack(fill="x", pady=(0, 6))
        ttk.Checkbutton(row, text=title, variable=var, command=self._apply_settings).pack(anchor="w")
        T.label(row, desc, fg=T.MUTED, font=self.app.fonts.small).pack(anchor="w", padx=(24, 0))

    def refresh(self) -> None:
        for child in self.recent_list.winfo_children():
            child.destroy()
        existing = [p for p in self.app.settings.recent_files if Path(p).exists()]
        self.app.settings.recent_files = existing
        for p in existing:
            self._recent_row(Path(p))
        self.recent_hint.configure(text="" if existing else "아직 연 파일이 없습니다.")

    def _recent_row(self, path: Path) -> None:
        f = self.app.fonts
        outer = tk.Frame(self.recent_list, bg=T.BORDER)
        outer.pack(fill="x", pady=(0, 6))
        row = tk.Frame(outer, bg=T.CARD, padx=12, pady=8, cursor="hand2")
        row.pack(fill="x", padx=1, pady=1)
        icon = tk.Label(row, text="▤", fg=T.ACCENT, bg=T.CARD, font=f.heading)
        icon.pack(side="left", padx=(0, 10))
        col = tk.Frame(row, bg=T.CARD)
        col.pack(side="left", fill="x", expand=True)
        name = T.label(col, path.name, font=f.bold)
        name.pack(anchor="w")
        folder = T.label(col, str(path.parent), fg=T.MUTED, font=f.small)
        folder.pack(anchor="w")
        widgets = (row, icon, col, name, folder)
        for w in widgets:
            w.bind("<Double-Button-1>", lambda _e, p=path: self.app.open_exam(p))
            w.bind("<Enter>", lambda _e, ws=widgets: [x.configure(bg=T.BG) for x in ws])
            w.bind("<Leave>", lambda _e, ws=widgets: [x.configure(bg=T.CARD) for x in ws])

    def _apply_settings(self) -> None:
        self.app.settings.ignore_inner_spaces = self.var_ignore_spaces.get()
        self.app.settings.always_checkbox = self.var_always_checkbox.get()
        self.app.settings.save()

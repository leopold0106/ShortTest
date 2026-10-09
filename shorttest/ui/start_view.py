"""시작 화면: 문제지 열기, 최근 파일, 설정."""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import ttk
from typing import TYPE_CHECKING

from shorttest import APP_NAME, __version__
from shorttest.ui.dialogs import HelpWindow, save_template

if TYPE_CHECKING:
    from shorttest.ui.app import App


class StartView(ttk.Frame):
    def __init__(self, parent: tk.Misc, app: "App"):
        super().__init__(parent, padding=24)
        self.app = app

        ttk.Label(self, text=APP_NAME, font=app.font_title).pack(anchor="w")
        ttk.Label(self, text="문제지와 정답지를 열고 문제를 풀면 자동으로 채점합니다.").pack(anchor="w", pady=(2, 18))

        ttk.Button(self, text="문제지 열기...", command=app.open_dialog, style="Big.TButton").pack(anchor="w")
        ttk.Label(self, text="같은 폴더의  이름.answers.txt  정답지를 자동으로 찾습니다.", foreground="#666").pack(anchor="w", pady=(4, 18))

        ttk.Label(self, text="최근 파일", font=app.font_heading).pack(anchor="w")
        self.recent_box = tk.Listbox(self, height=5, activestyle="none")
        self.recent_box.pack(fill="x", pady=(4, 2))
        self.recent_box.bind("<Double-Button-1>", self._open_selected)
        self.recent_box.bind("<Return>", self._open_selected)
        self.recent_hint = ttk.Label(self, text="", foreground="#666")
        self.recent_hint.pack(anchor="w", pady=(0, 18))

        ttk.Label(self, text="설정", font=app.font_heading).pack(anchor="w")
        self.var_ignore_spaces = tk.BooleanVar(value=app.settings.ignore_inner_spaces)
        self.var_always_checkbox = tk.BooleanVar(value=app.settings.always_checkbox)
        ttk.Checkbutton(
            self, text="단답형 채점 시 띄어쓰기 무시 (예: '엽록 체' = '엽록체')",
            variable=self.var_ignore_spaces, command=self._apply_settings,
        ).pack(anchor="w", pady=(4, 0))
        ttk.Checkbutton(
            self, text="객관식은 항상 체크 상자로 표시 (복수 정답 여부를 숨김)",
            variable=self.var_always_checkbox, command=self._apply_settings,
        ).pack(anchor="w", pady=(2, 18))

        links = ttk.Frame(self)
        links.pack(anchor="w")
        ttk.Button(links, text="문제지·정답지 작성법", command=lambda: HelpWindow.show(self)).pack(side="left")
        ttk.Button(links, text="템플릿 파일 만들기...", command=lambda: save_template(self)).pack(side="left", padx=(8, 0))

        ttk.Label(self, text=f"버전 {__version__}", foreground="#999").pack(side="bottom", anchor="e")
        self.refresh()

    def refresh(self) -> None:
        self.recent_box.delete(0, "end")
        existing = [p for p in self.app.settings.recent_files if Path(p).exists()]
        self.app.settings.recent_files = existing
        for p in existing:
            self.recent_box.insert("end", p)
        self.recent_hint.configure(text="더블클릭하면 엽니다." if existing else "아직 연 파일이 없습니다.")

    def _open_selected(self, _event=None) -> None:
        selection = self.recent_box.curselection()
        if selection:
            self.app.open_exam(Path(self.recent_box.get(selection[0])))

    def _apply_settings(self) -> None:
        self.app.settings.ignore_inner_spaces = self.var_ignore_spaces.get()
        self.app.settings.always_checkbox = self.var_always_checkbox.get()
        self.app.settings.save()

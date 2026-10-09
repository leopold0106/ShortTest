"""결과 화면: 점수 카드 3개 + 문항 표 + 버튼."""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import TYPE_CHECKING

from shorttest.core.markup import strip_markup
from shorttest.core.model import QuestionResult, Result
from shorttest.core.report import default_result_filename, format_answer, format_response, format_result
from shorttest.ui import theme as T

if TYPE_CHECKING:
    from shorttest.ui.app import App

RETRY_SUFFIX = " (오답 다시 풀기)"


class ResultView(tk.Frame):
    def __init__(self, parent: tk.Misc, app: "App"):
        super().__init__(parent, bg=T.BG)
        self.app = app
        self.result: Result | None = None
        f = app.fonts

        content = tk.Frame(self, bg=T.BG, padx=24, pady=20)
        content.pack(fill="both", expand=True)

        stats = tk.Frame(content, bg=T.BG)
        stats.pack(fill="x", pady=(0, 16))
        stats.columnconfigure((0, 1, 2), weight=1, uniform="stat")

        score = tk.Frame(stats, bg=T.ACCENT, padx=22, pady=16)
        score.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        T.label(score, "총점", fg="#D6ECE9", bg=T.ACCENT, font=f.small).pack(anchor="w")
        srow = tk.Frame(score, bg=T.ACCENT)
        srow.pack(anchor="w")
        self.score_big = T.label(srow, "", fg="#FFFFFF", bg=T.ACCENT, font=f.hero)
        self.score_big.pack(side="left")
        self.score_total = T.label(srow, "", fg="#D6ECE9", bg=T.ACCENT, font=f.heading)
        self.score_total.pack(side="left", anchor="s", padx=(6, 0), pady=(0, 6))
        self.score_title = T.label(score, "", fg="#D6ECE9", bg=T.ACCENT, font=f.small)
        self.score_title.pack(anchor="w")

        pct = T.card(stats, padx=22, pady=16)
        pct.outer.grid(row=0, column=1, sticky="nsew", padx=8)
        T.label(pct, "득점률", fg=T.MUTED, font=f.small).pack(anchor="w")
        self.pct_big = T.label(pct, "", font=f.hero)
        self.pct_big.pack(anchor="w")
        self.pct_bar = ttk.Progressbar(pct, style="Teal.Horizontal.TProgressbar", maximum=100, value=0)
        self.pct_bar.pack(fill="x", pady=(6, 0))

        cnt = T.card(stats, padx=22, pady=16)
        cnt.outer.grid(row=0, column=2, sticky="nsew", padx=(8, 0))
        T.label(cnt, "정답 문항", fg=T.MUTED, font=f.small).pack(anchor="w")
        crow = tk.Frame(cnt, bg=T.CARD)
        crow.pack(anchor="w")
        self.cnt_big = T.label(crow, "", font=f.hero)
        self.cnt_big.pack(side="left")
        self.cnt_total = T.label(crow, "", fg=T.MUTED, font=f.heading)
        self.cnt_total.pack(side="left", anchor="s", padx=(6, 0), pady=(0, 6))
        brk = tk.Frame(cnt, bg=T.CARD)
        brk.pack(anchor="w")
        self.cnt_ok = T.label(brk, "", fg=T.OK_FG, font=f.small_bold)
        self.cnt_ok.pack(side="left", padx=(0, 10))
        self.cnt_bad = T.label(brk, "", fg=T.BAD_FG, font=f.small_bold)
        self.cnt_bad.pack(side="left", padx=(0, 10))
        self.cnt_blank = T.label(brk, "", fg=T.MUTED, font=f.small_bold)
        self.cnt_blank.pack(side="left")

        table_card = T.card(content)
        table_card.outer.pack(fill="both", expand=True)
        cols = ("no", "type", "user", "key", "ok", "score")
        self.tree = ttk.Treeview(table_card, columns=cols, show="headings", selectmode="browse")
        for col, text, width, anchor, stretch in (
            ("no", "번호", 60, "center", False),
            ("type", "유형", 70, "center", False),
            ("user", "내 답", 220, "w", True),
            ("key", "정답", 220, "w", True),
            ("ok", "결과", 60, "center", False),
            ("score", "점수", 80, "center", False),
        ):
            self.tree.heading(col, text=text)
            self.tree.column(col, width=width, anchor=anchor, stretch=stretch)
        scroll = ttk.Scrollbar(table_card, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side="left", fill="both", expand=True, padx=(1, 0), pady=1)
        scroll.pack(side="left", fill="y")
        self.tree.tag_configure("wrong", background=T.BAD_BG, foreground=T.TEXT)
        self.tree.tag_configure("right", background=T.CARD, foreground=T.TEXT)
        self.tree.bind("<Double-Button-1>", self._show_detail)
        self.tree.bind("<Return>", self._show_detail)
        T.label(content, "행을 더블클릭하면 문제와 보기를 다시 볼 수 있습니다.", fg=T.FAINT, font=f.small).pack(anchor="w", pady=(6, 0))

        tk.Frame(self, bg=T.BORDER, height=1).pack(fill="x")
        bottom = tk.Frame(self, bg=T.CARD, padx=24, pady=10)
        bottom.pack(fill="x")
        ttk.Button(bottom, text="⌂  홈", style="Ghost.TButton", command=app.go_home).pack(side="left")
        ttk.Button(bottom, text="다시 풀기", style="Secondary.TButton", command=self._retry_all).pack(side="left", padx=(8, 0))
        self.retry_wrong_button = ttk.Button(bottom, text="틀린 문제만 다시", style="Outline.TButton", command=self._retry_wrong)
        self.retry_wrong_button.pack(side="left", padx=(8, 0))
        ttk.Button(bottom, text="결과 저장…", style="Primary.TButton", command=self._save).pack(side="right")

    def load(self, result: Result) -> None:
        self.result = result
        self.score_big.configure(text=str(result.earned))
        self.score_total.configure(text=f"/ {result.total}")
        self.score_title.configure(text=result.exam.title)
        self.pct_big.configure(text=f"{result.percent:.0f}%")
        self.pct_bar.configure(value=result.percent)
        blank = sum(1 for i in result.items if not i.answered)
        wrong = len(result.items) - result.correct_count - blank
        self.cnt_big.configure(text=str(result.correct_count))
        self.cnt_total.configure(text=f"/ {len(result.items)}")
        self.cnt_ok.configure(text=f"정답 {result.correct_count}")
        self.cnt_bad.configure(text=f"오답 {wrong}")
        self.cnt_blank.configure(text=f"미응답 {blank}")

        self.tree.delete(*self.tree.get_children())
        for item in result.items:
            q = item.question
            self.tree.insert(
                "", "end", iid=str(q.number),
                values=(q.number, q.type_label, format_response(item.user_answer), strip_markup(format_answer(item.correct_answer)),
                        "O" if item.correct else "X", f"{item.earned} / {q.points}"),
                tags=("right" if item.correct else "wrong",),
            )
        n_wrong = len(result.wrong_numbers)
        self.retry_wrong_button.configure(text=f"틀린 문제만 다시 ({n_wrong})" if n_wrong else "틀린 문제만 다시")
        self.retry_wrong_button.state(["!disabled"] if n_wrong else ["disabled"])

    def _item_for(self, iid: str) -> QuestionResult | None:
        assert self.result is not None
        number = int(iid)
        return next((i for i in self.result.items if i.question.number == number), None)

    def _show_detail(self, _event=None) -> None:
        selection = self.tree.selection()
        if not selection:
            return
        item = self._item_for(selection[0])
        if item is None:
            return
        q = item.question
        f = self.app.fonts
        win = tk.Toplevel(self, bg=T.CARD)
        win.title(f"{q.number}번 문제")
        win.transient(self.winfo_toplevel())
        win.geometry("600x460")
        body = tk.Frame(win, bg=T.CARD, padx=24, pady=20)
        body.pack(fill="both", expand=True)
        head = tk.Frame(body, bg=T.CARD)
        head.pack(fill="x", pady=(0, 10))
        tk.Label(head, text=str(q.number), bg=T.ACCENT, fg="#FFFFFF", font=f.heading, width=3, pady=2).pack(side="left", padx=(0, 10))
        T.chip(head, q.type_label, fg=T.ACCENT, bg=T.ACCENT_SOFT, font=f.small_bold).pack(side="left", padx=(0, 6))
        T.chip(head, "정답" if item.correct else "오답", fg=T.OK_FG if item.correct else T.BAD_FG,
               bg=T.OK_BG if item.correct else T.BAD_BG_STRONG, font=f.small_bold).pack(side="left")
        qt = T.RichText(body, f, size=f.size + 1, max_lines=10)
        qt.pack(fill="x")
        qt.set_markup(q.text)
        for c in q.choices:
            row = tk.Frame(body, bg=T.CARD)
            row.pack(fill="x", pady=(6, 0))
            T.label(row, f"{c.number})", font=f.bold, fg=T.MUTED, width=3).pack(side="left")
            ct = T.RichText(row, f, max_lines=4)
            ct.pack(side="left", fill="x", expand=True)
            ct.set_markup(c.text)
        tk.Frame(body, bg=T.BORDER, height=1).pack(fill="x", pady=12)
        T.label(body, f"내 답: {format_response(item.user_answer)}", font=f.bold).pack(anchor="w")
        T.label(body, f"정답: {strip_markup(format_answer(item.correct_answer))}", fg=T.MUTED).pack(anchor="w")
        T.label(body, f"점수: {item.earned} / {q.points}", fg=T.MUTED).pack(anchor="w")
        ttk.Button(body, text="닫기", style="Secondary.TButton", command=win.destroy).pack(anchor="e", pady=(12, 0))
        win.bind("<Escape>", lambda _e: win.destroy())

    def _retry_all(self) -> None:
        assert self.result is not None
        self.app.start_exam(self.result.exam, self.app.key)

    def _retry_wrong(self) -> None:
        assert self.result is not None
        exam = self.result.exam
        base_title = exam.title.removesuffix(RETRY_SUFFIX)
        subset = exam.subset(self.result.wrong_numbers)
        subset.title = base_title + RETRY_SUFFIX
        self.app.start_exam(subset, self.app.key)

    def _save(self) -> None:
        assert self.result is not None
        initial_dir = str(self.result.exam.source_path.parent) if self.result.exam.source_path else None
        chosen = filedialog.asksaveasfilename(
            parent=self, title="결과 저장", defaultextension=".txt",
            initialdir=initial_dir, initialfile=default_result_filename(self.result),
            filetypes=[("텍스트 파일", "*.txt")],
        )
        if not chosen:
            return
        try:
            Path(chosen).write_text(format_result(self.result), encoding="utf-8")
        except OSError as exc:
            messagebox.showerror("저장 실패", f"결과를 저장할 수 없습니다.\n{exc}", parent=self)
            return
        messagebox.showinfo("저장됨", f"결과를 저장했습니다.\n{chosen}", parent=self)

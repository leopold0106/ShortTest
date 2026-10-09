"""결과 화면."""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import TYPE_CHECKING

from shorttest.core.model import QuestionResult, Result
from shorttest.core.report import default_result_filename, format_answer, format_response, format_result

if TYPE_CHECKING:
    from shorttest.ui.app import App

RETRY_SUFFIX = " (오답 다시 풀기)"


class ResultView(ttk.Frame):
    def __init__(self, parent: tk.Misc, app: "App"):
        super().__init__(parent, padding=10)
        self.app = app
        self.result: Result | None = None

        self.title_label = ttk.Label(self, text="", font=app.font_heading)
        self.title_label.pack(anchor="w")
        self.score_label = ttk.Label(self, text="", font=app.font_title)
        self.score_label.pack(anchor="w", pady=(2, 2))
        self.count_label = ttk.Label(self, text="")
        self.count_label.pack(anchor="w", pady=(0, 10))

        table = ttk.Frame(self)
        table.pack(fill="both", expand=True)
        cols = ("no", "type", "user", "key", "ok", "score")
        self.tree = ttk.Treeview(table, columns=cols, show="headings", selectmode="browse")
        for col, text, width, anchor, stretch in (
            ("no", "번호", 60, "center", False),
            ("type", "유형", 70, "center", False),
            ("user", "내 답", 220, "w", True),
            ("key", "정답", 220, "w", True),
            ("ok", "결과", 60, "center", False),
            ("score", "점수", 70, "center", False),
        ):
            self.tree.heading(col, text=text)
            self.tree.column(col, width=width, anchor=anchor, stretch=stretch)
        scroll = ttk.Scrollbar(table, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        scroll.grid(row=0, column=1, sticky="ns")
        table.rowconfigure(0, weight=1)
        table.columnconfigure(0, weight=1)
        self.tree.tag_configure("wrong", background="#ffe3e3")
        self.tree.tag_configure("right", background="#e8f7e8")
        self.tree.bind("<Double-Button-1>", self._show_detail)
        self.tree.bind("<Return>", self._show_detail)

        ttk.Label(self, text="행을 더블클릭하면 문제와 보기를 다시 볼 수 있습니다.", foreground="#888").pack(anchor="w", pady=(4, 0))

        buttons = ttk.Frame(self)
        buttons.pack(fill="x", pady=(10, 0))
        ttk.Button(buttons, text="홈", command=app.go_home).pack(side="left")
        ttk.Button(buttons, text="다시 풀기", command=self._retry_all).pack(side="left", padx=(8, 0))
        self.retry_wrong_button = ttk.Button(buttons, text="틀린 문제만 다시", command=self._retry_wrong)
        self.retry_wrong_button.pack(side="left", padx=(8, 0))
        ttk.Button(buttons, text="결과 저장...", command=self._save).pack(side="right")

    def load(self, result: Result) -> None:
        self.result = result
        self.title_label.configure(text=f"결과: {result.exam.title}")
        self.score_label.configure(text=f"총점  {result.earned} / {result.total}  ({result.percent:.0f}%)")
        self.count_label.configure(text=f"정답 {result.correct_count} / {len(result.items)} 문항")
        self.tree.delete(*self.tree.get_children())
        for item in result.items:
            q = item.question
            self.tree.insert(
                "", "end", iid=str(q.number),
                values=(q.number, q.type_label, format_response(item.user_answer), format_answer(item.correct_answer),
                        "O" if item.correct else "X", f"{item.earned} / {q.points}"),
                tags=("right" if item.correct else "wrong",),
            )
        self.retry_wrong_button.state(["!disabled"] if result.wrong_numbers else ["disabled"])

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
        lines = [f"{q.number}. {q.text}", ""]
        for c in q.choices:
            lines.append(f"{c.number}) {c.text}")
        if q.choices:
            lines.append("")
        lines.append(f"내 답: {format_response(item.user_answer)}")
        lines.append(f"정답: {format_answer(item.correct_answer)}")
        lines.append(f"결과: {'정답' if item.correct else '오답'}  ({item.earned} / {q.points}점)")

        win = tk.Toplevel(self)
        win.title(f"{q.number}번 문제")
        win.transient(self.winfo_toplevel())
        win.geometry("560x400")
        text = tk.Text(win, wrap="word", padx=10, pady=8)
        text.pack(fill="both", expand=True)
        text.insert("1.0", "\n".join(lines))
        text.configure(state="disabled")
        ttk.Button(win, text="닫기", command=win.destroy).pack(pady=6)
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

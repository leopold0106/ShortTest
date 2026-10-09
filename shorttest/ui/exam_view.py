"""시험 화면: 문제 목록 + 문제 영역 + 이동/제출."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from typing import TYPE_CHECKING

from shorttest.core.model import AnswerKey, Exam, Question, ResponseValue

if TYPE_CHECKING:
    from shorttest.ui.app import App


class ExamView(ttk.Frame):
    def __init__(self, parent: tk.Misc, app: "App"):
        super().__init__(parent, padding=10)
        self.app = app
        self.exam: Exam | None = None
        self.key: AnswerKey | None = None
        self.responses: dict[int, ResponseValue] = {}
        self.index = 0
        self._suppress_tree_event = False
        self._answer_vars: list[tk.Variable] = []
        self._entry: ttk.Entry | None = None

        # 상단: 제목, 설명, 진행 상황
        header = ttk.Frame(self)
        header.pack(fill="x")
        self.title_label = ttk.Label(header, text="", font=app.font_heading)
        self.title_label.pack(side="left")
        self.progress_label = ttk.Label(header, text="")
        self.progress_label.pack(side="right")
        self.desc_label = ttk.Label(self, text="", foreground="#666")
        self.desc_label.pack(fill="x", pady=(0, 8))

        # 가운데: 왼쪽 목록 / 오른쪽 문제
        middle = ttk.Frame(self)
        middle.pack(fill="both", expand=True)

        left = ttk.Frame(middle)
        left.pack(side="left", fill="y", padx=(0, 10))
        self.tree = ttk.Treeview(left, columns=("no", "done"), show="headings", selectmode="browse", height=20)
        self.tree.heading("no", text="번호")
        self.tree.heading("done", text="응답")
        self.tree.column("no", width=60, anchor="center", stretch=False)
        self.tree.column("done", width=60, anchor="center", stretch=False)
        tree_scroll = ttk.Scrollbar(left, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_scroll.set)
        self.tree.pack(side="left", fill="y")
        tree_scroll.pack(side="left", fill="y")
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)

        right = ttk.Frame(middle)
        right.pack(side="left", fill="both", expand=True)
        self.q_header = ttk.Label(right, text="", font=app.font_heading)
        self.q_header.pack(anchor="w")

        text_frame = ttk.Frame(right)
        text_frame.pack(fill="x", pady=(4, 10))
        self.q_text = tk.Text(text_frame, wrap="word", height=7, padx=8, pady=6, relief="solid", borderwidth=1)
        q_scroll = ttk.Scrollbar(text_frame, orient="vertical", command=self.q_text.yview)
        self.q_text.configure(yscrollcommand=q_scroll.set, state="disabled")
        self.q_text.pack(side="left", fill="x", expand=True)
        q_scroll.pack(side="left", fill="y")

        self.answer_frame = ttk.Frame(right)
        self.answer_frame.pack(fill="both", expand=True)

        nav = ttk.Frame(right)
        nav.pack(fill="x", pady=(10, 0))
        self.prev_button = ttk.Button(nav, text="◀ 이전", command=self.prev)
        self.prev_button.pack(side="left")
        self.next_button = ttk.Button(nav, text="다음 ▶", command=self.next)
        self.next_button.pack(side="right")

        # 하단
        bottom = ttk.Frame(self)
        bottom.pack(fill="x", pady=(10, 0))
        ttk.Button(bottom, text="홈", command=self.home).pack(side="left")
        ttk.Label(bottom, text="PgUp/PgDn 또는 ←/→ 이동  ·  숫자 키로 보기 선택  ·  Enter 다음  ·  Ctrl+Enter 제출", foreground="#888").pack(side="left", padx=12)
        ttk.Button(bottom, text="제출하기", command=self.submit, style="Big.TButton").pack(side="right")

        app.bind("<Left>", self._key_prev)
        app.bind("<Prior>", self._key_prev)
        app.bind("<Right>", self._key_next)
        app.bind("<Next>", self._key_next)
        app.bind("<Control-Return>", self._key_submit)
        app.bind("<Key>", self._key_digit)

    # ------------------------------------------------------------ 로드

    def load(self, exam: Exam, key: AnswerKey) -> None:
        self.exam = exam
        self.key = key
        self.responses = {}
        self.index = 0
        self.title_label.configure(text=exam.title)
        self.desc_label.configure(text=exam.description)
        self.tree.delete(*self.tree.get_children())
        for q in exam.questions:
            self.tree.insert("", "end", iid=str(q.number), values=(q.number, ""))
        self.show_question(0)

    @property
    def current(self) -> Question:
        assert self.exam is not None
        return self.exam.questions[self.index]

    def answered_count(self) -> int:
        return sum(1 for v in self.responses.values() if v)

    # ------------------------------------------------------------ 표시

    def show_question(self, index: int) -> None:
        assert self.exam is not None
        self.index = max(0, min(index, len(self.exam.questions) - 1))
        q = self.current
        self.q_header.configure(text=f"{q.number}.  [{q.points}점]  {q.type_label}")
        self.q_text.configure(state="normal")
        self.q_text.delete("1.0", "end")
        self.q_text.insert("1.0", q.text)
        self.q_text.configure(state="disabled")
        self._build_answer(q)
        self.prev_button.state(["disabled"] if self.index == 0 else ["!disabled"])
        self.next_button.state(["disabled"] if self.index == len(self.exam.questions) - 1 else ["!disabled"])
        self._suppress_tree_event = True
        self.tree.selection_set(str(q.number))
        self.tree.see(str(q.number))
        self._suppress_tree_event = False
        self._update_progress()

    def _build_answer(self, q: Question) -> None:
        for child in self.answer_frame.winfo_children():
            child.destroy()
        self._answer_vars = []
        self._entry = None
        saved = self.responses.get(q.number)

        if q.is_multiple_choice:
            assert self.key is not None
            chosen: set[int] = saved if isinstance(saved, set) else set()
            multi = self.key.is_multi_select(q.number) or self.app.settings.always_checkbox
            if multi:
                ttk.Label(self.answer_frame, text="해당하는 것을 모두 고르세요.", foreground="#666").pack(anchor="w", pady=(0, 4))
                for c in q.choices:
                    var = tk.BooleanVar(value=c.number in chosen)
                    self._answer_vars.append(var)
                    tk.Checkbutton(
                        self.answer_frame, text=f"{c.number})  {c.text}", variable=var,
                        anchor="w", justify="left", wraplength=640, command=self._save_choices,
                    ).pack(anchor="w", fill="x")
            else:
                var = tk.IntVar(value=next(iter(chosen)) if chosen else 0)
                self._answer_vars.append(var)
                for c in q.choices:
                    tk.Radiobutton(
                        self.answer_frame, text=f"{c.number})  {c.text}", variable=var, value=c.number,
                        anchor="w", justify="left", wraplength=640, command=self._save_choices,
                    ).pack(anchor="w", fill="x")
        else:
            ttk.Label(self.answer_frame, text="답:").pack(anchor="w")
            var = tk.StringVar(value=saved if isinstance(saved, str) else "")
            self._answer_vars.append(var)
            entry = ttk.Entry(self.answer_frame, textvariable=var, width=40, font=self.app.font_entry)
            entry.pack(anchor="w", pady=(2, 0))
            entry.bind("<Return>", lambda _e: self.next())
            var.trace_add("write", lambda *_: self._save_text())
            self._entry = entry
            entry.focus_set()
            entry.icursor("end")

    # ------------------------------------------------------------ 응답 저장

    def _save_choices(self) -> None:
        q = self.current
        chosen: set[int] = set()
        if len(self._answer_vars) == 1 and isinstance(self._answer_vars[0], tk.IntVar):
            value = self._answer_vars[0].get()
            if value:
                chosen.add(value)
        else:
            for c, var in zip(q.choices, self._answer_vars):
                if var.get():
                    chosen.add(c.number)
        self._set_response(q.number, chosen if chosen else None)

    def _save_text(self) -> None:
        q = self.current
        value = self._answer_vars[0].get()
        self._set_response(q.number, value if value.strip() else None)

    def _set_response(self, number: int, value: ResponseValue) -> None:
        if value is None:
            self.responses.pop(number, None)
        else:
            self.responses[number] = value
        self.tree.item(str(number), values=(number, "✓" if value is not None else ""))
        self._update_progress()

    def _update_progress(self) -> None:
        assert self.exam is not None
        self.progress_label.configure(text=f"응답 {self.answered_count()} / {len(self.exam.questions)}")

    # ------------------------------------------------------------ 이동

    def _on_tree_select(self, _event=None) -> None:
        if self._suppress_tree_event or self.exam is None:
            return
        selection = self.tree.selection()
        if not selection:
            return
        number = int(selection[0])
        if number == self.current.number:
            return  # selection_set()이 다시 보낸 이벤트
        for i, q in enumerate(self.exam.questions):
            if q.number == number:
                self.show_question(i)
                break

    def prev(self) -> None:
        if self.exam and self.index > 0:
            self.show_question(self.index - 1)

    def next(self) -> None:
        if self.exam and self.index < len(self.exam.questions) - 1:
            self.show_question(self.index + 1)

    def _active(self) -> bool:
        return self.exam is not None and self.app.current_view is self

    def _focus_in_entry(self) -> bool:
        widget = self.app.focus_get()
        return isinstance(widget, (ttk.Entry, tk.Entry, tk.Text)) and widget is not self.q_text

    def _key_prev(self, _event=None):
        if self._active() and not self._focus_in_entry():
            self.prev()
            return "break"

    def _key_next(self, _event=None):
        if self._active() and not self._focus_in_entry():
            self.next()
            return "break"

    def _key_submit(self, _event=None):
        if self._active():
            self.submit()
            return "break"

    def _key_digit(self, event):
        if not self._active() or self._focus_in_entry() or not event.char.isdigit():
            return None
        q = self.current
        n = int(event.char)
        if not q.is_multiple_choice or not 1 <= n <= len(q.choices):
            return None
        if len(self._answer_vars) == 1 and isinstance(self._answer_vars[0], tk.IntVar):
            self._answer_vars[0].set(n)
        else:
            var = self._answer_vars[n - 1]
            var.set(not var.get())
        self._save_choices()
        return "break"

    # ------------------------------------------------------------ 제출 / 홈

    def submit(self) -> None:
        assert self.exam is not None
        unanswered = len(self.exam.questions) - self.answered_count()
        if unanswered:
            if not messagebox.askyesno("제출", f"아직 응답하지 않은 문제가 {unanswered}개 있습니다.\n그래도 제출할까요?", parent=self):
                return
        self.app.submit(self.exam, dict(self.responses))

    def home(self) -> None:
        if self.responses and not messagebox.askyesno("홈으로", "지금까지 쓴 답이 사라집니다. 홈으로 갈까요?", parent=self):
            return
        self.app.go_home()

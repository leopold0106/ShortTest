"""시험 화면: 진행 막대 + 번호 격자 + 문제 카드 + 이동/제출."""

from __future__ import annotations

import time
import tkinter as tk
from tkinter import messagebox, ttk
from typing import TYPE_CHECKING

from shorttest.core.model import AnswerKey, Exam, Question, ResponseValue
from shorttest.ui import theme as T

if TYPE_CHECKING:
    from shorttest.ui.app import App

GRID_COLUMNS = 4


class OptionRow(tk.Frame):
    """객관식 보기 한 줄. 행 전체가 클릭 영역이며 선택되면 틸 테두리와 연한 바탕."""

    def __init__(self, parent: tk.Misc, view: "ExamView", number: int, text: str, multi: bool):
        super().__init__(parent, bg=T.BORDER)
        self.view = view
        self.number = number
        self.multi = multi
        self.selected = False
        f = view.app.fonts
        self.inner = tk.Frame(self, bg=T.CARD, padx=12, pady=8, cursor="hand2", takefocus=1)
        self.inner.pack(fill="x", padx=1, pady=1)
        self.indicator = tk.Canvas(self.inner, width=18, height=18, bg=T.CARD, highlightthickness=0, cursor="hand2")
        self.indicator.pack(side="left", padx=(0, 10))
        self.num_label = tk.Label(self.inner, text=f"{number})", font=f.bold, fg=T.MUTED, bg=T.CARD, width=3, anchor="w", cursor="hand2")
        self.num_label.pack(side="left")
        self.text = T.RichText(self.inner, f, size=f.size + 1, max_lines=6, cursor="hand2")
        self.text.pack(side="left", fill="x", expand=True)
        self.text.set_markup(text)
        for w in (self.inner, self.indicator, self.num_label, self.text):
            w.bind("<Button-1>", self._click)
        self.inner.bind("<space>", self._click)
        self.inner.bind("<Return>", self._click)
        self.inner.bind("<FocusIn>", lambda _e: self.configure(bg=T.ACCENT if not self.selected else T.ACCENT_DARK))
        self.inner.bind("<FocusOut>", lambda _e: self._paint())
        self._paint()

    def _click(self, _event=None):
        self.view.toggle_choice(self.number)
        return "break"

    def set_selected(self, selected: bool) -> None:
        self.selected = selected
        self._paint()

    def _paint(self) -> None:
        bg = T.ACCENT_SOFT if self.selected else T.CARD
        self.configure(bg=T.ACCENT if self.selected else T.BORDER)
        for w in (self.inner, self.indicator, self.num_label, self.text):
            w.configure(bg=bg)
        self.num_label.configure(fg=T.ACCENT if self.selected else T.MUTED)
        c = self.indicator
        c.delete("all")
        if self.multi:
            c.create_rectangle(2, 2, 16, 16, outline=T.ACCENT if self.selected else T.BORDER_STRONG, width=2,
                               fill=T.ACCENT if self.selected else bg)
            if self.selected:
                c.create_line(5, 9, 8, 12, 13, 6, fill="#FFFFFF", width=2, capstyle="round", joinstyle="round")
        else:
            c.create_oval(2, 2, 16, 16, outline=T.ACCENT if self.selected else T.BORDER_STRONG, width=2, fill=bg)
            if self.selected:
                c.create_oval(6, 6, 12, 12, outline=T.ACCENT, fill=T.ACCENT)


class ExamView(tk.Frame):
    def __init__(self, parent: tk.Misc, app: "App"):
        super().__init__(parent, bg=T.BG)
        self.app = app
        f = app.fonts
        self.exam: Exam | None = None
        self.key: AnswerKey | None = None
        self.responses: dict[int, ResponseValue] = {}
        self.index = 0
        self.number_buttons: dict[int, tuple[tk.Frame, tk.Button]] = {}
        self.option_rows: list[OptionRow] = []
        self._entry: ttk.Entry | None = None
        self._entry_var: tk.StringVar | None = None
        self.started_at = 0.0
        self.deadline: float | None = None
        self._timer_job: str | None = None

        # 상단 바
        top = tk.Frame(self, bg=T.CARD, padx=24, pady=12)
        top.pack(fill="x")
        tk.Frame(self, bg=T.BORDER, height=1).pack(fill="x")
        row = tk.Frame(top, bg=T.CARD)
        row.pack(fill="x")
        titles = tk.Frame(row, bg=T.CARD)
        titles.pack(side="left")
        self.title_label = T.label(titles, "", font=f.heading)
        self.title_label.pack(anchor="w")
        self.desc_label = T.label(titles, "", fg=T.MUTED, font=f.small)
        self.desc_label.pack(anchor="w")
        self.progress_label = T.label(row, "", fg=T.MUTED, anchor="e")
        self.progress_label.pack(side="right")
        self.timer_label = tk.Label(row, text="", font=f.heading, fg=T.ACCENT, bg=T.ACCENT_SOFT, padx=12, pady=2)
        self.timer_label.pack(side="right", padx=(0, 16))
        self.progress = ttk.Progressbar(top, style="Teal.Horizontal.TProgressbar", maximum=1, value=0)
        self.progress.pack(fill="x", pady=(8, 0))

        # 가운데
        middle = tk.Frame(self, bg=T.BG, padx=24, pady=20)
        middle.pack(fill="both", expand=True)

        side = T.card(middle, padx=16, pady=16)
        side.outer.pack(side="left", fill="y", padx=(0, 20))
        T.label(side, "문제 목록", fg=T.MUTED, font=f.small_bold).pack(anchor="w", pady=(0, 10))
        self.number_grid = tk.Frame(side, bg=T.CARD)
        self.number_grid.pack(anchor="n")
        legend = tk.Frame(side, bg=T.CARD)
        legend.pack(anchor="w", pady=(14, 0))
        for color, border, text in ((T.ACCENT, T.ACCENT, "응답함"), (T.ACCENT_SOFT, T.ACCENT, "현재 문제"), (T.CARD, T.BORDER_STRONG, "미응답")):
            r = tk.Frame(legend, bg=T.CARD)
            r.pack(anchor="w", pady=1)
            tk.Frame(r, bg=border, width=12, height=12).pack(side="left", padx=(0, 8))
            tk.Frame(r, bg=color, width=8, height=8).place(x=2, y=2)
            T.label(r, text, fg=T.MUTED, font=f.small).pack(side="left")

        main = T.card(middle)
        main.outer.pack(side="left", fill="both", expand=True)
        self.scroll = T.ScrollFrame(main)
        self.scroll.pack(fill="both", expand=True)
        body = tk.Frame(self.scroll.body, bg=T.CARD, padx=28, pady=22)
        body.pack(fill="both", expand=True)

        head = tk.Frame(body, bg=T.CARD)
        head.pack(fill="x", pady=(0, 14))
        self.badge = tk.Label(head, text="", bg=T.ACCENT, fg="#FFFFFF", font=f.heading, width=3, pady=2)
        self.badge.pack(side="left", padx=(0, 10))
        self.type_chip = T.chip(head, "", fg=T.ACCENT, bg=T.ACCENT_SOFT, font=f.small_bold)
        self.type_chip.pack(side="left", padx=(0, 6))
        self.points_chip = T.chip(head, "", fg=T.MUTED, bg=T.BG, font=f.small_bold)
        self.points_chip.pack(side="left")

        self.q_text = T.RichText(body, f, size=f.size + 2, max_lines=16)
        self.q_text.pack(fill="x", pady=(0, 16))
        self.answer_frame = tk.Frame(body, bg=T.CARD)
        self.answer_frame.pack(fill="x")

        nav = tk.Frame(main, bg=T.CARD, padx=28, pady=16)
        nav.pack(fill="x", side="bottom")
        self.prev_button = ttk.Button(nav, text="◀  이전", style="Secondary.TButton", command=self.prev)
        self.prev_button.pack(side="left")
        self.next_button = ttk.Button(nav, text="다음  ▶", style="Secondary.TButton", command=self.next)
        self.next_button.pack(side="right")

        # 하단 바
        tk.Frame(self, bg=T.BORDER, height=1).pack(fill="x")
        bottom = tk.Frame(self, bg=T.CARD, padx=24, pady=10)
        bottom.pack(fill="x")
        ttk.Button(bottom, text="⌂  홈", style="Ghost.TButton", command=self.home).pack(side="left")
        T.label(bottom, "PgUp/PgDn 이동  ·  숫자 키로 보기 선택  ·  Enter 다음  ·  Ctrl+Enter 제출", fg=T.FAINT, font=f.small).pack(side="left", padx=16)
        ttk.Button(bottom, text="제출하기", style="Primary.TButton", command=self.submit).pack(side="right", ipadx=6)

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
        mc = sum(1 for q in exam.questions if q.is_multiple_choice)
        limit = f"제한 {exam.time_limit_minutes}분" if exam.has_time_limit else "시간 제한 없음"
        desc = f"객관식 {mc}문항, 단답형 {len(exam.questions) - mc}문항 · 총 {exam.total_points}점 · {limit}"
        if exam.description:
            desc = f"{exam.description}  ·  {desc}"
        self.desc_label.configure(text=desc)
        self.progress.configure(maximum=max(1, len(exam.questions)))
        self._start_timer(exam)

        for child in self.number_grid.winfo_children():
            child.destroy()
        self.number_buttons = {}
        for i, q in enumerate(exam.questions):
            outer = tk.Frame(self.number_grid, bg=T.BORDER)
            outer.grid(row=i // GRID_COLUMNS, column=i % GRID_COLUMNS, padx=3, pady=3)
            btn = tk.Button(outer, text=str(q.number), width=3, relief="flat", bd=0, highlightthickness=0,
                            font=self.app.fonts.bold, cursor="hand2", pady=6,
                            command=lambda idx=i: self.show_question(idx))
            btn.pack(padx=1, pady=1)
            self.number_buttons[q.number] = (outer, btn)
        self.show_question(0)

    # ------------------------------------------------------------ 타이머

    def _start_timer(self, exam: Exam) -> None:
        self._stop_timer()
        self.started_at = time.monotonic()
        if exam.has_time_limit:
            self.deadline = self.started_at + exam.time_limit_minutes * 60
            self.timer_label.configure(fg=T.ACCENT, bg=T.ACCENT_SOFT)
            self._tick()
        else:
            self.deadline = None
            self.timer_label.configure(text="제한 시간 없음", fg=T.MUTED, bg=T.BG)

    def _stop_timer(self) -> None:
        if self._timer_job is not None:
            self.after_cancel(self._timer_job)
            self._timer_job = None

    def remaining_seconds(self) -> int | None:
        if self.deadline is None:
            return None
        return max(0, int(round(self.deadline - time.monotonic())))

    def elapsed_seconds(self) -> int:
        return int(time.monotonic() - self.started_at)

    def _tick(self) -> None:
        self._timer_job = None
        remaining = self.remaining_seconds()
        if remaining is None:
            return
        minutes, seconds = divmod(remaining, 60)
        self.timer_label.configure(text=f"⏱ {minutes:02d}:{seconds:02d}")
        if remaining <= 60:
            self.timer_label.configure(fg=T.BAD_FG, bg=T.BAD_BG_STRONG)
        if remaining <= 0:
            self._time_up()
            return
        self._timer_job = self.after(500, self._tick)

    def _time_up(self) -> None:
        if self.exam is None or self.app.current_view is not self:
            return
        messagebox.showinfo("시간 종료", "제한 시간이 끝나 지금까지 쓴 답으로 자동 제출합니다.", parent=self)
        self._submit_now(timed_out=True)

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
        self.badge.configure(text=str(q.number))
        multi = q.is_multiple_choice and (self.key.is_multi_select(q.number) or self.app.settings.always_checkbox)  # type: ignore[union-attr]
        self.type_chip.configure(text="객관식 · 모두 고르기" if multi else q.type_label)
        self.points_chip.configure(text=f"{q.points}점")
        self.q_text.set_markup(q.text)
        self._build_answer(q, multi)
        self.prev_button.state(["disabled"] if self.index == 0 else ["!disabled"])
        self.next_button.state(["disabled"] if self.index == len(self.exam.questions) - 1 else ["!disabled"])
        self._paint_numbers()
        self._update_progress()
        self.scroll.scroll_top()

    def _build_answer(self, q: Question, multi: bool) -> None:
        for child in self.answer_frame.winfo_children():
            child.destroy()
        self.option_rows = []
        self._entry = None
        self._entry_var = None
        saved = self.responses.get(q.number)
        f = self.app.fonts

        if q.is_multiple_choice:
            chosen: set[int] = saved if isinstance(saved, set) else set()
            if multi:
                T.label(self.answer_frame, "해당하는 것을 모두 고르세요.", fg=T.MUTED, font=f.small).pack(anchor="w", pady=(0, 6))
            for c in q.choices:
                row = OptionRow(self.answer_frame, self, c.number, c.text, multi)
                row.pack(fill="x", pady=(0, 8))
                row.set_selected(c.number in chosen)
                self.option_rows.append(row)
        else:
            T.label(self.answer_frame, "답", fg=T.MUTED, font=f.small_bold).pack(anchor="w", pady=(0, 4))
            var = tk.StringVar(value=saved if isinstance(saved, str) else "")
            entry = ttk.Entry(self.answer_frame, textvariable=var, width=44, font=f.body)
            entry.pack(anchor="w")
            entry.bind("<Return>", lambda _e: self.next())
            var.trace_add("write", lambda *_: self._save_text())
            self._entry = entry
            self._entry_var = var
            entry.focus_set()
            entry.icursor("end")
            T.label(self.answer_frame, "앞뒤 공백과 영문 대소문자는 구분하지 않습니다.", fg=T.FAINT, font=f.small).pack(anchor="w", pady=(6, 0))

    def _paint_numbers(self) -> None:
        assert self.exam is not None
        current = self.current.number
        for number, (outer, btn) in self.number_buttons.items():
            answered = bool(self.responses.get(number))
            if number == current:
                outer.configure(bg=T.ACCENT)
                btn.configure(bg=T.ACCENT_SOFT, fg=T.ACCENT, activebackground=T.ACCENT_SOFT, activeforeground=T.ACCENT)
            elif answered:
                outer.configure(bg=T.ACCENT)
                btn.configure(bg=T.ACCENT, fg="#FFFFFF", activebackground=T.ACCENT_DARK, activeforeground="#FFFFFF")
            else:
                outer.configure(bg=T.BORDER)
                btn.configure(bg=T.CARD, fg=T.TEXT, activebackground=T.BG, activeforeground=T.TEXT)

    # ------------------------------------------------------------ 응답 저장

    def toggle_choice(self, number: int) -> None:
        q = self.current
        current: set[int] = self.responses.get(q.number) if isinstance(self.responses.get(q.number), set) else set()  # type: ignore[assignment]
        multi = any(r.multi for r in self.option_rows)
        if multi:
            chosen = set(current)
            chosen ^= {number}
        else:
            chosen = {number}
        for row in self.option_rows:
            row.set_selected(row.number in chosen)
        self._set_response(q.number, chosen if chosen else None)

    def _save_text(self) -> None:
        assert self._entry_var is not None
        value = self._entry_var.get()
        self._set_response(self.current.number, value if value.strip() else None)

    def _set_response(self, number: int, value: ResponseValue) -> None:
        if value is None:
            self.responses.pop(number, None)
        else:
            self.responses[number] = value
        self._paint_numbers()
        self._update_progress()

    def _update_progress(self) -> None:
        assert self.exam is not None
        n = self.answered_count()
        self.progress_label.configure(text=f"응답 {n} / {len(self.exam.questions)}")
        self.progress.configure(value=n)

    # ------------------------------------------------------------ 이동

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
        return isinstance(widget, (ttk.Entry, tk.Entry)) or (isinstance(widget, tk.Text) and not getattr(widget, "_rich", False))

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
        self.toggle_choice(n)
        return "break"

    # ------------------------------------------------------------ 제출 / 홈

    def submit(self) -> None:
        assert self.exam is not None
        unanswered = len(self.exam.questions) - self.answered_count()
        if unanswered:
            if not messagebox.askyesno("제출", f"아직 응답하지 않은 문제가 {unanswered}개 있습니다.\n그래도 제출할까요?", parent=self):
                return
        self._submit_now(timed_out=False)

    def _submit_now(self, *, timed_out: bool) -> None:
        assert self.exam is not None
        self._stop_timer()
        self.app.submit(self.exam, dict(self.responses), elapsed_seconds=self.elapsed_seconds(), timed_out=timed_out)

    def home(self) -> None:
        if self.responses and not messagebox.askyesno("홈으로", "지금까지 쓴 답이 사라집니다. 홈으로 갈까요?", parent=self):
            return
        self._stop_timer()
        self.app.go_home()

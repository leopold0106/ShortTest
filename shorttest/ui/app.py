"""Tk 루트 창, 화면 전환, 메뉴, 파일 열기."""

from __future__ import annotations

import sys
import traceback
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from tkinter import font as tkfont

from shorttest import APP_NAME, __version__
from shorttest.core.grader import GradeOptions, grade
from shorttest.core.model import AnswerKey, Exam, ResponseValue
from shorttest.core.parser import ANSWERS_SUFFIX, QUESTIONS_SUFFIX, ParseError, default_answers_path, load_exam
from shorttest.settings import Settings, error_log_path
from shorttest.ui.dialogs import HelpWindow, save_template, show_parse_errors
from shorttest.ui.exam_view import ExamView
from shorttest.ui.result_view import ResultView
from shorttest.ui.start_view import StartView


class App(tk.Tk):
    def __init__(self, settings: Settings | None = None):
        super().__init__()
        self.settings = settings or Settings.load()
        self.exam: Exam | None = None
        self.key: AnswerKey | None = None
        self.current_view: ttk.Frame | None = None

        self.title(APP_NAME)
        self.minsize(900, 600)
        self.geometry(f"{self.settings.window_width}x{self.settings.window_height}")
        self._setup_fonts_and_styles()
        self._build_menu()

        container = ttk.Frame(self)
        container.pack(fill="both", expand=True)
        container.rowconfigure(0, weight=1)
        container.columnconfigure(0, weight=1)
        self.start_view = StartView(container, self)
        self.exam_view = ExamView(container, self)
        self.result_view = ResultView(container, self)
        for view in (self.start_view, self.exam_view, self.result_view):
            view.grid(row=0, column=0, sticky="nsew")
        self.show(self.start_view)

        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.report_callback_exception = self._report_exception  # type: ignore[assignment]

    # ------------------------------------------------------------ 모양

    def _setup_fonts_and_styles(self) -> None:
        family = "맑은 고딕" if sys.platform == "win32" else None
        size = 11
        for name in ("TkDefaultFont", "TkTextFont", "TkMenuFont", "TkHeadingFont", "TkFixedFont"):
            f = tkfont.nametofont(name)
            if family and name != "TkFixedFont":
                f.configure(family=family)
            f.configure(size=size)
        base = tkfont.nametofont("TkDefaultFont")
        self.font_title = base.copy()
        self.font_title.configure(size=size + 7, weight="bold")
        self.font_heading = base.copy()
        self.font_heading.configure(size=size + 2, weight="bold")
        self.font_entry = base.copy()
        self.font_entry.configure(size=size + 1)

        style = ttk.Style(self)
        if sys.platform == "win32" and "vista" in style.theme_names():
            style.theme_use("vista")
        style.configure("Treeview", rowheight=size + 17)
        style.configure("Big.TButton", font=self.font_heading, padding=(14, 6))
        self.option_add("*Text.font", base)
        self.option_add("*Listbox.font", base)
        self.option_add("*Radiobutton.font", base)
        self.option_add("*Checkbutton.font", base)

    def _build_menu(self) -> None:
        menubar = tk.Menu(self)
        file_menu = tk.Menu(menubar, tearoff=False)
        file_menu.add_command(label="문제지 열기...", command=self.open_dialog, accelerator="Ctrl+O")
        self.recent_menu = tk.Menu(file_menu, tearoff=False)
        file_menu.add_cascade(label="최근 파일", menu=self.recent_menu)
        file_menu.add_separator()
        file_menu.add_command(label="템플릿 파일 만들기...", command=lambda: save_template(self))
        file_menu.add_separator()
        file_menu.add_command(label="종료", command=self.on_close)
        menubar.add_cascade(label="파일", menu=file_menu)

        help_menu = tk.Menu(menubar, tearoff=False)
        help_menu.add_command(label="문제지·정답지 작성법", command=lambda: HelpWindow.show(self), accelerator="F1")
        help_menu.add_command(label="프로그램 정보", command=self.show_about)
        menubar.add_cascade(label="도움말", menu=help_menu)
        self.config(menu=menubar)
        self.bind("<Control-o>", lambda _e: self.open_dialog())
        self.bind("<F1>", lambda _e: HelpWindow.show(self))
        self._refresh_recent_menu()

    def _refresh_recent_menu(self) -> None:
        self.recent_menu.delete(0, "end")
        for p in self.settings.recent_files:
            self.recent_menu.add_command(label=p, command=lambda path=p: self.open_exam(Path(path)))
        if not self.settings.recent_files:
            self.recent_menu.add_command(label="(없음)", state="disabled")

    # ------------------------------------------------------------ 화면 전환

    def show(self, view: ttk.Frame) -> None:
        self.current_view = view
        view.tkraise()

    def go_home(self) -> None:
        self.start_view.refresh()
        self._refresh_recent_menu()
        self.show(self.start_view)

    # ------------------------------------------------------------ 파일 열기

    def open_dialog(self) -> None:
        initial_dir = None
        if self.settings.recent_files:
            initial_dir = str(Path(self.settings.recent_files[0]).parent)
        chosen = filedialog.askopenfilename(
            parent=self, title="문제지 열기", initialdir=initial_dir,
            filetypes=[("문제지", "*" + QUESTIONS_SUFFIX), ("텍스트 파일", "*.txt"), ("모든 파일", "*.*")],
        )
        if chosen:
            self.open_exam(Path(chosen))

    def open_exam(self, questions_path: Path) -> bool:
        if not questions_path.exists():
            messagebox.showerror("파일 없음", f"파일을 찾을 수 없습니다.\n{questions_path}", parent=self)
            self.settings.remove_recent(questions_path)
            self.go_home()
            return False

        answers_path = default_answers_path(questions_path)
        if not answers_path.exists():
            if not messagebox.askokcancel(
                "정답지 없음",
                f"같은 폴더에 정답지가 없습니다.\n찾은 이름: {answers_path.name}\n\n정답지 파일을 직접 선택할까요?",
                parent=self,
            ):
                return False
            chosen = filedialog.askopenfilename(
                parent=self, title="정답지 열기", initialdir=str(questions_path.parent),
                filetypes=[("정답지", "*" + ANSWERS_SUFFIX), ("텍스트 파일", "*.txt"), ("모든 파일", "*.*")],
            )
            if not chosen:
                return False
            answers_path = Path(chosen)

        try:
            exam, key, warnings = load_exam(questions_path, answers_path)
        except ParseError as exc:
            show_parse_errors(self, exc.issues)
            return False
        except OSError as exc:
            messagebox.showerror("읽기 실패", f"파일을 읽을 수 없습니다.\n{exc}", parent=self)
            return False

        if warnings:
            messagebox.showwarning("주의", "\n".join(warnings), parent=self)
        self.settings.add_recent(questions_path)
        self.settings.save()
        self._refresh_recent_menu()
        self.start_exam(exam, key)
        return True

    # ------------------------------------------------------------ 시험 / 채점

    def start_exam(self, exam: Exam, key: AnswerKey | None) -> None:
        assert key is not None
        self.exam = exam
        self.key = key
        self.exam_view.load(exam, key)
        self.show(self.exam_view)

    def submit(self, exam: Exam, responses: dict[int, ResponseValue]) -> None:
        assert self.key is not None
        options = GradeOptions(ignore_inner_spaces=self.settings.ignore_inner_spaces)
        result = grade(exam, self.key, responses, options)
        self.result_view.load(result)
        self.show(self.result_view)

    # ------------------------------------------------------------ 기타

    def show_about(self) -> None:
        messagebox.showinfo(
            "프로그램 정보",
            f"{APP_NAME} {__version__}\n\n문제지·정답지 텍스트 파일로 시험을 보고 자동 채점하는 프로그램입니다.\n\n"
            f"설정 파일: {error_log_path().parent}",
            parent=self,
        )

    def on_close(self) -> None:
        try:
            self.settings.window_width = self.winfo_width()
            self.settings.window_height = self.winfo_height()
            self.settings.save()
        finally:
            self.destroy()

    def _report_exception(self, exc_type, exc_value, exc_tb) -> None:
        log_unexpected_error(exc_type, exc_value, exc_tb)
        try:
            messagebox.showerror(
                "오류",
                f"예상하지 못한 오류가 발생했습니다.\n{exc_value}\n\n자세한 내용: {error_log_path()}",
                parent=self,
            )
        except tk.TclError:
            pass


def log_unexpected_error(exc_type, exc_value, exc_tb) -> None:
    try:
        path = error_log_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(f"\n===== {datetime.now():%Y-%m-%d %H:%M:%S} {APP_NAME} {__version__}\n")
            fh.write("".join(traceback.format_exception(exc_type, exc_value, exc_tb)))
    except OSError:
        pass


def main() -> None:
    def hook(exc_type, exc_value, exc_tb):
        log_unexpected_error(exc_type, exc_value, exc_tb)
        try:
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("오류", f"프로그램을 실행할 수 없습니다.\n{exc_value}\n\n자세한 내용: {error_log_path()}")
            root.destroy()
        except tk.TclError:
            pass

    sys.excepthook = hook
    App().mainloop()

"""오류 목록 대화상자, 도움말 창, 템플릿 저장."""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from shorttest.core.parser import QUESTIONS_SUFFIX, ParseIssue, default_answers_path
from shorttest.help_text import HELP_TEXT, HELP_TITLE, TEMPLATE_ANSWERS, TEMPLATE_QUESTIONS


def _center_over(window: tk.Toplevel, parent: tk.Misc) -> None:
    window.update_idletasks()
    px, py = parent.winfo_rootx(), parent.winfo_rooty()
    pw, ph = parent.winfo_width(), parent.winfo_height()
    w, h = window.winfo_width(), window.winfo_height()
    window.geometry(f"+{max(0, px + (pw - w) // 2)}+{max(0, py + (ph - h) // 2)}")


def save_template(parent: tk.Misc) -> None:
    """문제지·정답지 템플릿 두 파일을 한 번에 저장한다."""
    chosen = filedialog.asksaveasfilename(
        parent=parent,
        title="문제지 템플릿 저장 (정답지도 같이 만들어집니다)",
        initialfile="새시험" + QUESTIONS_SUFFIX,
        defaultextension=".txt",
        filetypes=[("문제지", "*" + QUESTIONS_SUFFIX), ("텍스트 파일", "*.txt")],
    )
    if not chosen:
        return
    q_path = Path(chosen)
    if not q_path.name.endswith(QUESTIONS_SUFFIX):
        q_path = q_path.with_name(q_path.name.removesuffix(".txt") + QUESTIONS_SUFFIX)
    a_path = default_answers_path(q_path)
    try:
        q_path.write_text(TEMPLATE_QUESTIONS, encoding="utf-8")
        a_path.write_text(TEMPLATE_ANSWERS, encoding="utf-8")
    except OSError as exc:
        messagebox.showerror("저장 실패", f"파일을 저장할 수 없습니다.\n{exc}", parent=parent)
        return
    messagebox.showinfo(
        "템플릿 저장됨",
        f"두 파일을 만들었습니다. 메모장으로 열어 내용을 바꾸세요.\n\n{q_path}\n{a_path}",
        parent=parent,
    )


class HelpWindow(tk.Toplevel):
    _instance: "HelpWindow | None" = None

    @classmethod
    def show(cls, parent: tk.Misc) -> "HelpWindow":
        if cls._instance is not None and cls._instance.winfo_exists():
            cls._instance.lift()
            cls._instance.focus_set()
            return cls._instance
        cls._instance = cls(parent)
        return cls._instance

    def __init__(self, parent: tk.Misc):
        super().__init__(parent)
        self.title(HELP_TITLE)
        self.geometry("760x640")
        self.minsize(520, 400)

        body = ttk.Frame(self, padding=8)
        body.pack(fill="both", expand=True)
        text = tk.Text(body, wrap="word", padx=12, pady=8, relief="flat")
        scroll = ttk.Scrollbar(body, orient="vertical", command=text.yview)
        text.configure(yscrollcommand=scroll.set)
        text.grid(row=0, column=0, sticky="nsew")
        scroll.grid(row=0, column=1, sticky="ns")
        body.rowconfigure(0, weight=1)
        body.columnconfigure(0, weight=1)
        text.insert("1.0", HELP_TEXT)
        text.configure(state="disabled")

        buttons = ttk.Frame(self, padding=(8, 0, 8, 8))
        buttons.pack(fill="x")
        ttk.Button(buttons, text="템플릿 파일 만들기...", command=lambda: save_template(self)).pack(side="left")
        ttk.Button(buttons, text="닫기", command=self.destroy).pack(side="right")
        self.bind("<Escape>", lambda _e: self.destroy())
        _center_over(self, parent.winfo_toplevel())


def show_parse_errors(parent: tk.Misc, issues: list[ParseIssue]) -> None:
    win = tk.Toplevel(parent)
    win.title("문제지·정답지 오류")
    win.transient(parent.winfo_toplevel())
    win.geometry("760x420")
    win.minsize(500, 300)

    frame = ttk.Frame(win, padding=10)
    frame.pack(fill="both", expand=True)
    ttk.Label(
        frame,
        text=f"파일에 오류가 {len(issues)}개 있습니다. 메모장에서 해당 줄을 고친 뒤 다시 여세요.",
    ).pack(anchor="w", pady=(0, 8))

    table_frame = ttk.Frame(frame)
    table_frame.pack(fill="both", expand=True)
    cols = ("file", "line", "message")
    tree = ttk.Treeview(table_frame, columns=cols, show="headings", selectmode="browse")
    tree.heading("file", text="파일")
    tree.heading("line", text="줄")
    tree.heading("message", text="내용")
    tree.column("file", width=180, stretch=False)
    tree.column("line", width=50, anchor="center", stretch=False)
    tree.column("message", width=480)
    scroll = ttk.Scrollbar(table_frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scroll.set)
    tree.grid(row=0, column=0, sticky="nsew")
    scroll.grid(row=0, column=1, sticky="ns")
    table_frame.rowconfigure(0, weight=1)
    table_frame.columnconfigure(0, weight=1)
    for issue in issues:
        tree.insert("", "end", values=(issue.filename, issue.line or "", issue.message))

    buttons = ttk.Frame(frame, padding=(0, 8, 0, 0))
    buttons.pack(fill="x")
    ttk.Button(buttons, text="작성법 보기", command=lambda: HelpWindow.show(parent)).pack(side="left")
    ttk.Button(buttons, text="닫기", command=win.destroy).pack(side="right")
    win.bind("<Escape>", lambda _e: win.destroy())
    _center_over(win, parent.winfo_toplevel())
    win.grab_set()
    win.focus_set()
    win.wait_window()

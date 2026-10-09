"""오류 목록 대화상자, 도움말 창, 템플릿 저장."""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from shorttest.core.parser import QUESTIONS_SUFFIX, ParseIssue, default_answers_path
from shorttest.help_text import HELP_TEXT, HELP_TITLE, TEMPLATE_ANSWERS, TEMPLATE_QUESTIONS
from shorttest.ui import theme as T


def _center_over(window: tk.Toplevel, parent: tk.Misc) -> None:
    window.update_idletasks()
    px, py = parent.winfo_rootx(), parent.winfo_rooty()
    pw, ph = parent.winfo_width(), parent.winfo_height()
    w, h = window.winfo_width(), window.winfo_height()
    window.geometry(f"+{max(0, px + (pw - w) // 2)}+{max(0, py + (ph - h) // 2)}")


def _fonts(widget: tk.Misc) -> T.Fonts:
    return widget.winfo_toplevel().nametowidget(".").fonts  # type: ignore[attr-defined]


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
        super().__init__(parent, bg=T.BG)
        self.title(HELP_TITLE)
        self.geometry("780x660")
        self.minsize(560, 420)
        f = _fonts(parent)

        head = tk.Frame(self, bg=T.BG, padx=20, pady=14)
        head.pack(fill="x")
        T.label(head, HELP_TITLE, font=f.heading).pack(side="left")
        T.label(head, "docs/FORMAT.md 와 같은 내용", fg=T.MUTED, font=f.small).pack(side="right")

        body = T.card(self)
        body.outer.pack(fill="both", expand=True, padx=20)
        text = tk.Text(body, wrap="word", padx=18, pady=14, relief="flat", bg=T.CARD, fg=T.TEXT, font=f.base, spacing2=2)
        scroll = ttk.Scrollbar(body, orient="vertical", command=text.yview)
        text.configure(yscrollcommand=scroll.set)
        text.pack(side="left", fill="both", expand=True)
        scroll.pack(side="left", fill="y")
        text.tag_configure("h", font=f.heading, foreground=T.ACCENT, spacing1=10, spacing3=4)
        for line in HELP_TEXT.splitlines(keepends=True):
            text.insert("end", line, ("h",) if line.startswith("■") else ())
        text.configure(state="disabled")

        buttons = tk.Frame(self, bg=T.BG, padx=20, pady=14)
        buttons.pack(fill="x")
        ttk.Button(buttons, text="템플릿 파일 만들기…", style="Outline.TButton", command=lambda: save_template(self)).pack(side="left")
        ttk.Button(buttons, text="닫기", style="Secondary.TButton", command=self.destroy).pack(side="right")
        self.bind("<Escape>", lambda _e: self.destroy())
        _center_over(self, parent.winfo_toplevel())


def show_parse_errors(parent: tk.Misc, issues: list[ParseIssue]) -> None:
    f = _fonts(parent)
    win = tk.Toplevel(parent, bg=T.BG)
    win.title("문제지·정답지 오류")
    win.transient(parent.winfo_toplevel())
    win.geometry("780x440")
    win.minsize(520, 300)

    head = tk.Frame(win, bg=T.BG, padx=20, pady=14)
    head.pack(fill="x")
    T.label(head, f"파일에 오류가 {len(issues)}개 있습니다.", font=f.heading, fg=T.BAD_FG).pack(anchor="w")
    T.label(head, "메모장에서 해당 줄을 고친 뒤 다시 여세요. 오류는 한 번에 모두 표시됩니다.", fg=T.MUTED).pack(anchor="w")

    table = T.card(win)
    table.outer.pack(fill="both", expand=True, padx=20)
    cols = ("file", "line", "message")
    tree = ttk.Treeview(table, columns=cols, show="headings", selectmode="browse")
    tree.heading("file", text="파일")
    tree.heading("line", text="줄")
    tree.heading("message", text="내용")
    tree.column("file", width=190, stretch=False)
    tree.column("line", width=56, anchor="center", stretch=False)
    tree.column("message", width=480)
    scroll = ttk.Scrollbar(table, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scroll.set)
    tree.pack(side="left", fill="both", expand=True)
    scroll.pack(side="left", fill="y")
    for issue in issues:
        tree.insert("", "end", values=(issue.filename, issue.line or "", issue.message))

    buttons = tk.Frame(win, bg=T.BG, padx=20, pady=14)
    buttons.pack(fill="x")
    ttk.Button(buttons, text="작성법 보기", style="Outline.TButton", command=lambda: HelpWindow.show(parent)).pack(side="left")
    ttk.Button(buttons, text="닫기", style="Primary.TButton", command=win.destroy).pack(side="right")
    win.bind("<Escape>", lambda _e: win.destroy())
    _center_over(win, parent.winfo_toplevel())
    win.grab_set()
    win.focus_set()
    win.wait_window()

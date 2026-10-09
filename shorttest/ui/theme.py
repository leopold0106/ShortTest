"""색, 글꼴, ttk 스타일. 디자인 시안(docs/PLAN.md, 디자인 캔버스)과 같은 값."""

from __future__ import annotations

import math
import sys
import tkinter as tk
from tkinter import ttk
from tkinter import font as tkfont

from shorttest.core.markup import parse_markup

BG = "#F4F5F7"          # 바탕
CARD = "#FFFFFF"        # 카드
BORDER = "#E3E6EA"      # 카드 테두리
BORDER_STRONG = "#CFD4DA"
ROW_LINE = "#EEF0F2"
TEXT = "#1A1D21"
MUTED = "#5B6470"
FAINT = "#8A93A0"
ACCENT = "#0F766E"      # 틸
ACCENT_DARK = "#115E59"
ACCENT_SOFT = "#E6F4F2"
ACCENT_DISABLED = "#9CC5C0"
HEAD_BG = "#F9FAFB"
OK_FG = "#15803D"
OK_BG = "#ECFDF3"
BAD_FG = "#B91C1C"
BAD_BG = "#FEF2F2"
BAD_BG_STRONG = "#FEE2E2"


class Fonts:
    def __init__(self, root: tk.Misc):
        family = "맑은 고딕" if sys.platform == "win32" else tkfont.nametofont("TkDefaultFont").cget("family")
        size = 11
        for name in ("TkDefaultFont", "TkTextFont", "TkMenuFont", "TkHeadingFont"):
            tkfont.nametofont(name).configure(family=family, size=size)
        self.root = root
        self.family = family
        self.size = size
        self.base = tkfont.Font(root, family=family, size=size)
        self.bold = tkfont.Font(root, family=family, size=size, weight="bold")
        self.small = tkfont.Font(root, family=family, size=size - 2)
        self.small_bold = tkfont.Font(root, family=family, size=size - 2, weight="bold")
        self.body = tkfont.Font(root, family=family, size=size + 1)
        self.heading = tkfont.Font(root, family=family, size=size + 3, weight="bold")
        self.title = tkfont.Font(root, family=family, size=size + 8, weight="bold")
        self.hero = tkfont.Font(root, family=family, size=size + 20, weight="bold")
        self.mono = tkfont.Font(root, family="Consolas" if sys.platform == "win32" else "monospace", size=size - 1)
        self._rich: dict[tuple[int, frozenset[str]], tkfont.Font] = {}

    def rich(self, styles: frozenset[str], size: int | None = None) -> tkfont.Font:
        """마크업 스타일 조합에 맞는 글꼴. 첨자는 두 단계 작게."""
        size = size or self.size
        key = (size, styles)
        if key not in self._rich:
            actual = size - 3 if ("sub" in styles or "sup" in styles) else size
            self._rich[key] = tkfont.Font(
                self.root, family=self.family, size=actual,
                weight="bold" if "b" in styles else "normal",
                slant="italic" if "i" in styles else "roman",
            )
        return self._rich[key]


def apply_styles(root: tk.Tk, fonts: Fonts) -> None:
    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure(".", background=BG, foreground=TEXT, font=fonts.base, bordercolor=BORDER, focuscolor=ACCENT)
    style.configure("TFrame", background=BG)
    style.configure("Card.TFrame", background=CARD)

    # 버튼
    common = dict(padding=(14, 8), relief="raised", borderwidth=1, focusthickness=0)
    style.configure("Primary.TButton", background=ACCENT, foreground="#FFFFFF", bordercolor=ACCENT,
                    lightcolor=ACCENT, darkcolor=ACCENT, font=fonts.bold, **common)
    style.map("Primary.TButton", background=[("disabled", ACCENT_DISABLED), ("pressed", ACCENT_DARK), ("active", ACCENT_DARK)],
              foreground=[("disabled", "#FFFFFF")], bordercolor=[("disabled", ACCENT_DISABLED)])
    style.configure("Secondary.TButton", background=CARD, foreground=TEXT, bordercolor=BORDER_STRONG,
                    lightcolor=CARD, darkcolor=CARD, **common)
    style.map("Secondary.TButton", background=[("pressed", BG), ("active", BG)], foreground=[("disabled", FAINT)])
    style.configure("Outline.TButton", background=CARD, foreground=ACCENT, bordercolor=ACCENT,
                    lightcolor=CARD, darkcolor=CARD, font=fonts.bold, **common)
    style.map("Outline.TButton", background=[("pressed", ACCENT_SOFT), ("active", ACCENT_SOFT)],
              foreground=[("disabled", FAINT)], bordercolor=[("disabled", BORDER_STRONG)])
    style.configure("Ghost.TButton", background=CARD, foreground=MUTED, bordercolor=CARD,
                    lightcolor=CARD, darkcolor=CARD, **{**common, "relief": "flat"})
    style.map("Ghost.TButton", background=[("pressed", BG), ("active", BG)], foreground=[("active", TEXT)])

    # 체크/라디오 (설정 화면)
    style.configure("TCheckbutton", background=CARD, foreground=TEXT, indicatorcolor=CARD, padding=(0, 6))
    style.map("TCheckbutton", indicatorcolor=[("selected", ACCENT), ("pressed", ACCENT_SOFT)],
              background=[("active", CARD)])

    # 진행 막대
    style.configure("Teal.Horizontal.TProgressbar", troughcolor=BORDER, background=ACCENT,
                    bordercolor=BORDER, lightcolor=ACCENT, darkcolor=ACCENT, thickness=6)

    # 입력창
    style.configure("TEntry", fieldbackground=CARD, bordercolor=BORDER_STRONG, lightcolor=CARD, darkcolor=CARD, padding=(10, 8))
    style.map("TEntry", bordercolor=[("focus", ACCENT)], lightcolor=[("focus", ACCENT)], darkcolor=[("focus", ACCENT)])

    # 표
    style.configure("Treeview", background=CARD, fieldbackground=CARD, foreground=TEXT, rowheight=fonts.size + 20,
                    borderwidth=0, relief="flat")
    style.configure("Treeview.Heading", background=HEAD_BG, foreground=MUTED, font=fonts.small_bold,
                    relief="flat", padding=(8, 8), bordercolor=BORDER)
    style.map("Treeview.Heading", background=[("active", HEAD_BG)])
    style.map("Treeview", background=[("selected", ACCENT_SOFT)], foreground=[("selected", TEXT)])

    # 스크롤바
    style.configure("Vertical.TScrollbar", background=BORDER_STRONG, troughcolor=BG, bordercolor=BG,
                    arrowcolor=MUTED, lightcolor=BORDER_STRONG, darkcolor=BORDER_STRONG)

    root.configure(background=BG)
    root.option_add("*Text.font", fonts.base)
    root.option_add("*Listbox.font", fonts.base)


# ---------------------------------------------------------------- 위젯 도우미

def card(parent: tk.Misc, **kwargs) -> tk.Frame:
    """흰 바탕에 1px 테두리가 있는 카드. 내용은 반환된 프레임에 넣는다."""
    outer = tk.Frame(parent, bg=BORDER)
    inner = tk.Frame(outer, bg=CARD, **kwargs)
    inner.pack(fill="both", expand=True, padx=1, pady=1)
    inner.outer = outer  # type: ignore[attr-defined]
    return inner


def label(parent: tk.Misc, text: str = "", *, font=None, fg: str = TEXT, bg: str | None = None, **kw) -> tk.Label:
    if bg is None:
        bg = parent.cget("background") if "background" in parent.keys() else BG
    kw.setdefault("anchor", "w")
    return tk.Label(parent, text=text, font=font, fg=fg, bg=bg, **kw)


def chip(parent: tk.Misc, text: str, *, fg: str, bg: str, font) -> tk.Label:
    return tk.Label(parent, text=text, font=font, fg=fg, bg=bg, padx=10, pady=2)


class RichText(tk.Frame):
    """마크업을 이탤릭·굵게·첨자로 그리는 읽기 전용 텍스트. 내용에 맞춰 높이가 바뀐다.

    Text의 height는 글꼴 줄 수 단위라 첨자가 있는 줄이 잘리므로, 프레임 픽셀 높이로 맞춘다.
    """

    def __init__(self, parent: tk.Misc, fonts: Fonts, *, size: int | None = None, max_lines: int = 14, **kw):
        bg = kw.pop("bg", CARD)
        super().__init__(parent, bg=bg)
        kw.setdefault("wrap", "word")
        kw.setdefault("relief", "flat")
        kw.setdefault("borderwidth", 0)
        kw.setdefault("highlightthickness", 0)
        kw.setdefault("fg", TEXT)
        kw.setdefault("cursor", "arrow")
        self.fonts = fonts
        self.size = size or fonts.size
        self.max_lines = max_lines
        self._last_width = 0
        self.text = tk.Text(self, bg=bg, **kw)
        self.text._rich = True  # type: ignore[attr-defined]  # 키 처리에서 입력창과 구분
        self.text.configure(font=fonts.rich(frozenset(), self.size), state="disabled", height=1)
        self.text.pack(fill="both", expand=True)
        self.text.bind("<Configure>", self._on_configure)
        self.text.bind("<Key>", lambda _e: "break")

    # Text 메서드 위임 (get, tag_names, tag_cget, bind ...)
    def __getattr__(self, name):
        return getattr(self.__dict__["text"], name)

    def configure(self, cnf=None, **kw):  # bg는 프레임과 Text 양쪽에
        if "bg" in kw or "background" in kw:
            color = kw.get("bg", kw.get("background"))
            self.text.configure(bg=color)
            return super().configure(bg=color)
        return super().configure(cnf, **kw)

    config = configure

    def bind(self, sequence=None, func=None, add=None):  # 클릭 등은 Text 쪽에 묶는다
        return self.text.bind(sequence, func, add)

    def set_markup(self, text: str) -> None:
        t = self.text
        t.configure(state="normal")
        t.delete("1.0", "end")
        for seg in parse_markup(text):
            if not seg.styles:
                t.insert("end", seg.text)
                continue
            tag = "s_" + "_".join(sorted(seg.styles))
            if tag not in t.tag_names():
                offset = 0
                if "sup" in seg.styles:
                    offset = max(3, self.size // 2)
                elif "sub" in seg.styles:
                    offset = -max(2, self.size // 4)
                t.tag_configure(tag, font=self.fonts.rich(seg.styles, self.size), offset=offset)
            t.insert("end", seg.text, tag)
        t.configure(state="disabled")
        self.after_idle(self._fit)

    def _on_configure(self, event) -> None:
        if event.width != self._last_width:  # 높이만 바뀐 Configure는 무시 (무한 반복 방지)
            self._last_width = event.width
            self.after_idle(self._fit)

    def _fit(self) -> None:
        """표시 줄 수("end"까지 세어야 정확)로 height를 정한 뒤, 그래도 잘리면 픽셀 높이를 늘린다."""
        t = self.text
        try:
            n = t.count("1.0", "end", "displaylines")
            lines = max(1, min((n[0] if isinstance(n, tuple) else n) or 1, self.max_lines))
            t.configure(height=lines)
            self.pack_propagate(True)
            self.update_idletasks()
            first, last = t.yview()
            if lines < self.max_lines and 0 < last < 1.0:
                pad = 2 * (int(str(t.cget("pady"))) + int(str(t.cget("borderwidth"))))
                inner = max(1, t.winfo_height() - pad)
                self.configure(height=math.ceil(inner / last) + pad)
                self.pack_propagate(False)
        except (tk.TclError, ValueError):
            return


class ScrollFrame(tk.Frame):
    """세로 스크롤되는 영역. 내용은 .body 에 넣는다."""

    def __init__(self, parent: tk.Misc, bg: str = CARD, **kw):
        super().__init__(parent, bg=bg, **kw)
        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0, borderwidth=0)
        self.scroll = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.body = tk.Frame(self.canvas, bg=bg)
        self._window = self.canvas.create_window((0, 0), window=self.body, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scroll.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scroll.pack(side="right", fill="y")  # 항상 표시: 숨기면 폭이 바뀌어 줄바꿈이 흔들린다
        self.body.bind("<Configure>", self._on_body_configure)
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfigure(self._window, width=e.width))
        for w in (self.canvas, self.body):
            w.bind("<Enter>", lambda _e: self._bind_wheel())
            w.bind("<Leave>", lambda _e: self._unbind_wheel())

    def _on_body_configure(self, _event=None) -> None:
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _bind_wheel(self) -> None:
        self.canvas.bind_all("<MouseWheel>", self._wheel)
        self.canvas.bind_all("<Button-4>", self._wheel)
        self.canvas.bind_all("<Button-5>", self._wheel)

    def _unbind_wheel(self) -> None:
        for seq in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            self.canvas.unbind_all(seq)

    def _wheel(self, event) -> None:
        first, last = self.canvas.yview()
        if last - first < 1.0:
            step = -1 if (getattr(event, "num", None) == 4 or event.delta > 0) else 1
            self.canvas.yview_scroll(step, "units")

    def scroll_top(self) -> None:
        self.canvas.yview_moveto(0)

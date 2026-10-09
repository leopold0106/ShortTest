"""GUI 스모크 테스트. 화면(DISPLAY)이 없으면 건너뛴다."""

from pathlib import Path

import pytest

tk = pytest.importorskip("tkinter")

from shorttest.settings import Settings  # noqa: E402

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


@pytest.fixture
def app(monkeypatch, tmp_path):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    from shorttest.ui.app import App

    try:
        application = App(Settings())
    except tk.TclError as exc:
        pytest.skip(f"no display: {exc}")
    application.update()
    yield application
    application.destroy()


class Key:
    def __init__(self, char):
        self.char = char


def test_full_flow(app, monkeypatch):
    from tkinter import messagebox
    from shorttest.ui import theme as T

    assert app.current_view is app.start_view
    assert app.open_exam(EXAMPLES / "sample.questions.txt")
    assert app.current_view is app.exam_view
    view = app.exam_view
    assert len(view.number_buttons) == 6
    assert view.badge.cget("text") == "1"
    assert view.type_chip.cget("text") == "객관식"

    # 1번: 숫자 키로 2 선택 (라디오)
    view._key_digit(Key("2"))
    assert view.responses[1] == {2}
    assert [r.selected for r in view.option_rows] == [False, True, False, False]
    view._key_digit(Key("3"))
    assert view.responses[1] == {3}  # 단일 선택은 바꿔치기
    assert view.number_buttons[1][1].cget("bg") == T.ACCENT_SOFT  # 현재 문제
    view._key_digit(Key("2"))

    # 2번: 단답형 입력
    view.next()
    assert view._entry is not None
    view._entry_var.set("엽록체")
    assert view.responses[2] == "엽록체"
    assert view.number_buttons[1][1].cget("bg") == T.ACCENT  # 응답한 문제

    # 3번: 복수 정답이라 체크 상자, 토글
    view.next()
    assert view.type_chip.cget("text") == "객관식 · 모두 고르기"
    assert all(r.multi for r in view.option_rows)
    view.toggle_choice(1)
    view.toggle_choice(3)
    view.toggle_choice(2)
    view.toggle_choice(2)
    assert view.responses[3] == {1, 3}
    # 보기에 첨자 마크업이 렌더링됨
    assert view.option_rows[2].text.get("1.0", "end-1c") == "H2SO4"
    assert "s_sub" in view.option_rows[2].text.tag_names()

    # 4번은 비워 두고, 5번은 오답, 6번은 학명(마크업) 정답
    view.show_question(4)
    view.toggle_choice(3)
    view.show_question(5)
    assert view.q_text.get("1.0", "end-1c").startswith("대장균의 학명은 Escherichia coli이다.")
    view._entry_var.set("escherichia ")
    assert view.answered_count() == 5

    # 번호 버튼으로 이동했을 때 이전 응답이 유지되는지
    view.number_buttons[3][1].invoke()
    assert view.index == 2
    assert [r.selected for r in view.option_rows] == [True, False, True, False]

    monkeypatch.setattr(messagebox, "askyesno", lambda *a, **k: True)
    view.submit()
    assert app.current_view is app.result_view
    result = app.result_view.result
    assert result.earned == 2 + 1 + 3 + 1
    assert result.total == 9
    rows = [app.result_view.tree.item(i)["values"] for i in app.result_view.tree.get_children()]
    assert rows[3][2] == "(미응답)" and rows[3][4] == "X"
    assert rows[3][3] == "물 | H2O | 2H2O | H2O"
    assert rows[4][4] == "X"
    assert app.result_view.cnt_blank.cget("text") == "미응답 1"
    assert app.result_view.cnt_bad.cget("text") == "오답 1"

    # 틀린 문제만 다시
    app.result_view._retry_wrong()
    assert app.current_view is app.exam_view
    assert sorted(view.number_buttons) == [4, 5]
    assert view.title_label.cget("text").endswith("(오답 다시 풀기)")


def test_parse_error_dialog(app, monkeypatch, tmp_path):
    q = tmp_path / "bad.questions.txt"
    q.write_text("1. a\n1) only\n", encoding="utf-8")
    (tmp_path / "bad.answers.txt").write_text("1: 1\n", encoding="utf-8")
    shown = []
    import shorttest.ui.app as app_module
    monkeypatch.setattr(app_module, "show_parse_errors", lambda parent, issues: shown.append(issues))
    assert not app.open_exam(q)
    assert shown and any("1개뿐" in i.message for i in shown[0])
    assert app.current_view is app.start_view


def test_help_window(app):
    from shorttest.ui.dialogs import HelpWindow

    win = HelpWindow.show(app)
    assert win.winfo_exists()
    assert HelpWindow.show(app) is win
    win.destroy()


def test_rich_text_sub_sup(app):
    from shorttest.ui import theme as T

    w = T.RichText(app, app.fonts)
    w.set_markup("Ca^{2+} 와 *E. coli* 와 H_{2}O")
    assert w.get("1.0", "end-1c") == "Ca2+ 와 E. coli 와 H2O"
    assert set(w.tag_names()) >= {"s_sup", "s_i", "s_sub"}
    assert int(w.tag_cget("s_sup", "offset")) > 0
    assert int(w.tag_cget("s_sub", "offset")) < 0


def test_timer_and_auto_submit(app, monkeypatch, tmp_path):
    import time
    from tkinter import messagebox
    from shorttest.ui import theme as T

    q = tmp_path / "t.questions.txt"
    q.write_text("# 시간: 1\n1. q\n1) a\n2) b\n", encoding="utf-8")
    (tmp_path / "t.answers.txt").write_text("1: 2\n", encoding="utf-8")
    assert app.open_exam(q)
    view = app.exam_view
    assert view.timer_label.cget("text").startswith("⏱ 01:00") or view.timer_label.cget("text").startswith("⏱ 00:59")
    assert view.desc_label.cget("text").endswith("제한 1분")
    assert view._timer_job is not None

    view.toggle_choice(2)
    shown = []
    monkeypatch.setattr(messagebox, "showinfo", lambda *a, **k: shown.append(a))
    view.deadline = time.monotonic() - 1  # 시간이 끝난 것으로
    view._tick()
    assert shown and "시간 종료" in shown[0][0]
    assert app.current_view is app.result_view
    assert view._timer_job is None
    result = app.result_view.result
    assert result.timed_out and result.earned == 1
    assert "시간 종료로 자동 제출" in app.result_view.time_label.cget("text")
    assert view.timer_label.cget("fg") == T.BAD_FG


def test_no_time_limit_label(app):
    assert app.open_exam(EXAMPLES / "sample.questions.txt")
    assert app.exam_view.timer_label.cget("text") == "⏱ 10:00" or app.exam_view.timer_label.cget("text") == "⏱ 09:59"
    app.exam_view.exam.time_limit_minutes = 0
    app.exam_view.load(app.exam_view.exam, app.exam_view.key)
    assert app.exam_view.timer_label.cget("text") == "제한 시간 없음"
    assert app.exam_view._timer_job is None


def test_font_family_is_malgun_when_available(app, monkeypatch):
    from tkinter import font as tkfont
    from shorttest.ui import theme as T

    if any(n in set(tkfont.families(app)) for n in T.FONT_FAMILY_CANDIDATES):
        assert app.fonts.family in T.FONT_FAMILY_CANDIDATES
    monkeypatch.setattr(tkfont, "families", lambda *_: ["Malgun Gothic", "Arial"])
    assert T.pick_font_family(app) == "Malgun Gothic"
    monkeypatch.setattr(tkfont, "families", lambda *_: ["맑은 고딕", "Malgun Gothic"])
    assert T.pick_font_family(app) == "맑은 고딕"
    monkeypatch.setattr(tkfont, "families", lambda *_: ["Arial"])
    monkeypatch.setattr(T.sys, "platform", "win32")
    assert T.pick_font_family(app) == "Malgun Gothic"
    # 실제 Font 객체들이 같은 글꼴을 쓰는지
    assert app.fonts.heading.cget("family") == app.fonts.family
    assert tkfont.nametofont("TkDefaultFont").cget("family") == app.fonts.family

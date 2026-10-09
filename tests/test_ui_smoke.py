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


def test_full_flow(app, monkeypatch):
    from tkinter import messagebox

    assert app.current_view is app.start_view
    assert app.open_exam(EXAMPLES / "sample.questions.txt")
    assert app.current_view is app.exam_view
    view = app.exam_view
    assert len(view.tree.get_children()) == 5
    assert view.q_header.cget("text").startswith("1.")

    # 1번: 라디오 → 숫자 키로 2 선택
    class Key:
        char = "2"
    view._key_digit(Key())
    assert view.responses[1] == {2}
    assert view.tree.item("1")["values"][1] == "✓"

    # 2번: 단답형 입력
    view.next()
    assert view._entry is not None
    view._answer_vars[0].set("엽록체")
    assert view.responses[2] == "엽록체"

    # 3번: 복수 정답이라 체크 상자
    view.next()
    assert all(isinstance(v, tk.BooleanVar) for v in view._answer_vars)
    view._answer_vars[0].set(True)
    view._answer_vars[2].set(True)
    view._save_choices()
    assert view.responses[3] == {1, 3}

    # 4번은 비워 두고, 5번은 오답
    view.show_question(4)
    view._answer_vars[0].set(3)
    view._save_choices()
    assert view.answered_count() == 4

    # 목록 클릭으로 이동했을 때 이전 응답이 유지되는지
    view.tree.selection_set("3")
    view._on_tree_select()
    assert view.index == 2
    assert [v.get() for v in view._answer_vars] == [True, False, True, False]

    monkeypatch.setattr(messagebox, "askyesno", lambda *a, **k: True)
    view.submit()
    assert app.current_view is app.result_view
    result = app.result_view.result
    assert result.earned == 2 + 1 + 3
    assert result.total == 8
    rows = [app.result_view.tree.item(i)["values"] for i in app.result_view.tree.get_children()]
    assert rows[3][2] == "(미응답)" and rows[3][4] == "X"
    assert rows[4][4] == "X"

    # 틀린 문제만 다시
    app.result_view._retry_wrong()
    assert app.current_view is app.exam_view
    assert [int(i) for i in view.tree.get_children()] == [4, 5]
    assert view.title_label.cget("text").endswith("(오답 다시 풀기)")


def test_parse_error_dialog(app, monkeypatch, tmp_path):
    from shorttest.ui import dialogs

    q = tmp_path / "bad.questions.txt"
    q.write_text("1. a\n1) only\n", encoding="utf-8")
    (tmp_path / "bad.answers.txt").write_text("1: 1\n", encoding="utf-8")
    shown = []
    monkeypatch.setattr(dialogs, "show_parse_errors", lambda parent, issues: shown.append(issues))
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

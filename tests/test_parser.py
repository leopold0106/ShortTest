from pathlib import Path

import pytest

from shorttest.core.parser import (
    ParseError,
    default_answers_path,
    load_exam,
    parse_answers_text,
    parse_questions_text,
)

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


def test_parse_example_files():
    exam, key, warnings = load_exam(EXAMPLES / "sample.questions.txt", EXAMPLES / "sample.answers.txt")
    assert warnings == []
    assert exam.title == "샘플 시험 (과학)"
    assert exam.description.startswith("객관식 3문항")
    assert [q.number for q in exam.questions] == [1, 2, 3, 4, 5]
    assert exam.questions[0].points == 2
    assert exam.questions[0].text == "세포 안에서 에너지를 생산하는 소기관은?"
    assert [c.text for c in exam.questions[0].choices] == ["핵", "미토콘드리아", "리보솜", "골지체"]
    assert not exam.questions[1].is_multiple_choice
    assert exam.questions[3].text == "다음 반응의 생성물을 쓰시오.\n   2H2 + O2 -> ?"
    assert [c.number for c in exam.questions[4].choices] == [1, 2, 3, 4]  # ① 보기
    assert key.answers == {1: {2}, 2: ["엽록체"], 3: {1, 3}, 4: ["물", "H2O", "2H2O"], 5: {1}}
    assert exam.total_points == 2 + 1 + 3 + 1 + 1


def test_title_defaults_to_filename():
    exam = parse_questions_text("1. 질문", Path("biology_midterm.questions.txt"))
    assert exam.title == "biology_midterm"


def test_bom_and_points():
    exam = parse_questions_text("﻿# 제목: T\n\n1. 질문 [10점]\n1) a\n2) b\n")
    assert exam.title == "T"
    assert exam.questions[0].points == 10
    assert exam.questions[0].text == "질문"


def test_choice_continuation_line():
    exam = parse_questions_text("1. q\n1) 첫 줄\n   이어지는 줄\n2) b\n")
    assert exam.questions[0].choices[0].text == "첫 줄 이어지는 줄"


def _issues(text):
    with pytest.raises(ParseError) as info:
        parse_questions_text(text)
    return [i.message for i in info.value.issues]


def test_question_number_gap():
    msgs = _issues("1. a\n3. b\n")
    assert any("2번이어야" in m for m in msgs)


def test_single_choice_is_error():
    msgs = _issues("1. a\n1) only\n")
    assert any("1개뿐" in m for m in msgs)


def test_text_before_first_question():
    msgs = _issues("설명문\n1. a\n")
    assert any("앞에 내용" in m for m in msgs)


def test_empty_file():
    msgs = _issues("# 제목: x\n")
    assert any("하나도 없습니다" in m for m in msgs)


def test_choice_number_gap():
    msgs = _issues("1. a\n1) x\n3) y\n")
    assert any("보기 번호가 2)" in m for m in msgs)


def test_all_errors_reported_at_once():
    msgs = _issues("설명문\n1. a\n1) only\n3. b\n")
    assert len(msgs) == 3


def _answer_issues(answers, questions="1. q\n1) a\n2) b\n3) c\n\n2. short\n"):
    exam = parse_questions_text(questions)
    with pytest.raises(ParseError) as info:
        parse_answers_text(answers, exam)
    return [i.message for i in info.value.issues]


def test_answers_ok_variants():
    exam = parse_questions_text("1. q\n1) a\n2) b\n3) c\n\n2. short\n")
    key = parse_answers_text("1： ③\n2: 물 | H2O |\n", exam)
    assert key.answers == {1: {3}, 2: ["물", "H2O"]}
    key = parse_answers_text("1: 1，3\n2: x\n", exam)
    assert key.answers[1] == {1, 3}


def test_answers_missing():
    assert any("정답이 없는 문제: 2번" in m for m in _answer_issues("1: 1\n"))


def test_answers_out_of_range():
    assert any("범위" in m for m in _answer_issues("1: 4\n2: x\n"))


def test_answers_text_for_mc():
    assert any("객관식" in m for m in _answer_issues("1: 미토콘드리아\n2: x\n"))


def test_answers_duplicate_and_unknown():
    msgs = _answer_issues("1: 1\n1: 2\n2: x\n9: y\n")
    assert any("중복" in m for m in msgs)
    assert any("9번 문제가 없습니다" in m for m in msgs)


def test_answers_bad_line():
    assert any("'번호: 정답'" in m for m in _answer_issues("1 - 1\n2: x\n"))


def test_cp949_fallback(tmp_path):
    q = tmp_path / "t.questions.txt"
    a = tmp_path / "t.answers.txt"
    q.write_bytes("1. 한글 문제\n".encode("cp949"))
    a.write_text("1: 답\n", encoding="utf-8")
    exam, key, warnings = load_exam(q, a)
    assert exam.questions[0].text == "한글 문제"
    assert len(warnings) == 1 and "CP949" in warnings[0]


def test_load_exam_collects_both_files(tmp_path):
    q = tmp_path / "t.questions.txt"
    a = tmp_path / "t.answers.txt"
    q.write_text("1. a\n1) x\n", encoding="utf-8")
    a.write_text("1: 1\n", encoding="utf-8")
    with pytest.raises(ParseError) as info:
        load_exam(q, a)
    assert info.value.issues[0].filename == "t.questions.txt"


def test_default_answers_path():
    assert default_answers_path(Path("x/a.questions.txt")) == Path("x/a.answers.txt")
    assert default_answers_path(Path("x/a.txt")) == Path("x/a.answers.txt")

from shorttest.core.grader import GradeOptions, grade
from shorttest.core.parser import parse_answers_text, parse_questions_text
from shorttest.core.report import default_result_filename, format_answer, format_response, format_result

Q = """1. 단일 [2점]
1) a
2) b
3) c

2. 복수 [3점]
1) a
2) b
3) c

3. 단답

4. 단답 복수 인정
"""
A = "1: 2\n2: 1, 3\n3: 엽록체\n4: 물 | H2O\n"


def _exam():
    exam = parse_questions_text(Q)
    return exam, parse_answers_text(A, exam)


def test_grade_all():
    exam, key = _exam()
    result = grade(exam, key, {1: {2}, 2: {1, 3}, 3: " 엽록체 ", 4: "ｈ２ｏ"})
    assert [i.correct for i in result.items] == [True, True, True, True]
    assert result.earned == result.total == 7
    assert result.percent == 100.0


def test_partial_and_missing():
    exam, key = _exam()
    result = grade(exam, key, {1: {2}, 2: {1}, 3: "", 4: None})
    assert [i.correct for i in result.items] == [True, False, False, False]
    assert result.earned == 2
    assert result.correct_count == 1
    assert result.wrong_numbers == {2, 3, 4}
    assert not result.items[2].answered
    assert result.items[2].user_answer is None


def test_inner_spaces_option():
    exam, key = _exam()
    assert not grade(exam, key, {3: "엽록 체"}).items[2].correct
    assert grade(exam, key, {3: "엽록 체"}, GradeOptions(ignore_inner_spaces=True)).items[2].correct


def test_subset_exam():
    exam, key = _exam()
    sub = exam.subset({2, 4}, " (오답 다시 풀기)")
    assert [q.number for q in sub.questions] == [2, 4]
    result = grade(sub, key, {2: {1, 3}, 4: "물"})
    assert result.total == 4 and result.earned == 4


def test_report_text():
    exam, key = _exam()
    exam.title = "T"
    result = grade(exam, key, {1: {2}, 2: {3, 1}, 3: None, 4: "H2O"})
    text = format_result(result)
    assert "시험: T" in text
    assert "총점: 6 / 7 (86%)   정답: 3 / 4" in text
    assert "3\tX\t0/1\t단답형\t(미응답)\t엽록체" in text
    assert "2\tO\t3/3\t객관식\t1, 3\t1, 3" in text
    assert format_answer({3, 1}) == "1, 3"
    assert format_response("  ") == "(미응답)"
    assert default_result_filename(result).startswith("result.result.")

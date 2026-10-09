"""채점."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .model import AnswerKey, Exam, QuestionResult, ResponseValue, Result
from .normalize import normalize


@dataclass
class GradeOptions:
    ignore_inner_spaces: bool = False


def is_correct(question_number: int, response: ResponseValue, key: AnswerKey, options: GradeOptions) -> bool:
    expected = key.answers[question_number]
    if response is None:
        return False
    if isinstance(expected, set):
        return isinstance(response, set) and response == expected
    if not isinstance(response, str):
        return False
    given = normalize(response, ignore_inner_spaces=options.ignore_inner_spaces)
    if not given:
        return False
    return any(given == normalize(a, ignore_inner_spaces=options.ignore_inner_spaces) for a in expected)


def grade(
    exam: Exam,
    key: AnswerKey,
    responses: dict[int, ResponseValue],
    options: GradeOptions | None = None,
    *,
    elapsed_seconds: int | None = None,
    timed_out: bool = False,
) -> Result:
    options = options or GradeOptions()
    items: list[QuestionResult] = []
    for q in exam.questions:
        response = responses.get(q.number)
        if isinstance(response, str) and not response.strip():
            response = None
        if isinstance(response, set) and not response:
            response = None
        correct = is_correct(q.number, response, key, options)
        items.append(
            QuestionResult(
                question=q,
                user_answer=response,
                correct_answer=key.answers[q.number],
                correct=correct,
                earned=q.points if correct else 0,
            )
        )
    return Result(exam=exam, items=items, finished_at=datetime.now(), elapsed_seconds=elapsed_seconds, timed_out=timed_out)

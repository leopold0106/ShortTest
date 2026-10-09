"""데이터 모델. GUI와 무관한 순수 데이터 구조만 둔다."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass
class Choice:
    number: int
    text: str


@dataclass
class Question:
    number: int
    text: str
    points: int = 1
    choices: list[Choice] = field(default_factory=list)

    @property
    def is_multiple_choice(self) -> bool:
        return bool(self.choices)

    @property
    def type_label(self) -> str:
        return "객관식" if self.is_multiple_choice else "단답형"


@dataclass
class Exam:
    title: str = ""
    description: str = ""
    questions: list[Question] = field(default_factory=list)
    source_path: Path | None = None

    @property
    def total_points(self) -> int:
        return sum(q.points for q in self.questions)

    def subset(self, numbers: set[int], title_suffix: str = "") -> "Exam":
        """지정한 번호의 문제만 담은 새 Exam. 번호는 원래 번호를 유지한다."""
        return Exam(
            title=self.title + title_suffix,
            description=self.description,
            questions=[q for q in self.questions if q.number in numbers],
            source_path=self.source_path,
        )


# 객관식 정답: 보기 번호 집합 / 단답형 정답: 인정 답안 목록
AnswerValue = set[int] | list[str]
# 사용자 응답: 객관식은 선택한 번호 집합, 단답형은 문자열, 미응답은 None
ResponseValue = set[int] | str | None


@dataclass
class AnswerKey:
    answers: dict[int, AnswerValue] = field(default_factory=dict)
    source_path: Path | None = None

    def is_multi_select(self, number: int) -> bool:
        value = self.answers.get(number)
        return isinstance(value, set) and len(value) > 1


@dataclass
class QuestionResult:
    question: Question
    user_answer: ResponseValue
    correct_answer: AnswerValue
    correct: bool
    earned: int

    @property
    def answered(self) -> bool:
        if self.user_answer is None:
            return False
        if isinstance(self.user_answer, str):
            return self.user_answer.strip() != ""
        return len(self.user_answer) > 0


@dataclass
class Result:
    exam: Exam
    items: list[QuestionResult]
    finished_at: datetime

    @property
    def total(self) -> int:
        return sum(item.question.points for item in self.items)

    @property
    def earned(self) -> int:
        return sum(item.earned for item in self.items)

    @property
    def correct_count(self) -> int:
        return sum(1 for item in self.items if item.correct)

    @property
    def percent(self) -> float:
        return (self.earned / self.total * 100.0) if self.total else 0.0

    @property
    def wrong_numbers(self) -> set[int]:
        return {item.question.number for item in self.items if not item.correct}

"""문제지(.questions.txt)와 정답지(.answers.txt) 파서.

오류는 첫 번째에서 멈추지 않고 모두 모아 ParseError 하나로 보고한다.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .model import AnswerKey, AnswerValue, Choice, Exam, Question

ANSWERS_SUFFIX = ".answers.txt"
QUESTIONS_SUFFIX = ".questions.txt"

CIRCLED = "①②③④⑤⑥⑦⑧⑨⑩"

_RE_META = re.compile(r"^#\s*(제목|설명|시간)\s*[:：]\s*(.*)$")
_RE_COMMENT = re.compile(r"^#")
_RE_QUESTION = re.compile(r"^(\d+)\.\s+(.*)$")
_RE_CHOICE = re.compile(r"^\s*(?:(\d+)\)|([" + CIRCLED + r"]))\s*(.*)$")
_RE_POINTS = re.compile(r"\s*\[\s*(\d+)\s*점\s*\]\s*$")
_RE_ANSWER = re.compile(r"^(\d+)\s*[:：]\s*(.*)$")


@dataclass
class ParseIssue:
    path: Path | None
    line: int  # 0이면 특정 줄과 무관한 오류
    message: str

    @property
    def filename(self) -> str:
        return self.path.name if self.path else ""

    def __str__(self) -> str:
        where = self.filename
        if self.line:
            where += f" {self.line}줄"
        return f"{where}: {self.message}" if where else self.message


class ParseError(Exception):
    def __init__(self, issues: list[ParseIssue]):
        self.issues = issues
        super().__init__("\n".join(str(i) for i in issues))


def read_text_file(path: Path) -> tuple[str, str | None]:
    """UTF-8(BOM 허용)로 읽고, 실패하면 CP949로 읽는다.

    반환: (내용, 경고 메시지 또는 None)
    """
    data = path.read_bytes()
    try:
        return data.decode("utf-8-sig"), None
    except UnicodeDecodeError:
        pass
    try:
        text = data.decode("cp949")
    except UnicodeDecodeError as exc:
        raise ParseError(
            [ParseIssue(path, 0, "파일 인코딩을 읽을 수 없습니다. 메모장에서 UTF-8로 저장하세요.")]
        ) from exc
    return text, f"{path.name}: UTF-8이 아니라 CP949(ANSI)로 읽었습니다. 가능하면 UTF-8로 저장하세요."


def _circled_to_int(ch: str) -> int:
    return CIRCLED.index(ch) + 1


# ---------------------------------------------------------------- 문제지

def parse_questions_text(text: str, path: Path | None = None) -> Exam:
    issues: list[ParseIssue] = []
    text = text.lstrip("\ufeff")
    exam = Exam(source_path=path)
    if path is not None:
        exam.title = path.name.removesuffix(QUESTIONS_SUFFIX).removesuffix(".txt")

    current: Question | None = None
    body_lines: list[str] = []  # 현재 문제의 본문 줄들
    in_choices = False

    def flush() -> None:
        nonlocal current, body_lines, in_choices
        if current is None:
            return
        current.text = "\n".join(body_lines).strip()
        if not current.text:
            issues.append(ParseIssue(path, current_line_no, f"{current.number}번 문제의 내용이 비어 있습니다."))
        if len(current.choices) == 1:
            issues.append(
                ParseIssue(path, current_line_no, f"{current.number}번 문제의 보기가 1개뿐입니다. 2개 이상 쓰거나, 단답형이면 보기를 지우세요.")
            )
        exam.questions.append(current)
        current = None
        body_lines = []
        in_choices = False

    current_line_no = 0
    for line_no, raw in enumerate(text.splitlines(), start=1):
        line = raw.rstrip("\r\n")

        if current is None and not line.strip():
            continue

        m = _RE_META.match(line)
        if m and current is None:
            key, value = m.group(1), m.group(2).strip()
            if key == "제목":
                exam.title = value
            elif key == "설명":
                exam.description = value
            else:
                minutes = re.sub(r"\s*분\s*$", "", value)
                if minutes.isascii() and minutes.isdigit():
                    exam.time_limit_minutes = int(minutes)
                else:
                    issues.append(ParseIssue(path, line_no, f"'# 시간:'은 분 단위 숫자여야 합니다. (0 = 무제한) 지금 값: '{value}'"))
            continue
        if _RE_COMMENT.match(line):
            continue

        m = _RE_QUESTION.match(line)
        if m:
            flush()
            number = int(m.group(1))
            first = m.group(2)
            points = 1
            pm = _RE_POINTS.search(first)
            if pm:
                points = int(pm.group(1))
                first = first[: pm.start()]
                if points <= 0:
                    issues.append(ParseIssue(path, line_no, f"{number}번 문제의 배점은 1점 이상이어야 합니다."))
            expected = len(exam.questions) + 1
            if number != expected:
                issues.append(ParseIssue(path, line_no, f"문제 번호가 {expected}번이어야 하는데 {number}번입니다. 번호는 1부터 순서대로 매기세요."))
            current = Question(number=number, text="", points=points)
            current_line_no = line_no
            body_lines = [first.rstrip()]
            in_choices = False
            continue

        if current is None:
            issues.append(ParseIssue(path, line_no, "문제 번호(예: '1. ') 앞에 내용이 있습니다. 설명은 '#'으로 시작하세요."))
            continue

        m = _RE_CHOICE.match(line)
        if m:
            number = int(m.group(1)) if m.group(1) else _circled_to_int(m.group(2))
            expected = len(current.choices) + 1
            if number != expected:
                issues.append(ParseIssue(path, line_no, f"{current.number}번 문제의 보기 번호가 {expected})이어야 하는데 {number})입니다."))
            current.choices.append(Choice(number=number, text=m.group(3).strip()))
            in_choices = True
            continue

        if in_choices:
            if line.strip():
                current.choices[-1].text = (current.choices[-1].text + " " + line.strip()).strip()
            continue

        body_lines.append(line.rstrip())

    flush()

    if not exam.questions:
        issues.append(ParseIssue(path, 0, "문제가 하나도 없습니다. '1. 문제 내용' 형태로 시작하세요."))
    if issues:
        raise ParseError(issues)
    return exam


def parse_questions(path: Path) -> tuple[Exam, list[str]]:
    """반환: (Exam, 경고 목록)"""
    text, warning = read_text_file(path)
    exam = parse_questions_text(text, path)
    return exam, ([warning] if warning else [])


# ---------------------------------------------------------------- 정답지

def _parse_answer_value(raw: str, question: Question, path: Path | None, line_no: int, issues: list[ParseIssue]) -> AnswerValue | None:
    raw = raw.strip()
    if not raw:
        issues.append(ParseIssue(path, line_no, f"{question.number}번 정답이 비어 있습니다."))
        return None

    if question.is_multiple_choice:
        chosen: set[int] = set()
        for token in re.split(r"[,，]", raw):
            token = token.strip()
            if not token:
                continue
            if len(token) == 1 and token in CIRCLED:
                n = _circled_to_int(token)
            elif token.isascii() and token.isdigit():
                n = int(token)
            else:
                issues.append(ParseIssue(path, line_no, f"{question.number}번은 객관식이므로 보기 번호를 쓰세요. ('{token}'은 번호가 아닙니다)"))
                return None
            if not 1 <= n <= len(question.choices):
                issues.append(ParseIssue(path, line_no, f"{question.number}번 정답 {n}은 보기 범위(1~{len(question.choices)})를 벗어납니다."))
                return None
            chosen.add(n)
        if not chosen:
            issues.append(ParseIssue(path, line_no, f"{question.number}번 정답이 비어 있습니다."))
            return None
        return chosen

    accepted = [part.strip() for part in raw.split("|")]
    accepted = [part for part in accepted if part]
    if not accepted:
        issues.append(ParseIssue(path, line_no, f"{question.number}번 정답이 비어 있습니다."))
        return None
    return accepted


def parse_answers_text(text: str, exam: Exam, path: Path | None = None) -> AnswerKey:
    issues: list[ParseIssue] = []
    key = AnswerKey(source_path=path)
    by_number = {q.number: q for q in exam.questions}
    seen_lines: dict[int, int] = {}

    for line_no, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or _RE_COMMENT.match(line):
            continue
        m = _RE_ANSWER.match(line)
        if not m:
            issues.append(ParseIssue(path, line_no, "'번호: 정답' 형태가 아닙니다."))
            continue
        number = int(m.group(1))
        if number in seen_lines:
            issues.append(ParseIssue(path, line_no, f"{number}번 정답이 중복됩니다. ({seen_lines[number]}줄에 이미 있음)"))
            continue
        seen_lines[number] = line_no
        question = by_number.get(number)
        if question is None:
            issues.append(ParseIssue(path, line_no, f"문제지에 {number}번 문제가 없습니다."))
            continue
        value = _parse_answer_value(m.group(2), question, path, line_no, issues)
        if value is not None:
            key.answers[number] = value

    missing = [q.number for q in exam.questions if q.number not in seen_lines]
    if missing:
        numbers = ", ".join(str(n) for n in missing)
        issues.append(ParseIssue(path, 0, f"정답이 없는 문제: {numbers}번"))

    if issues:
        raise ParseError(issues)
    return key


def parse_answers(path: Path, exam: Exam) -> tuple[AnswerKey, list[str]]:
    text, warning = read_text_file(path)
    key = parse_answers_text(text, exam, path)
    return key, ([warning] if warning else [])


# ---------------------------------------------------------------- 한 번에

def default_answers_path(questions_path: Path) -> Path:
    name = questions_path.name
    if name.endswith(QUESTIONS_SUFFIX):
        return questions_path.with_name(name[: -len(QUESTIONS_SUFFIX)] + ANSWERS_SUFFIX)
    return questions_path.with_name(questions_path.stem + ANSWERS_SUFFIX)


def load_exam(questions_path: Path, answers_path: Path) -> tuple[Exam, AnswerKey, list[str]]:
    """문제지와 정답지를 함께 읽는다. 오류는 모두 모아 ParseError로 올린다.

    반환: (Exam, AnswerKey, 경고 목록)
    """
    warnings: list[str] = []
    issues: list[ParseIssue] = []
    exam: Exam | None = None
    try:
        exam, w = parse_questions(questions_path)
        warnings += w
    except ParseError as exc:
        issues += exc.issues

    key: AnswerKey | None = None
    if exam is not None:
        try:
            key, w = parse_answers(answers_path, exam)
            warnings += w
        except ParseError as exc:
            issues += exc.issues

    if issues or exam is None or key is None:
        raise ParseError(issues)
    return exam, key, warnings

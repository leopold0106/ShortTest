"""결과 표시용 문자열과 결과 파일 생성."""

from __future__ import annotations

from .markup import strip_markup
from .model import AnswerValue, ResponseValue, Result


def format_answer(value: AnswerValue) -> str:
    if isinstance(value, set):
        return ", ".join(str(n) for n in sorted(value))
    return " | ".join(strip_markup(v) for v in value)


def format_response(value: ResponseValue) -> str:
    if value is None:
        return "(미응답)"
    if isinstance(value, set):
        return ", ".join(str(n) for n in sorted(value)) if value else "(미응답)"
    return value.strip() if value.strip() else "(미응답)"


def format_duration(seconds: int) -> str:
    minutes, sec = divmod(max(0, int(seconds)), 60)
    return f"{minutes}분 {sec}초" if minutes else f"{sec}초"


def format_time_line(result: Result) -> str:
    """'소요 시간: 12분 3초 (제한 30분)' 또는 '소요 시간: 5초 (제한 없음)'. 시간이 끝나 자동 제출되면 표시."""
    if result.elapsed_seconds is None:
        return ""
    limit = f"제한 {result.exam.time_limit_minutes}분" if result.exam.has_time_limit else "제한 없음"
    text = f"소요 시간: {format_duration(result.elapsed_seconds)} ({limit})"
    if result.timed_out:
        text += " · 시간 종료로 자동 제출"
    return text


def format_result(result: Result) -> str:
    lines = [
        "ShortTest 결과",
        f"시험: {result.exam.title}",
        f"일시: {result.finished_at:%Y-%m-%d %H:%M}",
        f"총점: {result.earned} / {result.total} ({result.percent:.0f}%)   정답: {result.correct_count} / {len(result.items)}",
    ]
    if (time_line := format_time_line(result)):
        lines.append(time_line)
    lines += [
        "",
        "번호\t결과\t점수\t유형\t내 답\t정답",
    ]
    for item in result.items:
        q = item.question
        lines.append(
            "\t".join(
                [
                    str(q.number),
                    "O" if item.correct else "X",
                    f"{item.earned}/{q.points}",
                    q.type_label,
                    format_response(item.user_answer),
                    format_answer(item.correct_answer),
                ]
            )
        )
    lines.append("")
    return "\n".join(lines)


def default_result_filename(result: Result) -> str:
    base = result.exam.source_path.name if result.exam.source_path else "result"
    base = base.removesuffix(".questions.txt").removesuffix(".txt")
    return f"{base}.result.{result.finished_at:%Y-%m-%d_%H%M}.txt"

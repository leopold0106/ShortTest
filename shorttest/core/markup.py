"""문제·보기 본문의 인라인 마크업.

  *이탤릭*      학명 등           → italic
  **굵게**                         → bold
  H_{2}O        아래 첨자          → sub
  Ca^{2+}       위 첨자            → sup
  \\*            별표 자체를 쓸 때

파싱 결과는 (텍스트, 스타일 집합) 조각의 목록이다. 스타일은 "i", "b", "sub", "sup".
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

_TOKEN = re.compile(
    r"(?P<esc>\\[*_^\\])"
    r"|(?P<bi>\*\*\*(?=\S)(?P<bi_t>.+?)(?<=\S)\*\*\*)"
    r"|(?P<bold>\*\*(?=\S)(?P<bold_t>.+?)(?<=\S)\*\*)"
    r"|(?P<ital>\*(?=\S)(?P<ital_t>[^*\n]+?)(?<=\S)\*)"
    r"|(?P<sub>_\{(?P<sub_t>[^{}\n]*)\})"
    r"|(?P<sup>\^\{(?P<sup_t>[^{}\n]*)\})",
    re.DOTALL,
)


@dataclass
class Segment:
    text: str
    styles: frozenset[str] = field(default_factory=frozenset)


def parse_markup(text: str, _inherited: frozenset[str] = frozenset()) -> list[Segment]:
    segments: list[Segment] = []
    pos = 0

    def emit(chunk: str, styles: frozenset[str]) -> None:
        if not chunk:
            return
        if segments and segments[-1].styles == styles:
            segments[-1].text += chunk
        else:
            segments.append(Segment(chunk, styles))

    for m in _TOKEN.finditer(text):
        emit(text[pos : m.start()], _inherited)
        pos = m.end()
        if m.group("esc"):
            emit(m.group("esc")[1], _inherited)
        elif m.group("bi"):
            segments.extend(parse_markup(m.group("bi_t"), _inherited | {"b", "i"}))
        elif m.group("bold"):
            segments.extend(parse_markup(m.group("bold_t"), _inherited | {"b"}))
        elif m.group("ital"):
            segments.extend(parse_markup(m.group("ital_t"), _inherited | {"i"}))
        elif m.group("sub"):
            emit(m.group("sub_t"), _inherited | {"sub"})
        elif m.group("sup"):
            emit(m.group("sup_t"), _inherited | {"sup"})
    emit(text[pos:], _inherited)

    # 재귀 결과를 다시 합치기 (같은 스타일의 인접 조각)
    merged: list[Segment] = []
    for seg in segments:
        if merged and merged[-1].styles == seg.styles:
            merged[-1].text += seg.text
        else:
            merged.append(Segment(seg.text, seg.styles))
    return merged


def strip_markup(text: str) -> str:
    """마크업 기호를 제거한 평문. 채점 비교와 표 표시에 쓴다."""
    return "".join(seg.text for seg in parse_markup(text))


def has_markup(text: str) -> bool:
    return strip_markup(text) != text

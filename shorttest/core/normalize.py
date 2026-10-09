"""단답형 답안 정규화."""

from __future__ import annotations

import re
import unicodedata

_WS = re.compile(r"\s+")


def normalize(text: str, *, ignore_inner_spaces: bool = False) -> str:
    """비교용 문자열로 바꾼다.

    - NFKC 정규화: 전각/반각, 호환 문자 통일 (Ｈ２Ｏ → H2O)
    - 앞뒤 공백 제거
    - 영문 대소문자 무시
    - 내부 연속 공백은 하나로 (옵션: 모두 제거)
    """
    text = unicodedata.normalize("NFKC", text)
    text = text.strip().casefold()
    if ignore_inner_spaces:
        return _WS.sub("", text)
    return _WS.sub(" ", text)

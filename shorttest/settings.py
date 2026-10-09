"""설정 저장/로드. Windows: %APPDATA%\\ShortTest\\settings.json"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

from shorttest import APP_NAME

MAX_RECENT = 5


def config_dir() -> Path:
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA") or Path.home())
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    return base / APP_NAME


def settings_path() -> Path:
    return config_dir() / "settings.json"


def error_log_path() -> Path:
    return config_dir() / "error.log"


@dataclass
class Settings:
    recent_files: list[str] = field(default_factory=list)
    ignore_inner_spaces: bool = False
    always_checkbox: bool = False
    window_width: int = 1000
    window_height: int = 700

    @classmethod
    def load(cls) -> "Settings":
        try:
            data = json.loads(settings_path().read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return cls()
        obj = cls()
        for key, value in data.items():
            if hasattr(obj, key) and isinstance(value, type(getattr(obj, key))):
                setattr(obj, key, value)
        obj.recent_files = [p for p in obj.recent_files if isinstance(p, str)][:MAX_RECENT]
        return obj

    def save(self) -> None:
        try:
            config_dir().mkdir(parents=True, exist_ok=True)
            settings_path().write_text(json.dumps(asdict(self), ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError:
            pass  # 설정 저장 실패는 프로그램 동작에 영향 없음

    def add_recent(self, path: Path) -> None:
        text = str(path)
        self.recent_files = [text] + [p for p in self.recent_files if p != text]
        self.recent_files = self.recent_files[:MAX_RECENT]

    def remove_recent(self, path: Path) -> None:
        self.recent_files = [p for p in self.recent_files if p != str(path)]

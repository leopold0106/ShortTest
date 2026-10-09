# ShortTest GUI 구현 계획

## 1. 기술 스택: Python 3.12+ / tkinter(ttk) / PyInstaller

| 후보 | 장점 | 단점 | 판단 |
|---|---|---|---|
| **Python + tkinter** | 표준 라이브러리만으로 동작(추가 설치 없음), Windows에서 네이티브 `vista` 테마 사용, 한글 IME 정상 동작, 핵심 로직을 GUI 없이 테스트 가능 | 화면이 화려하진 않음 | **채택** |
| Python + PySide6 | 보기 좋은 UI | 의존성 100MB+, exe 크기 큼 | 필요 시 UI 계층만 교체 |
| C# WPF/WinForms | 가장 Windows다움, 단일 exe | Windows에서만 빌드 가능, 별도 툴체인 | 보류 |
| Electron | 웹 기술 | 수백 MB, 채점기엔 과함 | 제외 |

핵심 원칙: **파싱·채점 로직(core)과 화면(ui)을 완전히 분리**한다. core는 tkinter를 import하지 않으며 pytest로 검증한다. 화면 라이브러리를 바꾸더라도 core는 그대로 쓴다.

## 2. 디렉터리 구조

```text
shorttest/
  __init__.py
  __main__.py          # python -m shorttest  → App 실행
  core/
    model.py           # Question, Choice, AnswerKey, Exam, Result 데이터클래스
    parser.py          # 문제지·정답지 텍스트 → Exam / AnswerKey (+ ParseError)
    normalize.py       # 단답형 정규화 (공백, 대소문자, 전각/반각)
    grader.py          # 사용자 응답 + AnswerKey → Result
    report.py          # Result → 결과 텍스트 파일
  ui/
    app.py             # Tk 루트, 화면 전환, 메뉴, 설정 보관
    start_view.py      # 시작 화면
    exam_view.py       # 시험 화면
    result_view.py     # 결과 화면
    widgets.py         # 스크롤 가능한 프레임 등 공용 위젯
  settings.py          # 설정 저장/로드 (%APPDATA%\ShortTest\settings.json)
tests/
  test_parser.py
  test_normalize.py
  test_grader.py
examples/
build/
  shorttest.spec       # PyInstaller 설정
```

## 3. 데이터 모델 (`core/model.py`)

```python
@dataclass
class Choice:
    number: int          # 1..n
    text: str

@dataclass
class Question:
    number: int
    text: str            # 여러 줄 가능
    points: int = 1
    choices: list[Choice] = field(default_factory=list)

    @property
    def is_multiple_choice(self) -> bool:
        return bool(self.choices)

@dataclass
class Exam:
    title: str
    description: str
    questions: list[Question]
    source_path: Path

@dataclass
class AnswerKey:
    # 객관식: set[int], 단답형: list[str] (인정 답안 목록)
    answers: dict[int, set[int] | list[str]]

@dataclass
class QuestionResult:
    question: Question
    user_answer: set[int] | str | None   # None = 미응답
    correct: bool
    earned: int

@dataclass
class Result:
    exam: Exam
    items: list[QuestionResult]
    total: int
    earned: int
    finished_at: datetime
```

## 4. 파서 (`core/parser.py`)

- 입력: 파일 경로. UTF-8(BOM 허용)로 읽는다. 디코딩 실패 시 CP949로 한 번 더 시도하고 경고를 남긴다.
- 상태 기계로 줄 단위 처리: `META` → `QUESTION` → `CHOICE`.
  - `^#\s*(제목|설명)\s*:\s*(.*)` → 메타데이터. 그 외 `#` 줄 무시.
  - `^(\d+)\.\s+(.*)` → 새 문제 시작. 첫 줄 끝 `\[(\d+)점\]` 추출.
  - `^\s*(\d+)\)\s*(.*)` 또는 `^\s*([①②③④⑤⑥⑦⑧⑨⑩])\s*(.*)` → 보기.
  - 그 외 줄 → 현재 문제 본문(또는 마지막 보기)에 이어 붙임. 빈 줄은 본문 끝 공백으로만 유지.
- 정답지: `^(\d+)\s*:\s*(.*)`. 문제 유형을 보고 해석한다.
  - 객관식 → 쉼표 분리 → `set[int]`. 보기 범위를 벗어나면 오류.
  - 단답형 → `|` 분리 → 각 항목 strip → `list[str]`.
- 오류는 `ParseError(path, line_no, message)`로 모아 **한 번에 전부** 보고한다(첫 오류에서 멈추지 않음). 검사 항목:
  - 문제 번호가 1부터 연속이 아님
  - 보기가 1개뿐인 객관식
  - 정답지에 없는 문제 / 문제지에 없는 번호
  - 정답지의 번호 중복
  - 정답지 형식 오류(객관식에 문자, 범위 밖 번호 등)

## 5. 채점 (`core/normalize.py`, `core/grader.py`)

```python
def normalize(s: str, *, ignore_inner_spaces: bool = False) -> str:
    s = unicodedata.normalize("NFKC", s)   # 전각→반각, 호환 문자 통일
    s = s.strip().casefold()
    s = re.sub(r"\s+", "", s) if ignore_inner_spaces else re.sub(r"\s+", " ", s)
    return s
```

- 객관식: `user_set == key_set` 일 때만 정답. 부분 점수 없음.
- 단답형: `normalize(user)`가 `normalize(k) for k in key` 중 하나와 같으면 정답.
- 미응답(`None` 또는 빈 문자열)은 오답, 0점.
- `grade(exam, key, responses, options) -> Result`. `options.ignore_inner_spaces`는 설정 화면에서 토글.

## 6. 화면 흐름

```text
[시작 화면] --문제지 열기--> [시험 화면] --제출--> [결과 화면]
     ^                          |                     |
     |---------- 홈 ------------+------ 다시 풀기 ----+
```

하나의 `Tk` 루트에 `ttk.Frame` 세 개를 만들고 `tkraise()`로 전환한다. 창 최소 크기 900×600, 기본 폰트 `맑은 고딕 11`.

### 6.1 시작 화면 (`start_view.py`)

```text
┌──────────────────────────────────────────────┐
│  ShortTest                                    │
│                                               │
│   [ 문제지 열기... ]                           │
│                                               │
│   최근 파일                                    │
│   • biology_midterm.questions.txt             │
│   • chem_quiz.questions.txt                   │
│                                               │
│   □ 단답형 채점 시 띄어쓰기 무시                 │
└──────────────────────────────────────────────┘
```

- `filedialog.askopenfilename(filetypes=[("문제지", "*.questions.txt"), ("텍스트", "*.txt")])`
- 같은 폴더에서 `.answers.txt`를 찾는다. 없으면 정답지 선택 대화상자를 띄운다.
- 파싱 오류가 있으면 **오류 목록 대화상자**(파일명, 줄 번호, 메시지 표)를 띄우고 시작 화면에 머문다.
- 최근 파일 5개는 settings.json에 저장. 창 닫을 때 창 크기도 저장.

### 6.2 시험 화면 (`exam_view.py`)

```text
┌─ 2학기 중간고사 생물 ──────────────── 응답 3/10 ─┐
│ 번호  │  3. 다음 중 산(acid)에 해당하는 것을       │
│  1 ✓  │     모두 고르시오.                 [3점]   │
│  2 ✓  │                                           │
│ ▶3 ✓  │   ☑ 1) HCl                                │
│  4    │   ☐ 2) NaOH                               │
│  5    │   ☑ 3) H2SO4                              │
│  …    │   ☐ 4) NH3                                │
│       │                                           │
│       │  [ ◀ 이전 ]              [ 다음 ▶ ]        │
├───────┴───────────────────────────────────────────┤
│  [ 홈 ]                              [ 제출하기 ]   │
└───────────────────────────────────────────────────┘
```

- **왼쪽 문제 목록**: `ttk.Treeview`(열: 번호, 응답 여부). 클릭하면 해당 문제로 이동. 현재 문제 강조.
- **오른쪽 문제 영역**: 본문은 읽기 전용 `tk.Text`(줄바꿈 자동, 선택·복사 가능).
  - 객관식 정답이 1개면 **라디오 버튼**, 정답지가 복수 정답이면 **체크 버튼**. 라디오/체크 구분은 정답지의 정답 개수로 결정하므로, 응시자에게 "복수 선택" 힌트를 주지 않으려면 설정에서 **항상 체크 버튼** 옵션을 켠다.
  - 단답형은 `ttk.Entry` 한 줄. Enter 키 = 다음 문제.
- 응답은 `dict[int, set[int] | str]`에 즉시 저장하므로 이전/다음을 오가도 유지된다.
- 키보드: `←`/`→` 또는 `PageUp`/`PageDown` 이동, 숫자 키 `1~5`로 보기 선택, `Ctrl+Enter` 제출.
- **제출하기**: 미응답 문항이 있으면 `messagebox.askyesno("미응답 N문항이 있습니다. 제출할까요?")`.
- **홈**: 응답이 있으면 "응답이 사라집니다" 확인.

### 6.3 결과 화면 (`result_view.py`)

```text
┌─ 결과: 2학기 중간고사 생물 ───────────────────────┐
│   총점  17 / 20  (85%)     정답 8 / 10              │
├───────────────────────────────────────────────────┤
│ 번호 │ 유형   │ 내 답       │ 정답        │ 결과 │ 점수 │
│  1   │ 객관식 │ 2           │ 2           │  O   │ 2/2  │
│  2   │ 단답형 │ 엽록체      │ 엽록체      │  O   │ 1/1  │
│  3   │ 객관식 │ 1           │ 1, 3        │  X   │ 0/3  │
│  4   │ 단답형 │ (미응답)    │ 물 | H2O    │  X   │ 0/1  │
├───────────────────────────────────────────────────┤
│  [ 홈 ]   [ 다시 풀기 ]   [ 틀린 문제만 다시 ]  [ 결과 저장... ] │
└───────────────────────────────────────────────────┘
```

- `ttk.Treeview` 표. 오답 행은 연한 빨강 태그, 행을 더블클릭하면 문제 본문과 보기를 팝업으로 보여준다.
- **다시 풀기**: 응답을 비우고 시험 화면으로.
- **틀린 문제만 다시**: 오답·미응답 문항만 담은 `Exam`을 만들어 시험 화면으로. 번호는 원래 번호를 유지한다.
- **결과 저장**: `report.py`가 아래 형식의 텍스트를 만들고 `asksaveasfilename`으로 저장. 기본 이름 `biology_midterm.result.2026-10-09_1530.txt`.

```text
ShortTest 결과
시험: 2학기 중간고사 생물
일시: 2026-10-09 15:30
총점: 17 / 20 (85%)   정답: 8 / 10

번호  결과  점수  내 답        정답
1     O     2/2   2            2
3     X     0/3   1            1, 3
```

## 7. 설정 (`settings.py`)

`%APPDATA%\ShortTest\settings.json`

```json
{
  "recent_files": ["C:\\exams\\biology_midterm.questions.txt"],
  "ignore_inner_spaces": false,
  "always_checkbox": false,
  "window": {"width": 1000, "height": 700}
}
```

## 8. 에러 처리 방침

- 파일 관련 오류(없음, 권한, 인코딩)는 `messagebox.showerror`로 원인과 파일 경로를 보여준다.
- 파싱 오류는 전용 대화상자에 **표**로 보여준다. 사용자가 메모장에서 줄 번호를 보고 고칠 수 있게 한다.
- 예상 못 한 예외는 `sys.excepthook`에서 잡아 `%APPDATA%\ShortTest\error.log`에 기록하고, 사용자에게는 "오류가 발생했습니다. error.log를 확인하세요"만 보여준다.

## 9. 테스트

- `tests/test_parser.py`: 예시 파일 파싱, 각 오류 케이스(번호 건너뜀, 보기 1개, 정답 누락, 범위 밖 번호, `①` 보기, 여러 줄 본문, BOM).
- `tests/test_normalize.py`: 전각/반각, 대소문자, 공백 옵션.
- `tests/test_grader.py`: 객관식 단일/복수/부분 선택, 단답형 복수 인정, 미응답, 배점 합계.
- GUI는 자동 테스트하지 않는다. 대신 core가 GUI 없이 완결되도록 하고, 화면 코드는 core를 호출만 한다.
- 실행: `python -m pytest -q`

## 10. 배포

```powershell
pip install pyinstaller
pyinstaller --noconfirm --windowed --onefile --name ShortTest `
  --icon build/shorttest.ico shorttest/__main__.py
```

- 결과물 `dist/ShortTest.exe` 하나. Python 설치 없이 실행된다.
- `--windowed`로 콘솔 창을 숨긴다.
- 백신 오탐이 있으면 `--onedir`로 바꾸고 폴더째 zip으로 배포한다.
- GitHub Actions(`windows-latest`)에서 태그 푸시 시 exe를 빌드해 Release에 올린다.

## 11. 마일스톤

| 단계 | 내용 | 완료 기준 |
|---|---|---|
| M1 core | model, parser, normalize, grader, report + 테스트 | `pytest` 통과, 예시 파일이 파싱·채점됨 |
| M2 시험 화면 | app, start_view, exam_view | 문제지를 열어 끝까지 풀고 제출 가능 |
| M3 결과 화면 | result_view, 결과 저장, 다시 풀기, 틀린 문제만 다시 | 결과 표와 저장 파일 확인 |
| M4 마무리 | 설정 저장, 키보드 단축키, 오류 대화상자, 아이콘 | 설정이 재실행 후 유지됨 |
| M5 배포 | PyInstaller spec, GitHub Actions 빌드 | `ShortTest.exe` 단독 실행 |

M1은 Windows 없이도 개발·검증할 수 있으므로 먼저 진행한다. M2 이후는 Windows에서 직접 실행해 확인한다.

## 12. 이후 확장 후보 (이번 범위 아님)

- 제한시간 타이머
- 보기 순서 섞기
- 문항별 해설(`[해설]` 블록) 표시
- 여러 번 응시 기록 비교

# ShortTest

문제지와 정답지를 넣으면 **Windows에서 문제를 풀고 자동으로 채점**해 주는 프로그램입니다.

- 객관식은 보기 번호를 고르고, 단답형은 답을 입력하면 채점합니다.
- 문제지와 정답지는 **메모장으로 쓰는 일반 텍스트 파일(UTF-8)** 두 개입니다.
- **추가 설치 없이** `ShortTest.exe` 하나로 Windows 10/11에서 바로 실행됩니다.

## 다운로드와 실행

1. [Releases](../../releases) 페이지에서 `ShortTest-windows.zip`을 받아 압축을 풉니다. 안에 `ShortTest.exe`, 예시 파일(`examples/`), 작성법 안내가 들어 있습니다.
2. `ShortTest.exe`를 더블클릭합니다. Python 등 다른 프로그램을 설치할 필요가 없습니다.
3. 처음 실행할 때 Windows SmartScreen이 "알 수 없는 게시자" 경고를 띄우면 **추가 정보 → 실행**을 누릅니다. 서명되지 않은 exe라서 뜨는 경고입니다.

아직 Release가 없다면 [Actions](../../actions) 탭의 최신 "Build Windows exe" 실행에서 `ShortTest-windows` 아티팩트를 받을 수 있습니다. (로그인 필요)

## 사용법

1. **문제지 열기...**를 눌러 `이름.questions.txt`를 고릅니다. 같은 폴더의 `이름.answers.txt`를 정답지로 자동으로 찾습니다.
2. 왼쪽 목록이나 이전/다음 버튼으로 문제를 오가며 답합니다. 객관식은 숫자 키로도 고를 수 있고, 단답형은 Enter로 다음 문제로 넘어갑니다.
3. **제출하기**(Ctrl+Enter)를 누르면 총점과 문항별 정오표가 나옵니다. 행을 더블클릭하면 문제를 다시 볼 수 있습니다.
4. **틀린 문제만 다시**로 오답만 다시 풀거나, **결과 저장...**으로 결과를 텍스트 파일로 남길 수 있습니다.

처음 문제지를 만들 때는 **파일 → 템플릿 파일 만들기...**로 빈 문제지·정답지 한 쌍을 만든 뒤 메모장으로 고치면 됩니다. 작성법은 프로그램 안 **도움말(F1)** 또는 [docs/FORMAT.md](docs/FORMAT.md)에 있습니다.

## 문제지·정답지 형식 요약

문제지 `biology.questions.txt`

```text
# 제목: 2학기 중간고사 생물

1. 세포 안에서 에너지를 생산하는 소기관은? [2점]
1) 핵
2) 미토콘드리아
3) 리보솜
4) 골지체

2. 광합성이 일어나는 식물 세포의 소기관 이름을 쓰시오.

3. 다음 중 산(acid)에 해당하는 것을 모두 고르시오. [3점]
1) HCl
2) NaOH
3) H2SO4
4) NH3
```

정답지 `biology.answers.txt`

```text
1: 2
2: 엽록체
3: 1, 3
```

- `번호.`로 문제가 시작하고, `1)` 또는 `①` 줄이 보기입니다. **보기가 있으면 객관식, 없으면 단답형**입니다.
- `[N점]`은 배점이며 생략하면 1점입니다.
- 객관식 복수 정답은 쉼표(`1, 3`), 단답형 복수 인정은 `|`(`물 | H2O`)로 구분합니다.
- 단답형은 앞뒤 공백 제거, 대소문자 무시, 전각·반각 통일 후 비교합니다.

전체 규칙과 자주 하는 실수는 [docs/FORMAT.md](docs/FORMAT.md)를 보세요. 예시 파일은 [`examples/`](examples/)에 있습니다.

## 설정과 파일 위치

- 설정(최근 파일, 띄어쓰기 무시 등)은 `%APPDATA%\ShortTest\settings.json`에 저장됩니다.
- 예상 못 한 오류는 `%APPDATA%\ShortTest\error.log`에 기록됩니다.

## 개발

Python 3.12 이상과 tkinter(Windows용 Python에 기본 포함)가 필요합니다.

```powershell
pip install -r requirements-dev.txt
python -m shorttest          # 실행
python -m pytest -q          # 테스트 (core + GUI 스모크)
pyinstaller --noconfirm --clean --onefile --windowed --name ShortTest --collect-submodules shorttest shorttest/__main__.py
# → dist\ShortTest.exe
```

구조는 파싱·채점(`shorttest/core`)과 화면(`shorttest/ui`)이 분리되어 있고, core는 tkinter 없이 테스트됩니다. 설계와 화면 구성은 [docs/PLAN.md](docs/PLAN.md)에 있습니다.

### 자동 빌드

`.github/workflows/build.yml`이 푸시마다 Ubuntu에서 테스트를 돌리고 Windows 러너에서 `ShortTest.exe`를 만들어 아티팩트로 올립니다. `v1.0.0`처럼 `v`로 시작하는 태그를 푸시하면 Release에 exe와 zip이 첨부됩니다.

```powershell
git tag v0.1.0
git push origin v0.1.0
```

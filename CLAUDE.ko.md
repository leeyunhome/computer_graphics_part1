# CLAUDE.md

이 파일은 이 저장소에서 작업할 때 Claude Code(claude.ai/code)에 지침을 제공합니다.

## 프로젝트 개요

컴퓨터 그래픽스 학습을 위한 **포트폴리오 자동화 시스템**입니다. 개인 학습 저장소를 감시하다가 새 커밋이 감지되면, Gemini API를 사용해 학습 내용을 한국어 블로그 포스트로 생성하고 MkDocs를 통해 GitHub Pages에 배포합니다.

**핵심 제약사항:** 학습 저장소(`C:\coding\my-github-repository\HonglabComputerGraphics_part1`)는 강의 저장소이므로 그대로 공개해서는 안 됩니다. 포트폴리오 콘텐츠는 강의 코드를 그대로 복사하지 않고, 본인이 이해하고 구현한 내용을 기반으로 작성해야 합니다.

## 저장소 관계

- **학습 저장소** (비공개, 절대 공개 금지): `C:\coding\my-github-repository\HonglabComputerGraphics_part1`
- **포트폴리오 저장소** (이 저장소, 공개): `https://github.com/leeyunhome/computer_graphics_part1`
- 학습 저장소 경로는 `references/reference.txt`에 저장되어 있습니다.

## 학습 저장소 기술 스택

학습 저장소는 컴퓨터 그래픽스를 단계적으로 구현합니다:
- **언어:** C++ + DirectX 11 (D3D11) + HLSL 셰이더
- **수학 라이브러리:** GLM
- **UI:** Dear ImGui (실시간 파라미터 조작)
- **렌더링 패턴:** CPU 레이트레이싱 → GPU 텍스처 업로드 → 풀스크린 쿼드 렌더링
- **학습 주제:** DX11 초기화, Bloom, 레이트레이싱 14단계 (구 → Phong 셰이딩 → 원근 투영 → 그림자 → 텍스처 → 반사 → 굴절 → 환경 맵)

## 포트폴리오 자동화

### Watcher 실행 (학습 저장소의 새 커밋 감시)
```
start_watcher.bat
# 또는 직접:
venv\Scripts\python.exe scripts\watcher.py
```

### 최신 커밋으로 포트폴리오 포스트 수동 생성
```
run_generator.bat
# 또는 직접:
venv\Scripts\python.exe scripts\portfolio_generator.py
```

### 로컬에서 사이트 빌드 및 미리보기
```
venv\Scripts\mkdocs serve
```

### GitHub Pages 배포
```
venv\Scripts\mkdocs gh-deploy --force
```
`main` 브랜치에 푸시할 때마다 `.github/workflows/deploy.yml`을 통해 자동 배포됩니다.

## Python 환경 설정

```
venv\Scripts\pip install -r requirements.txt   # requirements.txt가 있는 경우
venv\Scripts\pip install mkdocs-material gitpython google-genai python-dotenv
```

`.env copy.example`을 `.env`로 복사한 후 Gemini API 키를 입력합니다:
```
GEMINI_API_KEY=발급받은_키_입력
```

## 콘텐츠 생성 규칙

포트폴리오 포스트를 생성할 때 AI 프롬프트는 반드시:
1. 강의 구조가 아닌 **본인이 구현하고 이해한 내용**에 집중할 것
2. 그래픽스 개념을 수식으로 설명할 것 (pymdownx.math를 통해 LaTeX 지원)
3. **한국어**로 작성할 것
4. 강의 코드를 그대로 복사하지 말 것 — 이해한 내용을 바탕으로 재서술할 것
5. 포스트 파일명 형식: `docs/YYYY-MM-DD-주제명.md`

## MkDocs 설정

사이트 설정은 `mkdocs.yml`에 있으며, 포스트는 `docs/` 폴더에 저장됩니다. Material 테마는 다음을 지원합니다:
- 수식 렌더링 (`pymdownx.arithmatex` + MathJax)
- 코드 문법 강조
- 네비게이션 탭 및 다크 모드

## GitHub Actions

`.github/workflows/deploy.yml`이 `main` 브랜치 푸시 시 트리거되어 `mkdocs gh-deploy --force`를 실행합니다. 기본 `GITHUB_TOKEN` 외에 별도 시크릿 설정 없이 GitHub Pages 배포가 가능합니다.

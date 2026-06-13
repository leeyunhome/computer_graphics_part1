# CLAUDE.ko.md

이 파일은 이 저장소에서 작업할 때 Claude Code(claude.ai/code)에 지침을 제공합니다.

## 프로젝트 개요

컴퓨터 그래픽스 학습을 위한 **포트폴리오 자동화 시스템**입니다. 개인 DX11/C++ 강의 저장소를 감시하다가 새 커밋이 감지되면, Gemini AI를 사용해 커밋 하나당 두 가지 결과물을 자동 생성합니다:
1. 한국어 블로그 포스트 (`docs/posts/YYYY-MM-DD-slug.md`)
2. WebGPU 인터랙티브 데모 (`docs/demos/<slug>/demo.html`) — DX11 개념을 브라우저에서 재현

두 결과물 모두 MkDocs를 통해 GitHub Pages에 배포됩니다. 새 콘텐츠가 생성될 때마다 홈페이지와 내비게이션이 자동으로 재구성됩니다.

**핵심 제약사항:** 학습 저장소는 강의 저장소이므로 그대로 공개해서는 안 됩니다. 포트폴리오 콘텐츠는 강의 코드를 그대로 복사하지 않고, 본인이 이해하고 구현한 내용을 기반으로 작성해야 합니다.

## 저장소 관계

- **학습 저장소** (비공개, 절대 공개 금지): `C:\coding\my-github-repository\HonglabComputerGraphics_part1`
- **포트폴리오 저장소** (이 저장소, 공개): `https://github.com/leeyunhome/computer_graphics_part1`
- 학습 저장소 경로는 `references/reference.txt`에 저장되어 있습니다.

## 학습 저장소 기술 스택

학습 저장소는 컴퓨터 그래픽스를 단계적으로 구현합니다:
- **언어:** C++ + DirectX 11 (D3D11) + HLSL 셰이더
- **수학 라이브러리:** GLM
- **UI:** Dear ImGui (실시간 파라미터 조작)
- **렌더링 패턴:** CPU 픽셀 루프 → GPU 텍스처 업로드 → 풀스크린 쿼드 렌더링
- **학습 주제:** DX11 초기화, 픽셀 버퍼 애니메이션, 이미지 밝기 조절, Box Blur, Bloom, 레이트레이싱 14단계 (구 → Phong → 원근 투영 → 그림자 → 텍스처 → 반사 → 굴절 → 환경 맵)

## 포트폴리오 자동화 스크립트

### Watcher (학습 저장소 커밋 자동 감지)
```
start_watcher.bat
# 또는 직접:
venv\Scripts\python.exe scripts\watcher.py
```
시작 시 현재 HEAD 커밋이 이미 처리됐는지 확인 — 미처리 상태면 즉시 처리합니다 (오프라인 중 발생한 커밋 자동 처리). 이후 2초마다 폴링합니다.

### 수동 생성 (최신 커밋 기준)
```
run_generator.bat
# 또는 직접:
venv\Scripts\python.exe scripts\portfolio_generator.py
```

### 소급 처리 (오프라인 중 누락된 커밋 일괄 처리)
```
run_sync.bat               # 미처리 커밋 모두 처리
run_sync.bat --dry-run     # 목록만 출력 (생성 안 함)
run_sync.bat --force       # 이미 처리된 커밋 강제 재처리
# 또는 직접:
venv\Scripts\python.exe scripts\sync_commits.py
```

### 로컬 미리보기
```
venv\Scripts\mkdocs serve
```

### GitHub Pages 배포
```
venv\Scripts\mkdocs gh-deploy --force
```
`main` 브랜치에 푸시할 때마다 `.github/workflows/deploy.yml`을 통해 자동 배포됩니다.

## 커밋 추적

처리된 학습 저장소 커밋 SHA는 `data/processed_commits.txt`에 저장됩니다 (한 줄에 SHA 하나). 이 파일은 git에 추적되어 여러 기기에서 처리 상태를 공유합니다. `data/` 디렉토리는 `data/.gitkeep`으로 git에 유지됩니다.

- `load_processed_commits()` — 이미 처리된 SHA 집합 반환
- `mark_commit_processed(sha)` — SHA를 파일에 추가
- 기본적으로 `process_commit()`은 이미 처리된 커밋을 건너뜁니다.

## Python 환경

```
venv\Scripts\pip install mkdocs-material gitpython google-genai python-dotenv
```

`.env copy.example`을 `.env`로 복사한 후 Gemini API 키를 입력합니다:
```
GEMINI_API_KEY=발급받은_키_입력
```

**Gemini 모델:** `gemini-3.5-flash`

## 콘텐츠 생성 규칙

### 블로그 포스트
1. 강의 구조가 아닌 **본인이 구현하고 이해한 내용**에 집중
2. 그래픽스 개념을 수식으로 설명 (LaTeX via `pymdownx.arithmatex`)
3. **한국어**로 작성
4. 강의 코드를 그대로 복사하지 말 것 — 이해한 내용을 바탕으로 재서술
5. 인터랙티브 데모 링크 포함: `[데모 보기](../demos/<slug>/demo.html)`

### WebGPU 데모 (`docs/demos/<slug>/demo.html`)
Gemini가 다음 규칙으로 생성합니다:
- 픽셀 데이터 업로드에 **`device.queue.writeTexture()`** 사용 — `copyExternalImageToTexture()` 사용 금지 (RENDER_ATTACHMENT 사용 플래그 필요, 없으면 무음 실패)
- **Canvas2D**로 절차적 소스 이미지 생성 → `getImageData()`로 픽셀 추출 → `writeTexture()`에 전달
- 파이프라인: Uniform Buffer → Storage Texture → Compute Pass → Render Pass (풀스크린 쿼드 6정점) → swapchain
- DX11→WebGPU 매핑:
  - `RWTexture2D<float4>` → `texture_storage_2d<rgba8unorm, write>`
  - `[numthreads(8,8,1)]` → `@workgroup_size(8,8)`
  - `SV_DispatchThreadID` → `@builtin(global_invocation_id)`
  - `cbuffer` → `var<uniform>`
  - `Dispatch(W/8,H/8,1)` → `dispatchWorkgroups(ceil(W/8), ceil(H/8))`
- 데모 파일 이름은 반드시 `demo.html` (NOT `index.html`) — MkDocs가 `slug.md` → `slug/index.html`로 렌더링하므로 데모 폴더에 `index.html`이 있으면 충돌 발생
- 데모 폴더 구조: `docs/demos/<slug>/demo.html`

## 파일 명명 규칙 및 경로

| 결과물 | 경로 |
|---|---|
| 블로그 포스트 | `docs/posts/YYYY-MM-DD-<slug>.md` |
| 데모 HTML | `docs/demos/<slug>/demo.html` |
| 데모 래퍼 페이지 | `docs/demos/<slug>.md` |
| 포스트 목록 | `docs/posts/index.md` |
| 데모 목록 | `docs/demos/index.md` |
| 홈페이지 | `docs/index.md` |

**주의:** MkDocs 페이지 내 raw HTML 링크는 렌더링된 URL을 사용해야 합니다 (`href="demos/slug/"`, NOT `href="demos/slug.md"`). Markdown 링크(`[text](slug.md)`)는 MkDocs가 변환하지만, raw HTML `href` 속성은 변환하지 않습니다.

## 사이트 자동 재구성

새 포스트+데모가 생성될 때마다 `save_and_commit()`이 자동으로 다음을 실행합니다:
- `rebuild_posts_index()` — `docs/posts/*.md` 스캔, 최신순 목록 생성
- `rebuild_demos_index()` — `docs/demos/*.md` 스캔 (index.md 제외)
- `rebuild_homepage()` — 홈페이지를 데모 카드 전체 + 최근 포스트 5개로 업데이트
- `create_demo_page(title, slug)` — `docs/demos/<slug>.md` 래퍼 페이지 생성 (iframe src="demo.html")
- `update_mkdocs_nav(title, slug)` — `mkdocs.yml` nav에 항목 삽입

## MkDocs 설정

사이트 설정은 `mkdocs.yml`에 있으며, 포스트는 `docs/` 폴더에 저장됩니다. Material 테마는 다음을 지원합니다:
- 수식 렌더링 (`pymdownx.arithmatex` + MathJax)
- 코드 문법 강조
- 네비게이션 탭 및 다크 모드

## GitHub Actions

`.github/workflows/deploy.yml`이 `main` 브랜치 푸시 시 트리거되어 `mkdocs gh-deploy --force`를 실행합니다. 기본 `GITHUB_TOKEN` 외에 별도 시크릿 설정 없이 GitHub Pages 배포가 가능합니다.

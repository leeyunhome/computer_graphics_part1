import os
import sys
import re
import shutil
import datetime
import argparse
from git import Repo
from google import genai
from dotenv import load_dotenv

load_dotenv()

STUDY_REPO_PATH = r"c:\coding\my-github-repository\HonglabComputerGraphics_part1"
PORTFOLIO_REPO_PATH = r"c:\coding\my-github-repository\computer_graphics_part1"
DOCS_PATH = os.path.join(PORTFOLIO_REPO_PATH, "docs")
POSTS_PATH = os.path.join(DOCS_PATH, "posts")
DEMOS_PATH = os.path.join(DOCS_PATH, "demos")
DATA_PATH = os.path.join(PORTFOLIO_REPO_PATH, "data")
PROCESSED_COMMITS_FILE = os.path.join(DATA_PATH, "processed_commits.txt")

# 강의에서 선택한 이미지 폴더 (private — 포트폴리오로 자동 동기화됨)
STUDY_IMAGES_PATH = os.path.join(
    STUDY_REPO_PATH, "HonglabComputerGraphics_part1", "images"
)
DOCS_IMAGES_PATH = os.path.join(DOCS_PATH, "images")

SUPPORTED_EXTS = ('.cpp', '.h', '.c', '.hlsl', '.glsl', '.vert', '.frag', '.py')
IMAGE_EXTS = ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp')


# ── Study image sync ──────────────────────────────────────────────────────────

def sync_study_images():
    """강의 이미지 폴더의 신규 파일을 docs/images/로 복사하고 전체 이미지 목록을 반환합니다.

    Returns:
        all_images  : docs/images/ 안의 모든 이미지 파일명 목록 (정렬)
        newly_synced: 이번에 새로 복사된 파일명 목록
    """
    os.makedirs(DOCS_IMAGES_PATH, exist_ok=True)
    newly_synced = []

    if os.path.isdir(STUDY_IMAGES_PATH):
        for fname in sorted(os.listdir(STUDY_IMAGES_PATH)):
            if fname.lower().endswith(IMAGE_EXTS):
                src = os.path.join(STUDY_IMAGES_PATH, fname)
                dst = os.path.join(DOCS_IMAGES_PATH, fname)
                if not os.path.exists(dst):
                    shutil.copy2(src, dst)
                    newly_synced.append(fname)
                    print(f"  이미지 동기화: {fname}")

    all_images = sorted(
        f for f in os.listdir(DOCS_IMAGES_PATH)
        if f.lower().endswith(IMAGE_EXTS)
    )
    return all_images, newly_synced


def _build_image_prompt_section(all_images):
    """Gemini 프롬프트에 삽입할 이미지 목록 섹션을 생성합니다."""
    if not all_images:
        return ""

    lines = ["## 사용 가능한 이미지 (docs/images/ 폴더):"]
    for fname in all_images:
        lines.append(f"  - `../../images/{fname}`")

    lines += [
        "",
        "이미지 활용 지침:",
        "- **이미지 처리 주제** (밝기·블러·색상 변환 등): 절차적 패턴 대신 위 이미지 중 하나를 소스 텍스처로 사용하세요.",
        "- **개념 다이어그램** (Phong, 법선벡터, 투영 등의 PNG): 데모 UI 패널에 `<img>` 태그로 표시해 이론 참고 이미지로 활용하세요.",
        "- **이미지 로드 패턴** (텍스처 용도일 때):",
        "```javascript",
        "async function loadImage(url, w, h) {",
        "  const img = new Image();",
        "  await new Promise((resolve, reject) => {",
        "    img.onload = resolve;",
        "    img.onerror = () => reject(new Error(`이미지 로드 실패: ${url}`));",
        "    img.src = url;",
        "  });",
        "  const c = document.createElement('canvas');",
        "  c.width = w; c.height = h;",
        "  c.getContext('2d').drawImage(img, 0, 0, w, h);",
        "  return c;",
        "}",
        "// srcCanvas.getContext('2d').getImageData(0,0,W,H) → writeTexture()",
        "```",
        "- `copyExternalImageToTexture()` 사용 금지 — `RENDER_ATTACHMENT` 플래그 없이 검은 화면이 됩니다.",
    ]
    return "\n".join(lines)


# ── Commit tracking ────────────────────────────────────────────────────────────

def load_processed_commits():
    if not os.path.exists(PROCESSED_COMMITS_FILE):
        return set()
    with open(PROCESSED_COMMITS_FILE, 'r', encoding='utf-8') as f:
        return set(line.strip() for line in f if line.strip())


def mark_commit_processed(commit_hash):
    os.makedirs(DATA_PATH, exist_ok=True)
    with open(PROCESSED_COMMITS_FILE, 'a', encoding='utf-8') as f:
        f.write(commit_hash + '\n')


# ── Git diff extraction ────────────────────────────────────────────────────────

def get_commit_diff(repo_path, commit_hash=None):
    """특정 커밋(또는 HEAD)의 diff와 변경 파일 전체 내용을 반환합니다.
    Returns: (hexsha, message, diff_text, file_contents)
      - diff_text: 변경 부분(+/- 줄)
      - file_contents: {파일경로: 커밋 시점 전체 내용} — 주석·코드 구조 파악용
    """
    repo = Repo(repo_path)
    commit = repo.commit(commit_hash) if commit_hash else repo.head.commit

    if not commit.parents:
        diff = commit.diff('4b825dc642cb6eb9a060e54bf8d69288fbee4904')
    else:
        diff = commit.parents[0].diff(commit, create_patch=True)

    diff_text = ""
    file_contents = {}
    for d in diff:
        path = d.b_path or d.a_path
        try:
            if path.endswith(SUPPORTED_EXTS):
                # diff (변경 부분)
                diff_text += f"--- File: {path} ---\n"
                diff_text += str(d.diff.decode('utf-8', errors='ignore')) + "\n\n"
                # 커밋 시점 전체 파일 내용
                try:
                    blob = commit.tree[path]
                    file_contents[path] = blob.data_stream.read().decode('utf-8', errors='ignore')
                except Exception:
                    pass
        except Exception as e:
            print(f"  diff 건너뜀 ({path}): {e}")

    return commit.hexsha, commit.message.strip(), diff_text, file_contents


# Keep backward-compat alias
def get_latest_commit_diff(repo_path):
    _, msg, diff, _ = get_commit_diff(repo_path)
    return msg, diff


# ── Gemini helpers ─────────────────────────────────────────────────────────────

def _format_file_contents(file_contents, max_chars_per_file=4000, max_files=4):
    """file_contents dict를 프롬프트용 텍스트로 포맷합니다.
    핵심 파일 우선 (HLSL 셰이더 > C++ > 헤더 순), 파일당 최대 max_chars_per_file 글자."""
    if not file_contents:
        return "(파일 내용 없음)"

    def _priority(path):
        if path.endswith(('.hlsl', '.glsl', '.vert', '.frag')):
            return 0
        if path.endswith('.cpp'):
            return 1
        if path.endswith('.h'):
            return 2
        return 3

    sorted_files = sorted(file_contents.items(), key=lambda kv: _priority(kv[0]))[:max_files]
    parts = []
    for path, content in sorted_files:
        truncated = content[:max_chars_per_file]
        if len(content) > max_chars_per_file:
            truncated += f"\n... (이하 {len(content) - max_chars_per_file}자 생략)"
        parts.append(f"=== {path} ===\n{truncated}")
    return "\n\n".join(parts)


def _call_gemini(prompt):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "your_api_key_here":
        print("오류: .env 파일에 GEMINI_API_KEY가 설정되지 않았습니다.")
        sys.exit(1)
    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model='gemini-3.5-flash',
        contents=prompt,
    )
    return response.text


def _make_slug(text):
    slug = re.sub(r'[^\w\s-]', '', text).strip().lower()
    slug = re.sub(r'[-\s]+', '-', slug)
    return slug or "portfolio-update"


# ── Content generation ─────────────────────────────────────────────────────────

def generate_portfolio_post(commit_msg, diff_text, file_contents=None):
    file_section = _format_file_contents(file_contents) if file_contents else "(파일 내용 없음)"
    prompt = f"""당신은 컴퓨터 그래픽스 전문가입니다.
아래는 학습자가 DirectX 11 / C++ 그래픽스 스터디 레포지토리에 커밋한 내용입니다.

커밋 메시지: {commit_msg}

────── 변경된 파일 전체 코드 (주석 포함) ──────
{file_section}

────── 코드 변경사항(diff) ──────
{diff_text[:4000] if diff_text.strip() else "(코드 변경 없음 — 위 파일 내용 기반으로 작성)"}

작성 규칙:
1. 한국어로 작성하세요.
2. Markdown 형식으로, 첫 줄은 반드시 # 제목 형식의 제목으로 시작하세요.
3. 위 전체 코드와 주석을 꼼꼼히 읽고, **이 커밋의 핵심 개념이 무엇인지** 파악하세요.
   - 주석에서 설명하는 알고리즘의 의도와 수식을 중심으로 서술하세요.
   - 단순히 diff에서 추가된 줄을 나열하지 말고, 전체 구조에서 이 변경이 갖는 의미를 설명하세요.
4. 학습자가 '직접 구현하며 이해한 개념'을 중심으로 서술하세요.
5. 핵심 수식은 $$ ... $$ LaTeX 블록으로 표현하세요.
6. 강의 소스코드를 그대로 붙여넣지 말고, 핵심 알고리즘을 의사코드(pseudo-code) 또는 추상화된 형태로 설명하세요.
7. 마지막에 **WebGPU 인터랙티브 데모** 섹션을 추가하세요 — 이 내용을 브라우저 WebGPU Compute Shader로 시각화하면 어떤 모습인지 간략히 설명하세요.
8. ```markdown 블록으로 감싸지 말고 바로 Markdown을 출력하세요.

## 용어 정확성 규칙 (반드시 준수):
- **Phong Reflection Model (퐁 반사 모델)**: Ambient + Diffuse + Specular로 조명을 표현하는 모델. 파트1 레이트레이싱에서 구현하는 것. 조명이 반사되어 눈에 보이는 방식을 단순화한 모델.
- **Phong Shading (퐁 셰이딩)**: 파트2 래스터화에서 등장하는 개념. 정점의 노멀 벡터를 픽셀 단위로 인터폴레이션해서 픽셀별 노멀로 셰이딩하는 기법.
- 이 레포지토리는 파트1이므로, 조명 모델을 설명할 때는 "Phong Shading" 대신 "Phong Reflection Model" 또는 "퐁 반사 모델"을 사용하세요.
"""
    print("  포스트 생성 중 (Gemini)...")
    return _call_gemini(prompt)


def generate_webgpu_demo(commit_msg, diff_text, topic_hint, file_contents=None, all_images=None):
    """WebGPU Compute Shader 기반 self-contained HTML 데모를 생성합니다."""
    file_section = _format_file_contents(file_contents, max_chars_per_file=3000) if file_contents else "(파일 내용 없음)"
    image_section = _build_image_prompt_section(all_images or [])
    prompt = f"""당신은 WebGPU/WGSL 전문가이며 DirectX 11 파이프라인을 WebGPU로 정확히 재현합니다.

아래 DirectX 11 / C++ 컴퓨터 그래픽스 주제를 WebGPU Compute Shader 기반으로 구현하세요.

주제: {topic_hint}
커밋 메시지: {commit_msg}

────── 변경된 파일 전체 코드 (주석 포함) ──────
{file_section}

────── 코드 변경사항(diff) ──────
{diff_text[:2000] if diff_text.strip() else "(커밋 메시지 기반으로 구현)"}

## 핵심 파악 지침 (데모 구현 전 반드시 확인):
- 위 전체 코드와 주석을 꼼꼼히 읽고, **이 커밋에서 가장 중요한 알고리즘/수식이 무엇인지** 파악하세요.
- HLSL 셰이더 코드가 있으면 해당 로직을 WGSL Compute Shader로 정확히 옮기세요.
- C++ 코드의 CPU 픽셀 루프가 있으면 GPU Compute Shader로 재현하세요.
- 주석에서 설명하는 수학적 개념(정규화, 감쇄, 컨볼루션 등)을 데모의 핵심 인터랙션으로 만드세요.

## DX11 → WebGPU 매핑 (반드시 이 패턴 사용)

| DX11 | WebGPU / WGSL |
|------|---------------|
| `RWTexture2D<float4>` (UAV) | `texture_storage_2d<rgba8unorm, write>` |
| `[numthreads(8,8,1)]` | `@workgroup_size(8,8)` |
| `SV_DispatchThreadID` | `@builtin(global_invocation_id)` |
| `cbuffer {{ float4 x; }}` | `struct Params {{ x: vec4f }}` + `var<uniform>` |
| `Dispatch(W/8, H/8, 1)` | `dispatchWorkgroups(ceil(W/8), ceil(H/8))` |
| CPU 픽셀 루프 | GPU Compute Pass |
| GPU 텍스처 fullscreen render | Vertex(6 verts) + Fragment Shader |

## 파이프라인 구조 (이 순서를 반드시 지키세요):
1. Uniform Buffer 생성 — 파라미터 (색상, 위치, 반지름 등)
2. Storage Texture 생성 — GPU 연산 결과 저장
3. Compute Pipeline + Compute Pass — 픽셀 값 계산
4. Render Pipeline + Render Pass — Storage Texture를 fullscreen quad로 표시
5. 슬라이더 변경 → `device.queue.writeBuffer` → scheduleRender()

## GUI 라벨 규칙 (최우선 — 반드시 준수):
위 C++ 소스 코드에서 ImGui 호출을 찾아 아래 규칙을 따르세요:

1. **패널 제목** — `ImGui::Begin("Circle")` → 사이드바 섹션 제목을 `"Circle"` 그대로 사용
2. **슬라이더 레이블** — `ImGui::SliderFloat("Radius", ...)` → HTML label을 `"Radius"` 그대로 사용
3. **슬라이더 범위** — `ImGui::SliderFloat("Radius", &val, 0.0f, 1.0f)` → `min="0" max="1"` 그대로 사용
4. **슬라이더3** — `ImGui::SliderFloat3("Center", ...)` → X/Y/Z 세 슬라이더로 분리하되 레이블은 `"Center X"`, `"Center Y"`, `"Center Z"`
5. **기본값** — C++ 소스의 초기값(`sphere->center = vec3(0,0,0.5)` 등)을 슬라이더 `value` 속성에 반영
6. ImGui 호출이 소스에 없으면 주제에 맞는 직관적인 영문 레이블 사용

예시 (Step5 PhongShading의 ImGui 코드 → HTML 변환):
```
// C++                                           // HTML
ImGui::Begin("Circle");                       →  <div class="section-title">Circle</div>
ImGui::SliderFloat3("Center", &c.x, -1, 1);  →  <label>Center X</label><input min="-1" max="1">
ImGui::SliderFloat("Radius", &r, 0, 1);      →  <label>Radius</label><input min="0" max="1">
ImGui::SliderFloat3("Light", &l.x, -2, 2);   →  <label>Light X/Y/Z</label><input min="-2" max="2">
ImGui::SliderFloat3("Ambient color",...);     →  <label>Ambient color R/G/B</label>
ImGui::SliderFloat("Specular power",...,100); →  <label>Specular power</label><input max="100">
```

## UI 요구사항:
- ImGui 스타일 다크 테마 (창 프레임 포함, DirectX 11 앱 느낌)
- 파라미터 조작 슬라이더 (레이블은 위 GUI 라벨 규칙 우선, 없으면 영문)
- 실시간 업데이트 (`scheduleRender` 패턴 — RAF 중복 방지)
- 창 제목표시줄: `DirectX 11 — [주제명]` 스타일
- 배경: `#1a1a2e`

## 레이아웃 규칙 (iframe 임베딩 호환성 — 반드시 준수):
이 HTML은 700px 높이 iframe 안에 임베딩됩니다. 아래 규칙을 정확히 따르세요.

```css
/* 필수 레이아웃 골격 */
body {{
  display: flex; flex-direction: column;
  height: 100vh; overflow: hidden;  /* iframe 높이에 맞게 고정 */
  margin: 0;
}}
.workspace {{
  display: flex; flex-direction: row;  /* flex-wrap:wrap 금지 — wrap하면 sidebar의 overflow-y:auto가 동작 안함 */
  flex: 1; min-height: 0;             /* ← min-height:0 필수: 없으면 overflow-y:auto가 동작 안함 */
  overflow: hidden;
}}
/* 모바일 대응: wrap 대신 flex-direction 전환 사용 */
@media (max-width: 680px) {{
  .workspace {{ flex-direction: column; }}
  .sidebar {{ width: 100% !important; max-height: 50vh; }}
}}
.canvas-container {{
  flex: 1; min-width: 300px; overflow: hidden;
}}
canvas {{
  /* 캔버스 가로 최대 520px — 사이드바(320px)와 합쳐 840px, 일반 콘텐츠 폭에 맞음 */
  width: 520px; height: 520px; max-width: 100%;
}}
.sidebar {{
  width: 320px; flex-shrink: 0;
  overflow-y: auto;  /* min-height:0이 있어야 스크롤 활성화됨 */
}}
@media (max-width: 700px) {{
  .sidebar {{ width: 100%; max-height: 55vh; }}
}}
```

- 캔버스는 반드시 **520×520** 이하로 유지하세요 (800×600 금지 — iframe 폭 초과).
- `dispatchWorkgroups`는 `ceil(W/8) × ceil(H/8)`로 계산하세요.

{image_section}

## 기술 요구사항:
- 단일 HTML 파일 (외부 라이브러리 금지 — WebGPU는 브라우저 내장)
- `<!DOCTYPE html>` 로 시작
- WebGPU 미지원 브라우저 시 명확한 오류 메시지 표시
- 모든 WGSL, CSS, JS 인라인

주제와 관련이 없거나 시각화가 불가능하면 "SKIP"이라고만 답하세요.
HTML 코드만 출력하고, 다른 설명 텍스트는 절대 넣지 마세요.
"""
    print("  WebGPU 데모 생성 중 (Gemini)...")
    result = _call_gemini(prompt)
    if result.strip().upper() == "SKIP":
        return None
    result = re.sub(r'^```html\s*', '', result.strip(), flags=re.IGNORECASE)
    result = re.sub(r'\s*```$', '', result.strip())
    return result.strip()


# Keep alias for backward compatibility
def generate_js_demo(commit_msg, diff_text, topic_hint):
    return generate_webgpu_demo(commit_msg, diff_text, topic_hint)


# ── Site index helpers ────────────────────────────────────────────────────────

def _extract_title_from_md(filepath):
    """마크다운 파일의 첫 번째 # 제목을 반환합니다."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line.startswith('# '):
                    return line[2:].strip()
    except Exception:
        pass
    return os.path.basename(filepath)[:-3]


def rebuild_posts_index():
    """docs/posts/index.md 를 포스트 목록으로 갱신합니다."""
    posts = sorted(
        [f for f in os.listdir(POSTS_PATH) if f.endswith('.md') and f != 'index.md'],
        reverse=True,  # 최신 순
    )
    lines = [
        "# 학습 포스트\n",
        "학습 저장소에 커밋할 때마다 자동 생성되는 포스트 목록입니다.\n",
        "\n---\n",
    ]
    for fname in posts:
        title = _extract_title_from_md(os.path.join(POSTS_PATH, fname))
        date = fname[:10] if fname[:4].isdigit() else ''
        lines.append(f"\n## [{title}]({fname})\n")
        if date:
            lines.append(f"\n📅 {date}\n")
        lines.append("\n---\n")

    with open(os.path.join(POSTS_PATH, 'index.md'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))


def rebuild_homepage():
    """docs/index.md 의 데모 카드와 최근 포스트 목록을 현재 상태로 갱신합니다."""
    def _demo_mtime(demo_slug):
        """demo.html 수정 시간 반환 — 없으면 float('inf') (맨 뒤 배치)."""
        demo_html = os.path.join(DEMOS_PATH, demo_slug, 'demo.html')
        try:
            return os.path.getmtime(demo_html)
        except OSError:
            return float('inf')

    # 데모 목록 (index.md 제외, demo.html 수정 시간 오름차순 — 파일 없는 항목은 맨 뒤)
    demo_pages = sorted(
        [f for f in os.listdir(DEMOS_PATH) if f.endswith('.md') and f != 'index.md'],
        key=lambda f: _demo_mtime(f[:-3])
    )
    # 최근 포스트 5개 (날짜 역순)
    recent_posts = sorted(
        [f for f in os.listdir(POSTS_PATH) if f.endswith('.md') and f != 'index.md'],
        reverse=True,
    )[:5]

    # 데모 카드 HTML 생성
    # raw HTML <a href> 안에서는 MkDocs가 .md→URL 변환을 하지 않으므로
    # 렌더링된 URL 경로인 "demos/<slug>/" 를 직접 사용
    demo_cards = ""
    for fname in demo_pages:
        title = _extract_title_from_md(os.path.join(DEMOS_PATH, fname))
        slug = fname[:-3]
        demo_cards += f"""
<div style="flex:1; min-width:200px; background:#1e293b; border-radius:8px; padding:16px; border:1px solid #334155;">
<strong>{title}</strong><br><br>
<a href="demos/{slug}/">데모 보기 →</a>
</div>
"""

    # 최근 포스트 목록 마크다운 생성
    post_lines = ""
    for fname in recent_posts:
        title = _extract_title_from_md(os.path.join(POSTS_PATH, fname))
        date = fname[:10] if fname[:4].isdigit() else ''
        post_lines += f"- [{title}](posts/{fname})"
        if date:
            post_lines += f" <small style='color:#64748b'>({date})</small>"
        post_lines += "\n"

    homepage = f"""# 컴퓨터 그래픽스 학습 포트폴리오

C++과 DirectX 11로 컴퓨터 그래픽스를 공부하며 직접 구현한 내용을 정리한 포트폴리오입니다.
강의 코드를 그대로 옮긴 것이 아니라, 학습한 수학·알고리즘을 **WebGPU Compute Shader로 재현**하여 브라우저에서 직접 체험할 수 있도록 했습니다.

---

## 학습 스택

| 분류 | 기술 |
|------|------|
| 렌더링 API | DirectX 11 (D3D11), HLSL |
| 언어 | C++17 |
| 수학 | GLM (vec3, mat4) |
| UI | Dear ImGui |
| 포트폴리오 | WebGPU / WGSL, MkDocs Material |

---

## 학습 로드맵

```mermaid
graph LR
  A[DX11 초기화<br/>픽셀버퍼] --> B[Bloom<br/>포스트프로세싱]
  A --> C[레이트레이싱 Step 1<br/>벡터·GLM]
  C --> D[Step 2-4<br/>구 렌더링]
  D --> E[Step 5<br/>Phong 셰이딩]
  E --> F[Step 6-9<br/>원근·삼각형·그림자]
  F --> G[Step 10-14<br/>텍스처·반사·굴절·환경맵]
```

---

## 인터랙티브 데모

각 주제의 핵심 알고리즘을 WebGPU Compute Shader로 재현한 인터랙티브 데모입니다.

<div style="display:flex; gap:16px; flex-wrap:wrap; margin-top:8px;">
{demo_cards}
</div>

[전체 데모 목록 →](demos/index.md)

---

## 최근 학습 포스트

{post_lines}
[모든 포스트 보기 →](posts/index.md)
"""
    with open(os.path.join(DOCS_PATH, 'index.md'), 'w', encoding='utf-8') as f:
        f.write(homepage)


def rebuild_demos_index():
    """docs/demos/index.md 를 데모 목록으로 갱신합니다."""
    # 수동으로 만든 데모 페이지 + 자동 생성 데모 페이지 모두 포함
    demo_pages = sorted(
        [f for f in os.listdir(DEMOS_PATH)
         if f.endswith('.md') and f != 'index.md'],
    )
    lines = [
        "# 인터랙티브 데모\n",
        "WebGPU Compute Shader로 DirectX 11 강의 예제를 재현한 데모입니다.  \n",
        "슬라이더를 조작해 실시간으로 파라미터를 바꿔볼 수 있습니다.\n",
        "\n---\n",
    ]
    for fname in demo_pages:
        title = _extract_title_from_md(os.path.join(DEMOS_PATH, fname))
        slug = fname[:-3]
        lines.append(f"\n## [{title}]({fname})\n")
        lines.append(f"\n[→ 데모 열기]({fname}){{.md-button}}\n")
        lines.append("\n---\n")

    with open(os.path.join(DEMOS_PATH, 'index.md'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))


def create_demo_page(title, demo_slug):
    """docs/demos/<slug>.md — 데모를 iframe으로 감싸는 독립 페이지를 생성합니다."""
    demo_page_path = os.path.join(DEMOS_PATH, f"{demo_slug}.md")
    if os.path.exists(demo_page_path):
        return  # 이미 존재하면 건너뜀 (pixel-animation.md, raytracer.md 등 수동 페이지 보호)
    # MkDocs renders demos/<slug>.md → demos/<slug>/index.html
    # demo.html is at demos/<slug>/demo.html
    # So relative iframe src from the rendered page is just "demo.html"
    content = f"""# {title}

<div style="border: 1px solid #312e81; border-radius: 8px; overflow: hidden; margin: 16px 0;">
<iframe src="demo.html" width="100%" height="640" frameborder="0" scrolling="no" style="display:block;"></iframe>
</div>
"""
    with open(demo_page_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"  데모 페이지 생성: {demo_page_path}")


def update_mkdocs_nav(demo_title, demo_slug):
    """mkdocs.yml의 인터랙티브 데모 섹션에 새 항목을 추가합니다."""
    mkdocs_path = os.path.join(PORTFOLIO_REPO_PATH, 'mkdocs.yml')
    # YAML 특수문자(콜론, 대괄호 등)가 포함된 제목은 따옴표로 감싸야 파싱 오류 방지
    needs_quote = ':' in demo_title or demo_title.startswith('[')
    safe_title = f'"{demo_title}"' if needs_quote else demo_title
    nav_entry = f"    - {safe_title}: demos/{demo_slug}.md"

    with open(mkdocs_path, 'r', encoding='utf-8') as f:
        content = f.read()

    if f"demos/{demo_slug}.md" in content:
        return  # 이미 등록됨

    # 마지막 "    - ...: demos/..." 라인 뒤에 삽입
    lines = content.split('\n')
    last_demo_idx = -1
    for i, line in enumerate(lines):
        if re.match(r'    - .+: demos/', line):
            last_demo_idx = i

    if last_demo_idx >= 0:
        lines.insert(last_demo_idx + 1, nav_entry)
        with open(mkdocs_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        print(f"  mkdocs.yml nav 업데이트: {demo_title}")


# ── Save & commit ──────────────────────────────────────────────────────────────

def save_and_commit(title, md_content, commit_hash=None, js_demo_html=None, demo_topic_slug=None):
    os.makedirs(POSTS_PATH, exist_ok=True)
    os.makedirs(DEMOS_PATH, exist_ok=True)

    date_str = datetime.datetime.now().strftime("%Y-%m-%d")
    slug = _make_slug(title)
    md_filename = f"{date_str}-{slug}.md"
    md_path = os.path.join(POSTS_PATH, md_filename)

    demo_rel_path = None
    if js_demo_html and demo_topic_slug:
        demo_dir = os.path.join(DEMOS_PATH, demo_topic_slug)
        os.makedirs(demo_dir, exist_ok=True)
        # demo.html (not index.html) — MkDocs renders foo.md -> foo/index.html
        # so index.html in a sub-folder would conflict
        demo_html_path = os.path.join(demo_dir, "demo.html")
        with open(demo_html_path, "w", encoding="utf-8") as f:
            f.write(js_demo_html)
        demo_rel_path = f"../../demos/{demo_topic_slug}/demo.html"
        print(f"  WebGPU 데모 저장: {demo_html_path}")

        # 데모 독립 페이지 생성 + 인덱스/nav 갱신
        create_demo_page(title, demo_topic_slug)
        update_mkdocs_nav(title, demo_topic_slug)

    final_content = md_content
    if demo_rel_path:
        final_content += f"""

---

## 인터랙티브 WebGPU 데모

<div style="border: 1px solid #312e81; border-radius: 8px; overflow: hidden; margin: 16px 0;">
<iframe src="{demo_rel_path}" width="100%" height="700" frameborder="0" scrolling="no" style="display:block;"></iframe>
</div>
"""

    with open(md_path, "w", encoding="utf-8") as f:
        f.write(final_content)
    print(f"  포스트 저장: {md_path}")

    # 포스트/데모 인덱스 + 홈페이지 항상 재빌드 (새 항목 반영)
    rebuild_posts_index()
    rebuild_demos_index()
    rebuild_homepage()
    print("  인덱스 갱신 완료 (index.md, posts/index.md, demos/index.md)")

    if commit_hash:
        mark_commit_processed(commit_hash)

    portfolio_repo = Repo(PORTFOLIO_REPO_PATH)
    portfolio_repo.git.add(A=True)
    portfolio_repo.index.commit(f"Add portfolio post: {title}")
    try:
        portfolio_repo.remote('origin').push()
        print("  GitHub 푸시 완료.")
    except Exception as e:
        print(f"  자동 푸시 실패 (수동 push 필요): {e}")


# ── High-level entry point ─────────────────────────────────────────────────────

def process_commit(commit_hash=None, skip_if_processed=True):
    """단일 커밋에 대한 포트폴리오를 생성합니다."""
    if skip_if_processed and commit_hash:
        if commit_hash in load_processed_commits():
            print(f"  건너뜀 (이미 처리됨): {commit_hash[:7]}")
            return False

    label = commit_hash[:7] if commit_hash else 'HEAD'
    print(f"커밋 처리 중: {label}")

    # 강의 이미지 동기화 (신규 이미지가 있으면 docs/images/로 복사)
    all_images, newly_synced = sync_study_images()
    if newly_synced:
        print(f"  이미지 {len(newly_synced)}개 새로 동기화: {newly_synced}")
    if all_images:
        print(f"  사용 가능한 이미지: {all_images}")

    hexsha, commit_msg, diff_text, file_contents = get_commit_diff(STUDY_REPO_PATH, commit_hash)
    if not diff_text.strip():
        print("  주의: 지원되는 파일 형식의 코드 변경이 없습니다.")
    else:
        print(f"  파일 내용 로드: {list(file_contents.keys())}")

    md_content = generate_portfolio_post(commit_msg, diff_text, file_contents)

    title = commit_msg.split('\n')[0]
    first_line = md_content.split('\n')[0].strip()
    if first_line.startswith('# '):
        title = first_line[2:].strip()

    demo_slug = _make_slug(title)[:40]
    js_html = generate_webgpu_demo(commit_msg, diff_text, commit_msg, file_contents, all_images)

    save_and_commit(
        title, md_content,
        commit_hash=hexsha,
        js_demo_html=js_html,
        demo_topic_slug=demo_slug if js_html else None,
    )
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="포트폴리오 포스트 생성")
    parser.add_argument('--commit', default=None, help='처리할 커밋 해시 (기본값: HEAD)')
    parser.add_argument('--force', action='store_true', help='이미 처리된 커밋도 재생성')
    args = parser.parse_args()

    process_commit(
        commit_hash=args.commit,
        skip_if_processed=not args.force,
    )

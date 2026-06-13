import os
import sys
import re
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

SUPPORTED_EXTS = ('.cpp', '.h', '.c', '.hlsl', '.glsl', '.vert', '.frag', '.py')


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
    """특정 커밋(또는 HEAD)의 diff를 반환합니다. (hexsha, message, diff_text)"""
    repo = Repo(repo_path)
    commit = repo.commit(commit_hash) if commit_hash else repo.head.commit

    if not commit.parents:
        diff = commit.diff('4b825dc642cb6eb9a060e54bf8d69288fbee4904')
    else:
        diff = commit.parents[0].diff(commit, create_patch=True)

    diff_text = ""
    for d in diff:
        try:
            if d.a_path.endswith(SUPPORTED_EXTS):
                diff_text += f"--- File: {d.a_path} ---\n"
                diff_text += str(d.diff.decode('utf-8', errors='ignore')) + "\n\n"
        except Exception as e:
            print(f"  diff 건너뜀 ({d.a_path}): {e}")

    return commit.hexsha, commit.message.strip(), diff_text


# Keep backward-compat alias
def get_latest_commit_diff(repo_path):
    _, msg, diff = get_commit_diff(repo_path)
    return msg, diff


# ── Gemini helpers ─────────────────────────────────────────────────────────────

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

def generate_portfolio_post(commit_msg, diff_text):
    prompt = f"""당신은 컴퓨터 그래픽스 전문가입니다.
아래는 학습자가 DirectX 11 / C++ 그래픽스 스터디 레포지토리에 커밋한 내용입니다.

커밋 메시지: {commit_msg}

코드 변경사항(diff):
{diff_text[:6000] if diff_text.strip() else "(코드 변경 없음 — 커밋 메시지 기반으로 작성)"}

작성 규칙:
1. 한국어로 작성하세요.
2. Markdown 형식으로, 첫 줄은 반드시 # 제목 형식의 제목으로 시작하세요.
3. 학습자가 '직접 구현하며 이해한 개념'을 중심으로 서술하세요.
4. 핵심 수식은 $$ ... $$ LaTeX 블록으로 표현하세요.
5. 강의 소스코드를 그대로 붙여넣지 말고, 핵심 알고리즘을 의사코드(pseudo-code) 또는 추상화된 형태로 설명하세요.
6. 마지막에 **WebGPU 인터랙티브 데모** 섹션을 추가하세요 — 이 내용을 브라우저 WebGPU Compute Shader로 시각화하면 어떤 모습인지 간략히 설명하세요.
7. ```markdown 블록으로 감싸지 말고 바로 Markdown을 출력하세요.
"""
    print("  포스트 생성 중 (Gemini)...")
    return _call_gemini(prompt)


def generate_webgpu_demo(commit_msg, diff_text, topic_hint):
    """WebGPU Compute Shader 기반 self-contained HTML 데모를 생성합니다."""
    prompt = f"""당신은 WebGPU/WGSL 전문가이며 DirectX 11 파이프라인을 WebGPU로 정확히 재현합니다.

아래 DirectX 11 / C++ 컴퓨터 그래픽스 주제를 WebGPU Compute Shader 기반으로 구현하세요.

주제: {topic_hint}
커밋 메시지: {commit_msg}

코드 변경사항 (요약):
{diff_text[:3000] if diff_text.strip() else "(커밋 메시지 기반으로 구현)"}

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

## UI 요구사항:
- ImGui 스타일 다크 테마 (창 프레임 포함, DirectX 11 앱 느낌)
- 파라미터 조작 슬라이더 (한국어 레이블)
- 실시간 업데이트 (`scheduleRender` 패턴 — RAF 중복 방지)
- 창 제목표시줄: `DirectX 11 — [주제명]` 스타일
- 배경: `#1a1a2e`

## 소스 이미지 (2D 이미지 처리 주제인 경우):
- 밝기 조절, 블러, 색상 변환, 픽셀 조작 등의 주제에는 절차적 그라디언트/패턴 대신 반드시 실제 이미지를 사용하세요.
- `../../images/colosseum.jpg` 를 아래 패턴으로 로드하세요:
```javascript
async function loadImage(url, w, h) {{
  const img = new Image();
  await new Promise((resolve, reject) => {{
    img.onload = resolve;
    img.onerror = () => reject(new Error(`이미지 로드 실패: ${{url}}`));
    img.src = url;
  }});
  const c = document.createElement('canvas');
  c.width = w; c.height = h;
  c.getContext('2d').drawImage(img, 0, 0, w, h);
  return c;
}}
// 사용: const srcCanvas = await loadImage('../../images/colosseum.jpg', W, H);
// 이후: srcCanvas.getContext('2d').getImageData(0, 0, W, H) → writeTexture()
```

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
    # 데모 목록 (index.md 제외, 알파벳순)
    demo_pages = sorted(
        [f for f in os.listdir(DEMOS_PATH) if f.endswith('.md') and f != 'index.md']
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
<iframe src="{demo_rel_path}" width="100%" height="640" frameborder="0" scrolling="no" style="display:block;"></iframe>
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

    hexsha, commit_msg, diff_text = get_commit_diff(STUDY_REPO_PATH, commit_hash)
    if not diff_text.strip():
        print("  주의: 지원되는 파일 형식의 코드 변경이 없습니다.")

    md_content = generate_portfolio_post(commit_msg, diff_text)

    title = commit_msg.split('\n')[0]
    first_line = md_content.split('\n')[0].strip()
    if first_line.startswith('# '):
        title = first_line[2:].strip()

    demo_slug = _make_slug(title)[:40]
    js_html = generate_webgpu_demo(commit_msg, diff_text, commit_msg)

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

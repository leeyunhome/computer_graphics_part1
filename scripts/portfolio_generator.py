import os
import sys
import re
import datetime
from git import Repo
from google import genai
from dotenv import load_dotenv

load_dotenv()

STUDY_REPO_PATH = r"c:\coding\my-github-repository\HonglabComputerGraphics_part1"
PORTFOLIO_REPO_PATH = r"c:\coding\my-github-repository\computer_graphics_part1"
DOCS_PATH = os.path.join(PORTFOLIO_REPO_PATH, "docs")
POSTS_PATH = os.path.join(DOCS_PATH, "posts")
DEMOS_PATH = os.path.join(DOCS_PATH, "demos")

SUPPORTED_EXTS = ('.cpp', '.h', '.c', '.hlsl', '.glsl', '.vert', '.frag', '.py')


def get_latest_commit_diff(repo_path):
    repo = Repo(repo_path)
    commit = repo.head.commit
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
            print(f"Skipping diff for {d.a_path}: {e}")

    return commit.message.strip(), diff_text


def _make_slug(text):
    slug = re.sub(r'[^\w\s-]', '', text).strip().lower()
    slug = re.sub(r'[-\s]+', '-', slug)
    return slug or "portfolio-update"


def _call_gemini(prompt):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "your_api_key_here":
        print("Error: GEMINI_API_KEY not set in .env")
        sys.exit(1)
    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt,
    )
    return response.text


def generate_portfolio_post(commit_msg, diff_text):
    prompt = f"""당신은 컴퓨터 그래픽스 전문가입니다.
아래는 학습자가 DirectX 11 / C++ 그래픽스 스터디 레포지토리에 커밋한 내용입니다.

커밋 메시지: {commit_msg}

코드 변경사항(diff):
{diff_text if diff_text.strip() else "(코드 변경 없음 — 커밋 메시지 기반으로 작성)"}

작성 규칙:
1. 한국어로 작성하세요.
2. Markdown 형식으로, 첫 줄은 반드시 # 제목 형식의 제목으로 시작하세요.
3. 학습자가 '직접 구현하며 이해한 개념'을 중심으로 서술하세요.
4. 핵심 수식은 $$ ... $$ LaTeX 블록으로 표현하세요.
5. 강의 소스코드를 그대로 붙여넣지 말고, 핵심 알고리즘을 의사코드(pseudo-code) 또는 추상화된 형태로 설명하세요.
6. 마지막에 **JavaScript 데모 연동 가능 여부** 섹션을 추가하세요 — 이 내용을 브라우저 Canvas/WebGL로 시각화하면 어떤 모습인지 간략히 설명하세요.
7. ```markdown 블록으로 감싸지 말고 바로 Markdown을 출력하세요.
"""
    print("Gemini로 포스트 생성 중...")
    return _call_gemini(prompt)


def generate_js_demo(commit_msg, diff_text, topic_hint):
    """핵심 그래픽스 알고리즘을 시각화하는 self-contained HTML+JS 파일을 생성."""
    prompt = f"""당신은 JavaScript Canvas/WebGL 전문가입니다.
아래 컴퓨터 그래픽스 주제를 브라우저에서 인터랙티브하게 시각화하는 self-contained HTML 파일을 작성하세요.

주제 힌트: {topic_hint}
커밋 메시지: {commit_msg}

요구사항:
- 단일 HTML 파일 (외부 라이브러리 CDN 사용 가능)
- Canvas 2D 또는 WebGL로 핵심 알고리즘을 시각화
- 파라미터 조작 슬라이더를 UI에 포함 (ImGui 슬라이더 역할)
- 배경은 어두운 테마 (#0f172a 계열)
- 한국어 레이블
- 파일 맨 위에 <!DOCTYPE html> 시작
- 외부 스크립트 불러오는 것 외 모든 코드 인라인 포함

주제와 관련이 없거나 시각화가 불가능하면 "SKIP"이라고만 답하세요.
HTML 코드만 출력하고 다른 설명 텍스트는 넣지 마세요.
"""
    print("JS 데모 생성 중...")
    result = _call_gemini(prompt)
    if result.strip().upper() == "SKIP":
        return None
    # Strip possible markdown code fences
    result = re.sub(r'^```html\s*', '', result.strip(), flags=re.IGNORECASE)
    result = re.sub(r'\s*```$', '', result.strip())
    return result.strip()


def save_and_commit(title, md_content, js_demo_html=None, demo_topic_slug=None):
    os.makedirs(POSTS_PATH, exist_ok=True)
    os.makedirs(DEMOS_PATH, exist_ok=True)

    date_str = datetime.datetime.now().strftime("%Y-%m-%d")
    slug = _make_slug(title)
    md_filename = f"{date_str}-{slug}.md"
    md_path = os.path.join(POSTS_PATH, md_filename)

    # If a JS demo was generated, save it and inject iframe into post
    demo_rel_path = None
    if js_demo_html and demo_topic_slug:
        demo_dir = os.path.join(DEMOS_PATH, demo_topic_slug)
        os.makedirs(demo_dir, exist_ok=True)
        demo_html_path = os.path.join(demo_dir, "index.html")
        with open(demo_html_path, "w", encoding="utf-8") as f:
            f.write(js_demo_html)
        # relative path from docs/posts/ to docs/demos/
        demo_rel_path = f"../demos/{demo_topic_slug}/index.html"
        print(f"JS 데모 저장: {demo_html_path}")

    # Append iframe to markdown if demo exists
    final_content = md_content
    if demo_rel_path:
        final_content += f"""

---

## 인터랙티브 데모

<div style="border: 1px solid #312e81; border-radius: 8px; overflow: hidden; margin: 16px 0;">
<iframe src="{demo_rel_path}" width="100%" height="560" frameborder="0" scrolling="no" style="display:block;"></iframe>
</div>
"""

    with open(md_path, "w", encoding="utf-8") as f:
        f.write(final_content)
    print(f"포스트 저장: {md_path}")

    # Commit & push
    repo = Repo(PORTFOLIO_REPO_PATH)
    repo.git.add(A=True)
    repo.index.commit(f"Add portfolio post: {title}")
    try:
        repo.remote('origin').push()
        print("GitHub 푸시 완료.")
    except Exception as e:
        print(f"자동 푸시 실패 (수동으로 push 필요): {e}")


if __name__ == "__main__":
    print("학습 저장소에서 최신 커밋 추출 중...")
    try:
        commit_msg, diff_text = get_latest_commit_diff(STUDY_REPO_PATH)
    except Exception as e:
        print(f"학습 저장소 접근 오류: {e}")
        sys.exit(1)

    if not diff_text.strip():
        print("주의: 지원되는 파일 형식의 코드 변경이 없습니다.")

    md_content = generate_portfolio_post(commit_msg, diff_text)

    title = commit_msg.split('\n')[0]
    first_line = md_content.split('\n')[0].strip()
    if first_line.startswith('# '):
        title = first_line[2:].strip()

    # Try to generate a JS demo
    topic_hint = commit_msg
    demo_slug = _make_slug(title)[:40]
    js_html = generate_js_demo(commit_msg, diff_text, topic_hint)

    save_and_commit(title, md_content, js_html, demo_slug if js_html else None)

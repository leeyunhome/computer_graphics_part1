import os
import sys
import datetime
from git import Repo
from google import genai
from dotenv import load_dotenv

load_dotenv()

# Configuration
STUDY_REPO_PATH = r"c:\coding\my-github-repository\HonglabComputerGraphics_part1"
PORTFOLIO_REPO_PATH = r"c:\coding\my-github-repository\computer_graphics_part1"
DOCS_PATH = os.path.join(PORTFOLIO_REPO_PATH, "docs")

def get_latest_commit_diff(repo_path):
    repo = Repo(repo_path)
    # Get the latest commit
    commit = repo.head.commit
    # Get diff from the parent commit
    if not commit.parents:
        diff = commit.diff(repo.tree('4b825dc642cb6eb9a060e54bf8d69288fbee4904')) # empty tree
    else:
        diff = commit.parents[0].diff(commit, create_patch=True)
    
    diff_text = ""
    for d in diff:
        try:
            # We only care about code changes
            if d.a_path.endswith(('.cpp', '.h', '.c', '.py', '.glsl', '.vert', '.frag')):
                diff_text += f"File: {d.a_path}\n"
                diff_text += str(d.diff.decode('utf-8', errors='ignore')) + "\n\n"
        except Exception as e:
            print(f"Skipping diff for {d.a_path}: {e}")
            
    return commit.message.strip(), diff_text

def generate_portfolio_post(commit_msg, diff_text):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "your_api_key_here":
        print("Error: GEMINI_API_KEY is not set. Please update the .env file.")
        sys.exit(1)

    client = genai.Client(api_key=api_key)
    
    prompt = f"""
I am studying computer graphics. I have just committed some code to my study repository. 
Commit message: {commit_msg}

Code Diff:
{diff_text}

Your task:
Write a professional portfolio blog post about what I implemented and learned in this commit.
You MUST write it in Korean.
You MUST format it as a beautiful Markdown document.
You MUST explain the core concepts, math, or rendering techniques used.
You MUST NOT copy the exact source code to avoid copyright issues (it is a course repository). 
Instead, you can write pseudo-code, explain the algorithms conceptually, or write brief code snippets that represent the core idea abstractly.
If no graphics code diff was found, write a short post based on the commit message.

Make the post engaging, academic but accessible, and suitable for a MkDocs material site. Use markdown headings, bullet points, and math blocks (using $math$ or $$math$$) where appropriate.
Do not wrap the whole output in ```markdown blocks, just output the raw markdown.
Add a # Title at the very beginning based on the content.
"""

    print("Generating portfolio post with Gemini 3.1 Pro...")
    response = client.models.generate_content(
        model='gemini-3.1-pro-preview',
        contents=prompt,
    )
    return response.text

def save_and_commit(title, content):
    # Ensure docs directory exists
    os.makedirs(DOCS_PATH, exist_ok=True)
    
    # Create filename
    date_str = datetime.datetime.now().strftime("%Y-%m-%d")
    
    # Clean up title for filename
    import re
    safe_title = re.sub(r'[^\w\s-]', '', title).strip().lower()
    safe_title = re.sub(r'[-\s]+', '-', safe_title)
    if not safe_title:
        safe_title = "portfolio-update"
        
    filename = f"{date_str}-{safe_title}.md"
    file_path = os.path.join(DOCS_PATH, filename)
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
        
    print(f"Saved post to {file_path}")
    
    # Commit to portfolio repo
    repo = Repo(PORTFOLIO_REPO_PATH)
    repo.git.add(A=True)
    repo.index.commit(f"Add portfolio post: {title}")
    
    # Push to GitHub
    try:
        origin = repo.remote(name='origin')
        origin.push()
        print("Successfully pushed to GitHub.")
    except Exception as e:
        print(f"Could not push to GitHub automatically: {e}")
        print("Please push manually.")

if __name__ == "__main__":
    print("Extracting changes from study repository...")
    try:
        commit_msg, diff_text = get_latest_commit_diff(STUDY_REPO_PATH)
    except Exception as e:
        print(f"Error accessing study repo: {e}")
        sys.exit(1)
        
    if not diff_text.strip():
        print("Notice: No significant code changes found in the latest commit for supported file types.")
        
    content = generate_portfolio_post(commit_msg, diff_text)
    
    # Extract title from the first line if it's a heading
    title = commit_msg.split('\n')[0]
    first_line = content.split('\n')[0].strip()
    if first_line.startswith('# '):
        title = first_line[2:].strip()
        
    save_and_commit(title, content)

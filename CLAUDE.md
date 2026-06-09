# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **portfolio automation system** for computer graphics study. It watches a private study repository, and when new commits are detected, uses AI (Gemini API) to generate Korean-language blog posts documenting the learned concepts — then deploys them to GitHub Pages via MkDocs.

**Critical constraint:** The study repository (`C:\coding\my-github-repository\HonglabComputerGraphics_part1`) is a lecture repository and must NOT be published directly. Portfolio content must describe the student's own understanding and implementation, not reproduce lecture code verbatim.

## Repository Relationships

- **Study repo** (private, never publish): `C:\coding\my-github-repository\HonglabComputerGraphics_part1`
- **Portfolio repo** (this repo, public): `https://github.com/leeyunhome/computer_graphics_part1`
- Path to study repo is stored in `references/reference.txt`

## Study Repository Tech Stack

The study repo implements computer graphics progressively:
- **Language:** C++ with DirectX 11 (D3D11) and HLSL shaders
- **Math:** GLM library
- **UI:** Dear ImGui for real-time parameter control
- **Pattern:** CPU raytracing → GPU texture upload → full-screen quad render
- **Topics:** DX11 init, Bloom, and 14-step raytracing progression (spheres → Phong → perspective → shadows → textures → reflection → refraction → environment maps)

## Portfolio Automation

### Running the watcher (watches study repo for new commits)
```
start_watcher.bat
# or directly:
venv\Scripts\python.exe scripts\watcher.py
```

### Manually generating a portfolio post from the latest commit
```
run_generator.bat
# or directly:
venv\Scripts\python.exe scripts\portfolio_generator.py
```

### Building and previewing the site locally
```
venv\Scripts\mkdocs serve
```

### Deploying to GitHub Pages
```
venv\Scripts\mkdocs gh-deploy --force
```
Deployment also runs automatically via `.github/workflows/deploy.yml` on every push to `main`.

## Python Environment

```
venv\Scripts\pip install -r requirements.txt   # if requirements.txt exists
venv\Scripts\pip install mkdocs-material gitpython google-genai python-dotenv
```

Copy `.env copy.example` to `.env` and fill in the Gemini API key:
```
GEMINI_API_KEY=your_key_here
```

## Content Generation Rules

When generating portfolio posts, the AI prompt must:
1. Focus on **what the student implemented and understood**, not the lecture structure
2. Explain the graphics concepts mathematically (LaTeX supported via pymdownx.math)
3. Write in **Korean**
4. Never reproduce lecture code blocks verbatim — paraphrase or rewrite to show understanding
5. Post filenames follow the pattern: `docs/YYYY-MM-DD-topic-name.md`

## MkDocs Configuration

Site config is in `mkdocs.yml`. Posts go in `docs/`. The Material theme supports:
- Math rendering (`pymdownx.arithmatex` with MathJax)
- Code syntax highlighting
- Navigation tabs and dark mode

## GitHub Actions

`.github/workflows/deploy.yml` triggers on push to `main` and runs `mkdocs gh-deploy --force`. No secrets needed beyond the default `GITHUB_TOKEN` (GitHub Pages deploy uses it automatically).

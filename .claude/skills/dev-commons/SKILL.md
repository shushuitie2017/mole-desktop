---
name: dev-commons
description: "Cross-project development intelligence. 20 Flask patterns, 18 Electron patterns, 20 frontend patterns, 15 Windows pitfalls, 12 git/release workflows, 15 code conventions, 12 security patterns, 15 Next.js patterns, 15 Python patterns. BM25 search engine. Actions: scaffold route, build feature, fix bug, configure build, debug pitfall, review code, release version, setup project. Stacks: Flask + vanilla JS, Electron + PyInstaller, Next.js + React + Prisma, FastAPI + SQLite, pure Python CLI. Shared across all projects."
metadata:
  tier: default
  cost: medium
  side_effects: none
---
# dev-commons — Cross-Project Development Intelligence

Shared development patterns extracted from 30+ projects. Contains Flask backend patterns, Electron desktop app patterns, frontend conventions, Windows pitfalls, security patterns, Next.js/React patterns, Python coding patterns, git/release workflows, and code conventions. 9 domains with 140+ entries searchable via BM25 engine.

## When to Apply

Reference this skill when:
- Starting a new project (scaffold from proven patterns)
- Adding Flask API routes, SSE streaming, or background tasks
- Building Electron desktop apps with PyInstaller backend
- Debugging Windows-specific issues (paths, encoding, ffmpeg)
- Implementing i18n, dark theme, XSS prevention, or localStorage patterns
- Setting up Next.js App Router, Prisma, shadcn/ui, or Tailwind v4
- Managing git tags, changelog, GitHub Releases, or multi-server deployment
- Reviewing code for naming conventions and security best practices
- Implementing license systems, auth guards, or API key management

## Domain Categories by Priority

| Priority | Domain | Entries | Impact |
|----------|--------|---------|--------|
| 1 | `windows-pitfalls` — Windows-specific issues and fixes | 15 | CRITICAL |
| 2 | `security-patterns` — Auth, encryption, XSS prevention | 12 | CRITICAL |
| 3 | `flask-patterns` — Flask backend patterns (routes, SSE, threading) | 20 | HIGH |
| 4 | `electron-patterns` — Electron + PyInstaller + IPC | 18 | HIGH |
| 5 | `frontend-patterns` — i18n, dark theme, localStorage, DOM | 20 | HIGH |
| 6 | `code-conventions` — Naming, imports, commit messages | 15 | MEDIUM |
| 7 | `python-patterns` — Python coding patterns, CLI, config | 15 | MEDIUM |
| 8 | `nextjs-patterns` — Next.js App Router, Prisma, shadcn | 15 | MEDIUM |
| 9 | `git-release` — Version management, GitHub Releases | 12 | LOW |

**Total: 142 entries / 9 domains**

---

## Quick Reference

### 1. Windows Pitfalls (CRITICAL — MUST KNOW)

- `backslash-in-onclick` — NEVER use inline onclick with Windows paths → use data-* + addEventListener
- `path-normpath` — ALWAYS use os.path.normpath() on file paths
- `utf8-stdout` — Force UTF-8: `sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')`
- `ffmpeg-winget-path` — Auto-detect ffmpeg from WinGet install path
- `pyinstaller-startup-slow` — Use --onedir (not --onefile) for large apps
- `file-lock-delete` — Retry with backoff when deleting locked files

### 2. Security Essentials (CRITICAL)

- `xss-prevention` — Always escapeHtml() for text, escapeAttr() for attributes
- `api-key-management` — Config JSON gitignored, NEVER hardcode keys
- `path-injection` — normpath + startswith check for path traversal
- `cors-whitelist` — Whitelist specific localhost ports only
- `data-isolation` — All DB queries MUST filter by userId

### 3. Flask Backend (HIGH)

- `route-post-json` — data.get() + strip() + 400 error for validation
- `sse-progress` — SSE generator with terminal status check
- `thread-safe-download` — threading.Lock + progress_store + daemon=True
- `subtitle-cache-arch` — Multi-layer cache to avoid 429 rate limits
- `error-status-codes` — 400/404/429/500 with error key in JSON

### 4. Electron Desktop (HIGH)

- `pyinstaller-onedir` — --onedir + --add-data + verify output size
- `electron-flask-fork` — Spawn Flask process, kill on quit
- `ipc-contextbridge` — Expose safe API via contextBridge
- `electron-builder-config` — NSIS + extraResources + icon 256x256+
- `vue-ipc-serialization` — Convert reactive proxy before IPC send

### 5. Frontend (HIGH)

- `i18n-system` — LANG object + t(key) + data-i18n attributes (en/zh/ja)
- `escape-html` — escapeHtml() + escapeAttr() implementations
- `data-attr-events` — data-* + addEventListener for dynamic content
- `async-button-disable` — Disable during operation, re-enable in finally
- `dark-theme-tokens` — CSS variables for bg/panel/card/border/accent/text

### 6. Code Conventions (MEDIUM)

- Python: snake_case / PascalCase / UPPER_SNAKE / _ prefix
- JavaScript: camelCase / PascalCase components
- CSS: kebab-case / BEM-like naming
- API: jsonify + status codes (200/400/404/429/500)
- Git: conventional commits (feat/fix/chore/docs/refactor)

---

## How to Use

### Prerequisites

```bash
python --version  # Python 3.6+
```

### Search Commands

```bash
# List all domains
python .claude/skills/dev-commons/scripts/search.py --domains

# Search specific domain
python .claude/skills/dev-commons/scripts/search.py "Flask route jsonify" --domain flask-patterns

# Auto-detect domain from query
python .claude/skills/dev-commons/scripts/search.py "Windows path backslash"

# Cross-domain overview
python .claude/skills/dev-commons/scripts/search.py "XSS security escape" --overview

# JSON output
python .claude/skills/dev-commons/scripts/search.py "Electron IPC preload" --json
```

---

## Workflow

### New Flask Project Setup

```bash
# 1. Get Flask app skeleton
python .claude/skills/dev-commons/scripts/search.py "flask app skeleton" --domain python-patterns

# 2. Get route patterns
python .claude/skills/dev-commons/scripts/search.py "route post json validate" --domain flask-patterns

# 3. Get frontend patterns
python .claude/skills/dev-commons/scripts/search.py "dark theme i18n" --domain frontend-patterns

# 4. Check Windows pitfalls
python .claude/skills/dev-commons/scripts/search.py "windows path encoding" --domain windows-pitfalls
```

### New Electron App Setup

```bash
# 1. Get Electron + Flask fork pattern
python .claude/skills/dev-commons/scripts/search.py "electron flask fork" --domain electron-patterns

# 2. Get IPC setup
python .claude/skills/dev-commons/scripts/search.py "ipc contextbridge preload" --domain electron-patterns

# 3. Get PyInstaller build pattern
python .claude/skills/dev-commons/scripts/search.py "pyinstaller onedir add-data" --domain electron-patterns

# 4. Get license system
python .claude/skills/dev-commons/scripts/search.py "license hardware fingerprint" --domain security-patterns
```

### New Next.js Project Setup

```bash
# 1. Get App Router structure
python .claude/skills/dev-commons/scripts/search.py "app router page layout" --domain nextjs-patterns

# 2. Get API route template
python .claude/skills/dev-commons/scripts/search.py "api route auth" --domain nextjs-patterns

# 3. Get Prisma + SQLite setup
python .claude/skills/dev-commons/scripts/search.py "prisma sqlite" --domain nextjs-patterns

# 4. Get shadcn/ui + Tailwind v4
python .claude/skills/dev-commons/scripts/search.py "shadcn tailwind v4" --domain nextjs-patterns
```

### Bug Fix Investigation

```bash
# 1. Check Windows pitfalls first
python .claude/skills/dev-commons/scripts/search.py "[error keyword]" --domain windows-pitfalls

# 2. Check security issues
python .claude/skills/dev-commons/scripts/search.py "[error keyword]" --domain security-patterns

# 3. Cross-domain search
python .claude/skills/dev-commons/scripts/search.py "[error keyword]" --overview
```

### Release Flow

```bash
# 1. Get version update checklist
python .claude/skills/dev-commons/scripts/search.py "version update checklist" --domain git-release

# 2. Get release commands
python .claude/skills/dev-commons/scripts/search.py "github release create" --domain git-release

# 3. Get post-release verification
python .claude/skills/dev-commons/scripts/search.py "verify release assets" --domain git-release
```

---

## Search Reference

### Available Domains

| Domain | File | Entries | Use For | Example Keywords |
|--------|------|---------|---------|------------------|
| `flask-patterns` | flask-patterns.csv | 20 | Routes, SSE, threading, caching | flask, route, sse, thread, subtitle, cache |
| `electron-patterns` | electron-patterns.csv | 18 | PyInstaller, IPC, auto-update, window | electron, pyinstaller, ipc, builder, updater |
| `frontend-patterns` | frontend-patterns.csv | 20 | i18n, XSS, localStorage, dark theme | i18n, escape, localstorage, dark, theme, fetch |
| `windows-pitfalls` | windows-pitfalls.csv | 15 | Path, encoding, ffmpeg, build issues | windows, backslash, utf8, ffmpeg, pyinstaller |
| `git-release` | git-release.csv | 12 | Versioning, releases, deployment | version, changelog, tag, release, deploy |
| `code-conventions` | code-conventions.csv | 15 | Naming, imports, commits, formatting | naming, convention, import, commit, docstring |
| `security-patterns` | security-patterns.csv | 12 | License, auth, XSS, CORS, secrets | license, aes, xss, cors, auth, gitignore |
| `nextjs-patterns` | nextjs-patterns.csv | 15 | App Router, Prisma, shadcn, Tailwind | nextjs, app router, prisma, shadcn, tailwind |
| `python-patterns` | python-patterns.csv | 15 | Flask/FastAPI, SQLite, threading, CLI | python, flask, fastapi, sqlite, argparse |

---

## Inheritance Model

**Loading order:** dev-commons (global) → project-specific SKILL

| Layer | Provides | Example |
|-------|----------|---------|
| **dev-commons** (this skill) | Universal patterns | How to write a Flask route, how to handle Windows paths |
| **Project SKILL** (e.g., yt-dl-dev) | Project-specific knowledge | This project's API endpoints, this project's UI components |

**No conflict:** Domain names are distinct — global uses `flask-patterns`, projects use `api-reference`.

Project SKILLs can override global conventions when needed (e.g., trading project uses FastAPI not Flask).

---

## Pre-Delivery Checklist

### Backend (Python)
- [ ] Routes return jsonify with appropriate status codes (400/404/429/500)
- [ ] Thread-safe access to shared state (use Lock)
- [ ] File paths use os.path.normpath() on Windows
- [ ] UTF-8 encoding forced for stdout/stderr
- [ ] API keys in gitignored config, never hardcoded
- [ ] SQL queries use parameterized statements (?)

### Frontend (JavaScript)
- [ ] User content escaped with escapeHtml() / escapeAttr()
- [ ] Dynamic elements use data-* + addEventListener (no inline onclick)
- [ ] Async buttons disabled during operation, re-enabled in finally
- [ ] i18n keys added for all 3 languages (en/zh/ja)
- [ ] Errors shown via showError() with translated messages
- [ ] Blob URLs revoked when no longer needed

### Electron
- [ ] PyInstaller output size verified (~37MB, not ~15MB)
- [ ] contextBridge methods match ipcMain.handle registrations
- [ ] requestSingleInstanceLock() called before app.whenReady()
- [ ] Window icon is 256x256+
- [ ] Server process killed on app quit

### Security
- [ ] No hardcoded API keys or secrets
- [ ] XSS prevention on all user-generated content
- [ ] CORS whitelist (no wildcard origins)
- [ ] Path traversal check (normpath + startswith)
- [ ] Sensitive files in .gitignore

### Release
- [ ] VERSION constant updated
- [ ] CHANGELOG.md updated
- [ ] Git tag created and pushed
- [ ] Release assets verified on GitHub
- [ ] Auto-updater tested (if Electron)

---

## Tips for Better Results

1. **Check Windows pitfalls first** — Most bugs in this workspace are Windows-specific
2. **Search across domains** — Use `--overview` when unsure which domain has the answer
3. **Combine with project SKILL** — dev-commons gives patterns, project SKILL gives specifics
4. **Use code snippets directly** — Code column contains copy-paste-ready implementations
5. **Follow the checklists** — Pre-delivery checklists prevent common regressions

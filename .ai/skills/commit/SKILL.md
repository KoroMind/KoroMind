---
name: commit
description: Create high-quality git commits by reviewing all unstaged and untracked changes, staging everything, and writing a senior-engineer commit message (1-line summary + concise bullet points). Use when you need to commit all current working tree changes in a git repo.
---

# Commit

## Overview

Create a complete, high-signal commit by inspecting all unstaged and untracked changes, staging everything, and writing a concise summary plus bullet points.

## Workflow

### 1) Verify repo and change state

- Run `git rev-parse --show-toplevel` to confirm a git repo.
- Run `git status --porcelain` to list changes.
- If there are no changes, stop and report.
- If any paths are conflicted (e.g., `UU`, `AA`, `DD`), stop and ask for resolution.

### 2) Read all unstaged and untracked changes

- Run `git diff` to review unstaged changes.
- For untracked files (`??`), read their content directly or use:
  - `git diff --no-index /dev/null -- <file>` for text files.
- If a file is binary or very large, summarize its purpose and size rather than dumping contents.

### 3) Stage everything

- Run `git add -A` to stage tracked + untracked changes.
- Run `git status --porcelain` and ensure the working tree is clean.

### 4) Compose the commit message from staged diff

- Run `git diff --cached` and derive a concise, high-signal summary.
- Use this format:

```
Short imperative summary (<= 72 chars)

- Bullet 1 (what changed + why, if known)
- Bullet 2
- Bullet 3
```

Guidelines:
- Keep 2-5 bullets, each short and specific.
- Prefer behavior/impact over file lists unless file names add clarity.
- Call out removals, renames, or migrations explicitly.
- If tests were run, include a bullet like `- Tests: <command>`.
- If tests were not run, include `- Tests: not run (not requested)` only when it adds clarity.

### 5) Commit

Use a commit message file to preserve formatting:

```
cat <<'MSG' > /tmp/COMMIT_MSG
Summary line

- Bullet 1
- Bullet 2
MSG

git commit -F /tmp/COMMIT_MSG
```

## Example

Request: "Commit my current changes."

Output commit message:

```
Refine Telegram voice processing flow

- Streamline STT/TTS handoff to reduce latency
- Harden error handling around download failures
- Tests: not run (not requested)
```

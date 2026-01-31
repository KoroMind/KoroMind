---
id: FEAT-003
type: feature
status: open
severity: low
location: Dockerfile:11-16
issue: null
validated: 2026-01-28
---

# Docker Dependencies

## Goal
- Include tools Claude needs for common operations
- Currently missing: git, gh, jq, ripgrep

## Solution
Add to Dockerfile:
```dockerfile
RUN apt-get update && apt-get install -y \
    git jq ripgrep \
    && rm -rf /var/lib/apt/lists/*

# GitHub CLI
RUN curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg \
    | dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=...] ..." \
    | tee /etc/apt/sources.list.d/github-cli.list \
    && apt-get update && apt-get install -y gh
```

## Test
- `docker exec koro git --version` → works
- `docker exec koro gh --version` → works

# Commit Skill

## Overview

The Commit skill guides Codex to create a full-repo git commit by reviewing all unstaged and untracked changes, staging everything, and composing a concise senior-engineer commit message (one-line summary plus bullet points).

## Architecture

- **Skill definition**: `.ai/skills/commit/SKILL.md`
- **Resources**: None required for initial version
- **Execution model**: Procedural workflow that relies on git CLI commands to inspect diffs, stage changes, and commit

## Data Models

Not applicable (no new data structures are introduced).

## API Contracts

Not applicable (no external APIs or services are used).

## UI/UX

Not applicable (CLI-only workflow).

## Configuration

- **Commit scope**: All working tree changes, including untracked files
- **Message format**: 1-line summary (<=72 chars) + concise bullet list

## Changelog

### 2026-01-27
- Initial specification for the Commit skill

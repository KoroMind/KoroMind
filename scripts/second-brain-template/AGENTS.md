# Second Brain Agent Instructions

This vault is a deterministic Markdown workspace for KoroMind.

## Mission
- Capture quickly.
- Structure information consistently.
- Preserve retrieval quality through strict indexing.

## Canonical Top-Level Layout
- `inbox/` - raw capture before triage.
- `notes/` - active thinking, source notes, meeting history.
- `knowledge/` - evergreen references for reuse.
- `projects/` - project and repository-specific memory.

Do not create extra top-level folders unless explicitly requested.

## Routing Rules
- Raw ideas/links/reminders -> `inbox/quick-notes.md`.
- Temporary artifacts for quick capture -> `inbox/quick-notes/`.
- Day-based planning/thinking -> `notes/daily/YYYY-MM-DD.md`.
- Course/talk/workshop notes -> `notes/lectures/YYYY-MM-DD_topic.md`.
- Meeting records -> `notes/meetings/YYYY-MM-DD_person-topic.md`.
- Paper/blog synthesis -> `notes/articles/YYYY-MM-DD_topic.md`.
- Long-lived conceptual hubs -> `notes/topics/topic-name.md`.
- People memory -> `notes/people/person-name.md`.
- Stable procedures -> `knowledge/howtos/`.
- Reusable commands/prompts/code -> `knowledge/snippets/`.
- Durable reading insights -> `knowledge/books/`.
- Repo or initiative execution context -> `projects/<project-name>/`.

## Filename Convention
- Date files: `YYYY-MM-DD.md`.
- Date + topic files: `YYYY-MM-DD_topic.md`.
- Meeting files: `YYYY-MM-DD_person-topic.md`.
- Topic/people files: lowercase kebab-case.
- Index files: `_INDEX.md` only.

## Required Frontmatter Schema
Use this schema for all non-trivial notes in `notes/` and `knowledge/`:

```yaml
---
title: <Human Title>
type: daily | lecture | meeting | article | topic | person | howto | snippet | book | glossary
created: YYYY-MM-DD
updated: YYYY-MM-DD
tags: []
status: draft | active | evergreen | archived
source: none
---
```

## Indexing Rules
- Every new file in `notes/`, `knowledge/`, or `projects/` must be linked from the nearest `_INDEX.md`.
- Keep `Recent` sections reverse chronological.
- Add one-line context next to each index entry.
- Add backlinks to related topic and people pages where relevant.
- Preserve links and headings when editing existing notes.

## Project Folder Contract
When adding a new folder under `projects/`:
1. Create `AGENTS.md` with project-specific conventions.
2. Create `README.md` describing scope and current goals.
3. Add links to both files in `projects/_INDEX.md`.

## Operating Quality Bar
- Prefer append-only updates in daily and meeting notes.
- Keep assumptions explicit and dated.
- Keep notes concise, factual, and auditable.

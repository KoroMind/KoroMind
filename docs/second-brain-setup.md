# Second Brain Setup

This guide explains a simple, editor-agnostic second-brain setup for Koro.

## 1. Create the Vault Directory

Choose a base path for your notes (example: `$HOME/second-brain`).

```bash
VAULT="$HOME/second-brain"
mkdir -p "$VAULT"
```

## 2. Folder Structure (Reference)

```text
vault/
|
|-- AGENTS.md
|-- README.md
|
|-- inbox/
|   |-- quick-notes.md
|   |-- voice-notes/
|   |-- web-clips/
|   `-- attachments/
|
|-- notes/
|   |-- _INDEX.md
|   |
|   |-- daily/
|   |   `-- YYYY-MM-DD.md
|   |
|   |-- lectures/
|   |   |-- _INDEX.md
|   |   `-- YYYY-MM-DD_topic.md
|   |
|   |-- meetings/
|   |   |-- _INDEX.md
|   |   `-- YYYY-MM-DD_person-topic.md
|   |
|   |-- videos/
|   |   |-- _INDEX.md
|   |   `-- YYYY-MM-DD_video-title.md
|   |
|   |-- research/
|   |   |-- _INDEX.md
|   |   `-- YYYY-MM-DD_topic.md
|   |
|   |-- topics/
|   |   |-- _INDEX.md
|   |   `-- topic-name.md
|   |
|   `-- people/
|       |-- _INDEX.md
|       `-- person-name.md
|
|-- knowledge/
|   |-- _INDEX.md
|   |
|   |-- howtos/
|   |   |-- _INDEX.md
|   |   `-- howto-name.md
|   |
|   |-- snippets/
|   |   |-- _INDEX.md
|   |   `-- snippet-name.md
|   |
|   |-- concepts/
|   |   |-- _INDEX.md
|   |   `-- concept-name.md
|   |
|   `-- glossary.md
|
|-- tasks/
|   |-- _INDEX.md
|   |-- TODO.md
|   |-- waiting-for.md
|   |-- someday-maybe.md
|   |
|   `-- projects/
|       |-- _INDEX.md
|       `-- project-name.md
|
|-- projects/
|   |-- _INDEX.md
|   |-- _manifest.yml
|   |
|   |-- koromind/
|   |   |-- AGENT.md
|   |   |-- docs/
|   |   `-- (cloned repo)
|   |
|   |-- actmate/
|   |   |-- AGENT.md
|   |   |-- docs/
|   |   `-- (cloned repo)
|   |
|   `-- other-project/
|       |-- AGENT.md
|       `-- (cloned repo)
|
|-- templates/
|   |-- note-template.md
|   |-- lecture-template.md
|   |-- meeting-template.md
|   |-- research-template.md
|   |-- video-template.md
|   |-- project-template.md
|   `-- decision-template.md
|
|-- ops/
|   |-- agent/
|   |   |-- routing.md
|   |   |-- conventions.md
|   |   |-- memory-policy.md
|   |   `-- playbooks/
|   |       |-- triage-inbox.md
|   |       |-- add-repo.md
|   |       `-- create-note.md
|   |
|   |-- logs/
|   |-- backups/
|   `-- exports/
|
`-- private/
    |-- _INDEX.md
    `-- sensitive-notes.md
```

## 3. Scaffold the Full Structure

Paste this command to create the proposed folders and starter files:

```bash
VAULT="$HOME/second-brain"   # change if needed
mkdir -p "$VAULT"/{
inbox/{voice-notes,web-clips,attachments},
notes/{daily,lectures,meetings,videos,research,topics,people},
knowledge/{howtos,snippets,concepts},
tasks/projects,
projects/{koromind/docs,actmate/docs,other-project},
templates,
ops/agent/playbooks,
ops/{logs,backups,exports},
private
}

touch \
"$VAULT/AGENTS.md" \
"$VAULT/README.md" \
"$VAULT/inbox/quick-notes.md" \
"$VAULT/knowledge/glossary.md" \
"$VAULT/tasks/TODO.md" \
"$VAULT/tasks/waiting-for.md" \
"$VAULT/tasks/someday-maybe.md" \
"$VAULT/projects/_manifest.yml" \
"$VAULT/templates/note-template.md" \
"$VAULT/templates/lecture-template.md" \
"$VAULT/templates/meeting-template.md" \
"$VAULT/templates/research-template.md" \
"$VAULT/templates/video-template.md" \
"$VAULT/templates/project-template.md" \
"$VAULT/templates/decision-template.md" \
"$VAULT/ops/agent/routing.md" \
"$VAULT/ops/agent/conventions.md" \
"$VAULT/ops/agent/memory-policy.md" \
"$VAULT/ops/agent/playbooks/triage-inbox.md" \
"$VAULT/ops/agent/playbooks/add-repo.md" \
"$VAULT/ops/agent/playbooks/create-note.md" \
"$VAULT/private/sensitive-notes.md" \
"$VAULT/projects/koromind/AGENT.md" \
"$VAULT/projects/actmate/AGENT.md" \
"$VAULT/projects/other-project/AGENT.md"

touch \
"$VAULT/notes/_INDEX.md" \
"$VAULT/notes/lectures/_INDEX.md" \
"$VAULT/notes/meetings/_INDEX.md" \
"$VAULT/notes/videos/_INDEX.md" \
"$VAULT/notes/research/_INDEX.md" \
"$VAULT/notes/topics/_INDEX.md" \
"$VAULT/notes/people/_INDEX.md" \
"$VAULT/knowledge/_INDEX.md" \
"$VAULT/knowledge/howtos/_INDEX.md" \
"$VAULT/knowledge/snippets/_INDEX.md" \
"$VAULT/knowledge/concepts/_INDEX.md" \
"$VAULT/tasks/_INDEX.md" \
"$VAULT/tasks/projects/_INDEX.md" \
"$VAULT/projects/_INDEX.md" \
"$VAULT/private/_INDEX.md"
```

## 4. How Indexing Works (`_INDEX.md`)

Use `_INDEX.md` files as section entry points:

- `notes/_INDEX.md`: map core note sections and recent notes
- `knowledge/_INDEX.md`: map durable reference knowledge
- `tasks/_INDEX.md`: map active lists and project tasks
- subfolder `_INDEX.md`: map only that folder

Minimal pattern:

```md
# Index

## Recent
- [[2026-02-11_topic]]

## Related
- [[../topics/topic-name]]
- [[../people/person-name]]
```

## 5. Naming Conventions

- Use ISO dates: `YYYY-MM-DD` (example: `2026-02-11.md`)
- Use lowercase kebab-case for topics and concepts (example: `system-design.md`)
- Keep `_INDEX.md` files updated as navigation maps

## 6. How Koro Uses This Vault

Koro can work directly with this structure by reading and writing Markdown files in place.

Recommended mode:

- set your vault path in environment: `KOROMIND_VAULT=/path/to/vault`
- ask Koro to create/update notes, maintain `_INDEX.md`, and manage tasks
- keep write operations deterministic by using full paths

## 7. Optional: Track the Vault with Git

You can make the whole vault a Git repository for version history, rollback, and backup sync.

```bash
cd "$VAULT"
git init
git add .
git commit -m "Initial second-brain structure"
```

Recommended:

- add a private remote repository for backup
- commit frequently after meaningful note updates
- avoid committing highly sensitive files from `private/` unless the remote is trusted and encrypted

## 8. First Notes to Fill In

- `README.md` (how your vault works)
- `notes/_INDEX.md` (main map of notes)
- `knowledge/_INDEX.md` (main map of reference content)
- `tasks/TODO.md` (active tasks)
- `inbox/quick-notes.md` (quick capture)

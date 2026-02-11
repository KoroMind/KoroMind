# Second Brain Obsidian Setup

This guide explains a simple way to set up your Obsidian second brain for Koro.

## 1. Install and Enable Obsidian CLI

If you run `scripts/setup.sh`, Obsidian is installed automatically (best effort) on compatible Linux systems.

Then enable CLI in Obsidian:

1. Open Obsidian.
2. Go to `Settings -> General -> Command line interface`.
3. Enable it and complete registration.

Verify in terminal:

```bash
obsidian version
obsidian help
```

Note: Obsidian app must be running. If it is not running, the first `obsidian ...` command starts it.

## 2. Create a Vault

1. Create a new vault in Obsidian (example name: `vault`).
2. Use the folder structure below.

## 3. Folder Structure

Use this exact structure:

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

### One-shot scaffold command

Paste this in terminal to create the full structure quickly:

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

Then in Obsidian:

1. If you are on a local desktop with GUI: `Open folder as vault` and select `$VAULT`.
2. Enable CLI: `Settings -> General -> Command line interface`.

Headless VM note:

- Obsidian CLI requires the Obsidian desktop app process.
- On a headless VM, use this scaffold command to create/sync the vault files, but run Obsidian app+CLI from your local machine against that vault copy.

## 4. How Indexing Works (`_INDEX.md`)

Use each `_INDEX.md` as a map of its section:

- `notes/_INDEX.md`: links to major notes sections (`daily`, `lectures`, `meetings`, `research`, etc.)
- `knowledge/_INDEX.md`: links to long-lived reference knowledge
- `tasks/_INDEX.md`: links to `TODO.md`, `waiting-for.md`, project task notes
- subfolder `_INDEX.md` files: link to notes in that specific folder

Simple pattern for each `_INDEX.md`:

```md
# Index

## Recent
- [[2026-02-11_topic]]

## Related
- [[../topics/topic-name]]
- [[../people/person-name]]
```

This keeps navigation fast and predictable for both you and Koro.

## 5. Naming Conventions

- Use ISO dates: `YYYY-MM-DD` (example: `2026-02-11.md`)
- Use lowercase kebab-case for topics and concepts (example: `system-design.md`)
- Keep category `_INDEX.md` files as entry points and link out from them

## 6. Recommended Obsidian Settings

- Files and links:
  - New link format: **Relative path to file**
  - Automatically update internal links: **On**
  - Default location for new notes: **Specified folder** (`inbox/`)
- Daily notes:
  - Folder: `notes/daily`
  - Date format: `YYYY-MM-DD`
- Attachments:
  - Default location: `inbox/attachments`

## 7. First Notes to Create

Create these first so the vault is immediately usable:

- `README.md` (how your vault works)
- `notes/_INDEX.md` (main map of notes)
- `knowledge/_INDEX.md` (main map of reference content)
- `tasks/TODO.md` (active tasks)
- `inbox/quick-notes.md` (quick capture)

## 8. How Koro Uses This Vault

Koro already has a dedicated skill at `skills/obsidian-cli/SKILL.md`.

What this means:

- Koro can use Obsidian CLI to read, search, and update notes efficiently.
- Koro follows safer command patterns (prefer `path=`, controlled writes, avoid destructive deletes).
- You can ask Koro to operate directly on this vault structure (daily notes, tasks, research, topics, people, and indexes).

Useful quick commands:

```bash
obsidian daily:read
obsidian search query="TODO" path="tasks" matches
obsidian tasks daily
obsidian open path="notes/_INDEX.md"
```

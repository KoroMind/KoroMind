# Second Brain Setup

This guide explains the default second-brain vault that KoroMind now scaffolds automatically.

## 1. Run Setup Script

The setup script creates and seeds the vault at:

`$HOME/koromind-work-dir/second-brain`

```bash
curl -fsSL https://raw.githubusercontent.com/KoroMind/KoroMind/main/scripts/setup.sh | bash
```

Scaffold source in this repo: `scripts/second-brain-template/`.

Notes:
- Existing vault files are preserved on repeated setup runs.
- Missing files/folders from the template are added automatically.

## 2. Generated Structure (Reference)

```text
second-brain/
|-- AGENTS.md                 # System instructions for the AI agent: structure, routing, naming, triage rules
|-- README.md                 # Human-readable explanation of the vault and how to use it
|-- inbox/                    # Capture layer for raw, unprocessed information
|   |-- quick-notes.md        # Primary fast capture file for ideas, links, reminders, thoughts
|   |-- quick-notes/          # Temporary storage for attachments, screenshots, voice transcripts before triage
|-- notes/                    # Working and intermediate knowledge, thinking and reflection
|   |-- _INDEX.md             # Map of the notes space for navigation by human and agent
|   |-- daily/                # Default workspace for journaling, planning, and daily thinking
|   |   |-- _INDEX.md         # Optional overview of daily notes
|   |   `-- YYYY-MM-DD.md     # Daily log, planning, and temporary structured thinking
|   |-- lectures/             # Notes from courses, conferences, seminars, workshops
|   |   |-- _INDEX.md         # Overview of lectures and learning sources
|   |   `-- YYYY-MM-DD_topic.md # Structured lecture or learning note
|   |-- meetings/             # Notes from professional, research, or business meetings
|   |   |-- _INDEX.md         # Overview of collaborators and discussions
|   |   `-- YYYY-MM-DD_person-topic.md # Meeting notes including decisions and next steps
|   |-- articles/             # Summaries and reflections from scientific papers and blog posts
|   |   |-- _INDEX.md         # Overview of reading and research material
|   |   `-- YYYY-MM-DD_topic.md # Article or paper summary and insights
|   |-- topics/               # Evolving high-level conceptual thinking and mental models
|   |   |-- _INDEX.md         # Map of key domains and interest areas
|   |   `-- topic-name.md     # Long-term growing concept note
|   `-- people/               # Relationship memory and context about collaborators and contacts
|       |-- _INDEX.md         # Overview of important people and network
|       `-- person-name.md    # Information, context, and history of interaction
|-- knowledge/                # Evergreen, stable, long-term reusable knowledge
|   |-- _INDEX.md             # Map of permanent knowledge
|   |-- glossary.md           # Definitions and terminology
|   |-- howtos/               # Stable step-by-step workflows and protocols
|   |   `-- _INDEX.md         # Overview of operational and technical procedures
|   |-- snippets/             # Reusable code, prompts, commands, and configurations
|   |   `-- _INDEX.md         # Map of reusable components
|   |-- books/                # Permanent insights extracted from books and long-form learning
|   |   `-- _INDEX.md         # Overview of book knowledge and mental models
|-- projects/                 # Active projects combining code, research, and decisions
|   |-- _INDEX.md             # Overview of active and archived projects
|   |-- git-repo1/            # Cloned Git repository with project code and documentation
|   |-- git-repo2/            # Another active repository and its associated thinking
|   `-- other-project/        # Non-code or hybrid project workspace
```

## 3. How Indexing Works (`_INDEX.md`)

Use `_INDEX.md` files as section entry points:

- `notes/_INDEX.md`: map source-driven notes
- `knowledge/_INDEX.md`: map durable reference pages
- `projects/_INDEX.md`: map active repositories and project context
- subfolder `_INDEX.md`: map only that folder

Minimal pattern:

```md
# Index

## Recent
- [[2026-02-11_topic]] - one-line context

## Related
- [[../topics/topic-name]]
- [[../people/person-name]]
```

## 4. Naming Conventions

- Dates: `YYYY-MM-DD` (example: `2026-02-11.md`)
- Topic/concept/person files: lowercase kebab-case (example: `system-design.md`)
- Keep `_INDEX.md` files current when adding new files
- Use the frontmatter schema described in vault root `AGENTS.md`

## 5. How Koro Uses This Vault

Koro can work directly with this structure by reading/writing Markdown files in place.

Recommended:
- set vault path in environment: `KOROMIND_VAULT=$HOME/koromind-work-dir/second-brain`
- ask Koro to maintain `_INDEX.md` as notes are added
- keep write operations deterministic by using full paths

## 6. Optional: Track Vault with Git

```bash
cd "$HOME/koromind-work-dir/second-brain"
git init
git add .
git commit -m "Initial second-brain structure"
```

Recommended:
- use a private remote for backup
- commit frequently after meaningful updates
- keep sensitive notes and attachments out of untrusted remotes

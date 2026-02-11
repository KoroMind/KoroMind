---
name: obsidian-cli
description: Interact with Obsidian vaults using the Obsidian CLI to read, create, search, and manage notes, tasks, properties, and more. Also supports plugin and theme development with commands to reload plugins, run JavaScript, capture errors, take screenshots, and inspect the DOM. Use when the user asks to interact with their Obsidian vault, manage notes, search vault content, perform vault operations from the command line, or develop and debug Obsidian plugins and themes.
---

# Obsidian CLI

Use the `obsidian` CLI to interact with a running Obsidian instance. Requires Obsidian to be open.

## Command reference

Run `obsidian help` to see all available commands. This is always up to date. Full docs: https://help.obsidian.md/cli

## Syntax

**Parameters** take a value with `=`. Quote values with spaces:

```bash
obsidian create name="My Note" content="Hello world"
```

**Flags** are boolean switches with no value:

```bash
obsidian create name="My Note" silent overwrite
```

For multiline content use `\n` for newline and `\t` for tab.

## File targeting

Many commands accept `file` or `path` to target a file. Without either, the active file is used.

- `file=<name>` — resolves like a wikilink (name only, no path or extension needed)
- `path=<path>` — exact path from vault root, e.g. `folder/note.md`

## Vault targeting

Commands target the most recently focused vault by default. Use `vault=<name>` as the first parameter to target a specific vault:

```bash
obsidian vault="My Vault" search query="test"
```

## Common patterns

```bash
obsidian read file="My Note"
obsidian create name="New Note" content="# Hello" template="Template" silent
obsidian append file="My Note" content="New line"
obsidian search query="search term" limit=10
obsidian daily:read
obsidian daily:append content="- [ ] New task"
obsidian property:set name="status" value="done" file="My Note"
obsidian tasks daily todo
obsidian tags sort=count counts
obsidian backlinks file="My Note"
```

Use `--copy` on any command to copy output to clipboard. Use `silent` to prevent files from opening. Use `total` on list commands to get a count.

## Koro second-brain essentials

Use these commands when operating a structured second-brain vault (capture, retrieval, task flow, and hygiene).

### Preflight

```bash
obsidian version
obsidian help
```

### Deterministic targeting

Prefer `path=` over `file=` in automation to avoid ambiguous filename resolution.

```bash
obsidian read path="notes/topics/ai-agents.md"
obsidian open path="notes/_INDEX.md"
obsidian vault="My Vault" search query="agent hooks" path="notes" matches
```

### Daily workflow

```bash
obsidian daily
obsidian daily:read
obsidian daily:append content="- [ ] Follow up with Alex"
obsidian daily:prepend content="## Focus\n- Ship docs"
```

### Writing and templates

```bash
obsidian create path="notes/research/2026-02-11_agent-routing.md" content="# Agent Routing\n\n" silent
obsidian append path="notes/topics/ai-agents.md" content="\n## Notes\n- ..."
obsidian prepend path="notes/topics/ai-agents.md" content="updated: 2026-02-11"
obsidian templates
obsidian template:read name=note-template resolve
obsidian create path="notes/meetings/2026-02-11_design-review.md" template=meeting-template
```

### Tasks and updates

```bash
obsidian tasks daily
obsidian tasks all todo
obsidian task ref="notes/daily/2026-02-11.md:8" toggle
obsidian task daily line=3 done
```

### Retrieval and vault hygiene

```bash
obsidian outline path="notes/research/2026-02-11_agent-routing.md" format=md
obsidian links path="notes/topics/ai-agents.md"
obsidian unresolved counts
obsidian orphans total
obsidian deadends total
```

### Metadata and safety

```bash
obsidian properties all counts
obsidian property:set path="notes/topics/ai-agents.md" name=status value=active type=text
obsidian property:read path="notes/topics/ai-agents.md" name=status
obsidian diff path="notes/topics/ai-agents.md" from=1
obsidian history path="notes/topics/ai-agents.md"
obsidian history:read path="notes/topics/ai-agents.md" version=1
```

Policy:
- Prefer read/search/outline/tasks/backlinks/links for analysis.
- Use create/append/prepend/property:set for controlled writes.
- Avoid `delete permanent` unless explicitly confirmed by the user.

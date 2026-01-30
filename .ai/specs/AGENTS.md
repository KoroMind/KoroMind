# Specs

Specifications for KoroMind services, features, and issues.

## Core Principle

**Specs describe services and usecases, NOT files.**

Bad: one spec per source file (`voice.md` for `voice.py`)
Good: one spec per mental model (`service-voice.md` for voice capability)

### The Litmus Test

> Can a new developer understand this capability by reading ONE spec?

If the answer is "no, read 3 specs and piece it together" - wrong granularity.

## Granularity Hierarchy

```
service (default)  →  feature (rare)  →  bug/security (temporary)
```

| Type | When to use | Example |
|------|-------------|---------|
| `service-*` | Major capability, answers "how does X work?" | `service-voice.md` |
| `feature-*` | Distinct sub-capability with own lifecycle | `feature-voice-streaming.md` |
| `bug-*` | Specific issue being tracked | `bug-rate-limit-bypass.md` |
| `security-*` | Security concern or vulnerability | `security-sandbox-escape.md` |
| `refactor-*` | Planned structural change | `refactor-handler-consolidation.md` |

**Most specs are services. Split only when genuinely necessary.**

## Format

```markdown
---
id: SVC-001
type: service | feature | bug | security | refactor
status: draft | active | done | obsolete
severity: critical | high | medium | low
issue: 22
validated: 2026-01-29
---

# Title

## What
- One sentence: what capability/problem this covers
- Scope boundary: what's included, what's NOT

## Why
- Business reason this exists
- What breaks without it

## How
- Key components involved (reference `src/path:lines`)
- Data flow or sequence (brief)
- Configuration options

## Test
- Key scenarios to verify (one line each)
- Edge cases that matter

## Changelog
- YYYY-MM-DD: Change summary
```

## Rules

1. **Max 50 lines per spec** (excluding frontmatter/changelog). Split if larger.
2. **One concern per spec.** Multiple related specs can live in one file, separated by `---`.
3. **Reference code locations**, don't duplicate code.
4. **Validate regularly.** Update `validated` date when you confirm spec matches reality.
5. **Link to issues.** Every spec should trace to a GitHub issue.

## ID Prefixes

| Prefix | Type |
|--------|------|
| SVC | Service |
| FEA | Feature |
| BUG | Bug |
| SEC | Security |
| REF | Refactor |

## Anti-Patterns

- **Spec mirrors file structure** - Coupling docs to implementation
- **Prose essays** - Nobody reads walls of text
- **Spec diverges from code** - Lies waiting to mislead
- **Orphan specs** - No linked issue, no owner, no validation

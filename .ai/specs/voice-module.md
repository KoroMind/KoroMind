# Voice Module

## Overview

The voice module handles speech-to-text (STT) and text-to-speech (TTS) across
interfaces (Telegram, API, CLI). This update adds robust STT language handling
for Telegram voice mode, allowing automatic language detection or a user-set
language. This is required because current STT uses a fixed English language
code, causing failures for non-English input (e.g., Polish).

## Architecture

- `koro.core.voice.VoiceEngine.transcribe()` accepts an optional
  `language_code` argument and passes it to the STT provider (ElevenLabs Scribe).
- `koro.core.brain.Brain.process_message()` passes a per-user language
  preference to `transcribe()` when content is voice.
- `koro.interfaces.telegram.handlers.messages.handle_voice()` obtains the
  user's STT language setting and passes it to the brain or voice engine.
- `koro.core.state.StateManager` persists the new setting in SQLite and legacy
  JSON (migration).

### Provider behavior

- If `stt_language` is set to `auto`, use provider auto-detection (preferred)
  or omit the language parameter if required by the SDK.
- If `stt_language` is a specific code (e.g., `pl`), pass it directly to
  the provider as `language_code`.
- On provider errors for unsupported codes, fall back to `auto` and report a
  friendly message to the user.

## Data Models

### UserSettings

Add a new field:

- `stt_language: str` (default: `"auto"`)

Valid values:
- `"auto"` (auto-detect) or
- a language code supported by the STT provider (prefer ISO 639-1 codes such
  as `en`, `pl`, `de`)

### SQLite

Add column to `settings` table:

- `stt_language TEXT DEFAULT 'auto'`

### Legacy JSON

Include `stt_language` in `user_settings.json` migration/serialization.

## API Contracts

### GET `/settings`

Add field:

- `stt_language: string`

### PUT `/settings`

Accept optional field:

- `stt_language: string` (`"auto"` or a provider-supported language code)

### POST `/messages`

Optional enhancement (if needed for API/CLI):

- Allow `stt_language` override when `content_type == "voice"`.

## UI/UX

### Telegram

- `/settings` shows "Voice Language: Auto" (or specific language).
- Add buttons for common choices:
  - `Auto`, `English`, `Polish` (expandable list later).
- Add command `/language <code>` for explicit language codes not in the button
  list (e.g., `/language pl`).
- Provide feedback on unsupported codes and recommend `Auto`.

### CLI (optional)

- Add `stt_language` to the settings display and allow set via CLI flags.

## Configuration

- `VOICE_STT_LANGUAGE_DEFAULT` (default: `auto`) to set the default for new
  users or when settings are missing.
- Maintain a small allowlist for Telegram UI labels (e.g., `en`, `pl`) while
  accepting arbitrary valid codes in the API.

## Changelog

### 2026-01-28
- Added STT language selection and auto-detection support to voice module.
- Documented settings, persistence, and Telegram UI updates.

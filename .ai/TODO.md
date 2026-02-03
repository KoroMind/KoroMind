# TODO

## Specs Needed

### service-settings.md
- User settings management (audio, mode, voice speed, watch)
- Per-user persistence in SQLite
- CLI commands: `/audio on|off`, `/mode approve|go_all`, `/watch on|off`
- API endpoints for settings CRUD
- Default values and validation

### service-logging.md
- Global logging configuration available everywhere
- Debug logging via --debug flag or KOROMIND_DEBUG env var
- Structured log format with timestamps
- Log levels: DEBUG, INFO, WARNING, ERROR
- File and console handlers

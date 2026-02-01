# Debugging Patterns

## Debug logging is a first-class feature

Build debug logging while implementing, not after. Add `--debug` flags and `logger.debug()` calls as you write the code.

## Where to add logging in KoroMind

Log at boundaries (config loaded, options built, SDK called):

- `src/koro/core/vault.py` - config loading, path resolution
- `src/koro/core/brain.py` - vault config being passed
- `src/koro/core/claude.py` - options being built, effective values
- `src/koro/interfaces/cli/app.py` - vault path resolution

## Pattern

```python
import logging
logger = logging.getLogger(__name__)

# At key decision points:
logger.debug(f"Loaded vault config: {config}")
logger.debug(f"Using cwd: {effective_cwd}")
logger.debug(f"Building options with model={model}")
```

## CLI usage

```bash
python -m koro cli --debug
python -m koro cli --vault ~/.koromind --debug
```

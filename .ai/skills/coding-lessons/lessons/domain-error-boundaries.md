# Domain Error Boundaries

**Lesson from PR #40 review (Phase 2)**

## The Rule

Each layer wraps raw exceptions into its own domain error type. Callers catch the domain error, not implementation details.

## Why

| Leaking raw errors | Domain boundaries |
|-------------------|-------------------|
| Caller catches `OSError`, `yaml.YAMLError`, `ValidationError` | Caller catches `VaultError` |
| Implementation detail leaks upward | Clean abstraction boundary |
| Changing YAML → JSON requires updating all callers | Only vault.py changes |
| Exception handling scattered across codebase | Centralized in one layer |

## How

```python
# In vault.py — wrap at the source
class VaultError(Exception):
    """Raised when vault configuration is invalid."""

def load(self) -> VaultConfig:
    try:
        with open(self.config_file) as f:
            raw = yaml.safe_load(f)
    except OSError as e:
        raise VaultError(f"Failed to read {self.config_file}: {e}") from e
    except yaml.YAMLError as e:
        raise VaultError(f"Invalid YAML: {e}") from e

    try:
        self._config = VaultConfig.model_validate(raw, context=...)
    except Exception as e:
        raise VaultError(f"Invalid config: {e}") from e
```

```python
# In brain.py — catch the domain error, not internals
vault_config: VaultConfig | None = None
if self._vault:
    try:
        vault_config = self._vault.load()
    except VaultError:
        logger.warning("Vault config load failed, proceeding without", exc_info=True)
```

## Key Details

- **`from e`** preserves the original traceback — critical for debugging
- **Brain catches `VaultError`** and degrades gracefully (proceeds without config)
- **Vault catches specific exceptions** (`OSError`, `YAMLError`) not bare `except`
- **The `except Exception` in `model_validate`** is acceptable because Pydantic can raise many types

## Checklist

- [ ] Each layer has its own error type (`VaultError`, `VoiceError`, etc.)
- [ ] Raw exceptions wrapped with `raise DomainError(...) from e`
- [ ] Callers catch domain errors, never raw `OSError`/`yaml.YAMLError`
- [ ] Graceful degradation where possible (proceed without optional config)

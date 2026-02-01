# Testing Patterns

## Test fixtures vs production defaults

Test fixtures serve tests; production defaults serve users. When building features like "vault", the real value isn't test fixtures—it's a production-ready default that ships in `src/tests/fixtures/test-vault/`.

Ask: "What will users actually use?" not "What do tests need?"

## Run the code, don't just read it

Reading code can miss integration gaps. Running the actual code path reveals what's really happening.

Example: CLI wasn't using vaults at all—only discovered by trying `python -m koro cli`.

Standard verification: actually run the feature before claiming it works.

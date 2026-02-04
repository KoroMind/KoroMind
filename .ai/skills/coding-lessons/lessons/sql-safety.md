# SQL Safety

**Lesson from full-sdk-impl branch review**

## The Rule

Never interpolate values into SQL. Always use parameterized queries.

## Why

| String interpolation | Parameterized |
|---------------------|---------------|
| SQL injection possible | Injection impossible |
| Quoting bugs | Database handles escaping |
| Type coercion issues | Types preserved |
| Audit tools flag it | Passes security scans |

## How

```python
# BAD: SQL injection vulnerability
user_id = "123; DROP TABLE users; --"
cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")
cursor.execute(f"UPDATE settings SET {key} = '{value}' WHERE user_id = {user_id}")

# GOOD: Parameterized queries
cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
cursor.execute("UPDATE settings SET audio_enabled = ? WHERE user_id = ?", (value, user_id))
```

## Dynamic Column Names

Column names can't be parameterized. Whitelist them.

```python
# BAD: Column injection
def update_setting(column: str, value: str):
    cursor.execute(f"UPDATE settings SET {column} = ?", (value,))

# GOOD: Whitelist columns
ALLOWED_COLUMNS = {"audio_enabled", "voice_speed", "language"}

def update_setting(column: str, value: str):
    if column not in ALLOWED_COLUMNS:
        raise ValueError(f"Invalid column: {column}")
    cursor.execute(f"UPDATE settings SET {column} = ?", (value,))
```

## Red Flags in Code Review

```python
# All of these are vulnerabilities:
f"SELECT * FROM {table}"           # Table injection
f"WHERE id = {user_input}"         # Value injection
f"ORDER BY {column}"               # Column injection
"WHERE id = " + str(user_id)       # Concatenation
f"SET {key} = '{value}'"           # Key and value injection
```

## Checklist

- [ ] No f-strings or .format() in SQL with user data
- [ ] No string concatenation in SQL
- [ ] All values passed as tuple: `(value,)`
- [ ] Dynamic columns whitelisted explicitly
- [ ] Search codebase: `execute(f"` should return 0 results

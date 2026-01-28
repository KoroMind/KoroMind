-- Initial schema for KoroMind
-- Creates sessions, settings, and memory tables

-- Sessions table: tracks conversation sessions per user
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    last_active TEXT NOT NULL,
    is_current INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_sessions_user_id
ON sessions(user_id);

CREATE INDEX IF NOT EXISTS idx_sessions_user_current
ON sessions(user_id, is_current);

-- Settings table: user preferences
CREATE TABLE IF NOT EXISTS settings (
    user_id TEXT PRIMARY KEY,
    mode TEXT DEFAULT 'go_all',
    audio_enabled INTEGER DEFAULT 1,
    voice_speed REAL DEFAULT 1.1,
    watch_enabled INTEGER DEFAULT 0
);

-- Memory table: key-value store for long-term memory
CREATE TABLE IF NOT EXISTS memory (
    user_id TEXT NOT NULL,
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (user_id, key)
);

-- Migration status (legacy - for tracking JSON migrations)
CREATE TABLE IF NOT EXISTS migration_status (
    name TEXT PRIMARY KEY,
    completed_at TEXT NOT NULL
);

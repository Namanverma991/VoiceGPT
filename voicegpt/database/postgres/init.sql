-- ============================================================
-- VoiceGPT PostgreSQL Schema Initialization
-- Run once on a fresh database to create all tables/indexes.
-- For production: use Alembic migrations instead.
-- ============================================================

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";   -- for fuzzy text search

-- ─── Users ───────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email               VARCHAR(255) UNIQUE NOT NULL,
    username            VARCHAR(100) UNIQUE NOT NULL,
    hashed_password     VARCHAR(255) NOT NULL,
    is_active           BOOLEAN DEFAULT TRUE,
    is_superuser        BOOLEAN DEFAULT FALSE,
    preferred_language  VARCHAR(20) DEFAULT 'en',
    voice_preference    VARCHAR(50) DEFAULT 'female',
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_email    ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);

-- ─── Chat Sessions ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS chat_sessions (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title       VARCHAR(255) DEFAULT 'New conversation',
    language    VARCHAR(20) DEFAULT 'en',
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sessions_user_id    ON chat_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_updated_at ON chat_sessions(updated_at DESC);

-- ─── Chat Messages ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS chat_messages (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id  UUID NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    role        VARCHAR(20) NOT NULL,       -- user | assistant | system
    content     TEXT NOT NULL,
    audio_path  VARCHAR(500),              -- path to TTS audio file if stored
    tokens_used INTEGER DEFAULT 0,
    latency_ms  INTEGER DEFAULT 0,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_messages_session_id  ON chat_messages(session_id);
CREATE INDEX IF NOT EXISTS idx_messages_created_at  ON chat_messages(created_at);

-- ─── Auto-update updated_at trigger ─────────────────────────────────────────
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS set_users_updated_at ON users;
CREATE TRIGGER set_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS set_sessions_updated_at ON chat_sessions;
CREATE TRIGGER set_sessions_updated_at
    BEFORE UPDATE ON chat_sessions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ─── Demo seed data (optional) ───────────────────────────────────────────────
-- Uncomment to insert a demo admin user (password: admin1234)
-- INSERT INTO users (email, username, hashed_password, is_superuser)
-- VALUES (
--   'admin@voicegpt.local',
--   'admin',
--   '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW',
--   TRUE
-- ) ON CONFLICT DO NOTHING;

CREATE TABLE IF NOT EXISTS partner_context (
context_key TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(user_id), merchant_id TEXT NOT NULL,
state_json TEXT NOT NULL, updated_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS partner_actions (
action_id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(user_id), merchant_id TEXT NOT NULL,
session_hash TEXT NOT NULL, state TEXT NOT NULL, action_json TEXT NOT NULL, expires_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS partner_action_actor ON partner_actions(user_id, merchant_id, state);

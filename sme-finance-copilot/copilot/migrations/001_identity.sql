CREATE TABLE users (
 user_id TEXT PRIMARY KEY, username TEXT NOT NULL COLLATE NOCASE UNIQUE,
 email TEXT NOT NULL COLLATE NOCASE UNIQUE, display_name TEXT NOT NULL, role TEXT NOT NULL,
 account_status TEXT NOT NULL DEFAULT 'active', password_hash TEXT NOT NULL,
 must_change_password INTEGER NOT NULL DEFAULT 1, created_at REAL NOT NULL, updated_at REAL NOT NULL,
 last_login_at REAL, created_by TEXT NOT NULL, organization TEXT NOT NULL DEFAULT '',
 failed_attempts INTEGER NOT NULL DEFAULT 0, locked_until REAL NOT NULL DEFAULT 0
);
CREATE TABLE memberships (user_id TEXT REFERENCES users(user_id), merchant_id TEXT,
 PRIMARY KEY(user_id,merchant_id));
CREATE TABLE optional_permissions (user_id TEXT REFERENCES users(user_id), permission TEXT,
 PRIMARY KEY(user_id,permission));
CREATE TABLE sessions (token_hash TEXT PRIMARY KEY, user_id TEXT REFERENCES users(user_id),
 csrf_token TEXT NOT NULL, created_at REAL NOT NULL, last_seen REAL NOT NULL,
 reauthenticated_at REAL NOT NULL, revoked INTEGER NOT NULL DEFAULT 0);
CREATE TABLE login_attempts (identity_hash TEXT, address_hash TEXT, created_at REAL);
CREATE INDEX login_attempts_time ON login_attempts(created_at);
CREATE TABLE reset_tokens (token_hash TEXT PRIMARY KEY, user_id TEXT REFERENCES users(user_id),
 expires_at REAL NOT NULL, used INTEGER NOT NULL DEFAULT 0);
CREATE TABLE security_policies (policy_key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE role_permissions (role TEXT, permission TEXT, PRIMARY KEY(role,permission));
CREATE TABLE consents (consent_id TEXT PRIMARY KEY, merchant_id TEXT NOT NULL,
 owner_id TEXT REFERENCES users(user_id), recipient_id TEXT REFERENCES users(user_id),
 purpose TEXT NOT NULL, categories TEXT NOT NULL, granted_at REAL NOT NULL,
 expires_at REAL NOT NULL, revoked_at REAL);
CREATE TABLE audit_events (seq INTEGER PRIMARY KEY, record TEXT NOT NULL, hash TEXT NOT NULL);

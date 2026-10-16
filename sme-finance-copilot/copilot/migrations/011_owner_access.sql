CREATE TABLE owner_user_links (
 user_id TEXT NOT NULL REFERENCES users(user_id), merchant_id TEXT NOT NULL,
 owner_id TEXT NOT NULL REFERENCES users(user_id), origin TEXT NOT NULL,
 created_at REAL NOT NULL, PRIMARY KEY(user_id,merchant_id)
);
CREATE TABLE consent_downloads (
 consent_id TEXT PRIMARY KEY REFERENCES consents(consent_id), allow_csv INTEGER NOT NULL DEFAULT 0
);

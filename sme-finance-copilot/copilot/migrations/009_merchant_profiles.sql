CREATE TABLE merchant_profiles (
 merchant_id TEXT PRIMARY KEY, name TEXT NOT NULL, country TEXT NOT NULL,
 sector TEXT NOT NULL, status TEXT NOT NULL CHECK(status IN ('active','inactive')),
 version INTEGER NOT NULL, updated_by TEXT, updated_at REAL NOT NULL
);

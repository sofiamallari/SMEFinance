CREATE TABLE merchant_transaction_settings (
 merchant_id TEXT PRIMARY KEY, config_json TEXT NOT NULL, version INTEGER NOT NULL CHECK(version>0),
 updated_by TEXT NOT NULL REFERENCES users(user_id), updated_at REAL NOT NULL
);
CREATE TABLE merchant_mapping_templates (
 merchant_id TEXT NOT NULL, template_id TEXT NOT NULL, version INTEGER NOT NULL CHECK(version>0),
 name TEXT NOT NULL, headers_json TEXT NOT NULL, mapping_json TEXT NOT NULL,
 updated_by TEXT NOT NULL REFERENCES users(user_id), updated_at REAL NOT NULL,
 PRIMARY KEY(merchant_id,template_id,version)
);

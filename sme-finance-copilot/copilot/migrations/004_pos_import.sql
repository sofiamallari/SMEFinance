CREATE TABLE merchant_transaction_grants (
 user_id TEXT REFERENCES users(user_id), merchant_id TEXT NOT NULL, permission TEXT NOT NULL,
 granted_by TEXT NOT NULL, updated_at REAL NOT NULL, PRIMARY KEY(user_id,merchant_id,permission)
);
-- Preserve existing encoding authority as explicit scoped grants, not new defaults.
INSERT INTO merchant_transaction_grants SELECT u.user_id,m.merchant_id,'create_transactions','migration',u.updated_at
 FROM users u JOIN memberships m ON m.user_id=u.user_id WHERE u.role='staff';
INSERT INTO merchant_transaction_grants SELECT u.user_id,m.merchant_id,'bulk_import','migration',u.updated_at
 FROM users u JOIN memberships m ON m.user_id=u.user_id JOIN optional_permissions p ON p.user_id=u.user_id
 WHERE u.role='staff' AND p.permission='bulk_import';
INSERT OR IGNORE INTO role_permissions VALUES ('owner','view_quality_monitoring');
INSERT OR IGNORE INTO role_permissions VALUES ('owner','acknowledge_quality_alerts');
INSERT OR IGNORE INTO role_permissions VALUES ('owner','resolve_quality_alerts');
INSERT OR IGNORE INTO role_permissions VALUES ('staff','view_quality_monitoring');
INSERT OR IGNORE INTO role_permissions VALUES ('staff','acknowledge_quality_alerts');
INSERT OR IGNORE INTO role_permissions VALUES ('staff','resolve_quality_alerts');
CREATE TABLE pos_import_runs (
 batch_id TEXT PRIMARY KEY, merchant_id TEXT NOT NULL, actor_id TEXT NOT NULL, session_hash TEXT NOT NULL,
 kind TEXT NOT NULL, state TEXT NOT NULL, created_at REAL NOT NULL, expires_at REAL NOT NULL,
 source_json TEXT, source_signature TEXT, mappings_json TEXT, dataset_json TEXT, dataset_signature TEXT,
 preview_hash TEXT, validation_version INTEGER NOT NULL DEFAULT 0, metrics_json TEXT NOT NULL DEFAULT '{}',
 findings_json TEXT NOT NULL DEFAULT '[]', result_json TEXT, completed_at REAL, idempotency_key TEXT,
 audit_reference INTEGER, UNIQUE(actor_id,merchant_id,kind,idempotency_key)
);
CREATE INDEX pos_runs_merchant_time ON pos_import_runs(merchant_id,created_at);
CREATE TABLE pos_integrity_key(singleton INTEGER PRIMARY KEY CHECK(singleton=1), secret TEXT NOT NULL);
CREATE TABLE quality_alerts (
 alert_id TEXT PRIMARY KEY, merchant_id TEXT NOT NULL, batch_id TEXT, rule TEXT NOT NULL, severity TEXT NOT NULL,
 description TEXT NOT NULL, affected_rows INTEGER NOT NULL, recommendation TEXT NOT NULL,
 state TEXT NOT NULL DEFAULT 'open', detected_at REAL NOT NULL, updated_at REAL NOT NULL,
 UNIQUE(merchant_id,batch_id,rule)
);
CREATE TABLE quality_alert_events (
 event_id TEXT PRIMARY KEY, alert_id TEXT REFERENCES quality_alerts(alert_id), actor_id TEXT NOT NULL,
 from_state TEXT NOT NULL, to_state TEXT NOT NULL, reason TEXT NOT NULL, created_at REAL NOT NULL
);

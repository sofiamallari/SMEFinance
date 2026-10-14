CREATE TABLE financing_drafts (draft_id TEXT PRIMARY KEY, merchant_id TEXT NOT NULL, creator_id TEXT REFERENCES users(user_id), updated_at REAL NOT NULL, state TEXT NOT NULL, body TEXT NOT NULL, application_id TEXT);
CREATE TABLE role_migration_history (user_id TEXT PRIMARY KEY, original_role TEXT NOT NULL, mapped_role TEXT NOT NULL);
INSERT INTO role_migration_history SELECT user_id,role,CASE role WHEN 'owner' THEN 'SME_OWNER' WHEN 'staff' THEN 'SME_STAFF' WHEN 'lender_analyst' THEN 'BANK' WHEN 'security_admin' THEN 'SYSTEM_ADMIN' ELSE role END FROM users;
UPDATE users SET role=CASE role WHEN 'owner' THEN 'SME_OWNER' WHEN 'staff' THEN 'SME_STAFF' WHEN 'lender_analyst' THEN 'BANK' WHEN 'security_admin' THEN 'SYSTEM_ADMIN' ELSE role END;
UPDATE sessions SET revoked=1 WHERE user_id IN (SELECT user_id FROM role_migration_history);
DELETE FROM role_permissions WHERE role IN ('coach','demo_guest','user_admin');

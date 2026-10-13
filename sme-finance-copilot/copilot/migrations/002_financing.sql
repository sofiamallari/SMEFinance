CREATE TABLE applications (application_id TEXT PRIMARY KEY, merchant_id TEXT NOT NULL,
 owner_id TEXT REFERENCES users(user_id), recipient_id TEXT REFERENCES users(user_id),
 created_at REAL NOT NULL, packet TEXT NOT NULL);
CREATE TABLE application_reviews (review_id TEXT PRIMARY KEY, application_id TEXT REFERENCES applications(application_id),
 actor_id TEXT REFERENCES users(user_id), outcome TEXT NOT NULL, note TEXT NOT NULL, created_at REAL NOT NULL);
CREATE TABLE staff_access_requests (request_id TEXT PRIMARY KEY, merchant_id TEXT NOT NULL,
 owner_id TEXT REFERENCES users(user_id), details TEXT NOT NULL, created_at REAL NOT NULL);

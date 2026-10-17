CREATE TABLE IF NOT EXISTS cashflow_books (
 merchant_id TEXT PRIMARY KEY,
 data_json TEXT NOT NULL,
 source_filename TEXT,
 uploaded_by TEXT NOT NULL,
 uploaded_at REAL NOT NULL
);

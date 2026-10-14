CREATE TABLE IF NOT EXISTS simulated_payment_state (
reference TEXT PRIMARY KEY, merchant_id TEXT NOT NULL, state_json TEXT NOT NULL, updated_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS simulated_wallet_state (
merchant_id TEXT PRIMARY KEY, amount TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS simulated_refund_state (
idempotency_key TEXT PRIMARY KEY, merchant_id TEXT NOT NULL, result_json TEXT NOT NULL
);

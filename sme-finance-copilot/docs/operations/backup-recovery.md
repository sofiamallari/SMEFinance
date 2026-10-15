# Backup and recovery

Back up the identity/workflow SQLite database, canonical JSONL ledger, audit/execution logs and dataset/version metadata as a coordinated set. Stop all writing app/MCP processes before a filesystem snapshot, or use the existing journal lock and SQLite backup API with a reviewed consistency procedure. This documentation adds no automated backup service.

Verify SQLite integrity and foreign keys, read/validate the journal through the existing service, verify file hashes and perform restoration in a separate directory. Do not overwrite active data to test restoration. JSONL audit process segments must be treated honestly: individual segment verification is not continuous cross-restart chaining.

Original pre-CNY snapshot and retirement directories remain under the ignored logs/backups tree on the preparer’s machine; paths are historical local evidence, not artifacts guaranteed in a ZIP. Original audit/execution logs remain preserved there. Do not expose credentials, private identity hashes, local paths or original backup contents in submission packages.

Recovery requires stopped writers, preservation of the failed/current dataset and a matching verified snapshot. Restore identity/journal/state together to an approved dedicated root, select that root, verify it and then start. Do not combine CNY journal with archived foreign-currency identity/state. Legacy cutover rollback also needs the corresponding selector code/configuration; consult the retained private cutover record rather than blindly copying five files over a live service.

[Storage](cny-dataset.md) · [troubleshooting](troubleshooting.md) · [historical preparation record](../archive/implementation-notes/CNY_DEMO_AND_RAILWAY.md).

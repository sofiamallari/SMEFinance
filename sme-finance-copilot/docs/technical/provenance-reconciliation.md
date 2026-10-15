# Financial provenance and reconciliation

Keep source meaning, merchant, period, currency, transaction state and lineage with every financial claim. The canonical import/journal layer records file hash, source row/worksheet, external reference, mapping/normalization versions, signed normalized amounts and source identity as implemented. Typed AI facts also validate scope/currency/period. See [processing](data-processing.md) and [source](../../copilot/reliability.py).

Backend validation reconciles parsed = eligible + exact duplicate exclusions + invalid rows. Source controls, when independently provided, compare count/net/gross on their declared basis. Missing source controls are unavailable, not silently treated as independently verified. Exact duplicates can be excluded while conflicting/ambiguous records block. Completed effective totals differ from nominal totals for noncompleted statuses; refunds/reversals/expenses retain sign rules.

Current Validate shows five cards, one outcome and only meaningful findings. Preview shows two cards, signed completed net, normalized rows/source and pagination. Those simplifications do not remove backend reconciliation or confirmation restrictions. Saved mapping templates still exist outside the removed Validate-save section.

Synthetic seed activity, imported receipts and sandbox collections are separately identified. Seed aggregates are not reinserted into the canonical journal. No reliable external match exists for unlinked duplicate real-world descriptions, so never assume an unlinked POS import and sandbox collection are different sales. Wallet settlement is not extra revenue; no FX conversion/relabeling is performed.

Maturity and forecast inputs include configured synthetic attributes/obligations. Recorded net income is not audited profit; operating projections are not cash balances. Historical evidence snapshots remain available in [archive](../archive/README.md), without approval of their provisional business assumptions.

> **Historical snapshot — superseded.** Use [current documentation](../../README.md). Original evidence/scope is retained; old roles, menus, currency and setup instructions are not current policy.

# Automatic XLSX transaction-table detection

Implemented on `feature/security-sme-bank-workflow`, baseline HEAD `db78556f88487b66f6f5786e3b087bd97c6f41e3`. Existing root README edits and ZIP are preserved. No commit, push, merge, reset or discard was performed.

## SME Owner workflow

**Upload Files → Select Worksheets → Map Columns → Validate → Preview → Import**

Upload the workbook and tick its transaction worksheets. Each worksheet shows its name, checkbox and detected transaction count. Confident detections have no row-number controls. Worksheets remain unselected by default, so overview/summary sheets are never imported automatically. CSV retains its existing flow and skips worksheet selection.

For uncertain data, the sheet shows a reason and **Review Detected Data**. Expand it to inspect sample rows, including suspicious and boundary rows, and formula-cell indicators. Optional **Advanced Row Range** controls appear only within that review section. Select a header and last transaction row, then explicitly confirm the reviewed range and excluded data. Editing either boundary clears confirmation. Acknowledging a range does not bypass formula, financial, duplicate, currency or authorization validation.

Independent per-sheet mapping/defaults, all-row validation, combined preview, reconciliation, duplicate detection and explicit final import confirmation are unchanged. Detection is structural inspection, not financial validation or a statement that source values are trustworthy.

## Detection and safety rules

`copilot/worksheet_detection.py` is a deterministic, versioned structural detector:

- It seeks a unique, non-formula header containing one recognized date column and at least one amount column, with nonempty unique labels. Generic sales/expense/date/amount aliases are used; workbook names, worksheet names and row positions are not special-cased. Choosing net versus gross remains an explicit mapping decision.
- Potentially financial pre-header rows, repeated/multiple headers, unsupported header layouts, duplicate/out-of-order row numbers, unexpected row widths and missing/unrecognized dates require review. Incomplete rows remain candidate records; they are not silently discarded.
- Only a trailing suffix of clearly labeled totals/summaries can be excluded automatically. Date and transaction-identity fields must be empty; other content must be a recognized summary label or monetary constant/formula in a recognized monetary column. Formula-only rows, rows with transaction identity/date, middle subtotals and unclear footer text are not assumed to be disposable totals.
- Empty rows are recognized separately. Review samples include header, first/last records and suspicious/footer rows. Numerical introduction metadata can conservatively trigger review because it may represent omitted records.
- The existing XLSX reader scans cells without evaluating formulas or trusting their cached results. Cached formula errors/numbers/dates are replaced by a formula marker for inspection. Any formula cell retained in the selected transaction range is still rejected by the existing extraction rule, even after review confirmation.

The authenticated inspection response includes detection status, reasons, proposed boundaries, counts, excluded summary row numbers and bounded samples. Normal selection sends only the worksheet name and `detection_mode: auto`. The server recomputes detection from uploaded bytes, rejects ambiguous auto selections and boundary overrides, then checks that detected and extracted row counts agree. Client-supplied counts/status are not trusted.

Reviewed selection sends `detection_mode: reviewed`, explicit boundaries and `review_confirmed: true`. The signed source metadata retains original detection, selected bounds and excluded nonempty row numbers. Existing explicit-range API descriptors remain compatible; they are explicit manual selections, not automatically trusted detections. The existing signed staging/preview/journal mechanisms retain their integrity and atomic commit behavior.

An existing variable collision in extraction could overwrite numeric `header_row` metadata with a column name. The new tests exposed it; the inner column variable was renamed. Transaction values/calculations were unaffected.

## Bao Burgers verification

No manual row inputs were used for the automatic acceptance journey:

| Worksheet | Automatically retained records | Treatment |
|---|---:|---|
| Revenue Report | 5,408 | Unique header detected; trailing formula total excluded |
| Expense Report | 212 | Unique header detected; trailing formula total excluded |
| Overview & Summary | Not selected | No unique transaction table; review required if selected |
| Combined | 5,620 | Existing validation, reconciliation and confirmed atomic import |

The actual workbook was not edited. Tests use disposable authorized CNY merchant data and retain the existing import-only CNY/fee-accounting limitations documented in [multi-worksheet import](MULTI_WORKSHEET_IMPORT.md). Reimport still excludes duplicates rather than adding transactions.

## Verification

| Final verification | Actual result |
|---|---|
| Detection + worksheet/Bao + original CSV/XLSX importer backend suites | 54 tests PASS; 131.881 seconds; supplied workbook enabled, no skipped tests |
| Ambiguity/review UI | 18 checks PASS |
| Updated automatic Bao/CSV import UI regression | 33 checks PASS |

Browser checks used headless Edge at desktop 1600px, tablet 900px, mobile 390px and 320px. Screenshots were visually reviewed. Tests verified that advanced inputs are absent for confident sheets, hidden within review for uncertain sheets, and that editing ranges clears acknowledgement. A missing-date record remains in the three-row candidate dataset and blocks normal validation instead of disappearing. Syntax/compilation and Git whitespace checks passed. Tests cover header offsets, blank rows, clear totals, cached formula errors, unlabeled formulas, formula records, middle summaries, unknown footers, incomplete rows, multiple/repeated headers, possible pre-header transactions, uncertain ranges, confirmation reset, server-side override rejection, row-count consistency, CSV compatibility, existing XLSX parsing, merchant isolation, duplicate handling and atomic commit.

[Review UI assessment](../../../evidence/worksheet-detection/assessment.json) · [Automatic selection](../../../evidence/worksheet-detection/automatic-desktop.png) · [Mobile review](../../../evidence/worksheet-detection/review-mobile.png) · [Bao/import assessment](../../../evidence/multi-worksheet-import/assessment.json).

Run from the application directory:

```powershell
$env:COPILOT_BAO_WORKBOOK = 'C:\path\to\Initial Test Data - Bao Burgers Business.xlsx'
python -m unittest tests.test_worksheet_detection tests.test_multi_worksheet_import tests.test_pos_import -v
node scripts/verify_detection_review.cjs
node scripts/verify_multi_worksheet_ui.cjs
```

Browser checks require Python, Node, Playwright and Edge, with optional `COPILOT_TEST_PYTHON` / `COPILOT_PLAYWRIGHT_MODULE` overrides. Run browser fixtures sequentially on port 8126. The supplied-workbook backend test uses optional openpyxl and is explicitly skipped when its workbook/reader is unavailable; the acceptance run here supplies both.

## Files changed

- `copilot/worksheet_detection.py`: new conservative structural detector.
- `copilot/pos_extract.py`: formula-aware inspection, automatic/reviewed range enforcement, count consistency and signed detection metadata; existing bounded reader/security checks reused.
- `web/merchant-transactions.js`, `web/index.html`: six-label XLSX progress indicator, compact checkbox/count selection, conditional review and advanced range confirmation.
- `tests/test_worksheet_detection.py`: detection and safety edge cases.
- `tests/test_multi_worksheet_import.py`, `scripts/verify_multi_worksheet_ui.cjs`: supplied-workbook acceptance updated to require automatic boundaries.
- `scripts/verify_detection_review.cjs`: actual ambiguity/review UI checks and screenshots.
- This guide, docs index and existing importer/module guides: current instructions. `evidence/worksheet-detection/` and refreshed import evidence contain actual test outputs.

## Boundaries and remaining limitations

Detection uses conservative English header/summary aliases, not a model or confidence score. Unfamiliar/localized formats may require review. Only one unambiguous transaction table per selected worksheet is automatically supported; multiple tables require an explicitly reviewed range. Review samples are bounded, so users must also inspect their original source when choosing an advanced range. Existing financial validation remains authoritative for all retained rows.

Inspection is bounded to 20,000 XML rows per worksheet and the existing ten-second/shared file/ZIP resource limits. The 10,000-transaction batch cap is unchanged. No formula is executed, no processing-fee formula or FX conversion is introduced, and no permissions, audit mechanism or financial calculation is altered. No production merchant/ledger records are modified by tests. Full application regression/live Gemini were not rerun for this focused importer change; prior results remain historical.

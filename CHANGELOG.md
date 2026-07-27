# Changelog

## v1.1 — 2026-07-27

Tax-correctness release addressing external review. The regime engine is now category-aware,
the interest engine profile- and event-aware, and both are pinned by a release-gate test suite
(`python -m unittest discover tests`).

- **Form selection (AY 2026-27):** ITR-1/ITR-4 now permit up to two house properties per the
  CBDT notification of 30 Mar 2026; caps moved into the registry's `itr_form_eligibility` block
- **Deadlines:** belated (31 Dec 2026) and revised (31 Mar 2027, s.234I fee after 31 Dec)
  returns are now separate registry fields
- **`compare_regimes.py`:**
  - 87A rebate is component-aware (old regime: slab + 111A STCG eligible, 112A barred by
    s.112A(6); new regime: slab tax only per s.115BAC(1A)) and residents-only
  - unused basic exemption now reduces 111A/112A/112 gains for residents (never VDA)
  - component-wise surcharge with the 15% cap on CG/dividend tax and the excluding-income
    test for the 25%/37% tiers; dividends split out via `--dividend-income`
  - s.288B rounding fixed (Python banker's rounding gave ₹1,000 for ₹1,005; now ₹1,010)
  - 80D split into structured self/parents/preventive/senior-medical inputs with statutory caps
- **`compute_interest_234.py`:** s.207(2) senior-citizen exemption, single 15-Mar instalment
  for 44AD/44ADA, 234C deferred-income relief via `--income-event`, and a reducing-balance
  234B ledger via `--payment` (s.234B(2))
- **Registry sources** restructured into primary (Act/CBDT/portal) vs explanatory; official
  primary source now required for every block (test-enforced); 194A senior threshold (₹1L)
  and 194S specified-person/other thresholds added
- **Privacy:** `unlock_documents.py` never prints password values, writes to a protected
  `extracted_text/` workspace (owner-only permissions where supported), adds `--output-dir` /
  `--delete-extracted`; `.gitignore` excludes extractions and data packs
- **Inference softened:** absence of 194S TDS is a weak negative signal, not proof of no
  crypto activity

## v1.0 — 2026-07-27

Initial release, built and field-validated against a complete real-world AY 2026-27 preparation
(salaried + intraday/ETF trading + multi-bank interest + home loan, ITR-3). All examples synthetic.

- Documents-first pipeline: unlock → extract → auto-profile → gap interview → ledger →
  reconcile → compute → data pack
- Rules registry `rules/AY2026-27.json` seeded with source-cited, verified rates
- Scripts: `unlock_documents.py`, `reconcile_ledger.py`, `compare_regimes.py`
  (validated to the rupee against a hand-computed return), `compute_interest_234.py`
  (Rule 119A statutory rounding)
- Eight profile modules covering salary, capital gains, trading/business, property,
  other sources/deductions, foreign/NRI, losses/regime, and the data-pack contract

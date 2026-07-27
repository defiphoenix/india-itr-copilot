# Changelog

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

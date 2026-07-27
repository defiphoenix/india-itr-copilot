# The data pack — output contract and portal verification

## Deliverable: `ITR_datapack_<PAN>_AY<year>.json`

Written to the user's documents folder, validated as parseable JSON, PII kept local. Sections
(include every relevant one; annotate every figure with its source document):

- `_README` — AY, form, regime, preparation basis, reconciliation status
- `rules_used` — copy of the registry rows actually applied (rule, value, source URL, verified_on)
- `taxpayer` — identity, address, residential status + basis, all bank accounts + refund nominee
- `salary` — per-TAN rows with quarterly TDS and receipt numbers; the single standard deduction
- `house_property`, `capital_gains` (scripwise where the form demands), `business` (turnover,
  audit reasoning, expense itemization), `other_sources` (per-account interest, quarter-wise
  dividends), `foreign` when applicable
- `losses` — set-off trail (what absorbed what), vintages carried with expiry AYs and the
  on-time-filing condition
- `regime_comparison` — both columns + recommendation (paste of the script output)
- `tax_and_interest` — slab walk, special rates, rebate, surcharge, cess, TDS/TCS credits,
  234-series with month counts, TOTAL payable, ₹/month cost of delay
- `payment` — self-assessment challan CIN once paid (return must show zero payable)
- `reconciliation` — per-item match status; unresolved items as VERIFY flags
- `pre_submission_checklist` — see below

Prefix anything only the user can settle with `TODO`/`VERIFY`, and repeat all open flags in the
final chat message — the pack is not done while one remains.

## Pre-submission checklist (embed in every pack)

1. Self-assessment tax paid, CIN entered, return shows zero payable
2. Aadhaar-PAN linked; refund account pre-validated; every bank account listed
3. Regime flags consistent (10-IEA only when opting out with business income)
4. One standard deduction; every employer TAN present
5. Loss schedules filled only if filing by the due date
6. Exempt income in Schedule EI; assets schedule if income crosses its threshold
7. File, then **e-verify within 30 days** — an unverified return was never filed
8. Keep the pack + source documents for the full notice window

## Verifying a portal or utility JSON (when the user brings a draft)

Recompute independently from source documents — never from the draft's own intermediate totals —
then diff leaf by leaf: salary per TAN, each OS line, CG rows, loss schedules, total income, tax,
interest, bank accounts, TDS rows. Report each mismatch with: field, draft value, computed value,
evidence, ₹ impact, over- or under-reporting. A draft figure with no source in your ledger is a
first-class finding — ask, don't assume. Structural traps: duplicated standard deduction,
regime-invalid deductions, losses carried despite late filing, missing exempt-income disclosure,
unclaimed TCS, quarter-wise dividend boxes left empty.

## Browser-agent handoff (user files with an AI in the browser)

Hand the pack with: fill each schedule with these exact figures; the pack wins over portal
pre-fill, but surface every disagreement; resolve all TODO/VERIFY flags with the user; user
handles login and OTP; **stop before final submission** for human review.

# india-itr-copilot

A **documents-first** Claude Code skill for preparing Indian Income Tax Returns (ITR-1/2/3/4).

Drop your tax documents in a folder — Form 16, AIS, Form 26AS, broker tax P&L, bank certificates,
loan statements, last year's return — and the skill unlocks and parses them, infers your profile
from the evidence, asks only the questions your paperwork can't answer, reconciles every rupee
across sources, computes both regimes, quantifies advance-tax interest, and hands you a
portal-ready data pack with every figure traced to its source.

## Why documents-first

Most tax interviews ask questions the documents already answer: your 26AS shows every employer and
job change, AIS shows every bank account and dividend, and the absence of crypto TDS is evidence in
itself. This skill parses first and interviews only for the gaps — typically 3–5 questions instead
of a dozen — and every downstream number is source-attributed rather than user-recalled.

## Design

```
unlock → extract → auto-profile → gap interview → ledger.json → reconcile
      → per-head computation → regime engine → interest engine → data pack
```

- **Rules registry** (`rules/AY<year>.json`) — every rate, slab, limit, and due date lives in one
  verified, source-cited file per assessment year. Scripts read it; nothing computes from memory.
  Stale or missing → the skill re-verifies online and rewrites it before touching your numbers.
- **Machine-checkable pipeline** — reconciliation and computation run through scripts, not prose:

| Script | Job |
|---|---|
| `unlock_documents.py` | Sweeps a folder; opens password-protected PDFs/Excels (mines candidates from filenames, PAN+DOB combos); extracts text |
| `reconcile_ledger.py` | Verifies that independent sources (Form 16 ↔ 26AS ↔ AIS ↔ certificates) agree, figure by figure |
| `compare_regimes.py` | Full old-vs-new computation from the rules registry: slab walk, 87A with marginal relief, surcharge with marginal relief, special-rate gains, cess |
| `compute_interest_234.py` | 234A/B/C/234F with statutory rounding (Rule 119A) and part-month conventions |

- **Profile modules** (`modules/*.md`) — salary, capital gains, trading/business, property,
  other sources & deductions, foreign/NRI, losses & regime, data pack — loaded only when the
  documents trigger them.

## Install

```bash
git clone https://github.com/<your-username>/india-itr-copilot.git ~/.claude/skills/india-itr-copilot
pip install pypdf msoffcrypto-tool openpyxl xlrd pycryptodome
```

Then just tell Claude Code: *"help me file my ITR — my documents are in `<folder>`"*.

## Boundaries (by design)

- Output ends at the **data pack**. Filing happens on the portal — by you, or by a browser agent
  you supervise, with an explicit stop before submission. The skill never handles portal passwords
  or OTPs.
- No aggressive positions: deductions follow statutory formulas, income visible to the department
  is never omitted, and audit/notice/representative cases are escalated to a chartered accountant.
- Your data stays on your machine. The data pack contains PAN, DOB, income, and bank details —
  the skill reminds you where it wrote the file and never transmits it.

## Disclaimer

This is a meticulous preparer, not a chartered accountant. You remain legally responsible for the
figures you file. Rates and limits in the registry are re-verified per assessment year against
official sources (incometaxindia.gov.in, incometax.gov.in) — trust the process, but review the pack.

## License

MIT — see `LICENSE`.

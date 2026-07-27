# Documents: collection, evidence mapping, parsing, ledger

## Checklist to offer the user (trim to their situation)

| Situation | Bring |
|---|---|
| Everyone | PAN, last year's filed return (PDF or JSON), list of every bank account + IFSC |
| The reconciliation trio | AIS (JSON or PDF), TIS, Form 26AS — all from the e-filing portal |
| Salaried | Form 16 Part A+B from each employer; Form 12BA if perquisites/ESOPs |
| Investors/traders | Broker tax P&L workbook per broker; CAMS/KFintech CG statement for off-broker MF |
| Crypto | Exchange tax report (per exchange) |
| Deposits | Bank interest certificates (or rely on AIS, cross-checked) |
| Property owner | Home-loan interest certificate; if rented: rent totals, tenant TDS, municipal tax receipts |
| Property sold | Sale + purchase deeds, improvement bills, stamp-duty value, 194-IA certificate |
| Foreign | Overseas brokerage/bank statements, RSU vesting confirmations, Form 67 if claiming FTC |
| Old-regime hopeful | 80C proofs, health-insurance premiums, donation receipts with donee PAN, NPS statement |

Tell the user up front: password-protected files are expected — put the password in the filename or
say it in chat. Run `scripts/unlock_documents.py` on the whole folder before asking for anything else.

## What each artifact proves (auto-profile inference)

| Observation | Inference — no question needed |
|---|---|
| Two+ TANs with s.192 rows in 26AS | Multiple employers → salary must be aggregated, slabs rebuilt |
| A tiny s.192 row (few thousand ₹, single date) | Trailing settlement from an old employer; no Form 16 will exist; still reportable |
| Broker F&O sheet has rows | Non-speculative business income → ITR-3, turnover check |
| Broker intraday P&L non-zero | Speculative business income → ITR-3 even for one trade |
| 194-IB TDS rows | User receives rent → house-property head, claim the credit |
| 194S rows / exchange report | VDA disposals → Schedule VDA at flat rate, no loss relief |
| 206C(1G) LRS rows | Foreign *spending* (forex card, remittance) — usually not an asset; confirm nothing opened abroad |
| SFT "purchase of time deposits" with big gross | Almost always FD rollovers, not new money — explain, don't alarm |
| No 194S anywhere + no exchange docs | Strong evidence of no crypto sales — confirm with one question, not an interrogation |
| Home-loan certificate | Property exists → occupancy + co-ownership questions |
| AIS Part A | DOB (drives senior slabs/limits) — never ask for age |
| Prior return's loss schedule | Brought-forward loss vintages — never ask the user to remember |

**The gap interview** covers only: property occupancy and ownership shares, residency day-counts
(when a foreign signal exists), intent behind anomalies, deduction proofs not in the folder, and
which account takes the refund.

## Parsing notes

- **AIS PDF** (what users actually download): Part A = identity + DOB. Part B walks TDS/TCS,
  then SFT (interest per account — figures are *paid + accrued*, so certificates must be summed the
  same way), then per-employer salary annexure with employment dates, then taxes paid, then
  demand/refund. An empty "taxes paid" section = no advance tax = interest exposure.
- **AIS JSON** is AES-encrypted by the portal; password derives from PAN + DOB. Prefer it when
  available — element arrays parse cleanly.
- **26AS text export** is caret (`^`) delimited, sections PART-I…X. Part-I = TDS per deductor with
  transaction rows (booking status F = final). Part-VI = TCS. Part-VII = refunds paid — but the
  interest column is often blank even when interest was embedded; see the refund-interest probe in
  the interest/dividends module.
- **Broker tax P&L workbooks** (Zerodha-pattern): segment sheets each carry a realized-P&L block, a
  turnover block, and a charges block; a tradewise sheet gives per-trade charges for precise expense
  allocation; an "other debits/credits" sheet holds account-level charges. Use the broker's stated
  turnover (absolute-sum convention) for the audit test — never contract value.
- **Form 16**: Part A quarterly TDS must equal the 26AS total for that TAN. Part B carries the
  regime flag the employer used (it does NOT bind the return), section-10 exemptions, and the
  single standard deduction. 12BA holds perquisite detail (RSU/ESOP values live here).
- **Prior-year return**: pull loss carry-forward vintages, the refund CLAIMED (feeds the
  refund-interest probe), and whether it was filed by the due date (late original = most losses die).

## ledger.json

One entry per figure per source; checks encode which sources must agree:

```json
{
  "entries": [
    {"id": "sal_f16_emp1",  "source": "Form16", "doc": "Form16.pdf", "field": "gross 17(1)", "amount": 1200000, "schedule": "S"},
    {"id": "sal_26as_emp1", "source": "26AS",   "doc": "26AS.txt",   "field": "TAN ABCD12345E paid", "amount": 1200000, "schedule": "S"},
    {"id": "sal_ais_emp1",  "source": "AIS",    "doc": "AIS.pdf",    "field": "s.192 total", "amount": 1200000, "schedule": "S"}
  ],
  "checks": [
    {"name": "employer-1 salary across sources", "ids": ["sal_f16_emp1", "sal_26as_emp1", "sal_ais_emp1"], "tolerance": 1}
  ]
}
```

Run `python scripts/reconcile_ledger.py ledger.json`; every MISMATCH becomes either a resolved
correction or an explicit VERIFY flag in the data pack. Single-source figures (the NOTE list) are
fine — but each must still name its document.

## Reconciliation probes (run every time)

1. **TDS/TCS implies income**: any credit row without a matching income entry → find the income.
2. **Refund-interest probe**: prior-year refund claimed vs amount credited (AIS); the excess is
   taxable interest even when no statement itemizes it.
3. **Form 16 TDS missing from 26AS** = employer deducted but didn't deposit → warn: credit at risk,
   chase the employer.
4. **TCS sweep**: LRS remittances, foreign travel packages, big car purchases — claimable credits
   users forget.
5. **Large SFT rows**: explain each (rollover, transfer between own accounts) — unexplained ones
   invite notices.

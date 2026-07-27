#!/usr/bin/env python3
"""
Ledger tie-out checker. The preparer builds ledger.json listing every extracted
figure with its source; this script verifies that independent sources agree.

ledger.json schema:
{
  "entries": [
    {"id": "sal_f16_emp1", "source": "Form16", "doc": "Form16_x.pdf",
     "field": "gross_17_1 TAN ABCD12345E", "amount": 1200000, "schedule": "S"},
    ...
  ],
  "checks": [
    {"name": "employer-1 salary: Form16 vs 26AS vs AIS",
     "ids": ["sal_f16_emp1", "sal_26as_emp1", "sal_ais_emp1"],
     "tolerance": 1},
    {"name": "TDS: Form16 total vs 26AS deposited",
     "left": ["tds_f16_emp1"], "right": ["tds_26as_emp1"], "tolerance": 0}
  ]
}

Two check styles:
  - "ids":  every listed entry must equal the first (within tolerance)
  - "left"/"right": sum(left) must equal sum(right) (within tolerance)

Exit code 0 = all tie out; 1 = at least one mismatch (fix or record a VERIFY flag).

Usage: python reconcile_ledger.py ledger.json
"""

import json
import sys


def run(path):
    with open(path, encoding="utf-8") as f:
        ledger = json.load(f)
    amounts = {e["id"]: e["amount"] for e in ledger["entries"]}
    failures = 0

    for chk in ledger.get("checks", []):
        tol = chk.get("tolerance", 1)
        name = chk.get("name", "unnamed check")
        try:
            if "ids" in chk:
                vals = [(i, amounts[i]) for i in chk["ids"]]
                base = vals[0][1]
                bad = [(i, v) for i, v in vals[1:] if abs(v - base) > tol]
                if bad:
                    failures += 1
                    detail = ", ".join(f"{i}={v:,}" for i, v in vals)
                    print(f"MISMATCH  {name}: {detail}")
                else:
                    print(f"OK        {name}: {base:,}")
            else:
                ls = sum(amounts[i] for i in chk["left"])
                rs = sum(amounts[i] for i in chk["right"])
                if abs(ls - rs) > tol:
                    failures += 1
                    print(f"MISMATCH  {name}: left {ls:,} vs right {rs:,} (diff {ls - rs:,})")
                else:
                    print(f"OK        {name}: {ls:,}")
        except KeyError as e:
            failures += 1
            print(f"ERROR     {name}: entry id {e} not found in ledger")

    unreferenced = set(amounts) - {
        i for c in ledger.get("checks", [])
        for i in c.get("ids", []) + c.get("left", []) + c.get("right", [])
    }
    if unreferenced:
        print(f"NOTE      entries in no check (single-source figures): {', '.join(sorted(unreferenced))}")

    print(f"\n{len(ledger.get('checks', []))} checks, {failures} mismatch(es).")
    return 1 if failures else 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(run(sys.argv[1]))

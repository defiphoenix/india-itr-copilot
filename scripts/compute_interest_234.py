#!/usr/bin/env python3
"""
Deterministic 234A / 234B / 234C / 234F calculator for an Individual filer.

Interest arithmetic is where hand computation goes wrong most often (rounding
base down to Rs 100, part-months counting as full months, the 12%/36%
tolerance on the first two installments, TDS netting). This script encodes
the MECHANICS; the RATES/THRESHOLDS are parameters with current defaults —
per the skill's rules, verify them for the AY being filed before relying on
the output, and record them in the data pack's rules_verification block.

Usage:
    python compute_interest_234.py --tax 150000 --tds 120000 \
        --fy 2025-26 --pay-date 2026-07-30 [--due-date 2026-08-31] \
        [--file-date 2026-08-15] \
        [--advance 2025-09-10:5000 2025-12-12:4000]   # advance-tax challans, if any

Outputs a line-by-line breakdown and the total to pay.
"""

import argparse
from datetime import date


def months_between(start, end):
    """Months from `start` to `end` inclusive of part months (part = full)."""
    if end < start:
        return 0
    return (end.year - start.year) * 12 + (end.month - start.month) + 1


def round_down_100(x):
    return int(x // 100) * 100


def compute(tax, tds, fy_start_year, pay_date, due_date, file_date,
            advance, rate=0.01, threshold=10000, safe_harbour=0.90,
            fee_high=5000, fee_low=1000, fee_income_cutoff=500000, total_income=None):
    assessed = max(0, tax - tds)          # assessed tax net of TDS/TCS
    base = round_down_100(assessed)
    ay_start = date(fy_start_year + 1, 4, 1)
    lines = []

    adv_paid_total = sum(a for _, a in advance)

    # ---- 234C: installment deferment (only if advance tax was payable) ----
    c_total = 0
    if assessed >= threshold:
        sched = [
            (date(fy_start_year, 6, 15), 0.15, 3, 0.12),   # (due, cum%, months, tolerance)
            (date(fy_start_year, 9, 15), 0.45, 3, 0.36),
            (date(fy_start_year, 12, 15), 0.75, 3, None),
            (date(fy_start_year + 1, 3, 15), 1.00, 1, None),
        ]
        for due, pct, months, tol in sched:
            paid_by = sum(a for d, a in advance if d <= due)
            required = base * pct
            tolerated = base * tol if tol is not None else required
            if paid_by >= tolerated:
                continue
            shortfall = round_down_100(required - paid_by)
            interest = int(shortfall * rate * months)
            c_total += interest
            lines.append(f"234C {due}: due {int(required):>8} paid {paid_by:>8} -> {interest}")
    else:
        lines.append(f"234C: not applicable (assessed {assessed} < threshold {threshold})")

    # ---- 234B: overall shortfall from 1 Apr of AY ----
    b_total = 0
    if assessed >= threshold and adv_paid_total < safe_harbour * assessed:
        b_base = round_down_100(assessed - adv_paid_total)
        m = months_between(ay_start, pay_date)
        b_total = int(b_base * rate * m)
        lines.append(f"234B: {b_base} x {rate:.0%} x {m} months (Apr-{pay_date.strftime('%b')}) = {b_total}")
    else:
        lines.append("234B: not applicable")

    # ---- 234A + 234F: late filing ----
    a_total = f_total = 0
    if file_date and due_date and file_date > due_date:
        m = months_between(due_date, file_date) - 1 or 1
        a_base = round_down_100(assessed - adv_paid_total)
        a_total = int(a_base * rate * m)
        f_total = fee_high if (total_income or 0) > fee_income_cutoff else fee_low
        lines.append(f"234A: {a_base} x {rate:.0%} x {m} months late = {a_total}")
        lines.append(f"234F: fee {f_total}")
    else:
        lines.append("234A/234F: filed on time — nil")

    shortfall_now = assessed - adv_paid_total
    total = shortfall_now + a_total + b_total + c_total + f_total
    return lines, shortfall_now, a_total, b_total, c_total, f_total, total


def parse_date(s):
    y, m, d = map(int, s.split("-"))
    return date(y, m, d)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tax", type=int, required=True, help="Total tax liability incl. surcharge+cess")
    ap.add_argument("--tds", type=int, default=0, help="TDS + TCS credit")
    ap.add_argument("--fy", required=True, help="Financial year like 2025-26")
    ap.add_argument("--pay-date", required=True, help="Planned self-assessment payment date YYYY-MM-DD")
    ap.add_argument("--due-date", default=None, help="139(1) due date YYYY-MM-DD (for 234A check)")
    ap.add_argument("--file-date", default=None, help="Planned filing date YYYY-MM-DD")
    ap.add_argument("--advance", nargs="*", default=[], help="Advance-tax challans as YYYY-MM-DD:amount")
    ap.add_argument("--total-income", type=int, default=None, help="For the 234F fee tier")
    ap.add_argument("--rate", type=float, default=0.01, help="Interest rate per month (VERIFY for the AY)")
    ap.add_argument("--threshold", type=int, default=10000, help="Advance-tax threshold (VERIFY)")
    args = ap.parse_args()

    fy_start = int(args.fy.split("-")[0])
    advance = []
    for tok in args.advance:
        d, a = tok.split(":")
        advance.append((parse_date(d), int(a)))

    lines, shortfall, a, b, c, f, total = compute(
        args.tax, args.tds, fy_start, parse_date(args.pay_date),
        parse_date(args.due_date) if args.due_date else None,
        parse_date(args.file_date) if args.file_date else None,
        advance, rate=args.rate, threshold=args.threshold,
        total_income=args.total_income,
    )
    print(f"Assessed tax (tax - TDS):        {args.tax - args.tds}")
    for ln in lines:
        print(ln)
    print("-" * 46)
    print(f"Tax shortfall {shortfall} + 234A {a} + 234B {b} + 234C {c} + 234F {f}")
    print(f"TOTAL TO PAY: {total}")
    print("NOTE: rates/thresholds are defaults — verify for the AY and record in rules_verification.")

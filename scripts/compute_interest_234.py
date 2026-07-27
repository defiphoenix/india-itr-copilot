#!/usr/bin/env python3
"""
Deterministic 234A / 234B / 234C / 234F calculator for an Individual filer.

Interest arithmetic is where hand computation goes wrong most often (rounding
base down to Rs 100, part-months counting as full months, the 12%/36%
tolerance on the first two installments, TDS netting, the senior-citizen and
presumptive carve-outs, deferred-income relief). This script encodes the
MECHANICS; the RATES/THRESHOLDS are parameters with current defaults — per
the skill's rules, verify them for the AY being filed before relying on the
output, and record them in the data pack's rules_verification block.

Usage:
    python compute_interest_234.py --tax 150000 --tds 120000 \
        --fy 2025-26 --pay-date 2026-07-30 [--due-date 2026-08-31] \
        [--file-date 2026-08-15] \
        [--age 45] [--non-resident] [--has-business-income] \
        [--presumptive 44ADA] \
        [--advance 2025-09-10:5000 2025-12-12:4000] \
        [--payment 2026-05-02:20000] \
        [--income-event 2025-11-20:30000]

Key flags:
    --age / --non-resident / --has-business-income
        A RESIDENT aged 60+ with NO business/professional income is not liable
        to advance tax (s.207(2)) — 234B and 234C are nil for them.
    --presumptive 44AD|44ADA
        Presumptive filers owe 100% of advance tax by 15 March in ONE
        instalment; the four-instalment 234C schedule does not apply.
    --income-event DATE:TAX
        Tax attributable to income that AROSE on DATE (capital gain, dividend,
        lottery, first-time business income). Proviso to s.234C: no interest
        on the shortfall attributable to such income for instalments that fell
        due BEFORE it arose, provided the tax is paid with the remaining
        instalments / by 31 March.
    --advance DATE:AMT   advance-tax challans (on or before 31 March of the FY)
    --payment DATE:AMT   self-assessment payments AFTER 31 March, before the
        final --pay-date; 234B runs on the reducing balance (s.234B(2)).

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
            advance, payments=(), income_events=(),
            age=45, resident=True, has_business_income=False, presumptive=None,
            rate=0.01, threshold=10000, safe_harbour=0.90,
            fee_high=5000, fee_low=1000, fee_income_cutoff=500000, total_income=None):
    assessed = max(0, tax - tds)          # assessed tax net of TDS/TCS
    base = round_down_100(assessed)
    ay_start = date(fy_start_year + 1, 4, 1)
    lines = []

    adv_paid_total = sum(a for _, a in advance)
    liable_advance = assessed >= threshold
    if resident and age >= 60 and not has_business_income and not presumptive:
        liable_advance = False
        lines.append("s.207(2): resident senior citizen with no business income — "
                     "not liable to advance tax; 234B/234C nil")

    # ---- 234C: installment deferment (only if advance tax was payable) ----
    c_total = 0
    if liable_advance:
        if presumptive:
            sched = [(date(fy_start_year + 1, 3, 15), 1.00, 1, None)]
            lines.append(f"234C: presumptive ({presumptive}) — single 100% instalment due 15 Mar")
        else:
            sched = [
                (date(fy_start_year, 6, 15), 0.15, 3, 0.12),   # (due, cum%, months, tolerance)
                (date(fy_start_year, 9, 15), 0.45, 3, 0.36),
                (date(fy_start_year, 12, 15), 0.75, 3, None),
                (date(fy_start_year + 1, 3, 15), 1.00, 1, None),
            ]
        for due, pct, months, tol in sched:
            # deferred-income relief: exclude tax on income arising after this due date
            deferred = sum(t for d, t in income_events if d > due)
            inst_base = round_down_100(max(0, assessed - deferred))
            paid_by = sum(a for d, a in advance if d <= due)
            required = inst_base * pct
            tolerated = inst_base * tol if tol is not None else required
            if paid_by >= tolerated:
                continue
            shortfall = round_down_100(required - paid_by)
            if shortfall <= 0:
                continue
            interest = int(shortfall * rate * months)
            c_total += interest
            note = f" (base excl. {int(deferred)} deferred-income tax)" if deferred else ""
            lines.append(f"234C {due}: due {int(required):>8} paid {paid_by:>8} -> {interest}{note}")
        if income_events:
            lines.append("234C proviso relief assumed — VERIFY the related tax was paid in the "
                         "remaining instalments or by 31 Mar, else relief does not apply")
    else:
        reason = "not liable to advance tax" if assessed >= threshold \
            else f"assessed {assessed} < threshold {threshold}"
        lines.append(f"234C: not applicable ({reason})")

    # ---- 234B: overall shortfall from 1 Apr of AY, reducing balance (234B(2)) ----
    b_total = 0
    if liable_advance and adv_paid_total < safe_harbour * assessed:
        outstanding = assessed - adv_paid_total
        ledger = sorted([(d, a) for d, a in payments if d >= ay_start]) + [(pay_date, None)]
        start = ay_start
        for d, amt in ledger:
            if outstanding <= 0:
                break
            m = months_between(start, d)
            seg = int(round_down_100(outstanding) * rate * m)
            b_total += seg
            lines.append(f"234B: {round_down_100(outstanding)} x {rate:.0%} x {m} months "
                         f"({start.strftime('%b %Y')}-{d.strftime('%b %Y')}) = {seg}")
            if amt is not None:
                outstanding -= amt
                # next segment starts the month after this payment's month
                start = date(d.year + (d.month == 12), d.month % 12 + 1, 1)
    else:
        lines.append("234B: not applicable")

    # ---- 234A + 234F: late filing ----
    a_total = f_total = 0
    paid_before_filing = adv_paid_total + sum(a for _, a in payments)
    if file_date and due_date and file_date > due_date:
        m = months_between(due_date, file_date) - 1 or 1
        a_base = round_down_100(max(0, assessed - paid_before_filing))
        a_total = int(a_base * rate * m)
        f_total = fee_high if (total_income or 0) > fee_income_cutoff else fee_low
        lines.append(f"234A: {a_base} x {rate:.0%} x {m} months late = {a_total}")
        lines.append(f"234F: fee {f_total}")
    else:
        lines.append("234A/234F: filed on time — nil")

    shortfall_now = assessed - paid_before_filing
    total = shortfall_now + a_total + b_total + c_total + f_total
    return lines, shortfall_now, a_total, b_total, c_total, f_total, total


def parse_date(s):
    y, m, d = map(int, s.split("-"))
    return date(y, m, d)


def parse_events(tokens):
    out = []
    for tok in tokens:
        d, a = tok.rsplit(":", 1)
        out.append((parse_date(d), int(a)))
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tax", type=int, required=True, help="Total tax liability incl. surcharge+cess")
    ap.add_argument("--tds", type=int, default=0, help="TDS + TCS credit")
    ap.add_argument("--fy", required=True, help="Financial year like 2025-26")
    ap.add_argument("--pay-date", required=True, help="Final self-assessment payment date YYYY-MM-DD")
    ap.add_argument("--due-date", default=None, help="139(1) due date YYYY-MM-DD (for 234A check)")
    ap.add_argument("--file-date", default=None, help="Planned filing date YYYY-MM-DD")
    ap.add_argument("--advance", nargs="*", default=[], help="Advance-tax challans as YYYY-MM-DD:amount")
    ap.add_argument("--payment", nargs="*", default=[], help="Self-assessment payments after 31 Mar as YYYY-MM-DD:amount")
    ap.add_argument("--income-event", nargs="*", default=[],
                    help="Deferred-income tax events as YYYY-MM-DD:tax_on_that_income (CG/dividend/lottery)")
    ap.add_argument("--age", type=int, default=45)
    ap.add_argument("--non-resident", dest="resident", action="store_false")
    ap.add_argument("--has-business-income", action="store_true")
    ap.add_argument("--presumptive", choices=["44AD", "44ADA"], default=None,
                    help="Presumptive filer: single 15-Mar advance-tax instalment")
    ap.add_argument("--total-income", type=int, default=None, help="For the 234F fee tier")
    ap.add_argument("--rate", type=float, default=0.01, help="Interest rate per month (VERIFY for the AY)")
    ap.add_argument("--threshold", type=int, default=10000, help="Advance-tax threshold (VERIFY)")
    args = ap.parse_args()

    fy_start = int(args.fy.split("-")[0])
    lines, shortfall, a, b, c, f, total = compute(
        args.tax, args.tds, fy_start, parse_date(args.pay_date),
        parse_date(args.due_date) if args.due_date else None,
        parse_date(args.file_date) if args.file_date else None,
        parse_events(args.advance), parse_events(args.payment),
        parse_events(args.income_event),
        age=args.age, resident=args.resident,
        has_business_income=args.has_business_income or bool(args.presumptive),
        presumptive=args.presumptive,
        rate=args.rate, threshold=args.threshold,
        total_income=args.total_income,
    )
    print(f"Assessed tax (tax - TDS):        {args.tax - args.tds}")
    for ln in lines:
        print(ln)
    print("-" * 46)
    print(f"Tax shortfall {shortfall} + 234A {a} + 234B {b} + 234C {c} + 234F {f}")
    print(f"TOTAL TO PAY: {total}")
    print("NOTE: rates/thresholds are defaults — verify for the AY and record in rules_verification.")

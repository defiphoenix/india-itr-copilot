#!/usr/bin/env python3
"""
Old-vs-new regime comparison engine. All rates come from the rules registry —
this file contains MECHANICS only (slab walk, 87A with marginal relief,
surcharge with marginal relief, cess, special-rate incomes outside the slabs).

Usage:
    python compare_regimes.py --rules rules/AY2026-27.json \
        --salary-gross 1500000 --other-income 60000 \
        [--hp-interest-paid 180000] [--stcg-111a 0] [--ltcg-112a 0] [--vda 0] \
        [--business-income 0] [--old-80c 150000] [--old-80d 25000] [--old-80tta 8000] \
        [--old-other-via 0] [--age 27]

Conventions:
    --hp-interest-paid  : self-occupied home-loan interest actually paid (engine caps it
                          and applies it in the OLD regime only; let-out property should be
                          netted into --other-income by the preparer instead)
    --old-*             : deductions that exist only under the old regime
    Special-rate gains  : enter NET taxable figures (after intra-CG set-off / 112A exemption)
"""

import argparse
import json


def slab_tax(taxable, slabs):
    tax, prev = 0.0, 0
    for ceiling, rate in slabs:
        top = taxable if ceiling is None else min(taxable, ceiling)
        if top > prev:
            tax += (top - prev) * rate
        if ceiling is None or taxable <= ceiling:
            break
        prev = ceiling
    return tax


def rebate_87a(cfg, total_income, normal_tax):
    if total_income > cfg["income_threshold"]:
        if cfg.get("marginal_relief"):
            # tax cannot exceed the income above the threshold
            excess = total_income - cfg["income_threshold"]
            if normal_tax > excess:
                return normal_tax - excess
        return 0.0
    return min(cfg["max_rebate"], normal_tax)


def surcharge_amt(cfg, total_income, tax, regime_cap=None):
    rate, prev = 0.0, 0
    for ceiling, r in cfg["tiers"]:
        if ceiling is None or total_income <= ceiling:
            rate = r
            break
        prev = ceiling
    if regime_cap is not None:
        rate = min(rate, regime_cap)
    s = tax * rate
    if cfg.get("marginal_relief") and rate > 0 and prev:
        # surcharge cannot exceed income above the tier threshold
        s = min(s, total_income - prev)
    return s


def compute_regime(rules, regime, args):
    r = rules[regime]
    std = min(r["standard_deduction_salary"], args.salary_gross) if args.salary_gross else 0
    salary = max(0, args.salary_gross - std)

    hp = 0
    if regime == "old_regime" and args.hp_interest_paid:
        cap = rules["deduction_caps_old_regime"]["24b_self_occupied"]
        hp = -min(args.hp_interest_paid, cap)

    normal_income = salary + hp + args.other_income + args.business_income
    via = 0
    if regime == "old_regime":
        caps = rules["deduction_caps_old_regime"]
        via = (min(args.old_80c, caps["80c"]) + args.old_80d
               + min(args.old_80tta, caps["80tta_savings_interest"]) + args.old_other_via)
        via = min(via, max(0, normal_income))
    normal_income = max(0, normal_income - via)

    special = args.stcg_111a + args.ltcg_112a + args.vda
    total_income = normal_income + special

    if regime == "old_regime":
        key = ("slabs_below_60" if args.age < 60
               else "slabs_60_to_80" if args.age < 80 else "slabs_above_80")
        slabs = r[key]
    else:
        slabs = r["slabs"]

    normal_tax = slab_tax(normal_income, slabs)
    cg = rules["capital_gains"]
    special_tax = (args.stcg_111a * cg["equity_stcg_111a"]
                   + args.ltcg_112a * cg["equity_ltcg_112a"]["rate"]
                   + args.vda * cg["vda_115bbh"]["rate"])

    reb = rebate_87a(r["rebate_87a"], total_income, normal_tax)
    if r["rebate_87a"].get("applies_to_special_rate_income", True) is False:
        pass  # rebate computed on normal_tax only, which is already the case above

    tax_after_rebate = max(0.0, normal_tax - reb) + special_tax
    cap = rules["surcharge"].get("new_regime_cap") if regime == "new_regime" else None
    sur = surcharge_amt(rules["surcharge"], total_income, tax_after_rebate, cap)
    cess = (tax_after_rebate + sur) * rules["cess"]
    total = round((tax_after_rebate + sur + cess) / 10) * 10  # s.288B rounding

    return {
        "total_income": int(total_income), "normal_tax": int(normal_tax),
        "special_rate_tax": int(special_tax), "rebate_87a": int(reb),
        "surcharge": int(sur), "cess": int(cess), "TOTAL_TAX": int(total),
    }


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--rules", required=True)
    ap.add_argument("--salary-gross", type=int, default=0)
    ap.add_argument("--other-income", type=int, default=0, help="interest + dividends + misc at slab")
    ap.add_argument("--business-income", type=int, default=0, help="net non-speculative + speculative profit")
    ap.add_argument("--hp-interest-paid", type=int, default=0)
    ap.add_argument("--stcg-111a", type=int, default=0)
    ap.add_argument("--ltcg-112a", type=int, default=0, help="NET of the exempt slice")
    ap.add_argument("--vda", type=int, default=0)
    ap.add_argument("--old-80c", type=int, default=0)
    ap.add_argument("--old-80d", type=int, default=0)
    ap.add_argument("--old-80tta", type=int, default=0)
    ap.add_argument("--old-other-via", type=int, default=0)
    ap.add_argument("--age", type=int, default=30)
    args = ap.parse_args()

    with open(args.rules, encoding="utf-8") as f:
        rules = json.load(f)

    print(f"Rules: AY {rules['assessment_year']}, verified {rules['verified_on']} — "
          f"re-verify if stale.")
    results = {}
    for regime in ("new_regime", "old_regime"):
        results[regime] = compute_regime(rules, regime, args)
    w = max(len(k) for k in results["new_regime"])
    print(f"{'':{w}}  {'NEW':>12}  {'OLD':>12}")
    for k in results["new_regime"]:
        print(f"{k:{w}}  {results['new_regime'][k]:>12,}  {results['old_regime'][k]:>12,}")
    n, o = results["new_regime"]["TOTAL_TAX"], results["old_regime"]["TOTAL_TAX"]
    winner = "NEW" if n <= o else "OLD"
    print(f"\nRecommendation: {winner} regime (saves Rs {abs(n - o):,}).")
    print("Reminder: business-income filers need Form 10-IEA by the due date to choose OLD.")

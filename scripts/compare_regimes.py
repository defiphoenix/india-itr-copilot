#!/usr/bin/env python3
"""
Old-vs-new regime comparison engine. All rates come from the rules registry —
this file contains MECHANICS only (slab walk, category-aware 87A, unused
basic-exemption adjustment against special-rate gains, component-wise
surcharge with the CG/dividend cap, cess, s.288B rounding).

Usage:
    python compare_regimes.py --rules rules/AY2026-27.json \
        --salary-gross 1500000 --other-income 60000 --dividend-income 0 \
        [--hp-interest-paid 180000] [--stcg-111a 0] [--ltcg-112a 0] [--ltcg-112 0] [--vda 0] \
        [--business-income 0] [--age 27] [--non-resident] \
        [--old-80c 150000] [--old-80tta 8000] [--old-other-via 0] \
        [--old-80d-self-premium 0] [--old-80d-self-medical 0] \
        [--old-80d-parents-premium 0] [--old-80d-parents-medical 0] \
        [--old-80d-preventive 0] [--parents-senior]

Conventions:
    --hp-interest-paid  : self-occupied home-loan interest actually paid (engine caps it
                          and applies it in the OLD regime only; let-out property should be
                          netted into --other-income by the preparer instead)
    --dividend-income   : slab-taxed, but kept separate because surcharge on its tax is
                          capped (do NOT also include it in --other-income)
    --old-80d-*-medical : senior-citizen medical expenditure, valid only where the insured
                          senior has NO health policy — engine caps, but preparer must verify
    Special-rate gains  : enter NET taxable figures (after intra-CG set-off; 112A net of
                          the exempt first slice). The engine then applies any unused
                          basic exemption for residents.
"""

import argparse
import json
import math


def round_288b(amount):
    """s.288B: round to nearest Rs 10, ties (5 and above) go UP. Paise ignored first."""
    whole = math.floor(amount)
    return ((whole + 5) // 10) * 10


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


def basic_exemption_limit(slabs):
    """The ceiling of the zero-rate band."""
    ceiling, rate = slabs[0]
    return ceiling if rate == 0.0 else 0


def deduction_80d(caps80d, args):
    """Statutory 80D: separate self/family and parents buckets, senior caps,
    preventive check-up within the caps, senior medical expenditure only in
    lieu of insurance (preparer verifies the no-policy condition)."""
    self_senior = args.age >= 60
    self_cap = caps80d["self_family_senior"] if self_senior else caps80d["self_family_below60"]
    parents_cap = caps80d["parents_senior"] if args.parents_senior else caps80d["parents_below60"]

    preventive = min(args.old_80d_preventive, caps80d["preventive_checkup_within_caps"])
    self_medical = args.old_80d_self_medical if self_senior else 0
    parents_medical = args.old_80d_parents_medical if args.parents_senior else 0

    self_bucket = min(args.old_80d_self_premium + self_medical + preventive, self_cap)
    parents_bucket = min(args.old_80d_parents_premium + parents_medical, parents_cap)
    return self_bucket + parents_bucket


def rebate_87a(cfg, total_income, eligible_tax):
    """Rebate against the ELIGIBLE tax components only (caller assembles them
    per the registry's eligible_tax_components)."""
    if total_income > cfg["income_threshold"]:
        if cfg.get("marginal_relief"):
            # tax cannot exceed the income above the threshold
            excess = total_income - cfg["income_threshold"]
            if eligible_tax > excess:
                return eligible_tax - excess
        return 0.0
    return min(cfg["max_rebate"], eligible_tax)


def tier_rate(tiers, income):
    for ceiling, r in tiers:
        if ceiling is None or income <= ceiling:
            return r
    return 0.0


def tier_floor(tiers, income):
    """Lower bound of the tier `income` falls in (for marginal relief)."""
    prev = 0
    for ceiling, _ in tiers:
        if ceiling is None or income <= ceiling:
            return prev
        prev = ceiling
    return prev


def surcharge_components(cfg, total_income, income_ex_cg_div, normal_tax_after_rebate,
                         capped_component_tax, uncapped_special_tax, regime_cap=None):
    """Component-wise surcharge:
      - tax on 111A/112/112A gains and dividends: rate capped at cg_and_dividend_cap
      - the 25%/37% tiers apply to the remaining tax only when income EXCLUDING
        those gains/dividends crosses the tier threshold; else 15% overall cap
      - regime cap (new regime 25%) on top
    Returns (surcharge, effective_normal_rate, effective_cg_rate)."""
    cg_cap = cfg["cg_and_dividend_cap"]
    r_all = tier_rate(cfg["tiers"], total_income)
    r_ex = tier_rate(cfg["tiers"], income_ex_cg_div)

    if r_ex > cg_cap:               # excluding-CG income itself crosses 2Cr/5Cr
        normal_rate = r_ex
    else:
        normal_rate = min(r_all, cg_cap)
    if regime_cap is not None:
        normal_rate = min(normal_rate, regime_cap)
    cg_rate = min(normal_rate, cg_cap)

    s = (normal_tax_after_rebate + uncapped_special_tax) * normal_rate \
        + capped_component_tax * cg_rate

    if cfg.get("marginal_relief") and s > 0:
        # surcharge cannot exceed income above the tier threshold crossed
        floor = tier_floor(cfg["tiers"], total_income)
        if floor:
            s = min(s, max(0, total_income - floor))
    return s, normal_rate, cg_rate


def compute_regime(rules, regime, args):
    r = rules[regime]
    std = min(r["standard_deduction_salary"], args.salary_gross) if args.salary_gross else 0
    salary = max(0, args.salary_gross - std)

    hp = 0
    if regime == "old_regime" and args.hp_interest_paid:
        cap = rules["deduction_caps_old_regime"]["24b_self_occupied"]
        hp = -min(args.hp_interest_paid, cap)

    normal_income = salary + hp + args.other_income + args.dividend_income + args.business_income
    via = 0
    if regime == "old_regime":
        caps = rules["deduction_caps_old_regime"]
        via = (min(args.old_80c, caps["80c"])
               + deduction_80d(caps["80d"], args)
               + min(args.old_80tta, caps["80tta_savings_interest"])
               + args.old_other_via)
        via = min(via, max(0, normal_income))
    normal_income = max(0, normal_income - via)

    if regime == "old_regime":
        key = ("slabs_below_60" if args.age < 60
               else "slabs_60_to_80" if args.age < 80 else "slabs_above_80")
        slabs = r[key]
    else:
        slabs = r["slabs"]

    # --- unused basic exemption first reduces 111A STCG, then 112A/112 LTCG ---
    # (provisos to ss.111A/112/112A: resident individual/HUF only; never VDA)
    stcg, ltcg_112a, ltcg_112 = args.stcg_111a, args.ltcg_112a, args.ltcg_112
    if args.resident:
        unused = max(0, basic_exemption_limit(slabs) - normal_income)
        take = min(unused, stcg); stcg -= take; unused -= take
        take = min(unused, ltcg_112a); ltcg_112a -= take; unused -= take
        take = min(unused, ltcg_112); ltcg_112 -= take; unused -= take

    special_gross = args.stcg_111a + args.ltcg_112a + args.ltcg_112 + args.vda
    total_income = normal_income + special_gross  # exemption adjustment shifts tax, not total income

    normal_tax = slab_tax(normal_income, slabs)
    cg = rules["capital_gains"]
    tax_111a = stcg * cg["equity_stcg_111a"]
    tax_112a = ltcg_112a * cg["equity_ltcg_112a"]["rate"]
    tax_112 = ltcg_112 * cg["other_assets_ltcg_112"]["rate"]
    tax_vda = args.vda * cg["vda_115bbh"]["rate"]

    # --- 87A against eligible components only (registry-driven); residents only ---
    component_tax = {"normal": normal_tax, "stcg_111a": tax_111a,
                     "ltcg_112a": tax_112a, "ltcg_112": tax_112, "vda": tax_vda}
    eligible = sum(component_tax[c] for c in r["rebate_87a"]["eligible_tax_components"])
    reb = rebate_87a(r["rebate_87a"], total_income, eligible) if args.resident else 0.0

    tax_after_rebate = max(0.0, normal_tax + tax_111a + tax_112a + tax_112 + tax_vda - reb)

    # --- component-wise surcharge with the CG/dividend cap ---
    # rebate consumes eligible-component tax first; attribute the remainder
    post_rebate_eligible = max(0.0, eligible - reb)
    scale = post_rebate_eligible / eligible if eligible > 0 else 1.0
    adj = {c: (t * scale if c in r["rebate_87a"]["eligible_tax_components"] else t)
           for c, t in component_tax.items()}
    # dividend is slab-taxed; its tax share of normal tax is apportioned pro rata
    div_tax = (adj["normal"] * args.dividend_income / normal_income) if normal_income > 0 else 0.0
    capped_tax = adj["stcg_111a"] + adj["ltcg_112a"] + adj["ltcg_112"] + div_tax
    uncapped_special = adj["vda"]
    plain_normal_tax = adj["normal"] - div_tax
    income_ex_cg_div = total_income - args.stcg_111a - args.ltcg_112a - args.ltcg_112 - args.dividend_income

    cap = rules["surcharge"].get("new_regime_cap") if regime == "new_regime" else None
    sur, _, _ = surcharge_components(rules["surcharge"], total_income, income_ex_cg_div,
                                     plain_normal_tax, capped_tax, uncapped_special, cap)
    cess = (tax_after_rebate + sur) * rules["cess"]
    total = round_288b(tax_after_rebate + sur + cess)

    return {
        "total_income": int(total_income), "normal_tax": int(normal_tax),
        "special_rate_tax": int(tax_111a + tax_112a + tax_112 + tax_vda),
        "rebate_87a": int(reb), "surcharge": int(sur), "cess": int(cess),
        "TOTAL_TAX": int(total),
    }


def build_parser():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--rules", required=True)
    ap.add_argument("--salary-gross", type=int, default=0)
    ap.add_argument("--other-income", type=int, default=0, help="interest + misc at slab (EXCLUDING dividends)")
    ap.add_argument("--dividend-income", type=int, default=0, help="slab-taxed but surcharge-capped — keep separate")
    ap.add_argument("--business-income", type=int, default=0, help="net non-speculative + speculative profit")
    ap.add_argument("--hp-interest-paid", type=int, default=0)
    ap.add_argument("--stcg-111a", type=int, default=0)
    ap.add_argument("--ltcg-112a", type=int, default=0, help="NET of the exempt first slice")
    ap.add_argument("--ltcg-112", type=int, default=0, help="LTCG on non-equity assets (s.112)")
    ap.add_argument("--vda", type=int, default=0)
    ap.add_argument("--old-80c", type=int, default=0)
    ap.add_argument("--old-80d-self-premium", type=int, default=0)
    ap.add_argument("--old-80d-self-medical", type=int, default=0,
                    help="senior medical expenditure, only if the senior has no health policy")
    ap.add_argument("--old-80d-parents-premium", type=int, default=0)
    ap.add_argument("--old-80d-parents-medical", type=int, default=0)
    ap.add_argument("--old-80d-preventive", type=int, default=0)
    ap.add_argument("--parents-senior", action="store_true", help="either parent aged 60+")
    ap.add_argument("--old-80tta", type=int, default=0)
    ap.add_argument("--old-other-via", type=int, default=0)
    ap.add_argument("--age", type=int, default=30)
    ap.add_argument("--non-resident", dest="resident", action="store_false",
                    help="disables the basic-exemption adjustment against special-rate gains")
    return ap


if __name__ == "__main__":
    args = build_parser().parse_args()

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

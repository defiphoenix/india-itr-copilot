#!/usr/bin/env python3
"""
Release-gate suite: the statutory edge cases the engines must get right before
any output is treated as filing-grade. Run from the repo root:

    python -m unittest discover tests -v

Every expected value below was hand-derived from the statute + registry; if a
registry rate changes for a new AY, re-derive rather than just re-recording
the engine's output.
"""

import json
import sys
import unittest
from argparse import Namespace
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import compare_regimes as cr
import compute_interest_234 as ci

RULES = json.loads((ROOT / "rules" / "AY2026-27.json").read_text(encoding="utf-8"))


def make_args(**kw):
    base = dict(
        salary_gross=0, other_income=0, dividend_income=0, business_income=0,
        hp_interest_paid=0, stcg_111a=0, ltcg_112a=0, ltcg_112=0, vda=0,
        old_80c=0, old_80d_self_premium=0, old_80d_self_medical=0,
        old_80d_parents_premium=0, old_80d_parents_medical=0,
        old_80d_preventive=0, parents_senior=False,
        old_80tta=0, old_other_via=0, age=30, resident=True,
    )
    base.update(kw)
    return Namespace(**base)


class TestRounding288B(unittest.TestCase):
    def test_1005_rounds_up_not_bankers(self):
        self.assertEqual(cr.round_288b(1005), 1010)   # Python round() gives 1000

    def test_below_five_rounds_down(self):
        self.assertEqual(cr.round_288b(1004), 1000)
        self.assertEqual(cr.round_288b(994.99), 990)  # paise ignored first

    def test_five_and_above_rounds_up(self):
        self.assertEqual(cr.round_288b(995), 1000)


class TestRebate87A(unittest.TestCase):
    def test_old_regime_111a_stcg_gets_rebate(self):
        # 3L slab income + 1.5L STCG = 4.5L total, under the 5L old-regime bar.
        # Slab tax 2500 + 111A tax 30000 are BOTH 87A-eligible: rebate 12500.
        # (2500 + 30000 - 12500) * 1.04 = 20800
        args = make_args(other_income=300000, stcg_111a=150000)
        out = cr.compute_regime(RULES, "old_regime", args)
        self.assertEqual(out["rebate_87a"], 12500)
        self.assertEqual(out["TOTAL_TAX"], 20800)

    def test_old_regime_112a_ltcg_no_rebate(self):
        # s.112A(6): no 87A against 112A tax. Only the slab tax (2500) is
        # rebate-eligible. 18750 LTCG tax survives: 18750 * 1.04 = 19500.
        args = make_args(other_income=300000, ltcg_112a=150000)
        out = cr.compute_regime(RULES, "old_regime", args)
        self.assertEqual(out["rebate_87a"], 2500)
        self.assertEqual(out["TOTAL_TAX"], 19500)

    def test_new_regime_rebate_excludes_special_rate(self):
        # 11L slab income + 1L STCG = 12L total (at the threshold). Rebate wipes
        # the 50000 slab tax but NOT the 20000 s.111A tax: 20000 * 1.04 = 20800.
        args = make_args(other_income=1100000, stcg_111a=100000)
        out = cr.compute_regime(RULES, "new_regime", args)
        self.assertEqual(out["rebate_87a"], 50000)
        self.assertEqual(out["TOTAL_TAX"], 20800)

    def test_non_resident_gets_no_rebate(self):
        args = make_args(other_income=400000, resident=False)
        out = cr.compute_regime(RULES, "old_regime", args)
        self.assertEqual(out["rebate_87a"], 0)


class TestBasicExemptionAdjustment(unittest.TestCase):
    def test_resident_unused_exemption_reduces_gains(self):
        # 1L slab income leaves 1.5L of the 2.5L old-regime exemption unused.
        # It absorbs STCG first (higher rate): 2L STCG -> 50k taxable @20% = 10000;
        # 1L 112A LTCG stays @12.5% = 12500. 87A then offsets the eligible 10000.
        # (10000 + 12500 - 10000) * 1.04 = 13000
        args = make_args(other_income=100000, stcg_111a=200000, ltcg_112a=100000)
        out = cr.compute_regime(RULES, "old_regime", args)
        self.assertEqual(out["special_rate_tax"], 22500)
        self.assertEqual(out["TOTAL_TAX"], 13000)

    def test_non_resident_no_exemption_adjustment(self):
        # Same figures, non-resident: full 2L STCG @20% = 40000, LTCG 12500,
        # no 87A. (40000 + 12500) * 1.04 = 54600
        args = make_args(other_income=100000, stcg_111a=200000, ltcg_112a=100000,
                         resident=False)
        out = cr.compute_regime(RULES, "old_regime", args)
        self.assertEqual(out["special_rate_tax"], 52500)
        self.assertEqual(out["TOTAL_TAX"], 54600)


class TestSurchargeCap(unittest.TestCase):
    def test_cg_and_dividend_capped_at_15_when_other_income_high(self):
        # Income ex-CG/dividend 2.49Cr (> 2Cr): 25% on normal tax, 15% on CG+div.
        s, normal_rate, cg_rate = cr.surcharge_components(
            RULES["surcharge"], total_income=34_925_000,
            income_ex_cg_div=24_925_000,
            normal_tax_after_rebate=7_000_000, capped_component_tax=1_500_000,
            uncapped_special_tax=0, regime_cap=0.25)
        self.assertEqual(normal_rate, 0.25)
        self.assertEqual(cg_rate, 0.15)
        self.assertEqual(s, 0.25 * 7_000_000 + 0.15 * 1_500_000)

    def test_whole_surcharge_capped_when_only_cg_crosses_2cr(self):
        # Total 6Cr but only 1Cr is non-CG: the 37%/25% tiers never engage;
        # everything is capped at 15%.
        s, normal_rate, cg_rate = cr.surcharge_components(
            RULES["surcharge"], total_income=60_000_000,
            income_ex_cg_div=10_000_000,
            normal_tax_after_rebate=2_800_000, capped_component_tax=6_250_000,
            uncapped_special_tax=0, regime_cap=None)
        self.assertEqual(normal_rate, 0.15)
        self.assertEqual(cg_rate, 0.15)

    def test_end_to_end_mixed_above_2cr(self):
        # 2.5Cr salary + 50L dividend + 50L 112A gains through the full engine —
        # must be cheaper than a naive single-rate surcharge on all tax.
        args = make_args(salary_gross=25_000_000, dividend_income=5_000_000,
                         ltcg_112a=5_000_000)
        out = cr.compute_regime(RULES, "new_regime", args)
        naive_sur = (out["normal_tax"] + out["special_rate_tax"]) * 0.25
        self.assertLess(out["surcharge"], naive_sur)


class TestDeduction80D(unittest.TestCase):
    def test_self_and_parents_caps(self):
        caps = RULES["deduction_caps_old_regime"]["80d"]
        args = make_args(old_80d_self_premium=200000,
                         old_80d_parents_premium=200000, parents_senior=True)
        self.assertEqual(cr.deduction_80d(caps, args), 25000 + 50000)

    def test_preventive_within_self_cap(self):
        caps = RULES["deduction_caps_old_regime"]["80d"]
        args = make_args(old_80d_self_premium=22000, old_80d_preventive=10000)
        # preventive capped at 5000, then 22000+5000 capped at 25000
        self.assertEqual(cr.deduction_80d(caps, args), 25000)

    def test_senior_medical_only_for_seniors(self):
        caps = RULES["deduction_caps_old_regime"]["80d"]
        young = make_args(old_80d_self_medical=40000, age=30)
        senior = make_args(old_80d_self_medical=40000, age=65)
        self.assertEqual(cr.deduction_80d(caps, young), 0)
        self.assertEqual(cr.deduction_80d(caps, senior), 40000)


class TestInterest234(unittest.TestCase):
    def run_compute(self, **kw):
        base = dict(tax=500_000, tds=0, fy_start_year=2025,
                    pay_date=date(2026, 7, 20), due_date=None, file_date=None,
                    advance=[], payments=(), income_events=())
        base.update(kw)
        return ci.compute(**base)

    def test_senior_citizen_no_business_owes_no_234bc(self):
        _, _, a, b, c, _, _ = self.run_compute(age=65, resident=True)
        self.assertEqual((b, c), (0, 0))

    def test_non_senior_same_facts_owes_both(self):
        _, _, a, b, c, _, _ = self.run_compute(age=45)
        # 234B: 500000 x 1% x 4 months (Apr-Jul) = 20000
        # 234C: 2250 + 6750 + 11250 + 5000 = 25250
        self.assertEqual(b, 20000)
        self.assertEqual(c, 25250)

    def test_presumptive_single_march_instalment(self):
        _, _, _, _, c, _, _ = self.run_compute(
            tax=100_000, presumptive="44ADA", has_business_income=True)
        # one instalment: 100000 x 1% x 1 month = 1000 (not the 5050 of the 4-step schedule)
        self.assertEqual(c, 1000)

    def test_presumptive_paid_by_march_owes_nothing(self):
        _, _, _, _, c, _, _ = self.run_compute(
            tax=100_000, presumptive="44ADA", has_business_income=True,
            advance=[(date(2026, 3, 10), 100_000)])
        self.assertEqual(c, 0)

    def test_capital_gain_after_instalment_gets_234c_relief(self):
        # Tax of 60000 arises from a gain on 20 Dec 2025: excluded from the
        # Jun/Sep/Dec instalment bases (40000 each), included only in March.
        # 234C = 180 + 540 + 900 + 1000 = 2620 (vs 5050 without relief).
        _, _, _, _, c, _, _ = self.run_compute(
            tax=100_000, income_events=[(date(2025, 12, 20), 60_000)])
        self.assertEqual(c, 2620)

    def test_234b_reducing_balance_on_part_payment(self):
        # 100k shortfall; 60k paid 2 May 2026, balance on 20 Jul.
        # Apr-May: 100000 x 1% x 2 = 2000; Jun-Jul: 40000 x 1% x 2 = 800.
        _, _, _, b, _, _, _ = self.run_compute(
            tax=100_000, payments=[(date(2026, 5, 2), 60_000)])
        self.assertEqual(b, 2800)


class TestRegistry(unittest.TestCase):
    def test_belated_and_revised_deadlines_are_separate(self):
        dd = RULES["due_dates"]
        self.assertNotIn("belated_or_revised", dd)
        self.assertEqual(dd["belated_return"], "2026-12-31")
        self.assertEqual(dd["revised_return_without_234i_fee"], "2026-12-31")
        self.assertEqual(dd["revised_return_final"], "2027-03-31")

    def test_194a_senior_threshold_present(self):
        t = RULES["tds_thresholds_common"]
        self.assertEqual(t["194a_bank_interest_non_senior"], 50000)
        self.assertEqual(t["194a_bank_interest_senior"], 100000)

    def test_itr_form_eligibility_block(self):
        e = RULES["itr_form_eligibility"]
        self.assertEqual(e["itr1_max_house_properties"], 2)
        self.assertEqual(e["itr4_max_house_properties"], 2)

    def test_every_block_has_primary_sources(self):
        for key, block in RULES.items():
            if isinstance(block, dict) and "sources" in block:
                src = block["sources"]
                self.assertIsInstance(src, dict, f"{key}: sources must split primary/explanatory")
                self.assertTrue(src.get("primary"), f"{key}: needs at least one primary source")
                for url in src["primary"]:
                    self.assertRegex(url, r"incometax|indiabudget|egazette",
                                     f"{key}: primary source must be official: {url}")


if __name__ == "__main__":
    unittest.main()

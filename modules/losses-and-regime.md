# Set-off, carry-forward, and the regime decision

## Set-off runs in statutory order — no discretion

1. Within each head/pool (speculative stays sealed; LTCL meets only LTCG).
2. Across heads for what remains, subject to the walls below. **Mandatory**: a loss that can be
   absorbed this year must be — it cannot be parked because next year's set-off would be worth more.
3. Brought-forward vintages absorb next, oldest first, same-head rules.
4. Survivors carry forward — only if this return is filed by the due date (house-property loss and
   unabsorbed depreciation survive late filing; nothing else does).

### Walls to respect

| Loss | Same-year set-off | Carry | Future absorbs |
|---|---|---|---|
| Non-speculative business | Any head except salary | 8 yrs | Any business income |
| Speculative (intraday) | Speculative profit only | 4 yrs | Speculative only |
| STCL | STCG + LTCG | 8 yrs | STCG + LTCG |
| LTCL | LTCG only | 8 yrs | LTCG only |
| House property | Other heads up to the cap, old regime only; none in new | 8 yrs | HP income only |
| VDA | Nothing | none | nothing |

Tell users the consequence honestly: a small trading loss beside large interest income gets eaten
this year at full slab value (good outcome), and nothing survives to next year — never promise a
carry-forward before running the set-off.

Unabsorbed depreciation is its own creature: no expiry, survives belated filing, absorbs against
any head except salary — keep it out of the business-loss rows.

## Regime choice — computed, never asserted

Run `scripts/compare_regimes.py` with real figures and present both columns. Heuristics
("old needs ~₹4L of deductions to win at mid incomes") are for setting expectations only; the table
decides. Structural notes:
- New is the default. Salaried-only filers flip freely inside each year's return.
- Business-income filers opting out need Form 10-IEA before the due date, and the door mostly
  locks behind them — flag this weight before recommending OLD to anyone with business income.
- The rebate and its marginal relief (new regime) never touch special-rate gains; a filer under the
  rebate ceiling can still owe real tax on equity gains.
- Prior-year vintages and current losses carry identically under both regimes; what differs is HP
  inter-head set-off and the deduction basket.

# Insights Spending Trend — Intent

- **Problem:** The Insights tab shows spending as period totals (cash flow bars, category trends by month) but never as an in-month trajectory — users can't see how this month's spending is pacing against previous months, the way banking apps (reference: DBS "Spending trend") show it.
- **Proposed outcome:** The Cash flow panel gains a pill toggle [Cash flow | Spending trend]. The trend view overlays one cumulative day-by-day spend line per month in the selected range window (1m/3m/6m…), newest month solid and colored — including the current partial month, ending at today with a marker — older months dashed/faded. Hovering a day shows each month's cumulative spend at that day-of-month.
- **Affected systems:** dashboard Insights page (toggle + chart view), dashboard data module (cumulative-by-day computation), their two test files.
- **Constraints:** Existing panel/idiom styles; range selector keeps governing all panels; category exclusions (`excludedCats`) apply to the trend exactly as they do to cash flow; privacy mode blurs amounts.
- **Resolved decisions:** placement → toggle inside Cash flow panel (user); month scope → follows the range selector (user, against recommendation — recorded); rendering → one cumulative line per month in window, overlaid (user); partial month → included, month-to-date with end marker (user; deliberate exception to the "exclude current month" convention of the other trend panels, for this view only).
- **Out of scope:** month picker; "Money Out / Money In" tabs from the screenshot; budgets/spending tracker; changes to the other Insights panels' current-month exclusion; backend/API changes (transactions are already client-side).
- **Open questions:** none.

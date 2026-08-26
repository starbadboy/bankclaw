const assert = require("node:assert/strict");
const test = require("node:test");

global.window = global;
require("./data.js");

test("portfolio net worth only emits months with real valuation activity", () => {
  const assets = [{ id: "cash" }, { id: "brokerage" }];
  const debts = [{ id: "loan" }];
  const histories = {
    "asset:cash": [
      { as_of_date: "2026-01-10", value: 1000 },
      { as_of_date: "2026-03-10", value: 1200 },
    ],
    "asset:brokerage": [{ as_of_date: "2026-04-01", value: 500 }],
    "debt:loan": [
      { as_of_date: "2026-01-01", value: 200 },
      { as_of_date: "2026-03-20", value: 150 },
    ],
  };

  const history = buildPortfolioNetWorthHistory(assets, debts, histories, {
    months: 4,
    now: new Date(2026, 3, 15),
  });

  assert.deepEqual(
    history.map(({ date, value }) => ({ date, value })),
    [
      { date: "2026-01-10", value: 800 },
      { date: "2026-03-20", value: 1050 },
      { date: "2026-04-01", value: 1550 },
    ],
  );
});

test("one real valuation produces one net-worth point", () => {
  const history = buildPortfolioNetWorthHistory(
    [{ id: "cash" }],
    [],
    { "asset:cash": [{ as_of_date: "2026-01-10", value: 1000 }] },
    { months: 12, now: new Date(2026, 3, 15) },
  );

  assert.deepEqual(history.map(({ date, value }) => ({ date, value })), [
    { date: "2026-01-10", value: 1000 },
  ]);
});

test("portfolio item series sorts real values chronologically", () => {
  const histories = {
    "asset:cash": [
      { as_of_date: "2026-04-30", value: 1250 },
      { as_of_date: "2026-01-31", value: 1000 },
    ],
  };

  assert.deepEqual(getPortfolioItemSeries(histories, "asset", "cash"), [1000, 1250]);
});

test("portfolio history stays empty when no real valuations exist", () => {
  const history = buildPortfolioNetWorthHistory([{ id: "cash" }], [], {}, {
    months: 12,
    now: new Date(2026, 3, 15),
  });

  assert.deepEqual(history, []);
});

test("performance rows compute windowed change per item", () => {
  const assets = [{ id: "cash", name: "Cash DBS" }];
  const debts = [];
  const histories = {
    "asset:cash": [
      { as_of_date: "2025-01-10", value: 10000 },
      { as_of_date: "2025-06-01", value: 12000 },
      { as_of_date: "2025-08-10", value: 12400 },
    ],
  };
  const rows = computePortfolioPerformance(assets, debts, histories, {
    months: 3, now: new Date(2025, 7, 24),
  });
  const cash = rows.items.find((r) => r.key === "asset:cash");
  // window starts 2025-05-24: baseline = latest at/before start = 10000 (Jan 10)
  assert.equal(cash.current, 12400);
  assert.equal(cash.delta, 2400);
  assert.equal(cash.deltaPct, 24);
  assert.deepEqual(cash.series, [10000, 12000, 12400]);
});

test("performance debt rows read pay-down as positive improvement", () => {
  const debts = [{ id: "loan", name: "Car loan" }];
  const histories = {
    "debt:loan": [
      { as_of_date: "2025-05-01", value: 8000 },
      { as_of_date: "2025-08-01", value: 7000 },
    ],
  };
  const rows = computePortfolioPerformance([], debts, histories, {
    months: 6, now: new Date(2025, 7, 24),
  });
  const loan = rows.items.find((r) => r.key === "debt:loan");
  assert.equal(loan.current, 7000);
  assert.equal(loan.delta, 1000);      // balance fell 1000 -> improvement +1000
  assert.equal(loan.deltaPct, 12.5);
});

test("performance rows with no in-window valuations show no change", () => {
  const assets = [{ id: "old", name: "Dormant" }];
  const histories = {
    "asset:old": [{ as_of_date: "2024-01-01", value: 5000 }],
  };
  const rows = computePortfolioPerformance(assets, [], histories, {
    months: 1, now: new Date(2025, 7, 24),
  });
  const old = rows.items.find((r) => r.key === "asset:old");
  assert.equal(old.current, 5000);
  assert.equal(old.delta, null);
  assert.equal(old.deltaPct, null);
});

test("performance percentage is null on a zero baseline", () => {
  const assets = [{ id: "new", name: "New account" }];
  const histories = {
    "asset:new": [
      { as_of_date: "2025-07-01", value: 0 },
      { as_of_date: "2025-08-01", value: 500 },
    ],
  };
  const rows = computePortfolioPerformance(assets, [], histories, {
    months: 3, now: new Date(2025, 7, 24),
  });
  const item = rows.items[0];
  assert.equal(item.delta, 500);
  assert.equal(item.deltaPct, null);
});

test("performance total row equals the sum of item moves", () => {
  const assets = [{ id: "a", name: "A" }];
  const debts = [{ id: "d", name: "D" }];
  const histories = {
    "asset:a": [
      { as_of_date: "2025-05-01", value: 10000 },
      { as_of_date: "2025-08-01", value: 11000 },
    ],
    "debt:d": [
      { as_of_date: "2025-05-01", value: 4000 },
      { as_of_date: "2025-08-01", value: 3500 },
    ],
  };
  const rows = computePortfolioPerformance(assets, debts, histories, {
    months: 6, now: new Date(2025, 7, 24),
  });
  assert.equal(rows.total.delta, 1000 + 500);   // asset up 1000, debt improved 500
  assert.equal(rows.total.deltaPct, 25);        // baseline net worth 6000
});

test("performance all-time window uses first valuation but needs two points", () => {
  const assets = [{ id: "a", name: "A" }, { id: "single", name: "One point" }];
  const histories = {
    "asset:a": [
      { as_of_date: "2023-01-01", value: 1000 },
      { as_of_date: "2025-08-01", value: 3000 },
    ],
    "asset:single": [{ as_of_date: "2025-08-01", value: 500 }],
  };
  const rows = computePortfolioPerformance(assets, [], histories, {
    months: null, now: new Date(2025, 7, 24),
  });
  assert.equal(rows.items[0].delta, 2000);
  assert.equal(rows.items[0].deltaPct, 200);
  assert.equal(rows.items[1].delta, null);
});


test("performance window start clamps at month boundaries instead of rolling over", () => {
  // 2025-03-30 minus 1 month must clamp to 2025-02-28, not roll to 2025-03-02
  const assets = [{ id: "a", name: "A" }];
  const histories = {
    "asset:a": [
      { as_of_date: "2025-02-20", value: 1000 },
      { as_of_date: "2025-03-01", value: 2000 },
    ],
  };
  const rows = computePortfolioPerformance(assets, [], histories, {
    months: 1, now: new Date(2025, 2, 30),
  });
  assert.equal(rows.items[0].delta, 1000);
  assert.equal(rows.items[0].deltaPct, 100);
});

test("performance three-month window from may 31 reaches back to february 28", () => {
  const assets = [{ id: "a", name: "A" }];
  const histories = {
    "asset:a": [
      { as_of_date: "2025-02-28", value: 100 },
      { as_of_date: "2025-04-01", value: 150 },
    ],
  };
  const rows = computePortfolioPerformance(assets, [], histories, {
    months: 3, now: new Date(2025, 4, 31),
  });
  assert.equal(rows.items[0].delta, 50);  // 02-28 entry is the baseline, not dropped
});

test("performance twelve-month window from leap day clamps to february 28", () => {
  const assets = [{ id: "a", name: "A" }];
  const histories = {
    "asset:a": [
      { as_of_date: "2023-02-27", value: 10 },
      { as_of_date: "2023-06-01", value: 20 },
    ],
  };
  const rows = computePortfolioPerformance(assets, [], histories, {
    months: 12, now: new Date(2024, 1, 29),
  });
  assert.equal(rows.items[0].delta, 10);
});

test("performance debt series follows the improvement direction of its own row", () => {
  const debts = [{ id: "loan", name: "Loan" }];
  const histories = {
    "debt:loan": [
      { as_of_date: "2025-05-01", value: 8000 },
      { as_of_date: "2025-08-01", value: 7000 },
    ],
  };
  const rows = computePortfolioPerformance([], debts, histories, {
    months: 6, now: new Date(2025, 7, 24),
  });
  // pay-down is +1000 (green); the sparkline must rise with it, not fall
  assert.deepEqual(rows.items[0].series, [-8000, -7000]);
});

test("spending trend accumulates money-out per day and respects exclusions", () => {
  const txns = [
    { date: "2025-08-05", amount: -100, category: "food" },
    { date: "2025-08-05", amount: -50, category: "rent" },     // excluded
    { date: "2025-08-10", amount: 200, category: "salary" },   // income ignored
    { date: "2025-08-12", amount: -25.5, category: "food" },
    { date: "2025-07-03", amount: -40, category: "food" },
  ];
  const trend = computeSpendingTrend(txns, {
    rangeMonths: 1, excludedCategories: new Set(["rent"]), now: new Date(2025, 7, 15),
  });
  assert.equal(trend.length, 2);                       // max(2, N): current + last
  const [july, august] = trend;
  assert.equal(august.isCurrent, true);
  assert.equal(august.cumulative.length, 15);          // cut at now (Aug 15)
  assert.equal(august.cumulative[3], 0);               // nothing before day 5 (day-exact, catches TZ shift)
  assert.equal(august.cumulative[4], 100);             // day 5: rent excluded
  assert.equal(august.cumulative[11], 125.5);          // day 12 cumulative
  assert.equal(august.cumulative[14], 125.5);          // income never counted
  assert.equal(july.isCurrent, false);
  assert.equal(july.cumulative.length, 31);            // full July
  assert.equal(july.cumulative[30], 40);
});

test("spending trend emits a zero series for months with no qualifying spend", () => {
  const trend = computeSpendingTrend([], { rangeMonths: 3, now: new Date(2025, 7, 15) });
  assert.equal(trend.length, 3);                       // current + 2 prior
  assert.deepEqual(trend[0].cumulative, new Array(30).fill(0));  // June has 30 days
  assert.equal(trend[1].cumulative.length, 31);        // July
});

test("spending trend handles leap february and month boundaries", () => {
  const txns = [
    { date: "2024-02-29", amount: -10, category: "food" },
    { date: "2024-01-31", amount: -20, category: "food" },
  ];
  const trend = computeSpendingTrend(txns, { rangeMonths: 2, now: new Date(2024, 1, 29) });
  const [jan, feb] = trend;
  assert.equal(feb.cumulative.length, 29);             // leap day included
  assert.equal(feb.cumulative[28], 10);
  assert.equal(jan.cumulative.length, 31);
  assert.equal(jan.cumulative[30], 20);
});

test("spending trend ignores transactions outside the window", () => {
  const txns = [
    { date: "2025-03-01", amount: -999, category: "food" },  // before window
    { date: "2025-08-01", amount: -1, category: "food" },
  ];
  const trend = computeSpendingTrend(txns, { rangeMonths: 3, now: new Date(2025, 7, 15) });
  const total = trend.reduce((s, m) => s + m.cumulative[m.cumulative.length - 1], 0);
  assert.equal(total, 1);
});


test("spending trend keeps first-of-month spend in its own month regardless of timezone", () => {
  const txns = [{ date: "2025-08-01", amount: -500, category: "food" }];
  const trend = computeSpendingTrend(txns, { rangeMonths: 1, now: new Date(2025, 7, 15) });
  const [july, august] = trend;
  assert.equal(august.cumulative[0], 500);   // Aug 1 stays in August
  assert.equal(july.cumulative[30], 0);      // never migrates into July
});

test("holding chart data picks the series by mode and labels month boundaries only", () => {
  const points = [
    { date: "2026-07-30", price: 1.5, value: 150 },
    { date: "2026-07-31", price: 1.6, value: 160 },
    { date: "2026-08-03", price: 1.7, value: 170 },
  ];
  const value = buildHoldingChartData(points, "value");
  assert.deepEqual(value.map((d) => d.value), [150, 160, 170]);
  assert.deepEqual(value.map((d) => d.label), ["Jul 26", "", "Aug 26"]);
  assert.deepEqual(buildHoldingChartData(points, "price").map((d) => d.value), [1.5, 1.6, 1.7]);
  assert.deepEqual(buildHoldingChartData([], "price"), []);
});

test("holding chart data falls back to year labels for multi-year spans", () => {
  const points = [
    { date: "2022-01-03", price: 1, value: 1 },
    { date: "2022-06-06", price: 1, value: 1 },
    { date: "2023-01-02", price: 1, value: 1 },
    { date: "2025-03-03", price: 1, value: 1 },
  ];
  assert.deepEqual(buildHoldingChartData(points, "value").map((d) => d.label), ["2022", "", "2023", "2025"]);
});

test("holding chart data thins boundary labels to at most maxLabels", () => {
  const points = Array.from({ length: 13 }, (_, i) => {
    const m = String(i + 1).padStart(2, "0");
    return { date: `2026-${m > 12 ? 12 : m}-01`, price: 1, value: 1 };
  }).map((p, i) => (i === 12 ? { ...p, date: "2027-01-01" } : p));
  const labels = buildHoldingChartData(points, "value", { maxLabels: 6 }).map((d) => d.label);
  assert.equal(labels.filter(Boolean).length, 5);
  assert.equal(labels[0], "Jan 26");
  assert.equal(buildHoldingChartData(points, "value").filter((d) => d.label).length, 13);
});

test("holding chart data drops the leading label when the next boundary is only a few points away", () => {
  const points = [
    { date: "2026-05-28", price: 1, value: 1 },
    { date: "2026-05-29", price: 1, value: 1 },
    ...Array.from({ length: 40 }, (_, i) => ({ date: `2026-06-${String(i + 1).padStart(2, "0")}`, price: 1, value: 1 })),
  ];
  const labels = buildHoldingChartData(points, "value").map((d) => d.label);
  assert.equal(labels[0], "");
  assert.equal(labels[2], "Jun 26");
});

test("holding chart data carries each point's date for hover tooltips", () => {
  const points = [{ date: "2026-08-03", price: 1.5, value: 150 }, { date: "2026-08-04", price: 1.6, value: 160 }];
  assert.deepEqual(buildHoldingChartData(points, "value").map((d) => d.date), ["2026-08-03", "2026-08-04"]);
});

test("goal progress: net worth (legacy and explicit), debt payoff from baseline, allocation band", () => {
  const ctx = {
    net: 50000,
    assetsTotal: 80000,
    allocationByKind: { equities: 24000, cash: 56000 },
    debtsById: { d1: { id: "d1", name: "Car loan", value: 6000 } },
  };
  const legacy = computeGoalProgress({ name: "100k", target_amount: 100000 }, ctx);
  assert.equal(legacy.progress, 0.5);
  assert.equal(legacy.done, false);
  assert.equal(computeGoalProgress({ kind: "net_worth", target_amount: 40000 }, ctx).done, true);

  const debt = computeGoalProgress({ kind: "debt_payoff", debt_id: "d1", baseline: 18000 }, ctx);
  assert.equal(debt.progress, 2 / 3);
  assert.equal(debt.current, 6000);
  assert.equal(debt.done, false);
  assert.equal(computeGoalProgress({ kind: "debt_payoff", debt_id: "d1", baseline: 18000 }, { ...ctx, debtsById: { d1: { value: 0 } } }).done, true);
  assert.equal(computeGoalProgress({ kind: "debt_payoff", debt_id: "gone", baseline: 18000 }, ctx).missing, true);

  const alloc = computeGoalProgress({ kind: "allocation", asset_kind: "equities", target_pct: 40 }, ctx);
  assert.equal(alloc.current, 30);             // 24k of 80k
  assert.equal(alloc.progress, 0.75);          // 1 - |30-40|/40
  assert.equal(alloc.done, false);
  assert.equal(computeGoalProgress({ kind: "allocation", asset_kind: "equities", target_pct: 31 }, ctx).done, true); // within ±2pp
  assert.equal(computeGoalProgress({ kind: "allocation", asset_kind: "crypto", target_pct: 10 }, ctx).current, 0);
  assert.equal(computeGoalProgress({ kind: "allocation", asset_kind: "equities", target_pct: 10 }, ctx).progress, 0); // floored
});

test("projectGoal: rising net worth gives an ETA and monthly pace; thin or wrong-way history does not", () => {
  const points = [
    { date: "2026-02-01", value: 100000 },
    { date: "2026-05-01", value: 106000 },
    { date: "2026-08-01", value: 112000 },
  ];
  const goal = { kind: "net_worth", target_amount: 124000, target_date: "2027-08-01" };
  const p = projectGoal(goal, points, { now: "2026-08-01", current: 112000 });
  assert.equal(p.reason, "ok");
  assert.match(p.eta, /^2027-0[12]-/);                 // ~+12k at ~2k/month → about 6 months out
  assert.ok(Math.abs(p.monthlyNeeded - 1000) < 10);     // 12k over 12 months

  assert.equal(projectGoal(goal, points.slice(0, 1), { now: "2026-08-01", current: 112000 }).reason, "not_enough_history");
  assert.equal(projectGoal(goal, [{ date: "2026-08-01", value: 1 }, { date: "2026-08-10", value: 2 }], { now: "2026-08-10", current: 2 }).reason, "not_enough_history");
  assert.equal(projectGoal(goal, [...points].map((x, i) => ({ ...x, value: 120000 - i * 1000 })), { now: "2026-08-01", current: 118000 }).reason, "not_on_track");
  assert.equal(projectGoal({ ...goal, target_date: null }, points, { now: "2026-08-01", current: 112000 }).monthlyNeeded, null);
  assert.equal(projectGoal(goal, points, { now: "2026-08-01", current: 130000 }).reason, "done");
});

test("projectGoal: debt payoff projects from a falling balance; allocation has no projection", () => {
  const balances = [
    { date: "2026-01-01", value: 12000 },
    { date: "2026-04-01", value: 9000 },
    { date: "2026-07-01", value: 6000 },
  ];
  const p = projectGoal({ kind: "debt_payoff", baseline: 12000, target_date: "2026-12-01" }, balances, { now: "2026-07-01", current: 6000 });
  assert.equal(p.reason, "ok");
  assert.match(p.eta, /^2026-12-(2|3)|^2027-01-0/);      // 6k at ~33/day → ~181 days after Jul 1
  assert.ok(Math.abs(p.monthlyNeeded - 1200) < 20);     // 6k over 5 months
  assert.equal(projectGoal({ kind: "allocation", target_pct: 30 }, balances, { now: "2026-07-01", current: 20 }).reason, "n/a");
});

test("pickNearestGoal prefers the unfinished goal with the highest progress, ties by earliest date", () => {
  const goals = [{ id: "a", target_date: null }, { id: "b", target_date: "2027-01-01" }, { id: "c", target_date: "2026-12-01" }, { id: "d" }];
  const results = { a: { progress: 1, done: true }, b: { progress: 0.6, done: false }, c: { progress: 0.6, done: false }, d: { progress: 0.2, done: false } };
  assert.equal(pickNearestGoal(goals, results).id, "c");
  assert.equal(pickNearestGoal([goals[0]], results), null);
  assert.equal(pickNearestGoal([], results), null);
});

test("pickNearestGoal comparator is stable on exact ties", () => {
  const goals = [{ id: "x", target_date: "2027-01-01" }, { id: "y", target_date: "2027-01-01" }];
  const results = { x: { progress: 0.5, done: false }, y: { progress: 0.5, done: false } };
  assert.equal(pickNearestGoal(goals, results).id, pickNearestGoal([...goals].reverse(), results).id);
});

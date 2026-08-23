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

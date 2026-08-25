const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const source = fs.readFileSync(path.join(__dirname, "page-portfolio.jsx"), "utf8");

test("portfolio page records values with an explicit date", () => {
  assert.match(source, /type="date"/);
  assert.match(source, /apiRecordPortfolioValuation/);
  assert.match(source, /Record value/);
});

test("portfolio page renders only real valuation histories", () => {
  assert.match(source, /buildPortfolioNetWorthHistory/);
  assert.match(source, /getPortfolioItemSeries/);
  assert.doesNotMatch(source, /function buildNetWorthHistory/);
  assert.doesNotMatch(source, /function buildSeries/);
  assert.doesNotMatch(source, /v \* 0\.98/);
});

test("portfolio page loads and renders user-defined asset types everywhere", () => {
  assert.match(source, /apiFetchPortfolioAssetTypes/);
  assert.match(source, /apiCreatePortfolioAssetType/);
  assert.match(source, /apiUpdatePortfolioAssetType/);
  assert.match(source, /apiDeletePortfolioAssetType/);
  assert.match(source, /Create custom type/);
  assert.match(source, /Manage types/);
  assert.match(source, /assetKinds\[a\.kind\]/);
  assert.doesNotMatch(source, /const k = PF_KINDS\[a\.kind\]/);
});

test("portfolio page prevents deleting a custom type that is in use", () => {
  assert.match(source, /assets\.filter\(\(asset\) => asset\.kind === assetType\.id\)/);
  assert.match(source, /inUseCount > 0/);
});

test("portfolio table summaries total the visible assets and all debts", () => {
  assert.match(source, /const filteredAssetTotal = filteredAssets\.reduce/);
  assert.match(source, /const debtTotal = debts\.reduce/);
  assert.match(source, /Total assets/);
  assert.match(source, /Total debts/);
  assert.match(source, /fmtSGD\(filteredAssetTotal, privacy\)/);
  assert.match(source, /fmtSGD\(-debtTotal, privacy\)/);
});

test("portfolio page manages net-worth goals through the API", () => {
  assert.match(source, /function GoalsCard/);
  assert.match(source, /apiFetchPortfolioGoals/);
  assert.match(source, /apiCreatePortfolioGoal/);
  assert.match(source, /apiUpdatePortfolioGoal/);
  assert.match(source, /apiDeletePortfolioGoal/);
});

test("goal progress derives from net worth, capped, with computed done state", () => {
  assert.match(source, /goal\.target_amount/);
  assert.match(source, /Math\.min\(1,/);
  assert.match(source, /net >= goal\.target_amount|goal\.target_amount <= .*net/);
});

test("dedicated goals page renders GoalsCard via the pf-goals sub", () => {
  assert.match(source, /sub === "pf-goals"/);
});

test("each wealth tab gates its own sections", () => {
  assert.match(source, /sub === "pf-networth"/);
  assert.match(source, /sub === "pf-holdings"/);
  assert.match(source, /sub === "pf-allocation"/);
  assert.match(source, /sub === "pf-performance"/);
});

test("wealth tab titles adapt per view", () => {
  assert.match(source, /WEALTH_TABS\[sub\]/);
});

test("allocation tab includes a per-class breakdown table", () => {
  assert.match(source, /% of assets/);
  assert.match(source, /Positions/);
});

test("performance tab renders windowed changes from the data helper", () => {
  assert.match(source, /computePortfolioPerformance/);
  assert.match(source, /PERF_WINDOWS/);
  assert.match(source, /row\.series/);
});

test("valuation panel lets the user set ticker and units through the asset PATCH api", () => {
  assert.match(source, /Market data/);
  assert.match(source, /Ticker/);
  assert.match(source, /Units/);
  assert.match(source, /handleUpdateAssetMarket/);
  assert.match(source, /apiUpdatePortfolioAsset\(/);
  assert.match(source, /onUpdateMarket/);
});

test("NetWorthChart skips empty x-labels and accepts a tick formatter", () => {
  const chart = source.slice(source.indexOf("function NetWorthChart"), source.indexOf("function AddRowForm"));
  assert.match(chart, /fmtTick/);
  assert.match(chart, /d\.label &&|d\.label \?|filter\(\(d\) => d\.label\)/);
  assert.doesNotMatch(chart, /\{Math\.round\(v \/ 1000\)\}k\s*<\/text>/);
});

test("valuation panel fetches market history and renders a Price/Value chart with a range pill", () => {
  assert.match(source, /apiFetchAssetMarketHistory\(/);
  assert.match(source, /buildHoldingChartData\(/);
  assert.match(source, /HOLDING_RANGES/);
  assert.match(source, /Loading prices/);
  assert.match(source, /"price"/);
  assert.match(source, /"value"/);
  assert.match(source, /<NetWorthChart[^>]*fmtTick/);
});

test("NetWorthChart exposes padFraction and fmtValue with behaviour-preserving defaults", () => {
  const chart = source.slice(source.indexOf("function NetWorthChart"), source.indexOf("function AddRowForm"));
  assert.match(chart, /padFraction/);
  assert.match(chart, /fmtValue = \(v\) => Math\.round\(v\)\.toLocaleString\("en-SG"\)/);
  assert.match(source, /<NetWorthChart[^>]*padFraction=\{0\.08\}/);
});

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

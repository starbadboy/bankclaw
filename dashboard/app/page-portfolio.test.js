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

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const source = fs.readFileSync(path.join(__dirname, "page-insights.jsx"), "utf8");

test("category trend draws a same-color monthly-average baseline for every selected series", () => {
  assert.match(source, /const monthlyAverage = s\.values\.reduce/);
  assert.match(source, /stroke=\{s\.color\}/);
  assert.match(source, /strokeDasharray="5 5"/);
  assert.match(source, /Monthly avg/);
});

test("category trend tooltip sums all selected categories for the hovered month", () => {
  assert.match(source, /const selectedTotal = series\.reduce/);
  assert.match(source, /s\.values\[hoverIdx\]/);
  assert.match(source, /Selected total/);
});

test("cash flow panel toggles to a spending trend view", () => {
  assert.match(source, /Spending trend/);
  assert.match(source, /trendView/);
  assert.match(source, /computeSpendingTrend/);
  assert.match(source, /SpendingTrendChart/);
});

test("spending trend hover shows each month's cumulative at the day, with progress marker", () => {
  assert.match(source, /trendHoverDay|hoverDay/);
  assert.match(source, /isCurrent/);
  assert.match(source, /Total to day|to day/);
});

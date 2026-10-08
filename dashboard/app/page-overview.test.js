const assert = require("node:assert/strict");
const test = require("node:test");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const React = require("react");
const esbuild = require("esbuild");

function overview(range, transactions, now = "2026-04-15T12:00:00") {
  const context = {
    React: { ...React, useState: (initial) => [typeof initial === "string" ? range : initial, () => {}], useMemo: (fn) => fn() },
    Date: class extends Date { constructor(...args) { super(...(args.length ? args : [now])); } },
    window: {},
    Icon() {}, Sparkline() {}, StatBlock() {}, BankBadge() {},
    getEmail: () => "test@example.com",
    getCatInfo: () => ({ name: "Shopping" }),
  };
  vm.createContext(context);
  vm.runInContext(fs.readFileSync(path.join(__dirname, "data.js"), "utf8"), context);
  Object.assign(context, context.window);
  vm.runInContext(esbuild.transformSync(fs.readFileSync(path.join(__dirname, "page-overview.jsx"), "utf8"), { loader: "jsx" }).code, context);
  const tree = context.window.OverviewPage({ transactions, privacy: false });
  let flow;
  let label;
  function visit(node) {
    if (!React.isValidElement(node)) return;
    if (node.type === context.Sparkline) flow = node.props.data;
    if (node.props.className === "hero-label" && String(node.props.children).includes("cash flow")) label = React.Children.toArray(node.props.children).join("");
    React.Children.forEach(node.props.children, visit);
  }
  visit(tree);
  return { flow, label };
}

const transactions = [
  ["2025-11-30", -5], ["2025-12-01", 10], ["2026-01-31", -20],
  ["2026-02-01", 30], ["2026-03-01", -40], ["2026-03-31", 50], ["2026-04-01", -60],
].map(([date, amount], id) => ({ id, date, amount, description: "Test", category: "Shopping" }));

for (const [range, label, income, spend, first, last] of [
  ["last_month", "Last month", 50, 40, "2026-03-01", "2026-03-31"],
  ["month", "This month", 0, 60, "2026-04-01", "2026-04-30"],
  ["last_3m", "Last 3 months", 80, 100, "2026-02-01", "2026-04-30"],
  ["last_6m", "Last 6 months", 90, 125, "2025-11-01", "2026-04-30"],
  ["all", "All time", 90, 125, "2025-11-30", "2026-04-01"],
]) {
  test(`overview graph follows ${label}`, () => {
    const result = overview(range, transactions);
    assert.equal(result.label, `${label} cash flow`);
    assert.equal(result.flow.reduce((sum, day) => sum + day.income, 0), income);
    assert.equal(result.flow.reduce((sum, day) => sum + day.spend, 0), spend);
    const date = (value) => `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, "0")}-${String(value.getDate()).padStart(2, "0")}`;
    assert.equal(date(result.flow[0].date), first);
    assert.equal(date(result.flow.at(-1).date), last);
  });
}

test("overview graph handles empty periods and all-time data", () => {
  assert.equal(overview("all", []).flow.length, 0);
  const { flow } = overview("last_month", []);
  assert.equal(flow.length, 31);
  assert.ok(flow.every((day) => day.income === 0 && day.spend === 0));
});

test("overview graph handles leap February and a previous-year month", () => {
  assert.equal(overview("last_month", [], "2024-03-15T12:00:00").flow.length, 29);
  const { flow } = overview("last_month", [], "2026-01-15T12:00:00");
  assert.equal(flow[0].date.getFullYear(), 2025);
  assert.equal(flow[0].date.getMonth(), 11);
  assert.equal(flow.length, 31);
});

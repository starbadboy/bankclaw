// Executed render probe for the goals UI: transpile page-goals.jsx and render its components in node.
// The source-regex tests cannot fail on runtime errors (a null dereference in render passed every one of them
// on 2026-08-26); this file can. GOALS_JSX overrides the source path so the probe can be pointed at an old revision.
const assert = require("node:assert/strict");
const test = require("node:test");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const React = require("react");
const { renderToStaticMarkup } = require("react-dom/server");
const esbuild = require("esbuild");

global.window = global;
global.React = React;
require("./data.js"); // computeGoalProgress, fmtSGD, goal helpers → window
// ui.jsx / api.js pieces the goals components reach for (presentation stubs; the API is never called in render)
Object.assign(global, {
  Icon: ({ name }) => React.createElement("i", { "data-icon": name }),
  StatBlock: ({ label, value, sub }) => React.createElement("div", null, label, value, sub),
  apiGoalSuggestions: async () => ({ suggestions: [], snapshot: null }),
});

const src = fs.readFileSync(process.env.GOALS_JSX || path.join(__dirname, "page-goals.jsx"), "utf8");
const js = esbuild.transformSync(src, { loader: "jsx" }).code + "\nObject.assign(window, { GoalPreview, GoalForm, GoalRow });";
vm.runInThisContext(js, { filename: "page-goals.jsx" });

const render = (Component, props) => renderToStaticMarkup(React.createElement(Component, props));
const assetKinds = { cash: { name: "Cash & savings" }, equities: { name: "Equities" } };
const debts = [{ id: "d1", name: "Car loan", value: 18500 }];
const contexts = {
  empty: { net: 0, assetsTotal: 0, allocationByKind: {}, debtsById: {} },
  live: { net: 206500, assetsTotal: 225000, allocationByKind: { cash: 42000, equities: 118000 }, debtsById: { d1: debts[0] } },
};
const drafts = [
  { kind: "net_worth", name: "", target_amount: "" },
  { kind: "net_worth", name: "Quarter million", target_amount: "250000", target_date: "2027-12-31" },
  { kind: "net_worth", name: "Met", target_amount: "1000" },
  { kind: "debt_payoff", name: "", debt_id: "" },            // the fix-#1 crash: no debt chosen yet
  { kind: "debt_payoff", name: "", debt_id: "d1" },
  { kind: "debt_payoff", name: "", debt_id: "stale-id" },    // debt removed since
  { kind: "debt_payoff", id: "g1", name: "Pay off", debt_id: "d1", baseline: 20000 }, // saved goal in edit mode
  { kind: "allocation", name: "", asset_kind: "equities", target_pct: "" },
  { kind: "allocation", name: "", asset_kind: "equities", target_pct: "30" },
  { kind: "allocation", name: "", asset_kind: "crypto", target_pct: "5" },   // class with no assets and no name
  { name: "legacy", target_amount: "100" },                                  // no kind → net worth
];

test("GoalPreview renders every kind × draft × context × privacy without throwing", () => {
  let renders = 0;
  for (const [ctxName, goalCtx] of Object.entries(contexts)) {
    for (const draft of drafts) {
      for (const privacy of [false, true]) {
        assert.doesNotThrow(() => render(GoalPreview, { draft, goalCtx, assetKinds, privacy }), `${ctxName} ${JSON.stringify(draft)} privacy=${privacy}`);
        renders += 1;
      }
    }
  }
  assert.equal(renders, Object.keys(contexts).length * drafts.length * 2);
});

test("GoalPreview copy follows the draft: empty target, live progress, done state, missing debt", () => {
  const live = contexts.live;
  assert.match(render(GoalPreview, { draft: drafts[0], goalCtx: live, assetKinds, privacy: false }), /Enter a target[^]*Net worth today 206,500\.00/);
  assert.match(render(GoalPreview, { draft: drafts[1], goalCtx: live, assetKinds, privacy: false }), /83%[^]*206,500\.00 of 250,000\.00 · by 2027-12-31/);
  assert.match(render(GoalPreview, { draft: drafts[2], goalCtx: live, assetKinds, privacy: false }), /data-icon="check"[^]*Done/);
  assert.match(render(GoalPreview, { draft: drafts[3], goalCtx: live, assetKinds, privacy: false }), /Choose a debt to see its balance/);
  assert.match(render(GoalPreview, { draft: drafts[4], goalCtx: live, assetKinds, privacy: false }), /0%[^]*18,500\.00 left of 18,500\.00 · baseline set when you save/);
  assert.doesNotMatch(render(GoalPreview, { draft: drafts[6], goalCtx: live, assetKinds, privacy: false }), /baseline set when you save/);
  assert.match(render(GoalPreview, { draft: drafts[8], goalCtx: live, assetKinds, privacy: false }), /25%[^]*Equities 52\.4% · target 30%/);
});

test("GoalForm and GoalRow (edit + saved, incl. removed debt) render on an empty portfolio", () => {
  const goalCtx = contexts.empty;
  const form = render(GoalForm, { debts: [], assetKinds, goalCtx, busy: false, onCreate: async () => {}, privacy: false });
  assert.match(form, /Goal kind[^]*Goal name[^]*Target \(S\$\)[^]*Target date/);
  assert.match(form, /<button[^>]*disabled/); // nothing typed → Add goal disabled
  const goal = { id: "g2", kind: "debt_payoff", name: "Pay off Car loan", debt_id: "gone", baseline: 18500 };
  const result = computeGoalProgress(goal, goalCtx);
  const common = { goal, result, projection: { reason: "n/a" }, assetKinds, goalCtx, busy: false, draft: { name: goal.name, target_date: "" }, setDraft() {}, onEdit() {}, onSave() {}, onCancel() {}, onDelete() {}, privacy: false };
  assert.match(render(GoalRow, { ...common, editing: false }), /Debt removed[^]*Remove goal/);
  assert.doesNotThrow(() => render(GoalRow, { ...common, editing: true }));
});

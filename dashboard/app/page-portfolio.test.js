const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const source = fs.readFileSync(path.join(__dirname, "page-portfolio.jsx"), "utf8");
const goalsSource = fs.readFileSync(path.join(__dirname, "page-goals.jsx"), "utf8");

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
  assert.match(goalsSource, /function GoalsCard/);
  assert.match(source, /apiFetchPortfolioGoals/);
  assert.match(source, /apiCreatePortfolioGoal/);
  assert.match(source, /apiUpdatePortfolioGoal/);
  assert.match(source, /apiDeletePortfolioGoal/);
});

test("goal progress and done state come from the shared data helper, not inline math", () => {
  assert.match(source, /computeGoalProgress\(g, goalCtx\)/);
  assert.match(goalsSource, /result\.done/);
  assert.doesNotMatch(goalsSource, /net \/ goal\.target_amount/);
  assert.equal((goalsSource.match(/computeGoalProgress\(/g) || []).length, 1); // saved rows use resultsById; only the draft preview computes
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

test("holding market block is its own component with a padding floor and an empty-series hint", () => {
  assert.match(source, /function HoldingMarketPanel/);
  assert.match(source, /<HoldingMarketPanel key=\{item\.id\}/);
  const chart = source.slice(source.indexOf("function NetWorthChart"), source.indexOf("function AddRowForm"));
  assert.match(chart, /Number\.EPSILON/);
  assert.match(source, /No prices returned/);
  assert.match(source, /Units must be a number/);
  assert.doesNotMatch(source, /pf-market-(form|chart)/);
});

test("NetWorthChart shows a hover tooltip with the point's date and value", () => {
  const chart = source.slice(source.indexOf("function NetWorthChart"), source.indexOf("function AddRowForm"));
  assert.match(chart, /onMouseMove/);
  assert.match(chart, /onMouseLeave/);
  assert.match(chart, /hoverIdx/);
  assert.match(chart, /\{hovered\.date\} · S\$ \{fmtValue\(hovered\.value\)\}/);
});

test("goal form offers three kinds and rows compute progress through the data helper", () => {
  assert.match(source, /computeGoalProgress\(/);
  assert.match(goalsSource, /"debt_payoff"/);
  assert.match(goalsSource, /"allocation"/);
  assert.match(goalsSource, /Debt removed/);
  assert.match(goalsSource, /aria-label="Goal kind"/);
});

test("goals page has a hero, goal rows with projections, and the net-worth hero names the next goal", () => {
  assert.match(goalsSource, /function GoalsHero/);
  assert.match(goalsSource, /function GoalRow/);
  assert.match(source, /projectGoal\(/);
  assert.match(source, /pickNearestGoal\(/);
  assert.match(goalsSource, /not enough history/i);
  assert.match(source, /Next goal/);
  assert.match(source, /no date yet/);
  assert.match(fs.readFileSync(path.join(__dirname, "..", "index.html"), "utf8"), /src="app\/page-goals\.jsx\?v=__V__"/);
  const css = fs.readFileSync(path.join(__dirname, "styles.css"), "utf8");
  assert.match(css, /\.pf-goal-card/);
  assert.match(css, /\.pf-goal-hero/);
});

test("goals page renders an AI suggestions panel wired to the suggestions API", () => {
  assert.match(goalsSource, /function GoalSuggestions/);
  assert.match(goalsSource, /apiGoalSuggestions\(/);
  assert.match(goalsSource, /Refresh suggestions/);
  assert.match(goalsSource, /Dismiss/);
  assert.match(goalsSource, /portfolio changed/i);
  assert.match(goalsSource, /not configured/i);
  assert.match(goalsSource, /DEEPSEEK_API_KEY/); // not-configured detection keys off the message, not just 503
  assert.doesNotMatch(goalsSource, /SUGGESTION_KIND_TAG/);
  const api = fs.readFileSync(path.join(__dirname, "api.js"), "utf8");
  assert.match(api, /async function apiGoalSuggestions/);
  assert.match(api, /\/api\/portfolio\/goals\/suggestions/);
});

test("goal form uses the labelled add-grid idiom and previews the draft through the progress helper", () => {
  assert.match(goalsSource, /function GoalPreview/);
  assert.match(goalsSource, /className="pf-add-row pf-goal-form"/);
  assert.match(goalsSource, /pf-add-grid/);
  assert.match(goalsSource, /<span>Goal kind<\/span>/);
  assert.match(goalsSource, /<span>Target date/);
  assert.match(goalsSource, /pf-add-actions/);
  assert.match(goalsSource, /Enter a target/);
  assert.match(goalsSource, /\(result\.current \?\? 0\)\.toFixed/); // preview text is evaluated for every kind; current is null for a debt draft with no debt chosen
  assert.match(goalsSource, /Number\(amount\) > 0/); // create guard matches the edit Save guard
  assert.match(goalsSource, /baseline set when you save/i);
  assert.match(goalsSource, /GoalForm[^]*goalCtx=\{goalCtx\}/); // GoalsCard passes the live context into the form
  assert.match(source, /<GoalsCard[^]*goalCtx=\{goalCtx\}/);
  assert.match(fs.readFileSync(path.join(__dirname, "..", "index.html"), "utf8"), /src="app\/page-goals\.jsx\?v=__V__"/); // server injects the asset version (webapp/dashboard_assets.py)
  assert.match(fs.readFileSync(path.join(__dirname, "styles.css"), "utf8"), /\.pf-goal-form \.pf-add-grid/);
});

test("goal edit mode uses labelled fields and previews the draft with a live bar", () => {
  const editBranch = goalsSource.slice(goalsSource.indexOf("if (editing) {"), goalsSource.indexOf("const projectionText"));
  assert.match(editBranch, /pf-add-grid/);
  assert.match(editBranch, /<span>Goal name<\/span>/);
  assert.match(editBranch, /<span>Target date/);
  assert.match(editBranch, /<GoalPreview draft=\{[^}]*\.\.\.goal, \.\.\.draft/); // saved goal + draft fields drive the bar
  assert.match(editBranch, /pf-add-actions/);
  assert.match(goalsSource, /<GoalRow[^]*goalCtx=\{goalCtx\}/);
});

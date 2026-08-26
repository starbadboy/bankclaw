// Bankclaw — reference data and utility functions.
// TRANSACTIONS is populated at runtime by shell.jsx via apiFetchTransactions().

const BANKS = [
  { id: "dbs",     name: "DBS/POSB",            short: "DBS",  color: "#E3000F", tone: "#B3000C" },
  { id: "ocbc",    name: "OCBC",                 short: "OCBC", color: "#C8102E", tone: "#8F0B20" },
  { id: "uob",     name: "UOB",                  short: "UOB",  color: "#005BAC", tone: "#003D75" },
  { id: "chase",   name: "Chase",                short: "CHA",  color: "#117ACA", tone: "#0C5A97" },
  { id: "sc",      name: "Standard Chartered",   short: "SC",   color: "#0473EA", tone: "#035AB8" },
  { id: "maybank", name: "Maybank",              short: "MAY",  color: "#FFCC00", tone: "#CC9900" },
  { id: "hsbc",    name: "HSBC",                 short: "HSB",  color: "#DB0011", tone: "#A3000D" },
  { id: "other",   name: "Other",                short: "OTH",  color: "#888888", tone: "#555555" },
];

// Full list of statement layouts supported by monopoly-core (kept in sync
// with webapp/constants.py SUPPORTED_BANKS). Credit/debit flags indicate
// whether that statement type can be parsed.
const SUPPORTED_BANKS = [
  { name: "Bank of America",                    credit: true,  debit: true  },
  { name: "Bank of Montreal (BMO)",             credit: true,  debit: true  },
  { name: "Canadian Imperial Bank of Commerce", credit: true,  debit: true  },
  { name: "Canadian Tire Bank",                 credit: true,  debit: false },
  { name: "Capital One Canada",                 credit: true,  debit: false },
  { name: "Chase",                              credit: true,  debit: false },
  { name: "Citibank",                           credit: true,  debit: false },
  { name: "DBS / POSB",                         credit: true,  debit: true  },
  { name: "HSBC",                               credit: true,  debit: false },
  { name: "Maybank",                            credit: true,  debit: true  },
  { name: "OCBC",                               credit: true,  debit: true  },
  { name: "Royal Bank of Canada (RBC)",         credit: true,  debit: true  },
  { name: "Scotiabank",                         credit: true,  debit: true  },
  { name: "Standard Chartered",                 credit: true,  debit: false },
  { name: "TD Canada Trust",                    credit: true,  debit: true  },
  { name: "Trust",                              credit: true,  debit: false },
  { name: "UOB",                                credit: true,  debit: true  },
  { name: "Zürcher Kantonalbank",               credit: false, debit: true  },
];

const CATEGORIES = [
  { id: "food",          name: "Food & Dining",  glyph: "🍽" },
  { id: "transport",     name: "Transport",       glyph: "🚕" },
  { id: "shopping",      name: "Shopping",        glyph: "🛍" },
  { id: "entertainment", name: "Entertainment",   glyph: "🎬" },
  { id: "utilities",     name: "Utilities",       glyph: "⚡" },
  { id: "healthcare",    name: "Healthcare",      glyph: "✚" },
  { id: "travel",        name: "Travel",          glyph: "✈" },
  { id: "income",        name: "Income",          glyph: "↑" },
  { id: "transfer",      name: "Transfer",        glyph: "⇄" },
  { id: "other",         name: "Other",           glyph: "•" },
];

// Runtime transaction store — replaced by shell.jsx after API load
let TRANSACTIONS = [];

// ── Aggregation helpers ────────────────────────────────────────────────────

function totalsFor(txs) {
  let income = 0, spend = 0;
  txs.forEach((t) => {
    if (t.amount > 0) income += t.amount;
    else spend += -t.amount;
  });
  return { income, spend, net: income - spend, count: txs.length };
}

function spendByCategory(txs) {
  const map = {};
  txs.forEach((t) => {
    if (t.amount < 0 && t.category !== "transfer") {
      map[t.category] = (map[t.category] || 0) + -t.amount;
    }
  });
  return Object.entries(map)
    .map(([id, total]) => ({ id, total, cat: (typeof getCatInfo === "function" ? getCatInfo(id) : CATEGORIES.find((c) => c.id === id)) }))
    .sort((a, b) => b.total - a.total);
}

function dailyFlow(txs, days = 30) {
  const end = new Date();
  const buckets = [];
  for (let i = days - 1; i >= 0; i--) {
    const d = new Date(end); d.setDate(d.getDate() - i); d.setHours(0, 0, 0, 0);
    buckets.push({ date: d, income: 0, spend: 0 });
  }
  txs.forEach((t) => {
    const td = new Date(t.date); td.setHours(0, 0, 0, 0);
    const idx = buckets.findIndex((b) => b.date.getTime() === td.getTime());
    if (idx >= 0) {
      if (t.amount > 0) buckets[idx].income += t.amount;
      else buckets[idx].spend += -t.amount;
    }
  });
  return buckets;
}

function lastMonthFlow(txs) {
  const now = new Date();
  const start = new Date(now.getFullYear(), now.getMonth() - 1, 1);
  const end = new Date(now.getFullYear(), now.getMonth(), 0); // last day of prev month
  const days = end.getDate();
  const buckets = [];
  for (let i = 0; i < days; i++) {
    const d = new Date(start); d.setDate(start.getDate() + i); d.setHours(0, 0, 0, 0);
    buckets.push({ date: d, income: 0, spend: 0 });
  }
  txs.forEach((t) => {
    const td = new Date(t.date); td.setHours(0, 0, 0, 0);
    const idx = buckets.findIndex((b) => b.date.getTime() === td.getTime());
    if (idx >= 0) {
      if (t.amount > 0) buckets[idx].income += t.amount;
      else buckets[idx].spend += -t.amount;
    }
  });
  return buckets;
}

// ── Portfolio history helpers ─────────────────────────────────────────────

function _portfolioIsoDate(value) {
  const year = value.getFullYear();
  const month = String(value.getMonth() + 1).padStart(2, "0");
  const day = String(value.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function _portfolioSortedValuations(entries) {
  return (entries || [])
    .filter((entry) => /^\d{4}-\d{2}-\d{2}$/.test(entry?.as_of_date) && Number.isFinite(Number(entry?.value)))
    .map((entry) => ({ ...entry, value: Number(entry.value) }))
    .sort((a, b) => a.as_of_date.localeCompare(b.as_of_date));
}

function _portfolioLatestAt(entries, asOfDate) {
  let latest = null;
  for (const entry of _portfolioSortedValuations(entries)) {
    if (entry.as_of_date > asOfDate) break;
    latest = entry;
  }
  return latest;
}

function getPortfolioItemSeries(histories, itemType, itemId) {
  const entries = histories?.[`${itemType}:${itemId}`] || [];
  return _portfolioSortedValuations(entries).map((entry) => entry.value);
}

const _HOLDING_YEAR_LABEL_MONTHS = 36; // spans longer than this label years instead of months
const _HOLDING_CROWDED_FIRST_LABEL = 0.4; // of average bucket width
const _HOLDING_MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

// Market-history points [{date, price, value}] → NetWorthChart data [{label, value}].
// Labels only where the month (or, for spans > 36 months, the year) changes; dates are sliced as ISO strings.
function buildHoldingChartData(points, mode, options = {}) {
  if (!points || points.length === 0) return [];
  const maxLabels = Number(options.maxLabels) || Infinity;
  const key = mode === "price" ? "price" : "value";
  const first = points[0].date, last = points[points.length - 1].date;
  const spanMonths = (Number(last.slice(0, 4)) - Number(first.slice(0, 4))) * 12 + Number(last.slice(5, 7)) - Number(first.slice(5, 7));
  const byYear = spanMonths > _HOLDING_YEAR_LABEL_MONTHS;
  const bucket = (date) => (byYear ? date.slice(0, 4) : date.slice(0, 7));
  const labelFor = (date) => (byYear ? date.slice(0, 4) : `${_HOLDING_MONTHS[Number(date.slice(5, 7)) - 1]} ${date.slice(2, 4)}`);
  let prev = null;
  const labelled = points.map((p) => {
    const b = bucket(p.date);
    const label = b === prev ? "" : labelFor(p.date);
    prev = b;
    return { label, value: p[key], date: p.date };
  });
  let boundaries = labelled.filter((d) => d.label).length;
  // The first point always starts a bucket; drop its label when the next boundary is unusually close.
  // ponytail: 0.4-of-average-spacing overlap guess; measure text width if labels still collide.
  const secondBoundary = labelled.findIndex((d, i) => i > 0 && d.label);
  if (secondBoundary > 0 && secondBoundary < (labelled.length / boundaries) * _HOLDING_CROWDED_FIRST_LABEL) {
    labelled[0] = { ...labelled[0], label: "" };
    boundaries -= 1;
  }
  if (boundaries <= maxLabels) return labelled;
  const step = Math.ceil(boundaries / maxLabels);
  let seen = 0;
  return labelled.map((d) => (d.label && seen++ % step !== 0 ? { ...d, label: "" } : d));
}

const GOAL_ALLOCATION_BAND_PP = 2; // allocation goals are "done" within ±2 percentage points

// Progress for one goal against the current portfolio.
// ctx: { net, assetsTotal, allocationByKind: {kind: value}, debtsById: {id: debt} }
// Returns { progress 0..1, done, current, target, missing? }. Goals without a kind are net-worth milestones.
function computeGoalProgress(goal, ctx) {
  const kind = goal.kind || "net_worth";
  const clamp = (v) => Math.min(1, Math.max(0, v));
  if (kind === "debt_payoff") {
    const debt = ctx.debtsById?.[goal.debt_id];
    if (!debt) return { progress: 0, done: false, current: null, target: 0, missing: true };
    const baseline = Number(goal.baseline) || 0;
    const current = Number(debt.value) || 0;
    const progress = baseline > 0 ? clamp((baseline - current) / baseline) : (current <= 0 ? 1 : 0);
    return { progress, done: current <= 0, current, target: 0 };
  }
  if (kind === "allocation") {
    const total = Number(ctx.assetsTotal) || 0;
    const current = total > 0 ? ((Number(ctx.allocationByKind?.[goal.asset_kind]) || 0) / total) * 100 : 0;
    const target = Number(goal.target_pct) || 0;
    const done = Math.abs(current - target) <= GOAL_ALLOCATION_BAND_PP;
    const progress = done ? 1 : clamp(1 - Math.abs(current - target) / Math.max(1, target));
    return { progress, done, current, target };
  }
  const target = Number(goal.target_amount) || 0;
  const current = Number(ctx.net) || 0;
  return { progress: target > 0 ? clamp(current / target) : 0, done: current >= target, current, target };
}

const _MS_PER_DAY = 86400000;
const _DAYS_PER_MONTH = 30.4375;
const _isoToDay = (iso) => Date.UTC(Number(iso.slice(0, 4)), Number(iso.slice(5, 7)) - 1, Number(iso.slice(8, 10))) / _MS_PER_DAY;
const _dayToIso = (day) => new Date(Math.round(day) * _MS_PER_DAY).toISOString().slice(0, 10);

// On-track projection for a goal from dated points [{date, value}] (net-worth history, or a debt's balances).
// opts: { now: "YYYY-MM-DD", current }. Returns { eta: iso|null, monthlyNeeded: number|null, reason }.
// reason ∈ ok | done | not_enough_history | not_on_track | n/a. Least-squares slope per day; no Date parsing of ISO strings.
function projectGoal(goal, points, opts = {}) {
  const kind = goal.kind || "net_worth";
  if (kind === "allocation") return { eta: null, monthlyNeeded: null, reason: "n/a" };
  const target = kind === "debt_payoff" ? 0 : Number(goal.target_amount) || 0;
  const current = Number(opts.current) || 0;
  const nowDay = _isoToDay(opts.now || new Date().toISOString().slice(0, 10));
  const remaining = kind === "debt_payoff" ? current : target - current;
  let monthlyNeeded = null;
  if (goal.target_date) {
    const months = (_isoToDay(goal.target_date) - nowDay) / _DAYS_PER_MONTH;
    monthlyNeeded = months > 0 ? remaining / months : null;
  }
  if (remaining <= 0) return { eta: opts.now || null, monthlyNeeded: null, reason: "done" };
  const pts = (points || []).filter((p) => p && /^\d{4}-\d{2}-\d{2}$/.test(p.date) && Number.isFinite(Number(p.value)));
  if (pts.length < 2 || _isoToDay(pts[pts.length - 1].date) - _isoToDay(pts[0].date) < 30) {
    return { eta: null, monthlyNeeded, reason: "not_enough_history" };
  }
  const xs = pts.map((p) => _isoToDay(p.date)), ys = pts.map((p) => Number(p.value));
  const mx = xs.reduce((a, b) => a + b, 0) / xs.length, my = ys.reduce((a, b) => a + b, 0) / ys.length;
  const slope = xs.reduce((a, x, i) => a + (x - mx) * (ys[i] - my), 0) / Math.max(1e-9, xs.reduce((a, x) => a + (x - mx) ** 2, 0));
  const towards = kind === "debt_payoff" ? -slope : slope; // positive = moving toward the target
  if (towards <= 1e-9) return { eta: null, monthlyNeeded, reason: "not_on_track" };
  return { eta: _dayToIso(nowDay + remaining / towards), monthlyNeeded, reason: "ok" };
}

// The unfinished goal with the highest progress; ties broken by the earliest target date (undated last).
function pickNearestGoal(goals, resultsById) {
  const open = (goals || []).filter((g) => resultsById?.[g.id] && !resultsById[g.id].done && !resultsById[g.id].missing);
  if (!open.length) return null;
  return [...open].sort((a, b) => (resultsById[b.id].progress - resultsById[a.id].progress)
    || (a.target_date || "9999").localeCompare(b.target_date || "9999")
    || String(a.id).localeCompare(String(b.id)))[0];
}

function buildPortfolioNetWorthHistory(assets, debts, histories, options = {}) {
  const months = Math.max(1, Number(options.months) || 12);
  const now = options.now instanceof Date ? options.now : new Date();
  const nowIso = _portfolioIsoDate(now);
  const firstMonth = _portfolioIsoDate(new Date(now.getFullYear(), now.getMonth() - months + 1, 1)).slice(0, 7);
  const itemKeys = [
    ...(assets || []).map((asset) => `asset:${asset.id}`),
    ...(debts || []).map((debt) => `debt:${debt.id}`),
  ];
  const latestActivityByMonth = new Map();

  for (const key of itemKeys) {
    for (const entry of _portfolioSortedValuations(histories?.[key])) {
      const month = entry.as_of_date.slice(0, 7);
      if (month < firstMonth || entry.as_of_date > nowIso) continue;
      const current = latestActivityByMonth.get(month);
      if (!current || entry.as_of_date > current) latestActivityByMonth.set(month, entry.as_of_date);
    }
  }

  return [...latestActivityByMonth.values()].sort().map((asOfDate) => {
    let value = 0;

    for (const asset of assets || []) {
      const latest = _portfolioLatestAt(histories?.[`asset:${asset.id}`], asOfDate);
      if (!latest) continue;
      value += latest.value;
    }
    for (const debt of debts || []) {
      const latest = _portfolioLatestAt(histories?.[`debt:${debt.id}`], asOfDate);
      if (!latest) continue;
      value -= latest.value;
    }

    const [year, month, day] = asOfDate.split("-").map(Number);
    return {
      date: asOfDate,
      label: new Date(year, month - 1, day).toLocaleDateString("en-SG", { month: "short" }),
      value: Math.round(value * 100) / 100,
    };
  });
}

function computePortfolioPerformance(assets, debts, histories, options = {}) {
  const now = options.now instanceof Date ? options.now : new Date();
  const nowIso = _portfolioIsoDate(now);
  const months = options.months == null ? null : Math.max(1, Number(options.months) || 1);
  let windowStart = null;
  if (months) {
    // clamp the day so month-end "now" doesn't roll the start into the wrong month
    const lastDay = new Date(now.getFullYear(), now.getMonth() - months + 1, 0).getDate();
    windowStart = _portfolioIsoDate(
      new Date(now.getFullYear(), now.getMonth() - months, Math.min(now.getDate(), lastDay)),
    );
  }

  const itemRow = (itemType, item) => {
    const entries = _portfolioSortedValuations(histories?.[`${itemType}:${item.id}`])
      .filter((entry) => entry.as_of_date <= nowIso);
    const latest = entries[entries.length - 1] || null;
    const current = latest ? latest.value : (Number.isFinite(Number(item.value)) ? Number(item.value) : null);

    let baseline = null;
    let inWindow = entries;
    if (windowStart) {
      baseline = _portfolioLatestAt(entries, windowStart);
      inWindow = entries.filter((entry) => entry.as_of_date > windowStart);
    }
    // No pre-window baseline: fall back to the earliest point, which then needs
    // a second point to measure against.
    if (!baseline) {
      baseline = inWindow.length >= 2 ? inWindow[0] : null;
    } else if (inWindow.length === 0) {
      baseline = null; // nothing moved inside the window -> no change to report
    }

    const sign = itemType === "debt" ? -1 : 1; // pay-down reads as improvement
    let delta = null;
    let deltaPct = null;
    if (baseline && latest) {
      delta = Math.round(sign * (latest.value - baseline.value) * 100) / 100;
      deltaPct = baseline.value === 0 ? null : Math.round((delta / Math.abs(baseline.value)) * 10000) / 100;
    }

    const seriesEntries = baseline && baseline.as_of_date !== inWindow[0]?.as_of_date
      ? [baseline, ...inWindow]
      : inWindow;
    const series = seriesEntries.map((entry) => sign * entry.value);

    return { key: `${itemType}:${item.id}`, itemType, label: item.name, current, delta, deltaPct, series };
  };

  const items = [
    ...(assets || []).map((asset) => itemRow("asset", asset)),
    ...(debts || []).map((debt) => itemRow("debt", debt)),
  ];

  const totalCurrent = items.reduce((sum, row) => {
    if (row.current == null) return sum;
    return sum + (row.itemType === "debt" ? -row.current : row.current);
  }, 0);
  const totalDelta = items.reduce((sum, row) => sum + (row.delta ?? 0), 0);
  const anyDelta = items.some((row) => row.delta != null);
  const totalBaseline = totalCurrent - totalDelta;
  const total = {
    delta: anyDelta ? Math.round(totalDelta * 100) / 100 : null,
    deltaPct: anyDelta && totalBaseline !== 0
      ? Math.round((totalDelta / Math.abs(totalBaseline)) * 10000) / 100
      : null,
  };

  return { items, total };
}

function computeSpendingTrend(transactions, options = {}) {
  const now = options.now instanceof Date ? options.now : new Date();
  const excluded = options.excludedCategories || new Set();
  const monthCount = Math.max(2, Number(options.rangeMonths) || 2);

  const months = [];
  for (let i = monthCount - 1; i >= 0; i--) {
    const start = new Date(now.getFullYear(), now.getMonth() - i, 1);
    const isCurrent = i === 0;
    const daysInMonth = new Date(start.getFullYear(), start.getMonth() + 1, 0).getDate();
    const lastDay = isCurrent ? now.getDate() : daysInMonth;
    months.push({
      key: `${start.getFullYear()}-${String(start.getMonth()).padStart(2, "0")}`,
      label: start.toLocaleDateString("en-GB", { month: "short" }).toUpperCase(),
      cumulative: new Array(lastDay).fill(0),
      isCurrent,
    });
  }
  const byKey = new Map(months.map((m) => [m.key, m]));

  (transactions || []).forEach((t) => {
    if (t.amount >= 0) return;                 // money-out only
    if (excluded.has(t.category)) return;
    // Parse the ISO string directly — new Date("YYYY-MM-DD") is UTC midnight and
    // shifts a day west of UTC, migrating 1st-of-month spend into the prior month.
    const [ty, tm, td] = String(t.date).slice(0, 10).split("-").map(Number);
    if (!ty || !tm || !td) return;
    const m = byKey.get(`${ty}-${String(tm - 1).padStart(2, "0")}`);
    if (!m) return;
    if (td > m.cumulative.length) return;      // future-dated inside current month
    m.cumulative[td - 1] += -t.amount;
  });

  months.forEach((m) => {
    for (let i = 1; i < m.cumulative.length; i++) m.cumulative[i] += m.cumulative[i - 1];
    for (let i = 0; i < m.cumulative.length; i++) m.cumulative[i] = Math.round(m.cumulative[i] * 100) / 100;
  });
  return months;
}

// ── Formatting ─────────────────────────────────────────────────────────────

function fmtSGD(n, privacy = false) {
  if (privacy) return "••••";
  const sign = n < 0 ? "−" : "";
  const abs = Math.abs(n);
  return sign + abs.toLocaleString("en-SG", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function fmtDate(iso, opts = {}) {
  const d = new Date(iso);
  if (opts.long) return d.toLocaleDateString("en-GB", { weekday: "short", day: "2-digit", month: "short", year: "numeric" });
  if (opts.time) return d.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" });
  return d.toLocaleDateString("en-GB", { day: "2-digit", month: "short" });
}

function relDateGroup(iso) {
  const d = new Date(iso); d.setHours(0, 0, 0, 0);
  const today = new Date(); today.setHours(0, 0, 0, 0);
  const diff = Math.round((today - d) / (1000 * 60 * 60 * 24));
  if (diff <= 0) return "Today";
  if (diff === 1) return "Yesterday";
  if (diff < 7) return `${diff} days ago`;
  return d.toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" });
}

Object.assign(window, {
  BANKS, CATEGORIES, SUPPORTED_BANKS, TRANSACTIONS,
  totalsFor, spendByCategory, dailyFlow, lastMonthFlow,
  buildPortfolioNetWorthHistory, getPortfolioItemSeries, computePortfolioPerformance, computeSpendingTrend, buildHoldingChartData, computeGoalProgress, projectGoal, pickNearestGoal,
  fmtSGD, fmtDate, relDateGroup,
});

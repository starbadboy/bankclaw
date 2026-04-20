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
    .map(([id, total]) => ({ id, total, cat: CATEGORIES.find((c) => c.id === id) }))
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
  BANKS, CATEGORIES, TRANSACTIONS,
  totalsFor, spendByCategory, dailyFlow,
  fmtSGD, fmtDate, relDateGroup,
});

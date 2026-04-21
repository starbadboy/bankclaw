// Bankclaw API client — auth, transactions, import, export.
// All functions are exposed on window for use by the React components.

const _TOKEN_KEY = "bc_token";
const _EMAIL_KEY = "bc_email";

function getToken() { return localStorage.getItem(_TOKEN_KEY); }
function getEmail() { return localStorage.getItem(_EMAIL_KEY); }

function _saveSession(token, email) {
  localStorage.setItem(_TOKEN_KEY, token);
  localStorage.setItem(_EMAIL_KEY, email);
}

function clearSession() {
  localStorage.removeItem(_TOKEN_KEY);
  localStorage.removeItem(_EMAIL_KEY);
}

function isLoggedIn() { return !!getToken(); }

async function _fetch(path, options = {}) {
  const token = getToken();
  const headers = { ...(options.headers || {}) };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  if (!(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }
  const res = await fetch(path, { ...options, headers });
  if (res.status === 401) {
    clearSession();
    window.dispatchEvent(new CustomEvent("bc:logout"));
  }
  return res;
}

// ── Auth ──────────────────────────────────────────────────────────────────

async function apiLogin(email, password) {
  const res = await fetch("/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Login failed");
  }
  const data = await res.json();
  _saveSession(data.token, data.email);
  return data;
}

async function apiLogout() { clearSession(); }

async function apiSignup(email, password) {
  const res = await fetch("/api/auth/signup", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Sign-up failed");
  }
  const data = await res.json();
  _saveSession(data.token, data.email);
  return data;
}

async function apiResetPassword(email, newPassword) {
  const res = await fetch("/api/auth/reset-password", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, new_password: newPassword }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Reset failed");
  }
  return res.json();
}

async function apiChangePassword(currentPassword, newPassword) {
  const res = await _fetch("/api/auth/change-password", {
    method: "POST",
    body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Change failed");
  }
  return res.json();
}

// ── Transactions ──────────────────────────────────────────────────────────

async function apiFetchTransactions({ start, end } = {}) {
  const params = new URLSearchParams();
  if (start) params.set("start", start);
  if (end) params.set("end", end);
  const qs = params.toString();
  const res = await _fetch(`/api/transactions${qs ? "?" + qs : ""}`);
  if (!res.ok) return [];
  const data = await res.json();
  return (data.transactions || []).map(normalizeApiTransaction);
}

async function apiCreateTransaction({ date, description, amount, bank, category }) {
  const res = await _fetch("/api/transactions", {
    method: "POST",
    body: JSON.stringify({ date, description, amount, bank, category }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to add transaction");
  }
  return res.json();
}

async function apiDeleteTransactions(transactions) {
  const res = await _fetch("/api/transactions", {
    method: "DELETE",
    body: JSON.stringify({ transactions }),
  });
  if (!res.ok) throw new Error("Delete failed");
  return res.json();
}

// Maps frontend CATEGORIES id → API category string (inverse of _CAT_MAP)
const _CAT_ID_TO_NAME = {
  food: "Food & Dining", transport: "Transport", shopping: "Shopping",
  entertainment: "Entertainment", utilities: "Utilities", healthcare: "Healthcare",
  travel: "Travel", income: "Income", transfer: "Transfer", other: "Other",
};

// Accepts either a built-in id ("food") or a literal category name ("Investment")
async function apiUpdateCategory(tx, newCategoryIdOrName) {
  const raw = tx._raw || {};
  const apiCategory = _CAT_ID_TO_NAME[newCategoryIdOrName] || newCategoryIdOrName;
  const payload = {
    transaction: {
      date: raw.date, description: raw.description,
      amount: raw.amount, bank: raw.bank,
    },
    category: apiCategory,
  };
  const res = await _fetch("/api/transactions/category", {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Update failed");
  }
  return res.json();
}

// ── Import ────────────────────────────────────────────────────────────────

async function apiImport(files, { password = null, categorize = true } = {}) {
  const form = new FormData();
  for (const f of files) form.append("files", f);
  if (password) form.append("password", password);
  form.append("categorize", String(categorize));
  const token = getToken();
  const headers = token ? { Authorization: `Bearer ${token}` } : {};
  const res = await fetch("/api/import", { method: "POST", body: form, headers });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Import failed");
  }
  const data = await res.json();
  // normalize transactions in the response too
  if (data.transactions) data.transactions = data.transactions.map(normalizeApiTransaction);
  return data;
}

// ── Categories ────────────────────────────────────────────────────────────

// Returns full category objects: [{ name, glyph, custom }]
async function apiFetchCategories() {
  const res = await _fetch("/api/categories");
  if (!res.ok) {
    return (typeof CATEGORIES !== "undefined" ? CATEGORIES : []).map(c => ({
      name: c.name, glyph: c.glyph, custom: false,
    }));
  }
  const data = await res.json();
  const cats = data.categories || [];
  // Backward-compat: API may return list of strings (older deploy) — normalize to objects
  return cats.map((c) => typeof c === "string"
    ? { name: c, glyph: "•", custom: false }
    : c);
}

async function apiAddCategory(name, glyph) {
  const body = { name };
  if (glyph) body.glyph = glyph;
  const res = await _fetch("/api/categories", { method: "POST", body: JSON.stringify(body) });
  if (!res.ok) { const e = await res.json().catch(() => ({})); throw new Error(e.detail || "Failed"); }
  return res.json();
}

async function apiDeleteCategory(name) {
  const res = await _fetch(`/api/categories/${encodeURIComponent(name)}`, { method: "DELETE" });
  if (!res.ok) { const e = await res.json().catch(() => ({})); throw new Error(e.detail || "Failed"); }
  return res.json();
}

async function apiRenameCategory(oldName, { name, glyph } = {}) {
  const body = {};
  if (name) body.name = name;
  if (glyph) body.glyph = glyph;
  const res = await _fetch(`/api/categories/${encodeURIComponent(oldName)}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
  if (!res.ok) { const e = await res.json().catch(() => ({})); throw new Error(e.detail || "Failed"); }
  return res.json();
}

// ── Export ────────────────────────────────────────────────────────────────

async function apiExportCsv({ start, end } = {}) {
  const params = new URLSearchParams();
  if (start) params.set("start", start);
  if (end) params.set("end", end);
  const qs = params.toString();
  const token = getToken();
  const headers = token ? { Authorization: `Bearer ${token}` } : {};
  const res = await fetch(`/api/export/csv${qs ? "?" + qs : ""}`, { headers });
  if (!res.ok) throw new Error("Export failed");
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = "transactions.csv"; a.click();
  URL.revokeObjectURL(url);
}

// ── Normalization ─────────────────────────────────────────────────────────
// Maps API bank_name strings → frontend BANKS ids
const _BANK_MAP = {
  // DBS / POSB
  Dbs: "dbs", dbs: "dbs", DBS: "dbs", "DBS/POSB": "dbs", POSB: "dbs",
  // OCBC
  Ocbc: "ocbc", ocbc: "ocbc", OCBC: "ocbc",
  // UOB
  Uob: "uob", uob: "uob", UOB: "uob",
  // Chase
  Chase: "chase", chase: "chase",
  // Standard Chartered
  Sc: "sc", sc: "sc", StandardChartered: "sc", "Standard Chartered": "sc",
  // Maybank
  Maybank: "maybank",
  // HSBC
  Hsbc: "hsbc", HSBC: "hsbc",
  // Generic
  GenericBank: "other",
};

// Maps API category strings → frontend CATEGORIES ids
const _CAT_MAP = {
  "Food & Dining": "food",
  "Transport": "transport",
  "Shopping": "shopping",
  "Entertainment": "entertainment",
  "Utilities": "utilities",
  "Healthcare": "healthcare",
  "Travel": "travel",
  "Income": "income",
  "Transfer": "transfer",
  "Other": "other",
};

let _txCounter = 0;

function normalizeApiTransaction(t) {
  _txCounter++;
  const bankId = _BANK_MAP[t.bank] || "other";
  // Built-in names map to the internal id; custom names keep the raw name
  const catId = _CAT_MAP[t.category] || t.category || "other";
  // Ensure ISO date string
  const dateStr = t.date && t.date.includes("T") ? t.date : `${t.date}T00:00:00.000Z`;
  return {
    id: t._id || `tx_api_${_txCounter}`,
    date: dateStr,
    description: t.description || "",
    amount: parseFloat(t.amount) || 0,
    bank: bankId,
    category: catId,
    reference: t.reference || `REF${String(_txCounter).padStart(6, "0")}`,
    _raw: t,  // keep original for delete/recategorize
  };
}

// Resolve a category id/name to display info. Works for built-ins (by id)
// and for custom categories (by raw name) via window.ALL_CATEGORIES.
function getCatInfo(idOrName) {
  if (!idOrName) return { id: "other", name: "Other", glyph: "•" };
  const cats = typeof CATEGORIES !== "undefined" ? CATEGORIES : [];
  const byId = cats.find((c) => c.id === idOrName);
  if (byId) return byId;
  const all = (typeof window !== "undefined" && window.ALL_CATEGORIES) || [];
  const byName = all.find((c) => c.name === idOrName);
  if (byName) return { id: byName.name, name: byName.name, glyph: byName.glyph || "•" };
  return { id: idOrName, name: idOrName, glyph: "•" };
}
window.getCatInfo = getCatInfo;

Object.assign(window, {
  getToken, getEmail, clearSession, isLoggedIn,
  apiLogin, apiLogout, apiSignup, apiResetPassword, apiChangePassword,
  apiFetchTransactions, apiCreateTransaction, apiDeleteTransactions, apiUpdateCategory,
  apiImport,
  apiFetchCategories, apiAddCategory, apiDeleteCategory, apiRenameCategory,
  apiExportCsv,
  normalizeApiTransaction, getCatInfo,
});

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

async function apiDeleteTransactions(transactions) {
  const res = await _fetch("/api/transactions", {
    method: "DELETE",
    body: JSON.stringify({ transactions }),
  });
  if (!res.ok) throw new Error("Delete failed");
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

async function apiFetchCategories() {
  const res = await _fetch("/api/categories");
  if (!res.ok) return DEFAULT_CATEGORIES.map(c => c.name);
  const data = await res.json();
  return data.categories || [];
}

async function apiAddCategory(name) {
  const res = await _fetch("/api/categories", { method: "POST", body: JSON.stringify({ name }) });
  if (!res.ok) { const e = await res.json().catch(() => ({})); throw new Error(e.detail || "Failed"); }
  return res.json();
}

async function apiDeleteCategory(name) {
  const res = await _fetch(`/api/categories/${encodeURIComponent(name)}`, { method: "DELETE" });
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
  const catId = _CAT_MAP[t.category] || "other";
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

Object.assign(window, {
  getToken, getEmail, clearSession, isLoggedIn,
  apiLogin, apiLogout, apiResetPassword, apiChangePassword,
  apiFetchTransactions, apiDeleteTransactions,
  apiImport,
  apiFetchCategories, apiAddCategory, apiDeleteCategory,
  apiExportCsv,
  normalizeApiTransaction,
});

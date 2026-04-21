// App shell — sidebar, topbar, drawer, tweaks, router
const { useState: useStateApp, useEffect: useEffectApp, useCallback: useCallbackApp } = React;

const TWEAK_DEFAULTS = /*EDITMODE-BEGIN*/{
  "density": "comfortable",
  "accent": "copper",
  "theme": "paper",
  "privacy": false
}/*EDITMODE-END*/;

const ACCENTS = {
  copper: { name: "Copper", swatch: "oklch(0.5 0.14 35)", css: "oklch(0.42 0.14 35)", css2: "oklch(0.55 0.14 35)" },
  olive: { name: "Olive", swatch: "oklch(0.45 0.09 145)", css: "oklch(0.4 0.1 145)", css2: "oklch(0.52 0.1 145)" },
  ink: { name: "Ink", swatch: "oklch(0.22 0.01 70)", css: "oklch(0.22 0.01 70)", css2: "oklch(0.32 0.01 70)" },
  gold: { name: "Gold", swatch: "oklch(0.72 0.12 85)", css: "oklch(0.55 0.12 85)", css2: "oklch(0.65 0.12 85)" },
  cobalt: { name: "Cobalt", swatch: "oklch(0.42 0.12 255)", css: "oklch(0.42 0.12 255)", css2: "oklch(0.52 0.12 255)" },
};

// ── Shared form field helper ────────────────────────────────────────────────

function _FormField({ label, type = "text", value, onChange, placeholder }) {
  return (
    <div style={{ marginBottom: 16 }}>
      <label style={{ display: "block", fontSize: 11, color: "var(--ink-3)", textTransform: "uppercase", letterSpacing: "0.07em", marginBottom: 6 }}>
        {label}
      </label>
      <input
        type={type} required value={value} onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        style={{ width: "100%", boxSizing: "border-box", padding: "10px 12px", border: "1px solid var(--rule)", borderRadius: 4, background: "var(--paper)", color: "var(--ink-1)", fontSize: 14, outline: "none" }}
      />
    </div>
  );
}

function _AuthError({ msg }) {
  if (!msg) return null;
  return (
    <div style={{ marginBottom: 16, padding: "10px 12px", background: "rgba(180,50,50,0.08)", border: "1px solid rgba(180,50,50,0.2)", borderRadius: 4, fontSize: 13, color: "var(--debit)" }}>
      {msg}
    </div>
  );
}

function _AuthSuccess({ msg }) {
  if (!msg) return null;
  return (
    <div style={{ marginBottom: 16, padding: "10px 12px", background: "rgba(50,140,50,0.08)", border: "1px solid rgba(50,140,50,0.2)", borderRadius: 4, fontSize: 13, color: "var(--credit)" }}>
      {msg}
    </div>
  );
}

// ── Login page ─────────────────────────────────────────────────────────────

function LoginPage({ onLogin }) {
  const [mode, setMode] = useStateApp("login"); // login | reset
  const [email, setEmail] = useStateApp("");
  const [password, setPassword] = useStateApp("");
  const [newPassword, setNewPassword] = useStateApp("");
  const [error, setError] = useStateApp("");
  const [success, setSuccess] = useStateApp("");
  const [loading, setLoading] = useStateApp(false);

  const switchMode = (m) => { setMode(m); setError(""); setSuccess(""); };

  const submitLogin = async (e) => {
    e.preventDefault();
    setError(""); setSuccess("");
    setLoading(true);
    try {
      await apiLogin(email, password);
      onLogin();
    } catch (err) {
      setError(err.message || "Login failed");
    } finally {
      setLoading(false);
    }
  };

  const submitReset = async (e) => {
    e.preventDefault();
    setError(""); setSuccess("");
    setLoading(true);
    try {
      await apiResetPassword(email, newPassword);
      setSuccess("Password reset. You can now sign in.");
      switchMode("login");
    } catch (err) {
      setError(err.message || "Reset failed");
    } finally {
      setLoading(false);
    }
  };

  const cardStyle = { width: 360, padding: "48px 40px", background: "var(--surface)", borderRadius: 8, boxShadow: "0 2px 24px rgba(0,0,0,0.08)" };

  return (
    <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", background: "var(--paper)", fontFamily: "var(--sans)" }}>
      <div style={cardStyle}>
        <div style={{ marginBottom: 32, textAlign: "center" }}>
          <div style={{ fontFamily: "Bodoni Moda, Georgia, serif", fontSize: 28, color: "var(--ink-1)", letterSpacing: "-0.01em" }}>
            Bankclaw
          </div>
          <div style={{ fontSize: 13, color: "var(--ink-3)", marginTop: 6 }}>
            {mode === "login" ? "Private Ledger" : "Reset Password"}
          </div>
        </div>

        {mode === "login" && (
          <form onSubmit={submitLogin}>
            <_FormField label="Email" type="email" value={email} onChange={setEmail} placeholder="you@example.com" />
            <_FormField label="Password" type="password" value={password} onChange={setPassword} placeholder="••••••••" />
            <_AuthError msg={error} />
            <_AuthSuccess msg={success} />
            <button type="submit" disabled={loading} style={{ width: "100%", padding: "11px", background: "var(--accent)", color: "#fff", border: "none", borderRadius: 4, fontSize: 14, fontWeight: 500, cursor: loading ? "not-allowed" : "pointer", opacity: loading ? 0.7 : 1 }}>
              {loading ? "Signing in…" : "Sign in"}
            </button>
            <div style={{ marginTop: 16, textAlign: "center" }}>
              <button type="button" onClick={() => switchMode("reset")} style={{ background: "none", border: "none", fontSize: 12, color: "var(--ink-3)", cursor: "pointer", textDecoration: "underline" }}>
                Forgot password?
              </button>
            </div>
          </form>
        )}

        {mode === "reset" && (
          <form onSubmit={submitReset}>
            <_FormField label="Email" type="email" value={email} onChange={setEmail} placeholder="you@example.com" />
            <_FormField label="New Password" type="password" value={newPassword} onChange={setNewPassword} placeholder="Min. 8 characters" />
            <_AuthError msg={error} />
            <button type="submit" disabled={loading} style={{ width: "100%", padding: "11px", background: "var(--accent)", color: "#fff", border: "none", borderRadius: 4, fontSize: 14, fontWeight: 500, cursor: loading ? "not-allowed" : "pointer", opacity: loading ? 0.7 : 1 }}>
              {loading ? "Resetting…" : "Reset password"}
            </button>
            <div style={{ marginTop: 16, textAlign: "center" }}>
              <button type="button" onClick={() => switchMode("login")} style={{ background: "none", border: "none", fontSize: 12, color: "var(--ink-3)", cursor: "pointer", textDecoration: "underline" }}>
                Back to sign in
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}

// ── Change-password modal (authenticated) ──────────────────────────────────

function ChangePasswordModal({ onClose }) {
  const [current, setCurrent] = useStateApp("");
  const [next, setNext] = useStateApp("");
  const [confirm, setConfirm] = useStateApp("");
  const [error, setError] = useStateApp("");
  const [success, setSuccess] = useStateApp("");
  const [loading, setLoading] = useStateApp(false);

  const submit = async (e) => {
    e.preventDefault();
    setError(""); setSuccess("");
    if (next !== confirm) { setError("New passwords don't match"); return; }
    setLoading(true);
    try {
      await apiChangePassword(current, next);
      setSuccess("Password changed. You can close this window.");
      setCurrent(""); setNext(""); setConfirm("");
    } catch (err) {
      setError(err.message || "Change failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <div onClick={onClose} style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.35)", zIndex: 200 }} />
      <div style={{ position: "fixed", top: "50%", left: "50%", transform: "translate(-50%,-50%)", zIndex: 201, width: 360, padding: "36px 32px", background: "var(--surface)", borderRadius: 8, boxShadow: "0 8px 40px rgba(0,0,0,0.18)" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24 }}>
          <div style={{ fontFamily: "Bodoni Moda, Georgia, serif", fontSize: 20, color: "var(--ink-1)" }}>Change Password</div>
          <button className="icon-btn" onClick={onClose}><Icon name="close" size={14} /></button>
        </div>
        <form onSubmit={submit}>
          <_FormField label="Current Password" type="password" value={current} onChange={setCurrent} placeholder="••••••••" />
          <_FormField label="New Password" type="password" value={next} onChange={setNext} placeholder="Min. 8 characters" />
          <_FormField label="Confirm New Password" type="password" value={confirm} onChange={setConfirm} placeholder="••••••••" />
          <_AuthError msg={error} />
          <_AuthSuccess msg={success} />
          <button type="submit" disabled={loading} style={{ width: "100%", padding: "11px", background: "var(--accent)", color: "#fff", border: "none", borderRadius: 4, fontSize: 14, fontWeight: 500, cursor: loading ? "not-allowed" : "pointer", opacity: loading ? 0.7 : 1 }}>
            {loading ? "Saving…" : "Update password"}
          </button>
        </form>
      </div>
    </>
  );
}

// ── Sidebar ────────────────────────────────────────────────────────────────

function Sidebar({ page, onNav, onSignOut, onChangePassword }) {
  const email = getEmail() || "";
  const initials = email
    ? email.slice(0, 2).toUpperCase()
    : "?";

  const items = [
    { id: "overview", label: "Overview", icon: "home" },
    { id: "transactions", label: "Transactions", icon: "list" },
    { id: "insights", label: "Insights", icon: "pie" },
    { id: "import", label: "Import", icon: "upload" },
  ];
  const meta = [
    { id: "history", label: "History", icon: "clock" },
    { id: "categories", label: "Categories", icon: "sparkle" },
    { id: "banks", label: "Connected banks", icon: "file" },
  ];
  return (
    <aside className="sidebar">
      <div className="brand">
        <div className="brand-mark">B</div>
        <div>
          <div className="brand-name">Bankclaw</div>
          <div className="brand-sub">Private Ledger</div>
        </div>
      </div>

      <div className="nav-group">
        <div className="nav-label">Workspace</div>
        {items.map((i) => (
          <div key={i.id} className={"nav-item" + (page === i.id ? " active" : "")}
            onClick={() => onNav(i.id)}>
            <Icon name={i.icon} size={15} stroke={1.5} />
            <span>{i.label}</span>
          </div>
        ))}
      </div>

      <div className="nav-group">
        <div className="nav-label">Library</div>
        {meta.map((i) => (
          <div key={i.id} className="nav-item" onClick={() => onNav(i.id)}>
            <Icon name={i.icon} size={15} stroke={1.5} />
            <span>{i.label}</span>
          </div>
        ))}
      </div>

      <div className="nav-spacer"></div>

      <div className="user-card">
        <div className="avatar">{initials}</div>
        <div style={{ minWidth: 0, flex: 1 }}>
          <div className="user-name">{email.split("@")[0] || "User"}</div>
          <div className="user-email">{email}</div>
        </div>
        <button
          className="icon-btn" title="Change password"
          onClick={onChangePassword}
          style={{ flexShrink: 0 }}
        >
          <Icon name="settings" size={14} />
        </button>
        <button
          className="icon-btn" title="Sign out"
          onClick={onSignOut}
          style={{ flexShrink: 0 }}
        >
          <Icon name="close" size={14} />
        </button>
      </div>
    </aside>
  );
}

function Topbar({ page, query, setQuery, privacy, setPrivacy, onOpenTweaks, onNav }) {
  const crumbs = {
    overview: ["Workspace", "Overview"],
    transactions: ["Workspace", "Transactions"],
    insights: ["Workspace", "Insights"],
    import: ["Workspace", "Import"],
    history: ["Library", "History"],
    categories: ["Library", "Categories"],
    banks: ["Library", "Connected banks"],
  }[page] || ["Workspace", page];
  return (
    <div className="topbar">
      <div className="crumbs">{crumbs[0]} · <b>{crumbs[1]}</b></div>
      <div className="spacer"></div>
      <div className="search">
        <Icon name="search" size={14} />
        <input placeholder="Search transactions, merchants, references…"
          value={query} onChange={(e) => { setQuery(e.target.value); if (page !== "transactions") onNav("transactions"); }} />
        <kbd>⌘K</kbd>
      </div>
      <button className="icon-btn" title={privacy ? "Reveal amounts" : "Hide amounts"} onClick={() => setPrivacy(!privacy)}>
        <Icon name={privacy ? "eyeOff" : "eye"} size={15} />
      </button>
      <button className="btn primary" onClick={() => onNav("import")}>
        <Icon name="plus" size={12} stroke={2.2} /> Import
      </button>
    </div>
  );
}

function Drawer({ tx, onClose, privacy, onChanged, availableCategories = [] }) {
  const { useState: useStateD } = React;
  const [picking, setPicking] = useStateD(false);
  const [busy, setBusy] = useStateD(false);
  const [err, setErr] = useStateD("");
  const open = !!tx;
  const cat = tx && getCatInfo(tx.category);
  const bank = tx && BANKS.find((b) => b.id === tx.bank);

  // Pass either a built-in id ("food") or a custom category name ("Investment")
  const handleRecategorise = async (idOrName) => {
    if (!tx) return;
    setBusy(true); setErr("");
    try {
      await apiUpdateCategory(tx, idOrName);
      setPicking(false);
      if (onChanged) await onChanged();
      onClose();
    } catch (e) {
      setErr(e.message || "Update failed");
    } finally {
      setBusy(false);
    }
  };

  const handleDelete = async () => {
    if (!tx || !window.confirm("Delete this transaction? This cannot be undone.")) return;
    setBusy(true); setErr("");
    try {
      const raw = tx._raw || {};
      await apiDeleteTransactions([{
        date: raw.date, description: raw.description,
        amount: raw.amount, bank: raw.bank,
      }]);
      if (onChanged) await onChanged();
      onClose();
    } catch (e) {
      setErr(e.message || "Delete failed");
    } finally {
      setBusy(false);
    }
  };
  return (
    <>
      <div className={"drawer-backdrop" + (open ? " open" : "")} onClick={onClose}></div>
      <div className={"drawer" + (open ? " open" : "")}>
        <div className="drawer-hd">
          <div>
            <div className="page-kicker" style={{ margin: 0 }}>Transaction</div>
            <div className="display" style={{ fontSize: 22 }}>{tx?.description || ""}</div>
          </div>
          <button className="icon-btn" onClick={onClose}><Icon name="close" size={14} /></button>
        </div>
        <div className="drawer-body">
          {tx && (
            <>
              <div style={{ padding: "12px 0 24px", borderBottom: "1px solid var(--rule)" }}>
                <div className="tag">Amount</div>
                <div className={"display tnum " + (tx.amount > 0 ? "" : "")} style={{
                  fontSize: 52, lineHeight: 1, marginTop: 4,
                  color: tx.amount > 0 ? "var(--credit)" : "var(--debit)",
                  filter: privacy ? "blur(10px)" : "none",
                }}>
                  {fmtSGD(tx.amount, privacy)}
                </div>
              </div>

              <div className="kv">
                <div className="k">Date</div><div>{fmtDate(tx.date, { long: true })}</div>
                <div className="k">Bank</div>
                <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                  <span style={{ width: 18, height: 18, borderRadius: 3, background: bank.color, display: "inline-block" }}></span>
                  {bank.name}
                </div>
                <div className="k">Category</div>
                <div>
                  <span className="chip" style={{ cursor: "default" }}>
                    {cat.glyph} {cat.name}
                  </span>
                </div>
                <div className="k">Reference</div>
                <div className="mono" style={{ fontSize: 12 }}>{tx.reference}</div>
                <div className="k">Statement</div>
                <div className="mono" style={{ fontSize: 12 }}>{bank.id}-{new Date(tx.date).toISOString().slice(0,7)}.pdf</div>
              </div>

              <div style={{ padding: "18px 0", borderBottom: "1px solid var(--rule)" }}>
                <div className="tag" style={{ marginBottom: 10 }}>AI summary</div>
                <div style={{ fontSize: 13, color: "var(--ink-2)", lineHeight: 1.6 }}>
                  {tx.amount > 0
                    ? `Credit matched to "${cat.name}" with high confidence.`
                    : `Categorised as ${cat.name}.`}
                </div>
              </div>

              {picking && (() => {
                // Merge built-ins (with ids) + customs (name only)
                const builtIns = CATEGORIES.map((c) => ({ key: c.id, label: `${c.glyph} ${c.name}`, value: c.id, name: c.name }));
                const builtInNames = new Set(CATEGORIES.map((c) => c.name));
                const customs = (availableCategories || [])
                  .filter((c) => c && c.custom && !builtInNames.has(c.name))
                  .map((c) => ({ key: `custom-${c.name}`, label: `${c.glyph || "•"} ${c.name}`, value: c.name, name: c.name }));
                const all = [...builtIns, ...customs];
                return (
                  <div style={{ padding: "14px 0", borderBottom: "1px solid var(--rule)" }}>
                    <div className="tag" style={{ marginBottom: 10 }}>Choose new category</div>
                    <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                      {all.map((c) => (
                        <button
                          key={c.key}
                          className="chip"
                          disabled={busy}
                          onClick={() => handleRecategorise(c.value)}
                          style={{
                            cursor: busy ? "not-allowed" : "pointer",
                            opacity: busy ? 0.5 : 1,
                            background: cat && c.name === cat.name ? "var(--paper-2)" : "transparent",
                          }}
                        >
                          {c.label}
                        </button>
                      ))}
                    </div>
                  </div>
                );
              })()}

              {err && (
                <div style={{ padding: "10px 12px", marginTop: 12, background: "var(--paper-2)", color: "var(--debit)", fontSize: 12, borderRadius: 4 }}>
                  {err}
                </div>
              )}

              <div style={{ display: "flex", gap: 8, marginTop: 18 }}>
                <button className="btn" disabled={busy} onClick={() => setPicking((p) => !p)}>
                  {picking ? "Cancel" : "Recategorise"}
                </button>
                <button className="btn ghost" disabled={busy} onClick={handleDelete} style={{ marginLeft: "auto", color: "var(--debit)" }}>
                  Delete
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </>
  );
}

function TweaksPanel({ open, onClose, state, setState, saveState }) {
  const set = (k, v) => { const next = { ...state, [k]: v }; setState(next); saveState(next); };
  return (
    <div className={"tweaks" + (open ? " open" : "")}>
      <div className="tweaks-hd">
        <h4>Tweaks</h4>
        <button className="icon-btn" style={{ width: 26, height: 26 }} onClick={onClose}><Icon name="close" size={12} /></button>
      </div>
      <div className="tweaks-body">
        <div className="tw-row">
          <div className="lab">Theme</div>
          <div className="tw-opts">
            {[["paper","Paper"],["noir","Noir"]].map(([k,v]) => (
              <button key={k} className={(state.theme || "paper") === k ? "on" : ""} onClick={() => set("theme", k)}>{v}</button>
            ))}
          </div>
        </div>

        <div className="tw-row">
          <div className="lab">Density</div>
          <div className="tw-opts">
            {["comfortable","compact"].map((d) => (
              <button key={d} className={state.density === d ? "on" : ""} onClick={() => set("density", d)}>
                {d[0].toUpperCase()+d.slice(1)}
              </button>
            ))}
          </div>
        </div>

        <div className="tw-row">
          <div className="lab">Accent</div>
          <div className="tw-swatches">
            {Object.entries(ACCENTS).map(([k, v]) => (
              <div key={k} className={"tw-sw" + (state.accent === k ? " on" : "")}
                style={{ background: v.swatch }} onClick={() => set("accent", k)} title={v.name}></div>
            ))}
          </div>
        </div>

        <div className="tw-row">
          <div className="lab">Privacy mode</div>
          <div className="tw-opts">
            <button className={!state.privacy ? "on" : ""} onClick={() => set("privacy", false)}>Off</button>
            <button className={state.privacy ? "on" : ""} onClick={() => set("privacy", true)}>Blurred</button>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ============ ROOT APP ============ */
function App() {
  const [authed, setAuthed] = useStateApp(isLoggedIn());
  const [transactions, setTransactions] = useStateApp([]);
  const [txLoading, setTxLoading] = useStateApp(false);
  const [allCategories, setAllCategories] = useStateApp([]); // [{ id?, name, glyph }] built-ins + custom

  const [tweaks, setTweaks] = useStateApp(() => {
    try { const s = JSON.parse(localStorage.getItem("bc_tweaks") || "null"); if (s) return { ...TWEAK_DEFAULTS, ...s }; } catch {}
    return TWEAK_DEFAULTS;
  });
  const saveTweaks = (t) => localStorage.setItem("bc_tweaks", JSON.stringify(t));

  const [page, setPage] = useStateApp(() => localStorage.getItem("bc_page") || "overview");
  useEffectApp(() => localStorage.setItem("bc_page", page), [page]);

  const [query, setQuery] = useStateApp("");
  const [openTx, setOpenTx] = useStateApp(null);
  const [tweaksOpen, setTweaksOpen] = useStateApp(false);
  const [editMode, setEditMode] = useStateApp(false);
  const [changePasswordOpen, setChangePasswordOpen] = useStateApp(false);

  const loadTransactions = useCallbackApp(async () => {
    setTxLoading(true);
    try {
      const txs = await apiFetchTransactions();
      setTransactions(txs);
      // keep global TRANSACTIONS in sync for any legacy helpers that read window.TRANSACTIONS
      window.TRANSACTIONS = txs;
    } catch {}
    setTxLoading(false);
  }, []);

  const loadCategories = useCallbackApp(async () => {
    try {
      const cats = await apiFetchCategories();
      setAllCategories(cats);
      window.ALL_CATEGORIES = cats; // used by getCatInfo() to resolve custom categories
    } catch {}
  }, []);

  // Load transactions + categories on first authed render
  useEffectApp(() => {
    if (authed) { loadTransactions(); loadCategories(); }
  }, [authed]);

  // Listen for 401 logout events from api.js
  useEffectApp(() => {
    const handler = () => { setAuthed(false); setTransactions([]); };
    window.addEventListener("bc:logout", handler);
    return () => window.removeEventListener("bc:logout", handler);
  }, []);

  // Apply accent + density to root
  useEffectApp(() => {
    const acc = ACCENTS[tweaks.accent] || ACCENTS.copper;
    document.documentElement.style.setProperty("--accent", acc.css);
    document.documentElement.style.setProperty("--accent-2", acc.css2);
    document.documentElement.setAttribute("data-density", tweaks.density);
    document.documentElement.setAttribute("data-privacy", tweaks.privacy ? "on" : "off");
    document.documentElement.setAttribute("data-theme", tweaks.theme || "paper");
  }, [tweaks]);

  // Edit-mode protocol
  useEffectApp(() => {
    const handler = (e) => {
      if (e.data?.type === "__activate_edit_mode") { setEditMode(true); setTweaksOpen(true); }
      if (e.data?.type === "__deactivate_edit_mode") { setEditMode(false); setTweaksOpen(false); }
    };
    window.addEventListener("message", handler);
    window.parent.postMessage({ type: "__edit_mode_available" }, "*");
    return () => window.removeEventListener("message", handler);
  }, []);

  const persistTweaks = (t) => {
    saveTweaks(t);
    try { window.parent.postMessage({ type: "__edit_mode_set_keys", edits: t }, "*"); } catch {}
  };

  const handleSignOut = async () => {
    await apiLogout();
    setAuthed(false);
    setTransactions([]);
    window.TRANSACTIONS = [];
  };

  const navigate = (p) => { setPage(p); setOpenTx(null); };

  if (!authed) {
    return <LoginPage onLogin={() => { setAuthed(true); }} />;
  }

  return (
    <div className="app">
      <Sidebar page={page} onNav={navigate} onSignOut={handleSignOut} onChangePassword={() => setChangePasswordOpen(true)} />
      <main className="main">
        <Topbar page={page} query={query} setQuery={setQuery}
          privacy={tweaks.privacy}
          setPrivacy={(v) => { const t = { ...tweaks, privacy: v }; setTweaks(t); saveTweaks(t); }}
          onOpenTweaks={() => setTweaksOpen(true)} onNav={navigate} />

        {page === "overview" && <OverviewPage transactions={transactions} privacy={tweaks.privacy} onNav={navigate} onOpenTx={setOpenTx} />}
        {page === "transactions" && <TransactionsPage transactions={transactions} privacy={tweaks.privacy} query={query} onOpenTx={setOpenTx} availableCategories={allCategories} />}
        {page === "insights" && <InsightsPage transactions={transactions} privacy={tweaks.privacy} />}
        {page === "import" && <ImportPage privacy={tweaks.privacy} onNav={navigate} onImportDone={loadTransactions} />}
        {page === "history" && <HistoryPage transactions={transactions} privacy={tweaks.privacy} onOpenTx={setOpenTx} />}
        {page === "categories" && <CategoriesPage transactions={transactions} privacy={tweaks.privacy} availableCategories={allCategories} reloadCategories={loadCategories} />}
        {page === "banks" && <BanksPage transactions={transactions} privacy={tweaks.privacy} onNav={navigate} />}
      </main>

      <Drawer tx={openTx} onClose={() => setOpenTx(null)} privacy={tweaks.privacy} onChanged={loadTransactions} availableCategories={allCategories} />

      {editMode && (
        <TweaksPanel open={tweaksOpen} onClose={() => setTweaksOpen(false)}
          state={tweaks} setState={setTweaks} saveState={persistTweaks} />
      )}

      {changePasswordOpen && <ChangePasswordModal onClose={() => setChangePasswordOpen(false)} />}

      {txLoading && (
        <div style={{ position: "fixed", bottom: 20, right: 20, padding: "8px 14px", background: "var(--surface)", border: "1px solid var(--rule)", borderRadius: 6, fontSize: 12, color: "var(--ink-3)", boxShadow: "0 2px 12px rgba(0,0,0,0.08)" }}>
          Loading transactions…
        </div>
      )}
    </div>
  );
}

// ── History page ────────────────────────────────────────────────────────────
// Transactions grouped by bank × month — shows the "statement view"

function HistoryPage({ transactions, privacy, onOpenTx }) {
  const { useMemo: useMemoH, useState: useStateH } = React;
  const [expanded, setExpanded] = useStateH({});

  const statements = useMemoH(() => {
    const map = new Map();
    transactions.forEach((t) => {
      const month = t.date.slice(0, 7); // "YYYY-MM"
      const key = `${t.bank}__${month}`;
      if (!map.has(key)) map.set(key, { bank: t.bank, month, txs: [], income: 0, spend: 0 });
      const s = map.get(key);
      s.txs.push(t);
      if (t.amount > 0) s.income += t.amount; else s.spend += -t.amount;
    });
    // sort transactions within each statement desc by date
    for (const s of map.values()) {
      s.txs.sort((a, b) => new Date(b.date) - new Date(a.date));
    }
    return [...map.values()].sort((a, b) => b.month.localeCompare(a.month) || a.bank.localeCompare(b.bank));
  }, [transactions]);

  const toggle = (key) => setExpanded((e) => ({ ...e, [key]: !e[key] }));

  return (
    <div className="page">
      <div className="page-kicker">Library</div>
      <h1 className="page-title"><i>History.</i></h1>
      <div className="page-sub">{statements.length} statement{statements.length !== 1 ? "s" : ""} across {new Set(transactions.map(t => t.bank)).size} banks.</div>
      <div style={{ height: 28 }} />

      {transactions.length === 0 && (
        <div className="panel panel-pad" style={{ textAlign: "center", padding: "80px 32px" }}>
          <div style={{ fontFamily: "Instrument Serif, serif", fontSize: 22, color: "var(--ink-3)" }}>No statements yet.</div>
          <div style={{ fontSize: 13, color: "var(--ink-4)", marginTop: 8 }}>Import a PDF to see your statement history.</div>
        </div>
      )}

      {statements.map((s) => {
        const bank = BANKS.find((b) => b.id === s.bank);
        const monthLabel = new Date(s.month + "-01").toLocaleDateString("en-GB", { month: "long", year: "numeric" });
        const key = `${s.bank}-${s.month}`;
        const isOpen = !!expanded[key];
        const visibleTxs = isOpen ? s.txs : s.txs.slice(0, 5);
        const hiddenCount = s.txs.length - 5;
        return (
          <div key={key} className="panel" style={{ marginBottom: 16 }}>
            <div className="panel-hd">
              <h3 style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <span style={{ width: 10, height: 10, borderRadius: 2, background: bank?.color, display: "inline-block" }}></span>
                {bank?.name} · {monthLabel}
              </h3>
              <div className="tools" style={{ gap: 18, fontSize: 12, color: "var(--ink-3)" }}>
                <span>{s.txs.length} transactions</span>
                <span style={{ color: "var(--credit)" }}>+{fmtSGD(s.income, privacy)}</span>
                <span style={{ color: "var(--debit)" }}>{fmtSGD(-s.spend, privacy)}</span>
              </div>
            </div>
            <div className="ledger">
              {visibleTxs.map((t) => {
                const cat = getCatInfo(t.category);
                return (
                  <div key={t.id} className="row" onClick={() => onOpenTx(t)}>
                    <div className="cell mono" style={{ color: "var(--ink-3)", fontSize: 12 }}>{fmtDate(t.date)}</div>
                    <div className="cell desc"><div>{t.description}</div></div>
                    <div className="cell num" style={{ justifyContent: "flex-end", color: "var(--ink-3)", fontSize: 12 }}>
                      {cat?.glyph} {cat?.name}
                    </div>
                    <div className={"cell num amt " + (t.amount > 0 ? "credit" : "debit")}>{fmtSGD(t.amount, privacy)}</div>
                  </div>
                );
              })}
              {hiddenCount > 0 && (
                <button
                  onClick={() => toggle(key)}
                  style={{
                    width: "100%", padding: "12px 20px", fontSize: 12,
                    color: "var(--accent)", borderTop: "1px solid var(--rule)",
                    background: "transparent", border: "none", borderTop: "1px solid var(--rule)",
                    cursor: "pointer", textAlign: "center", fontWeight: 500,
                  }}
                >
                  {isOpen ? "Show less" : `Show all ${s.txs.length} transactions`}
                </button>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ── Categories page ──────────────────────────────────────────────────────────

const _EMOJI_PALETTE = [
  "💰","💼","📈","📊","🏦","🏠","🏥","🎓","🎁","🎉",
  "💡","🔧","🛠","🚗","🚌","✈","⛵","🏖","🎮","🎵",
  "📱","💻","📚","✏","✂","🌱","🐾","☕","🍷","🍕",
  "👶","👨‍👩‍👧","💊","🧘","🏋","🎨","🛒","💳","📦","•",
];

function CategoriesPage({ transactions, privacy, availableCategories = [], reloadCategories }) {
  const { useState: useStateCAT, useMemo: useMemoCAT } = React;
  const [newCat, setNewCat] = useStateCAT("");
  const [newGlyph, setNewGlyph] = useStateCAT("💰");
  const [showPalette, setShowPalette] = useStateCAT(false);
  const [saving, setSaving] = useStateCAT(false);
  const [error, setError] = useStateCAT("");
  const [editing, setEditing] = useStateCAT(null); // { name, draftName, draftGlyph, paletteOpen }
  const [editError, setEditError] = useStateCAT("");

  const customCats = useMemoCAT(() => {
    const defaults = new Set(CATEGORIES.map(c => c.name));
    return (availableCategories || []).filter(c => c && !defaults.has(c.name));
  }, [availableCategories]);

  const spending = useMemoCAT(() => spendByCategory(transactions), [transactions]);
  const topSpend = spending[0]?.total || 1;

  const addCat = async (e) => {
    e.preventDefault();
    const name = newCat.trim();
    if (!name) return;
    setSaving(true); setError("");
    try {
      await apiAddCategory(name, newGlyph);
      setNewCat(""); setNewGlyph("💰"); setShowPalette(false);
      if (reloadCategories) await reloadCategories();
    } catch (err) {
      setError(err.message || "Failed to add");
    } finally {
      setSaving(false);
    }
  };

  const startEdit = (c) => {
    setEditError("");
    setEditing({ name: c.name, draftName: c.name, draftGlyph: c.glyph || "•", paletteOpen: false });
  };

  const cancelEdit = () => { setEditing(null); setEditError(""); };

  const saveEdit = async () => {
    if (!editing) return;
    const draftName = editing.draftName.trim();
    if (!draftName) { setEditError("Name cannot be blank"); return; }
    setSaving(true); setEditError("");
    try {
      await apiRenameCategory(editing.name, { name: draftName, glyph: editing.draftGlyph });
      setEditing(null);
      if (reloadCategories) await reloadCategories();
    } catch (err) {
      setEditError(err.message || "Failed to save");
    } finally {
      setSaving(false);
    }
  };

  const removeCat = async (name) => {
    try {
      await apiDeleteCategory(name);
      if (reloadCategories) await reloadCategories();
    } catch {}
  };

  return (
    <div className="page">
      <div className="page-kicker">Library</div>
      <h1 className="page-title"><i>Categories.</i></h1>
      <div className="page-sub">Ten built-in categories plus your custom tags. Spending totals across all time.</div>
      <div style={{ height: 28 }} />

      <div className="grid-2">
        <div className="panel">
          <div className="panel-hd"><h3>Built-in categories</h3></div>
          <div className="panel-pad" style={{ paddingTop: 8 }}>
            {CATEGORIES.map((cat) => {
              const s = spending.find(r => r.id === cat.id);
              const pct = s ? Math.round((s.total / topSpend) * 100) : 0;
              return (
                <div key={cat.id} className="cat-row" style={{ paddingTop: 10, paddingBottom: 10 }}>
                  <span className="cat-glyph">{cat.glyph}</span>
                  <div style={{ flex: 1 }}>
                    <div className="cat-name">{cat.name}</div>
                    {s && <div className="cat-bar" style={{ "--w": `${pct}%`, marginTop: 4 }}></div>}
                  </div>
                  <div className="cat-amt" style={{ fontSize: 13 }}>
                    {s ? fmtSGD(-s.total, privacy).replace("−","") : "—"}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        <div className="panel">
          <div className="panel-hd"><h3>Custom categories</h3></div>
          <div className="panel-pad">
            <form onSubmit={addCat} style={{ marginBottom: 20 }}>
              <div style={{ display: "flex", gap: 8 }}>
                <button
                  type="button"
                  onClick={() => setShowPalette((v) => !v)}
                  title="Choose icon"
                  style={{ width: 44, fontSize: 20, padding: "8px 0", border: "1px solid var(--rule)", borderRadius: 4, background: "var(--paper)", cursor: "pointer" }}
                >
                  {newGlyph}
                </button>
                <input
                  value={newCat} onChange={(e) => setNewCat(e.target.value)}
                  placeholder="e.g. Gym, Hobbies, Kids…"
                  style={{ flex: 1, padding: "8px 10px", border: "1px solid var(--rule)", borderRadius: 4, background: "var(--paper)", color: "var(--ink-1)", fontSize: 13 }}
                />
                <button type="submit" className="btn primary" disabled={saving || !newCat.trim()}>Add</button>
              </div>
              {showPalette && (
                <div style={{ marginTop: 10, padding: 10, background: "var(--paper-2)", border: "1px solid var(--rule)", borderRadius: 4, display: "grid", gridTemplateColumns: "repeat(10, 1fr)", gap: 4 }}>
                  {_EMOJI_PALETTE.map((g) => (
                    <button
                      key={g}
                      type="button"
                      onClick={() => { setNewGlyph(g); setShowPalette(false); }}
                      style={{
                        fontSize: 18, padding: 6, border: "none", borderRadius: 4, cursor: "pointer",
                        background: g === newGlyph ? "var(--paper-3)" : "transparent",
                      }}
                    >
                      {g}
                    </button>
                  ))}
                </div>
              )}
            </form>
            {error && <div style={{ marginBottom: 12, fontSize: 12, color: "var(--debit)" }}>{error}</div>}

            {customCats.length === 0 && (
              <div style={{ fontSize: 13, color: "var(--ink-4)", padding: "24px 0", textAlign: "center" }}>
                No custom categories yet. Add one above.
              </div>
            )}
            {customCats.map((c) => {
              const s = spending.find((r) => r.id === c.name);
              const pct = s ? Math.round((s.total / topSpend) * 100) : 0;
              const isEditing = editing && editing.name === c.name;

              if (isEditing) {
                return (
                  <div key={c.name} style={{ padding: "10px 0", borderBottom: "1px solid var(--rule)" }}>
                    <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                      <button
                        type="button"
                        onClick={() => setEditing((e) => ({ ...e, paletteOpen: !e.paletteOpen }))}
                        title="Choose icon"
                        style={{ width: 44, fontSize: 20, padding: "8px 0", border: "1px solid var(--rule)", borderRadius: 4, background: "var(--paper)", cursor: "pointer" }}
                      >
                        {editing.draftGlyph}
                      </button>
                      <input
                        value={editing.draftName}
                        onChange={(ev) => setEditing((e) => ({ ...e, draftName: ev.target.value }))}
                        autoFocus
                        style={{ flex: 1, padding: "8px 10px", border: "1px solid var(--rule)", borderRadius: 4, background: "var(--paper)", color: "var(--ink-1)", fontSize: 13 }}
                      />
                      <button className="btn primary" disabled={saving} onClick={saveEdit}>Save</button>
                      <button className="btn ghost" disabled={saving} onClick={cancelEdit}>Cancel</button>
                    </div>
                    {editing.paletteOpen && (
                      <div style={{ marginTop: 10, padding: 10, background: "var(--paper-2)", border: "1px solid var(--rule)", borderRadius: 4, display: "grid", gridTemplateColumns: "repeat(10, 1fr)", gap: 4 }}>
                        {_EMOJI_PALETTE.map((g) => (
                          <button
                            key={g}
                            type="button"
                            onClick={() => setEditing((e) => ({ ...e, draftGlyph: g, paletteOpen: false }))}
                            style={{
                              fontSize: 18, padding: 6, border: "none", borderRadius: 4, cursor: "pointer",
                              background: g === editing.draftGlyph ? "var(--paper-3)" : "transparent",
                            }}
                          >
                            {g}
                          </button>
                        ))}
                      </div>
                    )}
                    {editError && <div style={{ marginTop: 8, fontSize: 12, color: "var(--debit)" }}>{editError}</div>}
                  </div>
                );
              }

              return (
                <div key={c.name} className="cat-row" style={{ paddingTop: 10, paddingBottom: 10 }}>
                  <span className="cat-glyph">{c.glyph || "•"}</span>
                  <div style={{ flex: 1 }}>
                    <div className="cat-name">{c.name}</div>
                    {s && <div className="cat-bar" style={{ "--w": `${pct}%`, marginTop: 4 }}></div>}
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                    <div className="cat-amt" style={{ fontSize: 13 }}>
                      {s ? fmtSGD(-s.total, privacy).replace("−", "") : "—"}
                    </div>
                    <button className="btn ghost" style={{ fontSize: 12 }} onClick={() => startEdit(c)}>Edit</button>
                    <button className="btn ghost" style={{ fontSize: 12, color: "var(--debit)" }} onClick={() => removeCat(c.name)}>Remove</button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Connected banks page ─────────────────────────────────────────────────────

function BanksPage({ transactions, privacy, onNav }) {
  const { useMemo: useMemoB } = React;

  const bankStats = useMemoB(() => {
    const map = new Map();
    transactions.forEach((t) => {
      if (!map.has(t.bank)) map.set(t.bank, { id: t.bank, count: 0, income: 0, spend: 0, latest: "" });
      const s = map.get(t.bank);
      s.count++;
      if (t.amount > 0) s.income += t.amount; else s.spend += -t.amount;
      if (!s.latest || t.date > s.latest) s.latest = t.date;
    });
    return [...map.values()].sort((a, b) => b.count - a.count);
  }, [transactions]);

  return (
    <div className="page">
      <div className="page-kicker">Library</div>
      <h1 className="page-title"><i>Connected banks.</i></h1>
      <div className="page-sub">{bankStats.length} bank{bankStats.length !== 1 ? "s" : ""} with transaction data. Import more statements to add banks.</div>
      <div style={{ height: 28 }} />

      {bankStats.length === 0 && (
        <div className="panel panel-pad" style={{ textAlign: "center", padding: "80px 32px" }}>
          <div style={{ fontFamily: "Instrument Serif, serif", fontSize: 22, color: "var(--ink-3)" }}>No banks yet.</div>
          <div style={{ fontSize: 13, color: "var(--ink-4)", marginTop: 8 }}>Import a PDF to see your banks here.</div>
          <button className="btn primary" style={{ marginTop: 20 }} onClick={() => onNav("import")}>
            <Icon name="upload" size={14} /> Import statement
          </button>
        </div>
      )}

      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        {bankStats.map((s) => {
          const bank = BANKS.find((b) => b.id === s.id);
          return (
            <div key={s.id} className="panel panel-pad" style={{ display: "grid", gridTemplateColumns: "auto 1fr auto", gap: 20, alignItems: "center" }}>
              <div style={{ width: 44, height: 44, borderRadius: 8, background: bank?.color, display: "flex", alignItems: "center", justifyContent: "center", color: "#fff", fontFamily: "Instrument Serif, serif", fontSize: 15 }}>
                {bank?.short}
              </div>
              <div>
                <div style={{ fontSize: 15, fontWeight: 500 }}>{bank?.name}</div>
                <div style={{ fontSize: 12, color: "var(--ink-3)", marginTop: 3 }}>
                  {s.count} transactions · last {fmtDate(s.latest)}
                </div>
                <div style={{ fontSize: 12, color: "var(--ink-4)", marginTop: 2 }}>
                  <span style={{ color: "var(--credit)" }}>+{fmtSGD(s.income, privacy)}</span>
                  {" · "}
                  <span style={{ color: "var(--debit)" }}>{fmtSGD(-s.spend, privacy)}</span>
                </div>
              </div>
              <div style={{ textAlign: "right" }}>
                <button className="btn" onClick={() => onNav("import")}>
                  <Icon name="upload" size={13} /> Import
                </button>
              </div>
            </div>
          );
        })}
      </div>

      <div style={{ height: 28 }} />
      <div className="panel panel-pad" style={{ background: "oklch(0.97 0.01 35)" }}>
        <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
          <Icon name="file" size={16} />
          <div>
            <div style={{ fontSize: 14, fontWeight: 500 }}>Add another bank</div>
            <div style={{ fontSize: 12, color: "var(--ink-3)" }}>18 bank layouts supported — DBS, OCBC, UOB, Chase, SC, Maybank, HSBC, and more.</div>
          </div>
          <button className="btn primary" style={{ marginLeft: "auto", flexShrink: 0 }} onClick={() => onNav("import")}>
            <Icon name="plus" size={13} /> Import PDF
          </button>
        </div>
      </div>
    </div>
  );
}

Object.assign(window, { App, LoginPage, Sidebar, Topbar, Drawer, TweaksPanel, HistoryPage, CategoriesPage, BanksPage });

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

// ── Google sign-in button ──────────────────────────────────────────────────
// Renders Google's official button via GIS. Falls back to a disabled stub
// if the client ID env var is unset (shows a hint for the operator).
function GoogleSignInButton({ onLogin, onError, width = 280 }) {
  const ref = React.useRef(null);
  const [configured, setConfigured] = useStateApp(null); // null = loading

  React.useEffect(() => {
    let cancelled = false;
    (async () => {
      const cfg = await apiFetchPublicConfig();
      if (cancelled) return;
      if (!cfg.google_client_id) { setConfigured(false); return; }
      const tryRender = () => {
        if (!window.google?.accounts?.id || !ref.current) return false;
        window.google.accounts.id.initialize({
          client_id: cfg.google_client_id,
          callback: async (resp) => {
            try {
              await apiGoogleLogin(resp.credential);
              onLogin && onLogin();
            } catch (e) {
              onError && onError(e.message || "Google sign-in failed");
            }
          },
        });
        window.google.accounts.id.renderButton(ref.current, {
          theme: "outline", size: "large", type: "standard",
          text: "continue_with", shape: "rectangular", width,
        });
        setConfigured(true);
        return true;
      };
      if (!tryRender()) {
        const iv = setInterval(() => { if (tryRender()) clearInterval(iv); }, 200);
        setTimeout(() => clearInterval(iv), 8000);
      }
    })();
    return () => { cancelled = true; };
  }, [width]);

  if (configured === false) {
    return (
      <div style={{ fontSize: 11, color: "var(--ink-4)", textAlign: "center", padding: "10px 0" }}>
        Google sign-in not configured — set <code>GOOGLE_CLIENT_ID</code> env var.
      </div>
    );
  }
  return <div ref={ref} style={{ display: "flex", justifyContent: "center" }} />;
}

function LoginPage({ onLogin, initialMode = "login", onBackHome }) {
  const [mode, setMode] = useStateApp(initialMode === "signup" ? "login" : initialMode); // login | reset
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

  const cardStyle = { width: 360, maxWidth: "calc(100vw - 32px)", padding: "48px 40px", background: "var(--surface)", borderRadius: 8, boxShadow: "0 2px 24px rgba(0,0,0,0.08)" };

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
          <>
            <div style={{ marginBottom: 18 }}>
              <GoogleSignInButton onLogin={onLogin} onError={setError} width={280} />
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 16 }}>
              <div style={{ flex: 1, height: 1, background: "var(--rule)" }} />
              <div style={{ fontSize: 10, letterSpacing: "0.2em", color: "var(--ink-4)", textTransform: "uppercase" }}>or email</div>
              <div style={{ flex: 1, height: 1, background: "var(--rule)" }} />
            </div>
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
          </>
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

        {onBackHome && (
          <div style={{ marginTop: 24, textAlign: "center" }}>
            <button type="button" onClick={onBackHome} style={{ background: "none", border: "none", fontSize: 11, color: "var(--ink-4)", cursor: "pointer" }}>
              ← Back to home
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

// ── Landing page ───────────────────────────────────────────────────────────

// Deterministic mock data generators for the demo previews
function _buildMockDailyFlow(days = 30) {
  const end = new Date();
  const out = [];
  for (let i = days - 1; i >= 0; i--) {
    const d = new Date(end); d.setDate(d.getDate() - i); d.setHours(0, 0, 0, 0);
    // deterministic pseudo-random pattern
    const seed = (i * 7919) % 101;
    const dayOfMonth = d.getDate();
    const income = dayOfMonth === 1 || dayOfMonth === 15 ? 5200 + (seed * 4) : (seed < 12 ? 80 + seed * 6 : 0);
    const spend = 45 + (seed % 180) + (dayOfMonth % 7 === 0 ? 220 : 0);
    out.push({ date: d, income, spend });
  }
  return out;
}

function _buildMockMonthlyBars() {
  const base = [
    { label: "Oct", income: 8200, spend: 9100 },
    { label: "Nov", income: 11400, spend: 8300 },
    { label: "Dec", income: 7800, spend: 14600 },
    { label: "Jan", income: 14200, spend: 15100 },
    { label: "Feb", income: 19800, spend: 17500 },
    { label: "Mar", income: 18300, spend: 21200 },
  ];
  return base;
}

function _buildMockRingSegments() {
  // Mix of built-in + custom-sounding tags
  return [
    { id: "tax",         value: 7510.35, color: "oklch(0.45 0.09 155)", cat: { name: "Tax" } },
    { id: "loan",        value: 6000.00, color: "oklch(0.48 0.15 30)",  cat: { name: "Loan" } },
    { id: "food",        value: 4634.10, color: "oklch(0.52 0.09 240)", cat: { name: "Food & Dining" } },
    { id: "travel",      value: 4120.78, color: "oklch(0.68 0.12 85)",  cat: { name: "Travel" } },
    { id: "insurance",   value: 2795.12, color: "oklch(0.55 0.14 305)", cat: { name: "Insurance" } },
    { id: "shopping",    value: 2716.82, color: "oklch(0.60 0.10 195)", cat: { name: "Shopping" } },
    { id: "investment",  value: 2000.00, color: "oklch(0.62 0.10 20)",  cat: { name: "Investment" } },
    { id: "charging",    value: 1964.02, color: "oklch(0.55 0.08 140)", cat: { name: "Charging&Parking" } },
    { id: "utilities",   value: 1189.41, color: "oklch(0.58 0.08 90)",  cat: { name: "Utilities" } },
    { id: "entertain",   value: 512.91,  color: "oklch(0.52 0.05 60)",  cat: { name: "Entertainment" } },
    { id: "transport",   value: 506.88,  color: "oklch(0.50 0.10 150)", cat: { name: "Transport" } },
  ];
}

function LandingPage({ onSignIn }) {
  const navStyle = {
    display: "flex", justifyContent: "space-between", alignItems: "center",
    padding: "20px 48px", borderBottom: "1px solid var(--rule)",
  };
  const brand = { fontFamily: "Bodoni Moda, Georgia, serif", fontSize: 22, color: "var(--ink-1)", letterSpacing: "-0.01em" };

  const sectionPad = { padding: "80px 48px", maxWidth: 1200, margin: "0 auto" };

  return (
    <div style={{ minHeight: "100vh", background: "var(--paper)", color: "var(--ink-1)", fontFamily: "IBM Plex Sans, sans-serif" }}>
      {/* Nav */}
      <div className="landing-nav" style={navStyle}>
        <div style={brand}>Bankclaw</div>
        <div style={{ display: "flex", gap: 10 }}>
          <button className="btn" onClick={onSignIn}>Sign in</button>
        </div>
      </div>

      {/* Hero */}
      <div className="landing-section landing-hero" style={{ ...sectionPad, textAlign: "center", padding: "100px 48px 60px" }}>
        <div style={{ fontSize: 11, letterSpacing: "0.25em", color: "var(--accent)", textTransform: "uppercase", marginBottom: 18 }}>
          ◆ Private Ledger · No tracking
        </div>
        <h1 style={{ fontFamily: "Bodoni Moda, serif", fontSize: 72, lineHeight: 1.05, margin: "0 0 20px", letterSpacing: "-0.02em" }}>
          Your statements, <i style={{ color: "var(--accent)" }}>understood.</i>
        </h1>
        <div className="sub" style={{ fontSize: 18, color: "var(--ink-3)", maxWidth: 620, margin: "0 auto 36px", lineHeight: 1.55 }}>
          Drop a PDF bank statement and get a clean ledger with AI-categorised transactions,
          recurring-charge detection, and editorial-grade spending insights.
          Supports 18 banks across Asia and North America.
        </div>
        <div style={{ display: "flex", justifyContent: "center" }}>
          <button className="btn primary" onClick={onSignIn} style={{ padding: "12px 24px", fontSize: 14 }}>
            Sign in to get started →
          </button>
        </div>

        {/* Mock overview preview */}
        <div className="landing-preview" style={{ marginTop: 64, padding: "24px", background: "var(--surface)", border: "1px solid var(--rule)", borderRadius: 8, boxShadow: "0 30px 80px -40px oklch(0.15 0.01 60 / 0.25)", maxWidth: 1040, margin: "64px auto 0", textAlign: "left" }}>
          <div style={{ fontSize: 10, letterSpacing: "0.2em", color: "var(--ink-4)", marginBottom: 6 }}>LEDGER · APR 2026</div>
          <div style={{ fontFamily: "Bodoni Moda, serif", fontSize: 36, letterSpacing: "-0.01em" }}>
            Good morning, <i style={{ color: "var(--accent)" }}>Taylor.</i>
          </div>
          <div className="stats" style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 16, marginTop: 28 }}>
            {[
              { lab: "Money in", val: "12,840.00", accent: false },
              { lab: "Money out", val: "−7,206.43", accent: false },
              { lab: "Net", val: "+5,633.57", accent: true },
              { lab: "Subscriptions", val: "19", accent: false },
            ].map((s) => (
              <div key={s.lab} style={{ padding: "14px 16px", background: s.accent ? "var(--ink-1)" : "var(--paper-2)", color: s.accent ? "var(--paper)" : "var(--ink-1)", borderRadius: 4 }}>
                <div style={{ fontSize: 10, letterSpacing: "0.18em", opacity: 0.7, marginBottom: 6 }}>{s.lab.toUpperCase()}</div>
                <div style={{ fontFamily: "Bodoni Moda, serif", fontSize: 22, fontWeight: 500 }}>{s.val}</div>
              </div>
            ))}
          </div>

          {/* 30-day cash flow sparkline */}
          <div style={{ marginTop: 24, padding: "18px 20px", background: "var(--paper-2)", borderRadius: 4 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
              <div style={{ fontSize: 11, letterSpacing: "0.18em", color: "var(--ink-3)", textTransform: "uppercase" }}>◆ 30-day cash flow</div>
              <div style={{ fontSize: 11, color: "var(--ink-4)" }}>
                <span style={{ color: "var(--credit)" }}>— IN</span>
                <span style={{ marginLeft: 12, color: "var(--debit)" }}>— OUT</span>
              </div>
            </div>
            <Sparkline data={_buildMockDailyFlow(30)} height={120} />
          </div>
        </div>
      </div>

      {/* Insights preview */}
      <div style={{ ...sectionPad, padding: "40px 48px 20px" }}>
        <div style={{ display: "grid", gridTemplateColumns: "1.2fr 1fr", gap: 20 }}>
          <div style={{ padding: "22px 24px", background: "var(--surface)", border: "1px solid var(--rule)", borderRadius: 8 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 14 }}>
              <div style={{ fontFamily: "Bodoni Moda, serif", fontSize: 22 }}>Cash flow · last 6 months</div>
              <div style={{ fontSize: 11, color: "var(--ink-4)" }}>
                <span style={{ color: "var(--credit)" }}>— IN</span>
                <span style={{ marginLeft: 12, color: "var(--debit)" }}>— OUT</span>
              </div>
            </div>
            <Bars data={_buildMockMonthlyBars()} height={200} />
            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 14, marginTop: 20, paddingTop: 16, borderTop: "1px solid var(--rule)" }}>
              <div>
                <div style={{ fontSize: 10, letterSpacing: "0.18em", color: "var(--ink-4)", textTransform: "uppercase" }}>6-month income</div>
                <div style={{ fontFamily: "Bodoni Moda, serif", fontSize: 20, color: "var(--credit)", marginTop: 4 }}>79,700.00</div>
              </div>
              <div>
                <div style={{ fontSize: 10, letterSpacing: "0.18em", color: "var(--ink-4)", textTransform: "uppercase" }}>6-month spend</div>
                <div style={{ fontFamily: "Bodoni Moda, serif", fontSize: 20, color: "var(--debit)", marginTop: 4 }}>−85,800.00</div>
              </div>
              <div>
                <div style={{ fontSize: 10, letterSpacing: "0.18em", color: "var(--ink-4)", textTransform: "uppercase" }}>Savings rate</div>
                <div style={{ fontFamily: "Bodoni Moda, serif", fontSize: 20, marginTop: 4 }}>−8%</div>
              </div>
            </div>
          </div>

          <div style={{ padding: "22px 24px", background: "var(--surface)", border: "1px solid var(--rule)", borderRadius: 8 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 14 }}>
              <div style={{ fontFamily: "Bodoni Moda, serif", fontSize: 22 }}>Category split</div>
              <div style={{ fontSize: 10, letterSpacing: "0.14em", color: "var(--ink-4)", textTransform: "uppercase" }}>Mock data</div>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 20 }}>
              <Ring segments={_buildMockRingSegments()} size={170} thickness={20} center={
                <div>
                  <div style={{ fontFamily: "Bodoni Moda, serif", fontSize: 24, color: "var(--ink-1)" }}>22%</div>
                  <div style={{ fontSize: 10, letterSpacing: "0.14em", textTransform: "uppercase", color: "var(--ink-4)", marginTop: 3 }}>Tax</div>
                </div>
              } />
              <div style={{ flex: 1, fontSize: 12, color: "var(--ink-2)" }}>
                {_buildMockRingSegments().slice(0, 6).map((s) => (
                  <div key={s.id} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "4px 0" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <span style={{ width: 8, height: 8, borderRadius: 2, background: s.color, display: "inline-block" }}></span>
                      {s.cat.name}
                    </div>
                    <div className="tnum" style={{ color: "var(--ink-3)" }}>{s.value.toLocaleString("en-SG", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* How it works */}
      <div style={{ ...sectionPad, padding: "60px 48px" }}>
        <div style={{ fontSize: 11, letterSpacing: "0.25em", color: "var(--accent)", textTransform: "uppercase", textAlign: "center", marginBottom: 18 }}>
          ◆ How it works
        </div>
        <h2 style={{ fontFamily: "Bodoni Moda, serif", fontSize: 40, textAlign: "center", margin: "0 0 48px", letterSpacing: "-0.01em" }}>
          Three steps, <i>one ledger.</i>
        </h2>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 20 }}>
          {[
            { n: "01", t: "Import", d: "Drop a PDF statement. Bankclaw auto-detects your bank, unlocks password-protected files, runs OCR when needed." },
            { n: "02", t: "Categorise", d: "AI tags every transaction into the right bucket: Food & Dining, Transport, Shopping… or your own custom categories." },
            { n: "03", t: "Understand", d: "Cash-flow trends, recurring charges, top merchants, largest expenses — all in one editorial dashboard." },
          ].map((step) => (
            <div key={step.n} style={{ padding: 28, border: "1px solid var(--rule)", borderRadius: 4, background: "var(--surface)" }}>
              <div style={{ fontFamily: "Bodoni Moda, serif", fontSize: 44, color: "var(--accent)", lineHeight: 1, marginBottom: 12 }}>{step.n}</div>
              <div style={{ fontFamily: "Bodoni Moda, serif", fontSize: 22, marginBottom: 8 }}>{step.t}</div>
              <div style={{ fontSize: 13, color: "var(--ink-3)", lineHeight: 1.6 }}>{step.d}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Features */}
      <div style={{ ...sectionPad, padding: "60px 48px" }}>
        <div style={{ fontSize: 11, letterSpacing: "0.25em", color: "var(--accent)", textTransform: "uppercase", textAlign: "center", marginBottom: 18 }}>
          ◆ Features
        </div>
        <h2 style={{ fontFamily: "Bodoni Moda, serif", fontSize: 40, textAlign: "center", margin: "0 0 48px", letterSpacing: "-0.01em" }}>
          Built for <i>people who care about their books.</i>
        </h2>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 18 }}>
          {[
            { i: "🔒", t: "Private by default", d: "Statements never leave your account. No analytics, no third-party trackers, no selling your data." },
            { i: "🏦", t: "18 bank layouts", d: "DBS/POSB, OCBC, UOB, Chase, HSBC, Standard Chartered, Maybank, and more — credit + debit statements." },
            { i: "🎯", t: "Custom categories", d: "Add your own tags with emojis (Tax, Investment, Loan…) — rename and re-tag transactions freely." },
            { i: "🔁", t: "Recurring detection", d: "Spots subscriptions across months automatically, so you can cancel what you forgot you had." },
            { i: "✍", t: "Manual entries", d: "Log cash, IOUs, or anything that didn't come from a statement — your ledger stays complete." },
            { i: "📤", t: "Full export", d: "Your data is yours. Export clean CSVs anytime, for any range." },
          ].map((f) => (
            <div key={f.t} style={{ padding: 24, borderLeft: "2px solid var(--accent)", background: "var(--paper-2)" }}>
              <div style={{ fontSize: 24, marginBottom: 10 }}>{f.i}</div>
              <div style={{ fontFamily: "Bodoni Moda, serif", fontSize: 19, marginBottom: 6 }}>{f.t}</div>
              <div style={{ fontSize: 13, color: "var(--ink-3)", lineHeight: 1.55 }}>{f.d}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Supported banks */}
      <div style={{ ...sectionPad, padding: "60px 48px" }}>
        <div style={{ fontSize: 11, letterSpacing: "0.25em", color: "var(--accent)", textTransform: "uppercase", textAlign: "center", marginBottom: 18 }}>
          ◆ Supported
        </div>
        <h2 style={{ fontFamily: "Bodoni Moda, serif", fontSize: 40, textAlign: "center", margin: "0 0 14px", letterSpacing: "-0.01em" }}>
          {SUPPORTED_BANKS.length} bank <i>statement layouts.</i>
        </h2>
        <div style={{ textAlign: "center", fontSize: 13, color: "var(--ink-3)", marginBottom: 36 }}>
          Across Singapore, Canada, the US, Switzerland, and more.
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))", gap: 8 }}>
          {SUPPORTED_BANKS.map((b) => (
            <div key={b.name} style={{ padding: "10px 14px", background: "var(--surface)", border: "1px solid var(--rule)", borderRadius: 4, fontSize: 13 }}>
              {b.name}
            </div>
          ))}
        </div>
      </div>

      {/* CTA */}
      <div style={{ ...sectionPad, textAlign: "center", padding: "80px 48px" }}>
        <h2 style={{ fontFamily: "Bodoni Moda, serif", fontSize: 48, margin: "0 0 20px", letterSpacing: "-0.01em" }}>
          Ready for a <i style={{ color: "var(--accent)" }}>private ledger?</i>
        </h2>
        <div style={{ fontSize: 16, color: "var(--ink-3)", marginBottom: 30 }}>
          Free to use. Your data stays with you.
        </div>
        <div style={{ display: "flex", justifyContent: "center" }}>
          <button className="btn primary" onClick={onSignIn} style={{ padding: "14px 28px", fontSize: 15 }}>
            Sign in →
          </button>
        </div>
      </div>

      {/* Footer */}
      <div style={{ borderTop: "1px solid var(--rule)", padding: "24px 48px", display: "flex", justifyContent: "space-between", fontSize: 12, color: "var(--ink-4)" }}>
        <div>© Bankclaw · Private Ledger</div>
        <div>Built on <span style={{ fontStyle: "italic" }}>monopoly-core</span></div>
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
      <div style={{ position: "fixed", top: "50%", left: "50%", transform: "translate(-50%,-50%)", zIndex: 201, width: 360, maxWidth: "calc(100vw - 32px)", padding: "36px 32px", background: "var(--surface)", borderRadius: 8, boxShadow: "0 8px 40px rgba(0,0,0,0.18)" }}>
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

function Sidebar({ page, mode, onMode, onNav, onSignOut, onChangePassword, mobileOpen, onMobileClose }) {
  const email = getEmail() || "";
  const initials = email
    ? email.slice(0, 2).toUpperCase()
    : "?";

  const ledgerItems = [
    { id: "overview", label: "Overview", icon: "home" },
    { id: "transactions", label: "Transactions", icon: "list" },
    { id: "insights", label: "Insights", icon: "pie" },
    { id: "import", label: "Import", icon: "upload" },
    { id: "coach", label: "AI Coach", icon: "sparkle" },
  ];
  const ledgerMeta = [
    { id: "history", label: "History", icon: "clock" },
    { id: "categories", label: "Categories", icon: "sparkle" },
    { id: "profiles", label: "Profiles", icon: "home" },
    { id: "banks", label: "Connected banks", icon: "file" },
  ];
  const portfolioItems = [
    { id: "pf-networth", label: "Net worth", icon: "home" },
    { id: "pf-holdings", label: "Holdings", icon: "list" },
    { id: "pf-allocation", label: "Allocation", icon: "pie" },
    { id: "pf-performance", label: "Performance", icon: "sparkle" },
  ];
  const portfolioMeta = [
    { id: "pf-goals", label: "Goals", icon: "check" },
    { id: "pf-accounts", label: "Linked accounts", icon: "file" },
  ];
  const items = mode === "portfolio" ? portfolioItems : ledgerItems;
  const meta = mode === "portfolio" ? portfolioMeta : ledgerMeta;
  const handleNav = (id) => { onNav(id); if (onMobileClose) onMobileClose(); };
  return (
    <>
      {mobileOpen && <div className="mobile-backdrop" onClick={onMobileClose}></div>}
      <aside className={"sidebar" + (mobileOpen ? " mobile-open" : "")}>
        <div className="brand">
        <div className="brand-mark">B</div>
        <div>
          <div className="brand-name">Bankclaw</div>
          <div className="brand-sub">{mode === "portfolio" ? "Portfolio" : "Private Ledger"}</div>
        </div>
      </div>

      <div className="mode-switch" role="tablist" aria-label="Workspace mode">
        <button className={mode === "ledger" ? "on" : ""} onClick={() => onMode("ledger")} role="tab" aria-selected={mode === "ledger"}>
          <span className="m-glyph">§</span> Ledger
        </button>
        <button className={mode === "portfolio" ? "on" : ""} onClick={() => onMode("portfolio")} role="tab" aria-selected={mode === "portfolio"}>
          <span className="m-glyph">∆</span> Portfolio
        </button>
      </div>

      <div className="nav-group">
        <div className="nav-label">{mode === "portfolio" ? "Wealth" : "Workspace"}</div>
        {items.map((i) => (
          <div key={i.id} className={"nav-item" + (page === i.id ? " active" : "")}
            onClick={() => handleNav(i.id)}>
            <Icon name={i.icon} size={15} stroke={1.5} />
            <span>{i.label}</span>
          </div>
        ))}
      </div>

      <div className="nav-group">
        <div className="nav-label">Library</div>
        {meta.map((i) => (
          <div key={i.id} className={"nav-item" + (page === i.id ? " active" : "")} onClick={() => handleNav(i.id)}>
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
    </>
  );
}

function Topbar({ page, mode, query, setQuery, privacy, setPrivacy, onOpenTweaks, onNav, onOpenMobileMenu, profiles = [], currentProfileId, onChangeProfile }) {
  const ledgerCrumbs = {
    overview: ["Workspace", "Overview"],
    transactions: ["Workspace", "Transactions"],
    insights: ["Workspace", "Insights"],
    import: ["Workspace", "Import"],
    coach: ["Workspace", "AI Coach"],
    history: ["Library", "History"],
    categories: ["Library", "Categories"],
    profiles: ["Library", "Profiles"],
    banks: ["Library", "Connected banks"],
  };
  const portfolioCrumbs = {
    "pf-networth":    ["Wealth", "Net worth"],
    "pf-holdings":    ["Wealth", "Holdings"],
    "pf-allocation":  ["Wealth", "Allocation"],
    "pf-performance": ["Wealth", "Performance"],
    "pf-goals":       ["Library", "Goals"],
    "pf-accounts":    ["Library", "Linked accounts"],
  };
  const isPF = mode === "portfolio";
  const crumbs = (isPF ? portfolioCrumbs : ledgerCrumbs)[page] || ["Workspace", page];
  return (
    <div className="topbar">
      <button className="icon-btn mobile-only" title="Menu" onClick={onOpenMobileMenu} style={{ flexShrink: 0 }}>
        <Icon name="menu" size={16} />
      </button>
      <div className="crumbs">{crumbs[0]} · <b>{crumbs[1]}</b></div>

      {profiles.length > 0 && (
        <div style={{ display: "flex", alignItems: "center", gap: 6, marginLeft: 16 }}>
          <select
            value={currentProfileId}
            onChange={(e) => onChangeProfile && onChangeProfile(e.target.value)}
            title="Active profile"
            style={{
              padding: "6px 10px", border: "1px solid var(--rule)", borderRadius: 999,
              background: "var(--paper-2)", color: "var(--ink-1)", fontSize: 12,
              cursor: "pointer", maxWidth: 180,
            }}
          >
            <option value="all">All profiles</option>
            {profiles.map((p) => (
              <option key={p.id} value={p.id}>{p.name}</option>
            ))}
          </select>
        </div>
      )}

      <div className="spacer"></div>
      <div className="search">
        <Icon name="search" size={14} />
        <input placeholder={isPF ? "Search holdings, tickers, accounts…" : "Search transactions, merchants, references…"}
          value={query} onChange={(e) => { setQuery(e.target.value); if (!isPF && page !== "transactions") onNav("transactions"); }} />
        <kbd>⌘K</kbd>
      </div>
      <button className="icon-btn" title={privacy ? "Reveal amounts" : "Hide amounts"} onClick={() => setPrivacy(!privacy)}>
        <Icon name={privacy ? "eyeOff" : "eye"} size={15} />
      </button>
      {isPF ? (
        <button className="btn primary" onClick={() => onNav("pf-holdings")}>
          <Icon name="plus" size={12} stroke={2.2} /> Add holding
        </button>
      ) : (
        <button className="btn primary" onClick={() => onNav("import")}>
          <Icon name="plus" size={12} stroke={2.2} /> Import
        </button>
      )}
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
  const [authView, setAuthView] = useStateApp("landing"); // landing | login | signup (only used when !authed)
  const [transactions, setTransactions] = useStateApp([]);
  const [txLoading, setTxLoading] = useStateApp(false);
  const [allCategories, setAllCategories] = useStateApp([]); // [{ id?, name, glyph }] built-ins + custom
  const [profiles, setProfiles] = useStateApp([]);            // family/sub-accounts
  const [currentProfileId, setCurrentProfileId] = useStateApp(() => localStorage.getItem("bc_profile") || "all");
  useEffectApp(() => { localStorage.setItem("bc_profile", currentProfileId); }, [currentProfileId]);

  const [tweaks, setTweaks] = useStateApp(() => {
    try { const s = JSON.parse(localStorage.getItem("bc_tweaks") || "null"); if (s) return { ...TWEAK_DEFAULTS, ...s }; } catch {}
    return TWEAK_DEFAULTS;
  });
  const saveTweaks = (t) => localStorage.setItem("bc_tweaks", JSON.stringify(t));

  const [mode, setMode] = useStateApp(() => localStorage.getItem("bc_mode") || "ledger");
  useEffectApp(() => localStorage.setItem("bc_mode", mode), [mode]);

  const [page, setPage] = useStateApp(() => localStorage.getItem("bc_page") || "overview");
  useEffectApp(() => localStorage.setItem("bc_page", page), [page]);

  const [query, setQuery] = useStateApp("");
  const [openTx, setOpenTx] = useStateApp(null);
  const [tweaksOpen, setTweaksOpen] = useStateApp(false);
  const [editMode, setEditMode] = useStateApp(false);
  const [changePasswordOpen, setChangePasswordOpen] = useStateApp(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useStateApp(false);

  const loadTransactions = useCallbackApp(async () => {
    setTxLoading(true);
    try {
      const txs = await apiFetchTransactions({ profile_id: currentProfileId });
      setTransactions(txs);
      // keep global TRANSACTIONS in sync for any legacy helpers that read window.TRANSACTIONS
      window.TRANSACTIONS = txs;
    } catch {}
    setTxLoading(false);
  }, [currentProfileId]);

  const loadCategories = useCallbackApp(async () => {
    try {
      const cats = await apiFetchCategories();
      setAllCategories(cats);
      window.ALL_CATEGORIES = cats; // used by getCatInfo() to resolve custom categories
    } catch {}
  }, []);

  const loadProfiles = useCallbackApp(async () => {
    try {
      const ps = await apiFetchProfiles();
      setProfiles(ps);
      window.ALL_PROFILES = ps;
    } catch {}
  }, []);

  // Load transactions + categories + profiles on first authed render
  useEffectApp(() => {
    if (authed) { loadTransactions(); loadCategories(); loadProfiles(); }
  }, [authed]);

  // Reload transactions whenever the selected profile changes
  useEffectApp(() => {
    if (authed) loadTransactions();
  }, [currentProfileId]);

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

  const onMode = (m) => {
    setMode(m);
    if (m === "portfolio" && !page.startsWith("pf-")) setPage("pf-networth");
    if (m === "ledger" && page.startsWith("pf-")) setPage("overview");
    setOpenTx(null);
  };

  if (!authed) {
    if (authView === "landing") {
      return (
        <LandingPage onSignIn={() => setAuthView("login")} />
      );
    }
    return (
      <LoginPage
        onLogin={() => { setAuthed(true); setAuthView("landing"); }}
        onBackHome={() => setAuthView("landing")}
      />
    );
  }

  return (
    <div className="app">
      <Sidebar page={page} mode={mode} onMode={onMode} onNav={navigate} onSignOut={handleSignOut} onChangePassword={() => setChangePasswordOpen(true)} mobileOpen={mobileMenuOpen} onMobileClose={() => setMobileMenuOpen(false)} />
      <main className="main">
        <Topbar page={page} mode={mode} query={query} setQuery={setQuery}
          privacy={tweaks.privacy}
          setPrivacy={(v) => { const t = { ...tweaks, privacy: v }; setTweaks(t); saveTweaks(t); }}
          onOpenTweaks={() => setTweaksOpen(true)} onNav={navigate} onOpenMobileMenu={() => setMobileMenuOpen(true)}
          profiles={profiles} currentProfileId={currentProfileId}
          onChangeProfile={(id) => setCurrentProfileId(id)}
        />

        {mode === "ledger" && page === "overview" && <OverviewPage transactions={transactions} privacy={tweaks.privacy} onNav={navigate} onOpenTx={setOpenTx} />}
        {mode === "ledger" && page === "transactions" && <TransactionsPage transactions={transactions} privacy={tweaks.privacy} query={query} onOpenTx={setOpenTx} availableCategories={allCategories} onTxChanged={loadTransactions} profiles={profiles} currentProfileId={currentProfileId} />}
        {mode === "ledger" && page === "insights" && <InsightsPage transactions={transactions} privacy={tweaks.privacy} />}
        {mode === "ledger" && page === "import" && <ImportPage privacy={tweaks.privacy} onNav={navigate} onImportDone={loadTransactions} profiles={profiles} currentProfileId={currentProfileId} />}
        {mode === "ledger" && page === "coach" && <CoachPage currentProfileId={currentProfileId} profiles={profiles} />}
        {mode === "ledger" && page === "history" && <HistoryPage transactions={transactions} privacy={tweaks.privacy} onOpenTx={setOpenTx} />}
        {mode === "ledger" && page === "categories" && <CategoriesPage transactions={transactions} privacy={tweaks.privacy} availableCategories={allCategories} reloadCategories={loadCategories} />}
        {mode === "ledger" && page === "profiles" && <ProfilesPage profiles={profiles} reloadProfiles={loadProfiles} />}
        {mode === "ledger" && page === "banks" && <BanksPage transactions={transactions} privacy={tweaks.privacy} onNav={navigate} />}

        {mode === "portfolio" && (page === "pf-networth" || page === "pf-holdings" || page === "pf-allocation" || page === "pf-performance") &&
          <PortfolioPage privacy={tweaks.privacy} sub={page} />}
        {mode === "portfolio" && (page === "pf-goals" || page === "pf-accounts") && (
          <div className="page">
            <div className="page-kicker">Library</div>
            <h1 className="page-title">{page === "pf-goals" ? "Goals" : "Linked accounts"}</h1>
            <div className="page-sub">Coming soon.</div>
          </div>
        )}
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

// ── AI Coach page ──────────────────────────────────────────────────────────

function CoachPage({ currentProfileId = "all", profiles = [] }) {
  const { useState: useStateCO, useEffect: useEffectCO } = React;
  const [range, setRange] = useStateCO(90);
  const [loading, setLoading] = useStateCO(false);
  const [err, setErr] = useStateCO("");
  const [data, setData] = useStateCO(null); // { review, generated_at, from_cache }

  // Load cached review on mount / whenever profile or range changes
  useEffectCO(() => {
    let cancelled = false;
    (async () => {
      setLoading(true); setErr("");
      try {
        const res = await apiAiReview({ range_days: range, profile_id: currentProfileId });
        if (!cancelled) setData(res);
      } catch (e) {
        if (!cancelled) setErr(e.message || "Failed");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [range, currentProfileId]);

  const refresh = async () => {
    setLoading(true); setErr("");
    try {
      const res = await apiAiReview({ range_days: range, profile_id: currentProfileId, force_refresh: true });
      setData(res);
    } catch (e) {
      setErr(e.message || "Failed");
    } finally {
      setLoading(false);
    }
  };

  const review = data?.review;
  const generatedAt = data?.generated_at ? new Date(data.generated_at) : null;
  const fromCache = !!data?.from_cache;
  const activeProfile = profiles.find((p) => p.id === currentProfileId);

  const severityColor = (sev) => sev === "high" ? "var(--debit)" : sev === "medium" ? "var(--warn)" : "var(--ink-3)";

  return (
    <div className="page">
      <div className="page-kicker">Workspace</div>
      <h1 className="page-title"><i>AI Coach.</i></h1>
      <div className="page-sub">
        Aggregated review of your <b>{
          range === 30 ? "last month" :
          range === 90 ? "last 3 months" :
          range === 180 ? "last 6 months" :
          range === 365 ? "last 12 months" :
          `last ${range} days`
        }</b>
        {activeProfile ? <> for <b>{activeProfile.name}</b></> : currentProfileId === "all" && <> across <b>all profiles</b></>}.
        Only aggregates (totals, merchants, categories) are sent to the model — never raw statements.
      </div>

      <div style={{ height: 20 }} />

      {/* Controls */}
      <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center", marginBottom: 20 }}>
        <div className="seg" style={{ display: "flex" }}>
          {[
            [30, "1 month"],
            [90, "3 months"],
            [180, "6 months"],
            [365, "12 months"],
          ].map(([d, label]) => (
            <button key={d} className={range === d ? "on" : ""} onClick={() => setRange(d)}>{label}</button>
          ))}
        </div>
        <button className="btn" disabled={loading} onClick={refresh}>
          <Icon name="sparkle" size={13} /> {loading ? "Analysing…" : "Refresh review"}
        </button>
        {generatedAt && !loading && (
          <div style={{ fontSize: 11, color: "var(--ink-4)" }}>
            {fromCache ? "Cached · " : ""}Generated {generatedAt.toLocaleString()}
          </div>
        )}
      </div>

      {err && (
        <div className="panel panel-pad" style={{ marginBottom: 20, color: "var(--debit)", fontSize: 13 }}>
          {err.includes("DEEPSEEK_API_KEY") ? (
            <>
              <b>DeepSeek API key not configured.</b><br />
              Set <code>DEEPSEEK_API_KEY</code> in Railway Variables to enable AI Coach.
            </>
          ) : err}
        </div>
      )}

      {loading && !review && (
        <div className="panel panel-pad" style={{ textAlign: "center", padding: "60px 32px", color: "var(--ink-3)" }}>
          Crunching your transactions…
        </div>
      )}

      {review && (
        <div style={{ display: "grid", gap: 16 }}>
          {/* Summary */}
          {review.summary && (
            <div className="panel panel-pad">
              <div className="tag" style={{ marginBottom: 8 }}>◆ Summary</div>
              <div style={{ fontSize: 16, lineHeight: 1.55, color: "var(--ink-1)", fontFamily: "Instrument Serif, Georgia, serif" }}>
                {review.summary}
              </div>
            </div>
          )}

          {/* Opportunities */}
          {Array.isArray(review.opportunities) && review.opportunities.length > 0 && (
            <div className="panel">
              <div className="panel-hd"><h3>Opportunities</h3><div className="tools"><span className="hint">Things to try</span></div></div>
              <div style={{ padding: "4px 0 8px" }}>
                {review.opportunities.map((op, i) => (
                  <div key={i} style={{ padding: "14px 24px", borderTop: "1px solid var(--rule)" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 6 }}>
                      <span style={{
                        fontSize: 10, letterSpacing: "0.2em", textTransform: "uppercase",
                        color: severityColor(op.severity),
                        border: `1px solid ${severityColor(op.severity)}`,
                        borderRadius: 2, padding: "2px 8px",
                      }}>{op.severity || "low"}</span>
                      <div style={{ fontFamily: "Bodoni Moda, serif", fontSize: 18, color: "var(--ink-1)" }}>{op.area}</div>
                      {op.potential_monthly_savings > 0 && (
                        <div style={{ marginLeft: "auto", fontSize: 12, color: "var(--credit)" }}>
                          ~{op.potential_monthly_savings} SGD/mo
                        </div>
                      )}
                    </div>
                    <div style={{ fontSize: 13, color: "var(--ink-2)", marginBottom: 6 }}>{op.issue}</div>
                    <div style={{ fontSize: 13, color: "var(--accent)", fontWeight: 500 }}>→ {op.action}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Strengths + Subscriptions + Watchouts: side-by-side on desktop */}
          <div className="grid-3">
            {Array.isArray(review.strengths) && review.strengths.length > 0 && (
              <div className="panel">
                <div className="panel-hd"><h3>Strengths</h3></div>
                <div style={{ padding: "4px 0 8px" }}>
                  {review.strengths.map((s, i) => (
                    <div key={i} style={{ padding: "12px 20px", borderTop: "1px solid var(--rule)" }}>
                      <div style={{ fontWeight: 500, fontSize: 13, marginBottom: 4 }}>{s.area}</div>
                      <div style={{ fontSize: 12, color: "var(--ink-3)" }}>{s.note}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {Array.isArray(review.subscriptions_review) && review.subscriptions_review.length > 0 && (
              <div className="panel">
                <div className="panel-hd"><h3>Subscriptions</h3></div>
                <div style={{ padding: "4px 0 8px" }}>
                  {review.subscriptions_review.map((s, i) => (
                    <div key={i} style={{ padding: "12px 20px", borderTop: "1px solid var(--rule)" }}>
                      <div style={{ fontWeight: 500, fontSize: 13, marginBottom: 4 }}>{s.merchant}</div>
                      <div style={{ fontSize: 12, color: "var(--ink-3)" }}>{s.note}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {Array.isArray(review.watchouts) && review.watchouts.length > 0 && (
              <div className="panel">
                <div className="panel-hd"><h3>Watch-outs</h3></div>
                <div style={{ padding: "4px 0 8px" }}>
                  {review.watchouts.map((w, i) => (
                    <div key={i} style={{ padding: "12px 20px", borderTop: "1px solid var(--rule)" }}>
                      <div style={{ fontWeight: 500, fontSize: 13, marginBottom: 4 }}>{w.area}</div>
                      <div style={{ fontSize: 12, color: "var(--ink-3)" }}>{w.note}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// ── Profiles page (family / sub-accounts) ──────────────────────────────────

const _PROFILE_COLORS = [
  "#1f2937", "#b8602e", "#355e3b", "#6b4a83", "#a84a3b",
  "#2b6da3", "#c99b2d", "#4a6f61", "#8c3a5a", "#2f4c6b",
];

function ProfilesPage({ profiles = [], reloadProfiles }) {
  const { useState: useStatePR } = React;
  const [name, setName] = useStatePR("");
  const [color, setColor] = useStatePR(_PROFILE_COLORS[1]);
  const [saving, setSaving] = useStatePR(false);
  const [err, setErr] = useStatePR("");
  const [editing, setEditing] = useStatePR(null); // { id, draftName, draftColor }

  const add = async (e) => {
    e.preventDefault();
    if (!name.trim()) return;
    setSaving(true); setErr("");
    try {
      await apiCreateProfile(name.trim(), color);
      setName(""); setColor(_PROFILE_COLORS[1]);
      if (reloadProfiles) await reloadProfiles();
    } catch (e2) {
      setErr(e2.message || "Failed to add");
    } finally {
      setSaving(false);
    }
  };

  const save = async () => {
    if (!editing) return;
    setSaving(true); setErr("");
    try {
      await apiUpdateProfile(editing.id, { name: editing.draftName.trim(), color: editing.draftColor });
      setEditing(null);
      if (reloadProfiles) await reloadProfiles();
    } catch (e2) {
      setErr(e2.message || "Failed to save");
    } finally {
      setSaving(false);
    }
  };

  const remove = async (p) => {
    if (p.is_main) return;
    if (!window.confirm(`Delete profile "${p.name}"? Its transactions will move to Main.`)) return;
    try {
      await apiDeleteProfile(p.id);
      if (reloadProfiles) await reloadProfiles();
    } catch (e2) {
      setErr(e2.message || "Failed to delete");
    }
  };

  const inputStyle = {
    padding: "8px 10px", border: "1px solid var(--rule)", borderRadius: 4,
    background: "var(--paper)", color: "var(--ink-1)", fontSize: 13,
  };

  return (
    <div className="page">
      <div className="page-kicker">Library</div>
      <h1 className="page-title"><i>Profiles.</i></h1>
      <div className="page-sub">
        Create sub-accounts for different family members. Imports and manual transactions
        stay separate per profile, but categories and insights can be combined with the
        <b> All profiles</b> switcher in the top bar.
      </div>
      <div style={{ height: 28 }} />

      <div className="panel" style={{ maxWidth: 680 }}>
        <div className="panel-hd">
          <h3>Add a profile</h3>
        </div>
        <div className="panel-pad">
          <form onSubmit={add} style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <input
              value={name} onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Partner, Kids, Side business"
              style={{ ...inputStyle, flex: 1 }}
            />
            <div style={{ display: "flex", gap: 4 }}>
              {_PROFILE_COLORS.map((c) => (
                <button key={c} type="button" onClick={() => setColor(c)} title={c}
                  style={{
                    width: 22, height: 22, borderRadius: "50%", background: c,
                    border: c === color ? "2px solid var(--ink-1)" : "1px solid var(--rule)",
                    cursor: "pointer", padding: 0,
                  }}
                />
              ))}
            </div>
            <button className="btn primary" type="submit" disabled={saving || !name.trim()}>Add</button>
          </form>
          {err && <div style={{ marginTop: 10, fontSize: 12, color: "var(--debit)" }}>{err}</div>}
        </div>
      </div>

      <div style={{ height: 20 }} />

      <div className="panel" style={{ maxWidth: 680 }}>
        <div className="panel-hd"><h3>Your profiles</h3></div>
        <div className="panel-pad" style={{ paddingTop: 4 }}>
          {profiles.length === 0 && (
            <div style={{ fontSize: 13, color: "var(--ink-4)", padding: "16px 0", textAlign: "center" }}>
              Loading…
            </div>
          )}
          {profiles.map((p) => {
            const isEditing = editing && editing.id === p.id;
            if (isEditing) {
              return (
                <div key={p.id} style={{ padding: "10px 0", borderBottom: "1px solid var(--rule)", display: "flex", gap: 8, alignItems: "center" }}>
                  <input
                    value={editing.draftName}
                    onChange={(ev) => setEditing((e) => ({ ...e, draftName: ev.target.value }))}
                    style={{ ...inputStyle, flex: 1 }}
                  />
                  <div style={{ display: "flex", gap: 4 }}>
                    {_PROFILE_COLORS.map((c) => (
                      <button key={c} type="button" onClick={() => setEditing((e) => ({ ...e, draftColor: c }))} title={c}
                        style={{
                          width: 22, height: 22, borderRadius: "50%", background: c,
                          border: c === editing.draftColor ? "2px solid var(--ink-1)" : "1px solid var(--rule)",
                          cursor: "pointer", padding: 0,
                        }}
                      />
                    ))}
                  </div>
                  <button className="btn primary" disabled={saving} onClick={save}>Save</button>
                  <button className="btn ghost" disabled={saving} onClick={() => setEditing(null)}>Cancel</button>
                </div>
              );
            }
            return (
              <div key={p.id} style={{ padding: "12px 0", borderBottom: "1px solid var(--rule)", display: "flex", gap: 12, alignItems: "center" }}>
                <span style={{ width: 14, height: 14, borderRadius: "50%", background: p.color || "#1f2937", display: "inline-block", flexShrink: 0 }} />
                <div style={{ flex: 1, fontSize: 14 }}>
                  {p.name} {p.is_main && <span style={{ fontSize: 10, letterSpacing: "0.18em", color: "var(--ink-4)", textTransform: "uppercase", marginLeft: 6 }}>Main</span>}
                </div>
                <button className="btn ghost" style={{ fontSize: 12 }}
                  onClick={() => setEditing({ id: p.id, draftName: p.name, draftColor: p.color || _PROFILE_COLORS[0] })}
                >
                  Edit
                </button>
                {!p.is_main && (
                  <button className="btn ghost" style={{ fontSize: 12, color: "var(--debit)" }} onClick={() => remove(p)}>
                    Remove
                  </button>
                )}
              </div>
            );
          })}
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
      <div className="panel">
        <div className="panel-hd">
          <h3>Supported banks</h3>
          <div className="tools" style={{ fontSize: 12, color: "var(--ink-3)" }}>
            <span>{SUPPORTED_BANKS.length} layouts</span>
          </div>
        </div>
        <div className="panel-pad" style={{ paddingTop: 4 }}>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(240px, 1fr))", gap: 8 }}>
            {SUPPORTED_BANKS.map((b) => (
              <div
                key={b.name}
                style={{
                  display: "flex", justifyContent: "space-between", alignItems: "center",
                  padding: "10px 12px", border: "1px solid var(--rule)", borderRadius: 4,
                  background: "var(--paper)",
                }}
              >
                <div style={{ fontSize: 13 }}>{b.name}</div>
                <div style={{ display: "flex", gap: 6, fontSize: 11, color: "var(--ink-3)" }}>
                  <span title="Credit card statement" style={{ opacity: b.credit ? 1 : 0.3 }}>
                    💳
                  </span>
                  <span title="Debit / account statement" style={{ opacity: b.debit ? 1 : 0.3 }}>
                    🏦
                  </span>
                </div>
              </div>
            ))}
          </div>
          <div style={{ marginTop: 14, display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: 11, color: "var(--ink-4)" }}>
            <span>💳 credit statement · 🏦 debit statement · faded = not supported</span>
            <button className="btn primary" onClick={() => onNav("import")}>
              <Icon name="plus" size={13} /> Import PDF
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

Object.assign(window, { App, LoginPage, LandingPage, Sidebar, Topbar, Drawer, TweaksPanel, HistoryPage, CategoriesPage, CoachPage, ProfilesPage, BanksPage });

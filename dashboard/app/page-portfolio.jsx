// Portfolio tracking page — assets, debts, net worth trend
const { useState: useStatePF, useMemo: useMemoPF, useEffect: useEffectPF } = React;

/* ============ Seed data ============ */
const PF_ASSETS_SEED = [
  { id: "a1", name: "DBS Multiplier",        kind: "cash",       sub: "Operating · 1.85% p.a.",       value: 32400.00, base: 31200.00, ticker: null },
  { id: "a2", name: "OCBC 360 Savings",      kind: "cash",       sub: "Emergency fund · 4.05% p.a.",  value: 18240.50, base: 17400.00, ticker: null },
  { id: "a3", name: "VWRA · All-World ETF",  kind: "equities",   sub: "145 units · LSE",              value: 26410.00, base: 21850.00, ticker: "VWRA" },
  { id: "a4", name: "Apple Inc.",            kind: "equities",   sub: "60 shares · NASDAQ",           value: 14820.00, base: 11400.00, ticker: "AAPL" },
  { id: "a5", name: "Tesla, Inc.",           kind: "equities",   sub: "22 shares · NASDAQ",           value:  6182.00, base:  9100.00, ticker: "TSLA" },
  { id: "a6", name: "Singapore 10Y SGS",     kind: "bonds",      sub: "Treasury · matures 2034",      value: 25000.00, base: 25000.00, ticker: null },
  { id: "a7", name: "CPF Ordinary Account",  kind: "retirement", sub: "Statutory · 2.5% p.a.",        value: 84200.00, base: 78600.00, ticker: null },
  { id: "a8", name: "CPF Special Account",   kind: "retirement", sub: "Statutory · 4.0% p.a.",        value: 42820.00, base: 39400.00, ticker: null },
  { id: "a9", name: "SRS Account",           kind: "retirement", sub: "Voluntary · tax deferred",     value: 28000.00, base: 26200.00, ticker: null },
  { id: "a10", name: "HDB · Tiong Bahru",    kind: "property",   sub: "5-room · valuation Apr 2026",  value: 720000.00, base: 685000.00, ticker: null },
  { id: "a11", name: "Bitcoin",              kind: "crypto",     sub: "0.42 BTC · cold storage",      value: 28140.00, base: 21800.00, ticker: "BTC" },
  { id: "a12", name: "Ethereum",             kind: "crypto",     sub: "3.4 ETH · cold storage",       value: 11424.00, base: 10120.00, ticker: "ETH" },
];

const PF_DEBTS_SEED = [
  { id: "d1", name: "HDB Mortgage",          kind: "mortgage", sub: "DBS · 2.60% · 21y left",        value: 284500.00, base: 296800.00, apr: 2.60, monthly: 1240.00 },
  { id: "d2", name: "UOB One Card",          kind: "credit",   sub: "Statement Apr 18 · 26.9% APR",  value:   4820.00, base:   2400.00, apr: 26.9, monthly: 280.00 },
  { id: "d3", name: "MOE Tuition Loan",      kind: "loan",     sub: "Maturing Jul 2028 · 4.2%",      value:  12400.00, base:  15600.00, apr: 4.2, monthly:  340.00 },
];

const PF_KINDS = {
  cash:       { name: "Cash & savings",   color: "oklch(0.62 0.09 145)", glyph: "◆" },
  equities:   { name: "Equities",         color: "oklch(0.5 0.13 35)",   glyph: "▲" },
  bonds:      { name: "Bonds",            color: "oklch(0.55 0.08 75)",  glyph: "■" },
  retirement: { name: "Retirement",       color: "oklch(0.42 0.08 255)", glyph: "◉" },
  property:   { name: "Property",         color: "oklch(0.4 0.04 60)",   glyph: "⬢" },
  crypto:     { name: "Crypto",           color: "oklch(0.7 0.14 70)",   glyph: "◇" },
};

const PF_DEBT_KINDS = {
  mortgage: { name: "Mortgage" },
  credit:   { name: "Credit card" },
  loan:     { name: "Loan" },
};

/* Build a 12-month net worth trend with a few small dips */
function buildNetWorthHistory(currentNet) {
  const months = ["May","Jun","Jul","Aug","Sep","Oct","Nov","Dec","Jan","Feb","Mar","Apr"];
  const seedRng = mulberry32(7);
  const out = [];
  let v = currentNet;
  for (let i = months.length - 1; i >= 0; i--) {
    out.unshift({ label: months[i], value: v });
    const drift = 0.018 + seedRng() * 0.014;
    const wobble = (seedRng() - 0.5) * 0.022;
    v = v / (1 + drift + wobble);
  }
  return out;
}

/* Sparkline series (12 monthly points) per asset/debt */
function buildSeries(start, end, n = 12, jitter = 0.04) {
  const out = [];
  const seedRng = mulberry32(Math.round(end * 1000) | 0);
  for (let i = 0; i < n; i++) {
    const t = i / (n - 1);
    const base = start + (end - start) * t;
    const j = (seedRng() - 0.5) * jitter * Math.max(start, end);
    out.push(Math.max(0, base + j));
  }
  return out;
}

/* ============ Mini sparkline (assets/debts) ============ */
function MiniSpark({ data, w = 84, h = 28 }) {
  if (!data || data.length < 2) return null;
  const min = Math.min(...data), max = Math.max(...data);
  const span = Math.max(1, max - min);
  const xAt = (i) => (i / (data.length - 1)) * (w - 2) + 1;
  const yAt = (v) => h - 2 - ((v - min) / span) * (h - 4);
  const d = data.map((v, i) => `${i ? "L" : "M"} ${xAt(i).toFixed(1)} ${yAt(v).toFixed(1)}`).join(" ");
  const last = data[data.length - 1], first = data[0];
  const stroke = last >= first ? "oklch(0.5 0.1 150)" : "oklch(0.5 0.13 30)";
  return (
    <svg width={w} height={h} style={{ display: "block" }}>
      <path d={d} fill="none" stroke={stroke} strokeWidth="1.25" strokeLinecap="round" />
      <circle cx={xAt(data.length - 1)} cy={yAt(last)} r="2" fill={stroke} />
    </svg>
  );
}

/* ============ Net worth area chart (large) ============ */
function NetWorthChart({ data, height = 220, privacy = false }) {
  const wrapRef = React.useRef(null);
  const [w, setW] = useStatePF(700);
  useEffectPF(() => {
    if (!wrapRef.current) return;
    const ro = new ResizeObserver((ents) => { for (const e of ents) setW(e.contentRect.width); });
    ro.observe(wrapRef.current);
    return () => ro.disconnect();
  }, []);
  const padX = 24, padY = 28;
  const max = Math.max(...data.map((d) => d.value)) * 1.06;
  const min = Math.min(...data.map((d) => d.value)) * 0.96;
  const xAt = (i) => padX + (i * (w - padX * 2)) / Math.max(1, data.length - 1);
  const yAt = (v) => padY + (1 - (v - min) / (max - min)) * (height - padY * 2);
  const linePath = data.map((d, i) => `${i ? "L" : "M"} ${xAt(i)} ${yAt(d.value)}`).join(" ");
  const areaPath = `${linePath} L ${xAt(data.length - 1)} ${height - padY} L ${xAt(0)} ${height - padY} Z`;

  const ticks = 4;
  const tickVals = [];
  for (let i = 0; i <= ticks; i++) tickVals.push(min + ((max - min) * i) / ticks);

  return (
    <div ref={wrapRef} style={{ height, filter: privacy ? "blur(10px)" : "none", position: "relative" }}>
      <svg width={w} height={height} style={{ overflow: "visible" }}>
        <defs>
          <linearGradient id="nw-grad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="var(--accent)" stopOpacity="0.22" />
            <stop offset="100%" stopColor="var(--accent)" stopOpacity="0" />
          </linearGradient>
        </defs>
        {tickVals.map((v, i) => {
          const y = yAt(v);
          return (
            <g key={i}>
              <line x1={padX} x2={w - padX} y1={y} y2={y} stroke="var(--rule)" strokeDasharray="2 5" />
              <text x={w - padX + 6} y={y + 3} fontSize="9.5" fill="var(--ink-4)"
                fontFamily="JetBrains Mono, monospace" letterSpacing="0.06em">
                {Math.round(v / 1000)}k
              </text>
            </g>
          );
        })}
        {data.map((d, i) => (
          <text key={i} x={xAt(i)} y={height - 6} textAnchor="middle"
            fontSize="9.5" fill={i === data.length - 1 ? "var(--accent)" : "var(--ink-4)"}
            fontFamily="JetBrains Mono, monospace" letterSpacing="0.1em">
            {d.label.toUpperCase()}
          </text>
        ))}
        <path d={areaPath} fill="url(#nw-grad)" />
        <path d={linePath} fill="none" stroke="var(--accent)" strokeWidth="1.6" />
        {[0, data.length - 1].map((i) => (
          <circle key={i} cx={xAt(i)} cy={yAt(data[i].value)} r="3.5"
            fill="var(--paper)" stroke="var(--accent)" strokeWidth="1.5" />
        ))}
        <g transform={`translate(${xAt(data.length - 1)}, ${yAt(data[data.length - 1].value) - 14})`}>
          <text textAnchor="middle" fontSize="11"
            fill="var(--accent)" fontFamily="Bodoni Moda, serif" fontWeight="500">
            S$ {Math.round(data[data.length - 1].value).toLocaleString("en-SG")}
          </text>
        </g>
      </svg>
    </div>
  );
}

/* ============ Add asset / debt inline form ============ */
function AddRowForm({ kind, onSave, onCancel }) {
  const [name, setName] = useStatePF("");
  const [type, setType] = useStatePF(kind === "asset" ? "cash" : "credit");
  const [value, setValue] = useStatePF("");
  const [sub, setSub] = useStatePF("");
  const types = kind === "asset" ? Object.entries(PF_KINDS) : Object.entries(PF_DEBT_KINDS);
  const submit = () => {
    const v = parseFloat(String(value).replace(/[, ]/g, ""));
    if (!name.trim() || !isFinite(v)) return;
    onSave({
      id: `${kind === "asset" ? "a" : "d"}_${Date.now().toString(36)}`,
      name: name.trim(),
      kind: type,
      sub: sub.trim() || "Manual entry",
      value: v,
      base: v * 0.98,
    });
  };
  return (
    <div className="pf-add-row">
      <div className="pf-add-grid">
        <label>
          <span>Name</span>
          <input value={name} onChange={(e) => setName(e.target.value)} placeholder={kind === "asset" ? "e.g. Endowus Cash Smart" : "e.g. HSBC Personal Loan"} autoFocus />
        </label>
        <label>
          <span>Type</span>
          <select value={type} onChange={(e) => setType(e.target.value)}>
            {types.map(([k, v]) => <option key={k} value={k}>{v.name}</option>)}
          </select>
        </label>
        <label>
          <span>{kind === "asset" ? "Current value (S$)" : "Outstanding balance (S$)"}</span>
          <input value={value} onChange={(e) => setValue(e.target.value)} placeholder="0.00" inputMode="decimal" />
        </label>
        <label>
          <span>Subtitle <em>(optional)</em></span>
          <input value={sub} onChange={(e) => setSub(e.target.value)} placeholder="e.g. 24 units · NASDAQ" />
        </label>
      </div>
      <div className="pf-add-actions">
        <button className="btn ghost" onClick={onCancel}>Cancel</button>
        <button className="btn primary" onClick={submit}>
          <Icon name="check" size={12} stroke={2} /> Add {kind}
        </button>
      </div>
    </div>
  );
}

/* ============ Portfolio Page ============ */
function PortfolioPage({ privacy, sub = "pf-networth" }) {
  const [assets, setAssets] = useStatePF(() => {
    try { const s = JSON.parse(localStorage.getItem("bc_pf_assets") || "null"); if (s) return s; } catch {}
    return PF_ASSETS_SEED;
  });
  const [debts, setDebts] = useStatePF(() => {
    try { const s = JSON.parse(localStorage.getItem("bc_pf_debts") || "null"); if (s) return s; } catch {}
    return PF_DEBTS_SEED;
  });
  useEffectPF(() => localStorage.setItem("bc_pf_assets", JSON.stringify(assets)), [assets]);
  useEffectPF(() => localStorage.setItem("bc_pf_debts", JSON.stringify(debts)), [debts]);

  const [adding, setAdding] = useStatePF(null);
  const [filter, setFilter] = useStatePF("all");

  const totals = useMemoPF(() => {
    const A = assets.reduce((s, x) => s + x.value, 0);
    const D = debts.reduce((s, x) => s + x.value, 0);
    const Abase = assets.reduce((s, x) => s + x.base, 0);
    const Dbase = debts.reduce((s, x) => s + x.base, 0);
    return { A, D, net: A - D, aDelta: A - Abase, dDelta: D - Dbase, netDelta: (A - D) - (Abase - Dbase) };
  }, [assets, debts]);

  const allocation = useMemoPF(() => {
    const map = {};
    assets.forEach((a) => { map[a.kind] = (map[a.kind] || 0) + a.value; });
    return Object.entries(map).map(([k, v]) => ({
      id: k, value: v, color: PF_KINDS[k]?.color || "var(--ink-3)", name: PF_KINDS[k]?.name || k,
    })).sort((a, b) => b.value - a.value);
  }, [assets]);

  const history = useMemoPF(() => buildNetWorthHistory(totals.net), [totals.net]);

  const dollars = Math.floor(Math.max(0, totals.net)).toLocaleString("en-SG");
  const cents = (Math.abs(totals.net) - Math.floor(Math.abs(totals.net))).toFixed(2).slice(1);
  const netUp = totals.netDelta >= 0;

  const filteredAssets = filter === "all" ? assets : assets.filter((a) => a.kind === filter);

  return (
    <div className="page">
      <div className="page-kicker">Portfolio · April 2026</div>
      <h1 className="page-title">Net worth, <i>plainly stated.</i></h1>
      <div className="page-sub">
        Twelve assets and three liabilities, valued nightly. Edits sync to the ledger so cash flow and balance always agree.
      </div>

      <div style={{ height: 28 }} />

      <div className="grid-2">
        <div className="hero">
          <div className="hero-row">
            <div>
              <div className="hero-label">Net Worth · Total</div>
              <div className="hero-amount tnum" style={{ filter: privacy ? "blur(10px)" : "none" }}>
                <span className="sym">S$</span>{dollars}<span className="cents">{cents}</span>
              </div>
              <div className={"hero-delta" + (netUp ? "" : " down")}>
                <Icon name={netUp ? "arrowUp" : "arrowDown"} size={12} stroke={2} />
                {netUp ? "+" : "−"}S${Math.abs(totals.netDelta).toLocaleString("en-SG", { maximumFractionDigits: 0 })} · {(Math.abs(totals.netDelta) / Math.max(1, totals.net - totals.netDelta) * 100).toFixed(1)}% YTD
              </div>
            </div>
            <div style={{ textAlign: "right" }}>
              <div className="hero-label" style={{ justifyContent: "flex-end" }}>12-month trajectory</div>
              <div className="legend" style={{ marginTop: 8, justifyContent: "flex-end" }}>
                <span><span className="sw" style={{ background: "var(--accent)" }}></span>Net worth</span>
              </div>
            </div>
          </div>

          <div style={{ marginTop: 14 }}>
            <NetWorthChart data={history} height={210} privacy={privacy} />
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 16, marginTop: 12, paddingTop: 20, borderTop: "1px solid var(--rule)" }}>
            <div>
              <div className="tag">Assets</div>
              <div className="display tnum" style={{ fontSize: 26, marginTop: 2, color: "var(--credit)", filter: privacy ? "blur(8px)" : "none" }}>
                {fmtSGD(totals.A, false)}
              </div>
              <div className="hint" style={{ marginTop: 4 }}>{assets.length} positions</div>
            </div>
            <div>
              <div className="tag">Liabilities</div>
              <div className="display tnum" style={{ fontSize: 26, marginTop: 2, color: "var(--debit)", filter: privacy ? "blur(8px)" : "none" }}>
                {fmtSGD(-totals.D, false)}
              </div>
              <div className="hint" style={{ marginTop: 4 }}>{debts.length} obligations</div>
            </div>
            <div>
              <div className="tag">Debt-to-asset ratio</div>
              <div className="display tnum" style={{ fontSize: 26, marginTop: 2 }}>
                {((totals.D / Math.max(1, totals.A)) * 100).toFixed(1)}<span style={{ fontSize: 16, color: "var(--ink-3)" }}>%</span>
              </div>
              <div className="hint" style={{ marginTop: 4 }}>Healthy below 30%</div>
            </div>
          </div>
        </div>

        <div className="panel">
          <div className="panel-hd">
            <h3>Allocation</h3>
            <div className="tools"><span>By asset class</span></div>
          </div>
          <div className="panel-pad" style={{ display: "flex", flexDirection: "column", alignItems: "center", paddingTop: 18 }}>
            <Ring
              segments={allocation.map((s) => ({ id: s.id, value: s.value, color: s.color }))}
              size={188} thickness={20}
              center={
                <div>
                  <div className="tag" style={{ fontSize: 8.5 }}>Largest</div>
                  <div className="display" style={{ fontSize: 22, lineHeight: 1, marginTop: 2 }}>
                    {allocation[0]?.name.split(" ")[0]}
                  </div>
                  <div className="mono" style={{ fontSize: 10, color: "var(--ink-3)", marginTop: 4 }}>
                    {((allocation[0]?.value / totals.A) * 100).toFixed(1)}%
                  </div>
                </div>
              }
            />
            <div style={{ width: "100%", marginTop: 18, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
              {allocation.map((a) => (
                <div key={a.id} className="alloc-leg">
                  <span className="dot" style={{ background: a.color }}></span>
                  <span className="nm">{a.name}</span>
                  <span className="pc mono">{((a.value / totals.A) * 100).toFixed(1)}%</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      <div style={{ height: 28 }} />
      <div className="panel">
        <div className="panel-hd">
          <h3>Assets <em>· holdings</em></h3>
          <div className="tools" style={{ gap: 12 }}>
            <div className="filterbar" style={{ padding: 0 }}>
              <div className="seg">
                {[["all", "All"], ...Object.entries(PF_KINDS).map(([k, v]) => [k, v.name.split(" ")[0]])].map(([k, lab]) => (
                  <button key={k} className={filter === k ? "on" : ""} onClick={() => setFilter(k)}>{lab}</button>
                ))}
              </div>
            </div>
            <button className="btn" onClick={() => setAdding(adding === "asset" ? null : "asset")}>
              <Icon name="plus" size={12} stroke={2.2} /> Add asset
            </button>
          </div>
        </div>

        {adding === "asset" && (
          <AddRowForm kind="asset"
            onSave={(row) => { setAssets([row, ...assets]); setAdding(null); }}
            onCancel={() => setAdding(null)} />
        )}

        <div className="pf-table-hd">
          <div>Holding</div>
          <div>Class</div>
          <div className="num">Cost basis</div>
          <div>Trend · 12M</div>
          <div className="num">Δ</div>
          <div className="num">Value</div>
        </div>
        <div className="pf-table">
          {filteredAssets.map((a) => {
            const k = PF_KINDS[a.kind] || { color: "var(--ink-3)", name: a.kind, glyph: "·" };
            const series = buildSeries(a.base, a.value);
            const delta = a.value - a.base;
            const pct = (delta / Math.max(1, a.base)) * 100;
            return (
              <div key={a.id} className="pf-row">
                <div className="pf-cell desc">
                  <div className="pf-glyph" style={{ color: k.color, borderColor: k.color }}>{k.glyph}</div>
                  <div style={{ minWidth: 0 }}>
                    <div className="nm">{a.name}</div>
                    <div className="sub">{a.sub}</div>
                  </div>
                </div>
                <div className="pf-cell">
                  <span className="kind-chip">{k.name}</span>
                </div>
                <div className="pf-cell num mono" style={{ color: "var(--ink-3)", fontSize: 12 }}>
                  {fmtSGD(a.base, privacy)}
                </div>
                <div className="pf-cell">
                  <MiniSpark data={series} />
                </div>
                <div className={"pf-cell num pf-delta " + (delta >= 0 ? "up" : "down")}>
                  <span>{delta >= 0 ? "+" : "−"}{Math.abs(pct).toFixed(2)}%</span>
                </div>
                <div className="pf-cell num pf-val">
                  {fmtSGD(a.value, privacy)}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      <div style={{ height: 24 }} />
      <div className="panel">
        <div className="panel-hd">
          <h3>Liabilities <em>· debts</em></h3>
          <div className="tools">
            <button className="btn" onClick={() => setAdding(adding === "debt" ? null : "debt")}>
              <Icon name="plus" size={12} stroke={2.2} /> Add debt
            </button>
          </div>
        </div>

        {adding === "debt" && (
          <AddRowForm kind="debt"
            onSave={(row) => { setDebts([{ ...row, apr: 0, monthly: 0 }, ...debts]); setAdding(null); }}
            onCancel={() => setAdding(null)} />
        )}

        <div className="pf-table-hd debts">
          <div>Liability</div>
          <div className="num">APR</div>
          <div className="num">Monthly</div>
          <div>Trend · 12M</div>
          <div className="num">Δ</div>
          <div className="num">Balance</div>
        </div>
        <div className="pf-table">
          {debts.map((d) => {
            const series = buildSeries(d.base, d.value);
            const delta = d.value - d.base;
            const pct = (delta / Math.max(1, d.base)) * 100;
            return (
              <div key={d.id} className="pf-row debts">
                <div className="pf-cell desc">
                  <div className="pf-glyph" style={{ color: "var(--debit)", borderColor: "var(--debit)" }}>·</div>
                  <div style={{ minWidth: 0 }}>
                    <div className="nm">{d.name}</div>
                    <div className="sub">{d.sub}</div>
                  </div>
                </div>
                <div className="pf-cell num mono" style={{ fontSize: 12 }}>
                  {(d.apr || 0).toFixed(2)}%
                </div>
                <div className="pf-cell num mono" style={{ color: "var(--ink-3)", fontSize: 12 }}>
                  {d.monthly ? fmtSGD(d.monthly, privacy) : "—"}
                </div>
                <div className="pf-cell">
                  <MiniSpark data={series} />
                </div>
                <div className={"pf-cell num pf-delta " + (delta <= 0 ? "up" : "down")}>
                  <span>{delta >= 0 ? "+" : "−"}{Math.abs(pct).toFixed(2)}%</span>
                </div>
                <div className="pf-cell num pf-val" style={{ color: "var(--debit)" }}>
                  −{fmtSGD(d.value, privacy)}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      <div style={{ height: 24 }} />
      <div className="grid-4">
        <StatBlock label="Equity exposure" value={`${(((allocation.find(x => x.id === "equities")?.value || 0) + (allocation.find(x => x.id === "crypto")?.value || 0)) / Math.max(1, totals.A) * 100).toFixed(1)}%`} sub="Equities + crypto · target 35%" />
        <StatBlock label="Liquidity" value={fmtSGD((allocation.find(x => x.id === "cash")?.value || 0), privacy)} sub="6.4 months of expenses" />
        <StatBlock label="Highest APR debt" value="26.9%" sub="UOB One Card · pay first" />
        <StatBlock label="Projected at 60" value={fmtSGD(2_840_000, privacy)} sub="@ 5.4% real return" accent />
      </div>
    </div>
  );
}

Object.assign(window, { PortfolioPage });

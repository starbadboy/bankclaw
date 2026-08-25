// Portfolio tracking page — assets, debts, net worth trend
const { useState: useStatePF, useMemo: useMemoPF, useEffect: useEffectPF } = React;

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

const HOLDING_RANGES = ["1M", "3M", "1Y", "All"];
const holdingValue = (v) => (Math.abs(v) >= 1000 ? Math.round(v).toLocaleString("en-SG") : v.toFixed(2));
const holdingTick = (v) => (Math.abs(v) < 1e-9 ? "0.00" : Math.abs(v) >= 1000 ? `${Math.round(v / 1000)}k` : Math.abs(v) >= 100 ? String(Math.round(v)) : v.toFixed(2));

function portfolioTodayIso() {
  const now = new Date();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${now.getFullYear()}-${month}-${day}`;
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
function NetWorthChart({
  data, height = 220, privacy = false,
  fmtTick = (v) => `${Math.round(v / 1000)}k`,
  fmtValue = (v) => Math.round(v).toLocaleString("en-SG"),
  padFraction = null, // null keeps the net-worth look (pad by the full range); e.g. 0.08 hugs the line
}) {
  const wrapRef = React.useRef(null);
  const [w, setW] = useStatePF(700);
  const [hoverIdx, setHoverIdx] = useStatePF(null);
  useEffectPF(() => {
    if (!wrapRef.current) return;
    const ro = new ResizeObserver((ents) => { for (const e of ents) setW(e.contentRect.width); });
    ro.observe(wrapRef.current);
    return () => ro.disconnect();
  }, []);
  if (!data || data.length === 0) {
    return (
      <div className="pf-chart-empty" style={{ height }}>
        Record a dated value to begin the net worth trend.
      </div>
    );
  }
  const padX = 24, padY = 28;
  const rawMax = Math.max(...data.map((d) => d.value));
  const rawMin = Math.min(...data.map((d) => d.value));
  const padding = padFraction == null
    ? Math.max(1, rawMax - rawMin, Math.abs(rawMax) * 0.08, Math.abs(rawMin) * 0.08)
    : Math.max(Math.abs(rawMax) * 1e-6, (rawMax - rawMin) * padFraction, Number.EPSILON); // flat series must not divide by 0
  const max = rawMax + padding;
  const min = rawMin - padding;
  const xAt = (i) => data.length === 1
    ? w / 2
    : padX + (i * (w - padX * 2)) / (data.length - 1);
  const yAt = (v) => padY + (1 - (v - min) / (max - min)) * (height - padY * 2);
  const linePath = data.map((d, i) => `${i ? "L" : "M"} ${xAt(i)} ${yAt(d.value)}`).join(" ");
  const areaPath = `${linePath} L ${xAt(data.length - 1)} ${height - padY} L ${xAt(0)} ${height - padY} Z`;

  const handleMove = (e) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const idx = data.length === 1 ? 0 : Math.round(((e.clientX - rect.left - padX) / Math.max(1, w - padX * 2)) * (data.length - 1));
    setHoverIdx(Math.max(0, Math.min(data.length - 1, idx)));
  };
  const hovered = hoverIdx != null && hoverIdx < data.length ? data[hoverIdx] : null;
  const hoverX = hovered ? xAt(hoverIdx) : 0;
  const hoverAnchor = hoverX > w * 0.75 ? "end" : hoverX < w * 0.25 ? "start" : "middle";

  const ticks = 4;
  const tickVals = [];
  for (let i = 0; i <= ticks; i++) tickVals.push(min + ((max - min) * i) / ticks);

  return (
    <div ref={wrapRef} style={{ height, filter: privacy ? "blur(10px)" : "none", position: "relative" }}
      onMouseMove={handleMove} onMouseLeave={() => setHoverIdx(null)}>
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
                {fmtTick(v)}
              </text>
            </g>
          );
        })}
        {data.map((d, i) => d.label && (
          <text key={i} x={xAt(i)} y={height - 6} textAnchor="middle"
            fontSize="9.5" fill={i === data.length - 1 ? "var(--accent)" : "var(--ink-4)"}
            fontFamily="JetBrains Mono, monospace" letterSpacing="0.1em">
            {d.label.toUpperCase()}
          </text>
        ))}
        <path d={areaPath} fill="url(#nw-grad)" />
        <path d={linePath} fill="none" stroke="var(--accent)" strokeWidth="1.6" />
        {[...new Set([0, data.length - 1])].map((i) => (
          <circle key={i} cx={xAt(i)} cy={yAt(data[i].value)} r="3.5"
            fill="var(--paper)" stroke="var(--accent)" strokeWidth="1.5" />
        ))}
        {!hovered && (
          <g transform={`translate(${xAt(data.length - 1)}, ${yAt(data[data.length - 1].value) - 14})`}>
            <text textAnchor="middle" fontSize="11"
              fill="var(--accent)" fontFamily="Bodoni Moda, serif" fontWeight="500">
              S$ {fmtValue(data[data.length - 1].value)}
            </text>
          </g>
        )}
        {hovered && (
          <g pointerEvents="none">
            <line x1={hoverX} x2={hoverX} y1={padY} y2={height - padY} stroke="var(--ink-4)" strokeDasharray="3 3" />
            <circle cx={hoverX} cy={yAt(hovered.value)} r="4" fill="var(--accent)" stroke="var(--paper)" strokeWidth="1.5" />
            <text x={hoverX} y={padY - 10} textAnchor={hoverAnchor} fontSize="10.5" fill="var(--ink)"
              fontFamily="JetBrains Mono, monospace" letterSpacing="0.04em">
              {hovered.date || hovered.label} · S$ {fmtValue(hovered.value)}
            </text>
          </g>
        )}
      </svg>
    </div>
  );
}

/* ============ Add asset / debt inline form ============ */
function AddRowForm({ kind, onSave, onCancel, assetKinds = PF_KINDS, onCreateAssetType }) {
  const [name, setName] = useStatePF("");
  const [type, setType] = useStatePF(kind === "asset" ? "cash" : "credit");
  const [value, setValue] = useStatePF("");
  const [sub, setSub] = useStatePF("");
  const [asOfDate, setAsOfDate] = useStatePF(portfolioTodayIso());
  const [customName, setCustomName] = useStatePF("");
  const [customColor, setCustomColor] = useStatePF("#8B5CF6");
  const [customBusy, setCustomBusy] = useStatePF(false);
  const [customError, setCustomError] = useStatePF("");
  const types = kind === "asset" ? Object.entries(assetKinds) : Object.entries(PF_DEBT_KINDS);
  const createCustomType = async () => {
    if (!customName.trim() || !onCreateAssetType) return;
    setCustomBusy(true);
    setCustomError("");
    try {
      const created = await onCreateAssetType({ name: customName.trim(), color: customColor });
      setType(created.id);
      setCustomName("");
    } catch (error) {
      setCustomError(error.message || "Failed to create asset type");
    } finally {
      setCustomBusy(false);
    }
  };
  const submit = () => {
    const v = parseFloat(String(value).replace(/[, ]/g, ""));
    if (!name.trim() || !isFinite(v) || v < 0 || !asOfDate || type === "__new_custom__") return;
    onSave({
      id: `${kind === "asset" ? "a" : "d"}_${Date.now().toString(36)}`,
      name: name.trim(),
      kind: type,
      sub: sub.trim() || "Manual entry",
      value: v,
      base: v,
      as_of_date: asOfDate,
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
            {kind === "asset" && <option value="__new_custom__">+ Create custom type…</option>}
          </select>
        </label>
        <label>
          <span>{kind === "asset" ? "Current value (S$)" : "Outstanding balance (S$)"}</span>
          <input value={value} onChange={(e) => setValue(e.target.value)} placeholder="0.00" inputMode="decimal" />
        </label>
        <label>
          <span>Valuation date</span>
          <input type="date" max={portfolioTodayIso()} value={asOfDate} onChange={(e) => setAsOfDate(e.target.value)} />
        </label>
        <label>
          <span>Subtitle <em>(optional)</em></span>
          <input value={sub} onChange={(e) => setSub(e.target.value)} placeholder="e.g. 24 units · NASDAQ" />
        </label>
      </div>
      {kind === "asset" && type === "__new_custom__" && (
        <div className="pf-custom-type-inline">
          <label>
            <span>Custom type name</span>
            <input value={customName} onChange={(event) => setCustomName(event.target.value)}
              placeholder="e.g. CPF, Gold, Insurance" autoFocus />
          </label>
          <label className="pf-color-field">
            <span>Color</span>
            <input type="color" value={customColor} onChange={(event) => setCustomColor(event.target.value)} />
          </label>
          <button className="btn" type="button" disabled={customBusy || !customName.trim()} onClick={createCustomType}>
            <Icon name="plus" size={12} stroke={2} /> {customBusy ? "Creating…" : "Create custom type"}
          </button>
          {customError && <div className="pf-custom-type-error">{customError}</div>}
        </div>
      )}
      <div className="pf-add-actions">
        <button className="btn ghost" onClick={onCancel}>Cancel</button>
        <button className="btn primary" onClick={submit}>
          <Icon name="check" size={12} stroke={2} /> Add {kind}
        </button>
      </div>
    </div>
  );
}

function GoalsCard({ goals, net, busyId, onCreate, onUpdate, onDelete, privacy }) {
  const [name, setName] = useStatePF("");
  const [amount, setAmount] = useStatePF("");
  const [targetDate, setTargetDate] = useStatePF("");
  const [editingId, setEditingId] = useStatePF(null);
  const [draft, setDraft] = useStatePF({});
  const [error, setError] = useStatePF("");

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    try {
      await onCreate({ name, target_amount: Number(amount), target_date: targetDate || null });
      setName(""); setAmount(""); setTargetDate("");
    } catch (err) { setError(err.message); }
  };

  const saveEdit = async (goal) => {
    setError("");
    try {
      await onUpdate(goal.id, {
        name: draft.name,
        target_amount: Number(draft.target_amount),
        target_date: draft.target_date || null,
      });
      setEditingId(null);
    } catch (err) { setError(err.message); }
  };

  return (
    <div className="panel">
      <div className="panel-hd">
        <h3>Goals <em>· net-worth milestones</em></h3>
        <div className="tools"><span>Progress vs current net worth</span></div>
      </div>
      <div className="panel-pad">
        {goals.map((goal) => {
          const progress = Math.min(1, Math.max(0, net / goal.target_amount));
          const done = net >= goal.target_amount;
          const busy = busyId === `goal:${goal.id}`;
          if (editingId === goal.id) {
            return (
              <div key={goal.id} style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 10 }}>
                <input aria-label="Goal name" value={draft.name}
                  onChange={(e) => setDraft((cur) => ({ ...cur, name: e.target.value }))} />
                <input aria-label="Target amount (S$)" type="number" min="1" step="any" value={draft.target_amount}
                  onChange={(e) => setDraft((cur) => ({ ...cur, target_amount: e.target.value }))} style={{ width: 110 }} />
                <input aria-label="Target date" type="date" value={draft.target_date || ""}
                  onChange={(e) => setDraft((cur) => ({ ...cur, target_date: e.target.value }))} />
                <button className="btn ghost" type="button" disabled={busy || !draft.name.trim()} onClick={() => saveEdit(goal)}>Save</button>
                <button className="btn ghost" type="button" onClick={() => setEditingId(null)}>Cancel</button>
              </div>
            );
          }
          return (
            <div key={goal.id} style={{ marginBottom: 12 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", gap: 8 }}>
                <span>
                  {done && <Icon name="check" size={12} stroke={2.2} />} <strong>{goal.name}</strong>
                  <span className="hint" style={{ marginLeft: 8 }}>
                    {fmtSGD(goal.target_amount, privacy)}{goal.target_date ? ` · by ${goal.target_date}` : ""}
                  </span>
                </span>
                <span className="tools" style={{ gap: 8 }}>
                  <span className="tnum">{done ? "Done" : `${Math.round(progress * 100)}%`}</span>
                  <button className="btn ghost" type="button" disabled={busy}
                    onClick={() => { setEditingId(goal.id); setDraft({ name: goal.name, target_amount: goal.target_amount, target_date: goal.target_date }); }}>Edit</button>
                  <button className="btn ghost" type="button" disabled={busy}
                    onClick={async () => { setError(""); try { await onDelete(goal.id); } catch (err) { setError(err.message); } }}>Remove</button>
                </span>
              </div>
              <div style={{ height: 6, borderRadius: 3, background: "var(--rule)", marginTop: 6 }}>
                <div style={{ height: 6, borderRadius: 3, width: `${progress * 100}%`, background: done ? "var(--credit)" : "var(--accent)" }} />
              </div>
            </div>
          );
        })}
        {!goals.length && <div className="hint" style={{ marginBottom: 10 }}>No goals yet — add a net-worth milestone below.</div>}
        <form onSubmit={submit} style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
          <input aria-label="Goal name" placeholder="Goal name" value={name} onChange={(e) => setName(e.target.value)} />
          <input aria-label="Target amount (S$)" type="number" min="1" step="any" placeholder="Target S$" value={amount}
            onChange={(e) => setAmount(e.target.value)} style={{ width: 110 }} />
          <input aria-label="Target date" type="date" value={targetDate} onChange={(e) => setTargetDate(e.target.value)} />
          <button className="btn primary" type="submit" disabled={!name.trim() || !amount || busyId === "goal:create"}>
            <Icon name="plus" size={12} stroke={2.2} /> Add goal
          </button>
        </form>
        {error && <div className="hint" style={{ color: "var(--debit)", marginTop: 6 }}>{error}</div>}
      </div>
    </div>
  );
}

function AssetTypeManager({ assetTypes, assets, busyId, onCreate, onUpdate, onDelete, onClose }) {
  const [newName, setNewName] = useStatePF("");
  const [newColor, setNewColor] = useStatePF("#8B5CF6");
  const [drafts, setDrafts] = useStatePF({});
  const [localError, setLocalError] = useStatePF("");

  useEffectPF(() => {
    setDrafts(Object.fromEntries(assetTypes.map((assetType) => [
      assetType.id,
      { name: assetType.name, color: assetType.color },
    ])));
  }, [assetTypes]);

  const createType = async (event) => {
    event.preventDefault();
    if (!newName.trim()) return;
    setLocalError("");
    try {
      await onCreate({ name: newName.trim(), color: newColor });
      setNewName("");
    } catch (error) {
      setLocalError(error.message || "Failed to create asset type");
    }
  };

  const updateType = async (assetType, draft) => {
    setLocalError("");
    try {
      await onUpdate(assetType.id, { name: draft.name.trim(), color: draft.color });
    } catch (error) {
      setLocalError(error.message || "Failed to update asset type");
    }
  };

  const deleteType = async (assetType) => {
    setLocalError("");
    try {
      await onDelete(assetType.id);
    } catch (error) {
      setLocalError(error.message || "Failed to delete asset type");
    }
  };

  return (
    <div className="pf-valuation-overlay" role="presentation" onMouseDown={onClose}>
      <aside className="pf-valuation-panel pf-asset-type-panel" role="dialog" aria-modal="true"
        aria-label="Manage asset types" onMouseDown={(event) => event.stopPropagation()}>
        <div className="pf-valuation-head">
          <div>
            <div className="tag">Portfolio settings</div>
            <h2>Asset types</h2>
            <p>Create your own classes for holdings. Built-in types remain available.</p>
          </div>
          <button className="pf-panel-close" onClick={onClose} aria-label="Close asset type manager">
            <Icon name="close" size={16} stroke={1.8} />
          </button>
        </div>

        <form className="pf-asset-type-create" onSubmit={createType}>
          <label>
            <span>New type</span>
            <input value={newName} onChange={(event) => setNewName(event.target.value)}
              placeholder="e.g. CPF, Gold, Insurance" />
          </label>
          <label className="pf-color-field">
            <span>Color</span>
            <input type="color" value={newColor} onChange={(event) => setNewColor(event.target.value)} />
          </label>
          <button className="btn primary" type="submit" disabled={!newName.trim() || busyId === "asset-type:create"}>
            <Icon name="plus" size={12} stroke={2} /> Create custom type
          </button>
        </form>
        {localError && <div className="pf-custom-type-error">{localError}</div>}

        <div className="pf-valuation-list-head">
          <span>Custom types</span>
          <span>{assetTypes.length}</span>
        </div>
        <div className="pf-asset-type-list">
          {assetTypes.length === 0 && (
            <div className="pf-asset-type-empty">No custom asset types yet.</div>
          )}
          {assetTypes.map((assetType) => {
            const inUseCount = assets.filter((asset) => asset.kind === assetType.id).length;
            const draft = drafts[assetType.id] || assetType;
            const busy = busyId === `asset-type:${assetType.id}`;
            return (
              <div className="pf-asset-type-row" key={assetType.id}>
                <input className="pf-asset-type-color" type="color" value={draft.color}
                  aria-label={`Color for ${assetType.name}`}
                  onChange={(event) => setDrafts((current) => ({
                    ...current,
                    [assetType.id]: { ...draft, color: event.target.value },
                  }))} />
                <div className="pf-asset-type-main">
                  <input value={draft.name} aria-label={`Name for ${assetType.name}`}
                    onChange={(event) => setDrafts((current) => ({
                      ...current,
                      [assetType.id]: { ...draft, name: event.target.value },
                    }))} />
                  <span>{inUseCount > 0 ? `${inUseCount} ${inUseCount === 1 ? "asset" : "assets"} in use` : "Unused"}</span>
                </div>
                <button className="btn ghost" type="button" disabled={busy || !draft.name.trim()}
                  onClick={() => updateType(assetType, draft)}>
                  Save
                </button>
                <button className="pf-valuation-delete" type="button" title="Delete custom asset type"
                  disabled={busy || inUseCount > 0} onClick={() => deleteType(assetType)}>
                  <Icon name="close" size={11} stroke={2} />
                </button>
              </div>
            );
          })}
        </div>
      </aside>
    </div>
  );
}

/* ============ Holding market data: ticker/units + fetched Price | Value chart ============ */
function HoldingMarketPanel({ item, busy, onUpdateMarket }) {
  const [ticker, setTicker] = useStatePF(item.ticker || "");
  const [units, setUnits] = useStatePF(item.units == null ? "" : String(item.units));
  const [marketError, setMarketError] = useStatePF("");
  const [chartMode, setChartMode] = useStatePF("value");
  const [chartRange, setChartRange] = useStatePF("1Y");
  const [market, setMarket] = useStatePF({ loading: false, error: "", data: null });
  const priced = Boolean(item.ticker) && item.units != null;

  useEffectPF(() => {
    if (!priced) { setMarket({ loading: false, error: "", data: null }); return undefined; }
    let cancelled = false;
    setMarket((cur) => ({ ...cur, loading: true, error: "" }));
    apiFetchAssetMarketHistory(item.id, chartRange)
      .then((data) => { if (!cancelled) setMarket({ loading: false, error: "", data }); })
      .catch((e) => { if (!cancelled) setMarket({ loading: false, error: e.message || "Market data unavailable", data: null }); });
    return () => { cancelled = true; };
  }, [priced, item.id, item.ticker, item.units, chartRange]);

  const submitMarket = async (event) => {
    event.preventDefault();
    const raw = units.trim();
    const parsedUnits = raw === "" ? null : parseFloat(raw.replace(/[, ]/g, ""));
    if (parsedUnits != null && !isFinite(parsedUnits)) { setMarketError("Units must be a number"); return; }
    if (parsedUnits != null && parsedUnits < 0) { setMarketError("Units must be zero or more"); return; }
    setMarketError("");
    try { await onUpdateMarket({ ticker: ticker.trim().toUpperCase() || null, units: parsedUnits }); }
    catch (e) { setMarketError(e.message || "Failed to save market data"); }
  };

  const points = market.data?.points || [];
  return (
    <>
      <form className="pf-valuation-form" onSubmit={submitMarket}>
        <div className="pf-valuation-list-head" style={{ gridColumn: "1 / -1", padding: "0 0 2px" }}>
          <span>Market data</span>
          <span>{priced ? `${item.ticker} · ${item.units} units` : "optional"}</span>
        </div>
        <label>
          <span>Ticker</span>
          <input value={ticker} onChange={(event) => setTicker(event.target.value)} placeholder="e.g. ADSK, D05.SI" />
        </label>
        <label>
          <span>Units</span>
          <input value={units} onChange={(event) => setUnits(event.target.value)} inputMode="decimal" placeholder="e.g. 672" />
        </label>
        <button className="btn" type="submit" disabled={busy}>
          <Icon name="check" size={12} stroke={2} /> Save market data
        </button>
        {marketError && <div className="pf-custom-type-error" style={{ gridColumn: "1 / -1" }}>{marketError}</div>}
      </form>

      {priced && (
        <div>
          <div className="pf-valuation-list-head">
            <span>{market.data?.ticker || item.ticker} · {market.data ? `${market.data.currency}${market.data.currency !== "SGD" ? " → S$" : ""}` : "market"}</span>
            <div className="tools" style={{ display: "flex", gap: 8 }}>
              <div className="seg">
                {[["value", "Value"], ["price", "Price"]].map(([m, label]) => (
                  <button key={m} type="button" className={chartMode === m ? "on" : ""} onClick={() => setChartMode(m)}>{label}</button>
                ))}
              </div>
              <div className="seg">
                {HOLDING_RANGES.map((r) => (
                  <button key={r} type="button" className={chartRange === r ? "on" : ""} onClick={() => setChartRange(r)}>{r}</button>
                ))}
              </div>
            </div>
          </div>
          {market.loading && !market.data && <div className="hint" style={{ padding: "12px 0" }}>Loading prices…</div>}
          {market.error && <div className="pf-custom-type-error">{market.error}</div>}
          {market.data && !market.error && points.length === 0 && (
            <div className="hint" style={{ padding: "12px 0" }}>No prices returned for {item.ticker} in this range.</div>
          )}
          {market.data && !market.error && points.length > 0 && (
            <NetWorthChart data={buildHoldingChartData(points, chartMode, { maxLabels: 6 })} height={170}
              fmtTick={holdingTick} fmtValue={holdingValue} padFraction={0.08} />
          )}
        </div>
      )}
    </>
  );
}

function ValuationPanel({ itemType, item, history, busy, onSave, onDelete, onClose, onUpdateMarket }) {
  const [asOfDate, setAsOfDate] = useStatePF(portfolioTodayIso());
  const [value, setValue] = useStatePF(String(item.value ?? ""));
  const orderedHistory = [...(history || [])].sort((a, b) => b.as_of_date.localeCompare(a.as_of_date));

  useEffectPF(() => {
    setAsOfDate(portfolioTodayIso());
    setValue(String(item.value ?? ""));
  }, [item.id]);

  const submit = (event) => {
    event.preventDefault();
    const parsed = parseFloat(String(value).replace(/[, ]/g, ""));
    if (!asOfDate || !isFinite(parsed) || parsed < 0) return;
    onSave({ as_of_date: asOfDate, value: parsed });
  };
  const editEntry = (entry) => {
    setAsOfDate(entry.as_of_date);
    setValue(String(entry.value));
  };

  return (
    <div className="pf-valuation-overlay" role="presentation" onMouseDown={onClose}>
      <aside className="pf-valuation-panel" role="dialog" aria-modal="true" aria-label={`Valuation history for ${item.name}`}
        onMouseDown={(event) => event.stopPropagation()}>
        <div className="pf-valuation-head">
          <div>
            <div className="tag">{itemType === "asset" ? "Asset valuation" : "Debt balance"}</div>
            <h2>{item.name}</h2>
            <p>Record the value on a specific date. Saving the same date updates that entry.</p>
          </div>
          <button className="pf-panel-close" onClick={onClose} aria-label="Close valuation history">
            <Icon name="close" size={16} stroke={1.8} />
          </button>
        </div>

        {itemType === "asset" && <HoldingMarketPanel key={item.id} item={item} busy={busy} onUpdateMarket={onUpdateMarket} />}

        <form className="pf-valuation-form" onSubmit={submit}>
          <label>
            <span>Date</span>
            <input type="date" max={portfolioTodayIso()} value={asOfDate}
              onChange={(event) => setAsOfDate(event.target.value)} required />
          </label>
          <label>
            <span>{itemType === "asset" ? "Value (S$)" : "Outstanding balance (S$)"}</span>
            <input value={value} onChange={(event) => setValue(event.target.value)}
              inputMode="decimal" placeholder="0.00" required />
          </label>
          <button className="btn primary" type="submit" disabled={busy}>
            <Icon name="check" size={12} stroke={2} /> {busy ? "Saving…" : "Record value"}
          </button>
        </form>

        <div className="pf-valuation-list-head">
          <span>History</span>
          <span>{orderedHistory.length} {orderedHistory.length === 1 ? "entry" : "entries"}</span>
        </div>
        <div className="pf-valuation-list">
          {orderedHistory.map((entry) => (
            <div className="pf-valuation-entry" key={entry.as_of_date}>
              <button className="pf-valuation-edit" onClick={() => editEntry(entry)}>
                <span className="mono">{entry.as_of_date}</span>
                <strong>{itemType === "debt" ? "−" : ""}{fmtSGD(entry.value, false)}</strong>
              </button>
              <button className="pf-valuation-delete" title="Delete this dated value"
                disabled={busy || orderedHistory.length <= 1}
                onClick={() => onDelete(entry.as_of_date)}>
                <Icon name="close" size={11} stroke={2} />
              </button>
            </div>
          ))}
        </div>
        {orderedHistory.length <= 1 && (
          <div className="hint pf-valuation-hint">Keep at least one value so this holding always has a current balance.</div>
        )}
      </aside>
    </div>
  );
}

/* ============ Portfolio Page ============ */
const WEALTH_TABS = {
  "pf-networth":    { title: <>Net worth, <i>plainly stated.</i></>, sub: "The headline number and its 12-month trend." },
  "pf-holdings":    { title: <>Holdings, <i>owned and owed.</i></>, sub: "Every asset and liability — add, edit, and record values here." },
  "pf-allocation":  { title: <>Allocation, <i>at a glance.</i></>, sub: "How your assets are distributed across classes." },
  "pf-performance": { title: <>Performance, <i>over time.</i></>, sub: "What moved, by how much, over the window you pick." },
};

const PERF_WINDOWS = { "1M": 1, "3M": 3, "1Y": 12, "All": null };

function PortfolioPage({ privacy, sub = "pf-networth" }) {
  const [assets, setAssets] = useStatePF([]);
  const [debts, setDebts] = useStatePF([]);
  const [assetTypes, setAssetTypes] = useStatePF([]);
  const [loading, setLoading] = useStatePF(true);
  const [err, setErr] = useStatePF("");
  const [adding, setAdding] = useStatePF(null);
  const [filter, setFilter] = useStatePF("all");
  const [busyId, setBusyId] = useStatePF(null);
  const [goals, setGoals] = useStatePF([]);
  const [perfWindow, setPerfWindow] = useStatePF("3M");

  const refreshGoals = async () => setGoals(await apiFetchPortfolioGoals());

  const createGoal = async (payload) => {
    setBusyId("goal:create");
    try { await apiCreatePortfolioGoal(payload); await refreshGoals(); }
    finally { setBusyId(null); }
  };

  const updateGoal = async (id, payload) => {
    setBusyId(`goal:${id}`);
    try { await apiUpdatePortfolioGoal(id, payload); await refreshGoals(); }
    finally { setBusyId(null); }
  };

  const deleteGoal = async (id) => {
    setBusyId(`goal:${id}`);
    try { await apiDeletePortfolioGoal(id); await refreshGoals(); }
    finally { setBusyId(null); }
  };
  const [histories, setHistories] = useStatePF({});
  const [activeValuation, setActiveValuation] = useStatePF(null);
  const [managingTypes, setManagingTypes] = useStatePF(false);

  const assetKinds = useMemoPF(() => ({
    ...PF_KINDS,
    ...Object.fromEntries(assetTypes.map((assetType) => [
      assetType.id,
      { name: assetType.name, color: assetType.color, glyph: "◆", custom: true },
    ])),
  }), [assetTypes]);

  const fetchPortfolioData = async () => {
    const [data, customAssetTypes, goalList] = await Promise.all([
      apiFetchPortfolio(),
      apiFetchPortfolioAssetTypes(),
      apiFetchPortfolioGoals(),
    ]);
    const items = [
      ...data.assets.map((item) => ({ itemType: "asset", item })),
      ...data.debts.map((item) => ({ itemType: "debt", item })),
    ];
    const entries = await Promise.all(items.map(async ({ itemType, item }) => [
      `${itemType}:${item.id}`,
      await apiFetchPortfolioValuations(itemType, item.id),
    ]));
    return { ...data, assetTypes: customAssetTypes, goals: goalList, histories: Object.fromEntries(entries) };
  };

  const applyPortfolioData = (data) => {
    setAssets(data.assets);
    setDebts(data.debts);
    setAssetTypes(data.assetTypes || []);
    setGoals(data.goals || []);
    setHistories(data.histories);
  };

  const refreshPortfolio = async () => {
    const data = await fetchPortfolioData();
    applyPortfolioData(data);
    return data;
  };

  useEffectPF(() => {
    let cancelled = false;
    (async () => {
      try {
        const data = await fetchPortfolioData();
        if (!cancelled) applyPortfolioData(data);
      } catch (e) {
        if (!cancelled) setErr(e.message || "Failed to load portfolio");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, []);

  const handleAddAsset = async (row) => {
    try {
      await apiCreatePortfolioAsset({
        name: row.name, kind: row.kind, sub: row.sub, value: row.value, base: row.base,
        as_of_date: row.as_of_date,
      });
      await refreshPortfolio();
      setAdding(null);
    } catch (e) { setErr(e.message || "Failed to add asset"); }
  };
  const handleAddDebt = async (row) => {
    try {
      await apiCreatePortfolioDebt({
        name: row.name, kind: row.kind, sub: row.sub, value: row.value, base: row.base,
        apr: 0, monthly: 0, as_of_date: row.as_of_date,
      });
      await refreshPortfolio();
      setAdding(null);
    } catch (e) { setErr(e.message || "Failed to add debt"); }
  };

  const handleCreateAssetType = async (payload) => {
    setBusyId("asset-type:create");
    setErr("");
    try {
      const created = await apiCreatePortfolioAssetType(payload);
      setAssetTypes((current) => [...current, created].sort((a, b) => a.name.localeCompare(b.name)));
      return created;
    } catch (e) {
      setErr(e.message || "Failed to create asset type");
      throw e;
    } finally {
      setBusyId(null);
    }
  };

  const handleUpdateAssetType = async (typeId, payload) => {
    setBusyId(`asset-type:${typeId}`);
    setErr("");
    try {
      const updated = await apiUpdatePortfolioAssetType(typeId, payload);
      setAssetTypes((current) => current
        .map((assetType) => assetType.id === typeId ? updated : assetType)
        .sort((a, b) => a.name.localeCompare(b.name)));
      return updated;
    } catch (e) {
      setErr(e.message || "Failed to update asset type");
      throw e;
    } finally {
      setBusyId(null);
    }
  };

  const handleDeleteAssetType = async (typeId) => {
    setBusyId(`asset-type:${typeId}`);
    setErr("");
    try {
      await apiDeletePortfolioAssetType(typeId);
      setAssetTypes((current) => current.filter((assetType) => assetType.id !== typeId));
      if (filter === typeId) setFilter("all");
    } catch (e) {
      setErr(e.message || "Failed to delete asset type");
      throw e;
    } finally {
      setBusyId(null);
    }
  };

  const handleDeleteAsset = async (id) => {
    setBusyId(id);
    try {
      await apiDeletePortfolioAsset(id);
      setAssets((cur) => cur.filter((a) => a.id !== id));
      setHistories((cur) => {
        const next = { ...cur };
        delete next[`asset:${id}`];
        return next;
      });
      if (activeValuation?.itemType === "asset" && activeValuation.itemId === id) setActiveValuation(null);
    } catch (e) { setErr(e.message || "Failed to delete asset"); }
    finally { setBusyId(null); }
  };
  const handleDeleteDebt = async (id) => {
    setBusyId(id);
    try {
      await apiDeletePortfolioDebt(id);
      setDebts((cur) => cur.filter((d) => d.id !== id));
      setHistories((cur) => {
        const next = { ...cur };
        delete next[`debt:${id}`];
        return next;
      });
      if (activeValuation?.itemType === "debt" && activeValuation.itemId === id) setActiveValuation(null);
    } catch (e) { setErr(e.message || "Failed to delete debt"); }
    finally { setBusyId(null); }
  };

  const handleUpdateAssetMarket = async (payload) => {
    if (!activeValuation || activeValuation.itemType !== "asset") return;
    const id = activeValuation.itemId;
    setBusyId(`valuation:asset:${id}`);
    try {
      const updated = await apiUpdatePortfolioAsset(id, payload);
      setAssets((cur) => cur.map((a) => (a.id === id ? { ...a, ...updated } : a)));
    } finally { setBusyId(null); }
  };

  const handleRecordValuation = async (payload) => {
    if (!activeValuation) return;
    const { itemType, itemId } = activeValuation;
    setBusyId(`valuation:${itemType}:${itemId}`);
    setErr("");
    try {
      await apiRecordPortfolioValuation(itemType, itemId, payload);
      await refreshPortfolio();
    } catch (e) { setErr(e.message || "Failed to record value"); }
    finally { setBusyId(null); }
  };

  const handleDeleteValuation = async (asOfDate) => {
    if (!activeValuation) return;
    const { itemType, itemId } = activeValuation;
    setBusyId(`valuation:${itemType}:${itemId}`);
    setErr("");
    try {
      await apiDeletePortfolioValuation(itemType, itemId, asOfDate);
      await refreshPortfolio();
    } catch (e) { setErr(e.message || "Failed to delete dated value"); }
    finally { setBusyId(null); }
  };

  const totals = useMemoPF(() => {
    const A = assets.reduce((s, x) => s + x.value, 0);
    const D = debts.reduce((s, x) => s + x.value, 0);
    return { A, D, net: A - D };
  }, [assets, debts]);

  const perfRows = useMemoPF(
    () => computePortfolioPerformance(assets, debts, histories, { months: PERF_WINDOWS[perfWindow] }),
    [assets, debts, histories, perfWindow],
  );

  const allocation = useMemoPF(() => {
    const map = {};
    assets.forEach((a) => { map[a.kind] = (map[a.kind] || 0) + a.value; });
    return Object.entries(map).map(([k, v]) => ({
      id: k, value: v, color: assetKinds[k]?.color || "var(--ink-3)", name: assetKinds[k]?.name || k,
    })).sort((a, b) => b.value - a.value);
  }, [assets, assetKinds]);

  const history = useMemoPF(
    () => buildPortfolioNetWorthHistory(assets, debts, histories, { months: 12 }),
    [assets, debts, histories],
  );
  const netDelta = history.length > 1 ? history[history.length - 1].value - history[0].value : 0;

  const dollars = Math.floor(Math.abs(totals.net)).toLocaleString("en-SG");
  const cents = (Math.abs(totals.net) - Math.floor(Math.abs(totals.net))).toFixed(2).slice(1);
  const netUp = netDelta >= 0;

  const filteredAssets = filter === "all" ? assets : assets.filter((a) => a.kind === filter);
  const filteredAssetTotal = filteredAssets.reduce((sum, asset) => sum + asset.value, 0);
  const assetSummaryLabel = filter === "all"
    ? "Total assets"
    : `${assetKinds[filter]?.name || filter} total`;
  const debtTotal = debts.reduce((sum, debt) => sum + debt.value, 0);

  const isEmpty = !loading && assets.length === 0 && debts.length === 0;
  const wealthTab = WEALTH_TABS[sub] || WEALTH_TABS["pf-networth"];
  const activeItem = activeValuation
    ? (activeValuation.itemType === "asset" ? assets : debts).find((item) => item.id === activeValuation.itemId)
    : null;

  if (sub === "pf-goals") {
    return (
      <div className="page">
        <div className="page-kicker">Library</div>
        <h1 className="page-title">Goals</h1>
        <div className="page-sub">Net-worth milestones, measured against what you hold today.</div>
        {err && (
          <div className="panel panel-pad" style={{ marginTop: 18, color: "var(--debit)", fontSize: 13 }}>{err}</div>
        )}
        <div style={{ height: 18 }} />
        <GoalsCard goals={goals} net={totals.net} busyId={busyId} privacy={privacy}
          onCreate={createGoal} onUpdate={updateGoal} onDelete={deleteGoal} />
      </div>
    );
  }

  return (
    <div className="page">
      <div className="page-kicker">Portfolio</div>
      <h1 className="page-title">{wealthTab.title}</h1>
      <div className="page-sub">
        {wealthTab.sub}{" "}
        {assets.length} {assets.length === 1 ? "asset" : "assets"} and {debts.length} {debts.length === 1 ? "liability" : "liabilities"} tracked.
      </div>

      {err && (
        <div className="panel panel-pad" style={{ marginTop: 18, color: "var(--debit)", fontSize: 13 }}>
          {err}
        </div>
      )}

      {loading && (
        <div className="panel panel-pad" style={{ marginTop: 18, color: "var(--ink-3)", fontSize: 13 }}>
          Loading portfolio…
        </div>
      )}

      {isEmpty && (
        <div className="panel panel-pad" style={{ marginTop: 18, textAlign: "center", padding: "60px 32px" }}>
          <div style={{ fontFamily: "Bodoni Moda, serif", fontSize: 26, color: "var(--ink-2)" }}>
            Build your portfolio.
          </div>
          <div style={{ fontSize: 13, color: "var(--ink-3)", marginTop: 8, marginBottom: 20 }}>
            Track every account, holding, and obligation in one place.
          </div>
          <div style={{ display: "inline-flex", gap: 10 }}>
            <button className="btn primary" onClick={() => setAdding("asset")}>
              <Icon name="plus" size={12} stroke={2.2} /> Add asset
            </button>
            <button className="btn" onClick={() => setAdding("debt")}>
              <Icon name="plus" size={12} stroke={2.2} /> Add debt
            </button>
            <button className="btn" onClick={() => setManagingTypes(true)}>Manage types</button>
          </div>
          {adding === "asset" && (
            <div style={{ marginTop: 24, textAlign: "left" }}>
              <AddRowForm kind="asset" assetKinds={assetKinds} onCreateAssetType={handleCreateAssetType}
                onSave={handleAddAsset} onCancel={() => setAdding(null)} />
            </div>
          )}
          {adding === "debt" && (
            <div style={{ marginTop: 24, textAlign: "left" }}>
              <AddRowForm kind="debt" onSave={handleAddDebt} onCancel={() => setAdding(null)} />
            </div>
          )}
        </div>
      )}

      {!loading && !isEmpty && (
      <>
      <div style={{ height: 28 }} />

      {sub === "pf-networth" && (
      <div>
        <div className="hero">
          <div className="hero-row">
            <div>
              <div className="hero-label">Net Worth · Total</div>
              <div className="hero-amount tnum" style={{ filter: privacy ? "blur(10px)" : "none" }}>
                <span className="sym">S$</span>{totals.net < 0 ? "−" : ""}{dollars}<span className="cents">{cents}</span>
              </div>
              <div className={"hero-delta" + (netUp ? "" : " down")}>
                {history.length > 1 ? (
                  <>
                    <Icon name={netUp ? "arrowUp" : "arrowDown"} size={12} stroke={2} />
                    {netUp ? "+" : "−"}S${Math.abs(netDelta).toLocaleString("en-SG", { maximumFractionDigits: 0 })}
                    {" · "}{(Math.abs(netDelta) / Math.max(1, Math.abs(history[0].value)) * 100).toFixed(1)}% since first point
                  </>
                ) : "Add another dated value to measure change"}
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
      </div>
      )}

      {sub === "pf-allocation" && (
      <div className="grid-2">
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
                    {(((allocation[0]?.value || 0) / Math.max(1, totals.A)) * 100).toFixed(1)}%
                  </div>
                </div>
              }
            />
          </div>
        </div>

        <div className="panel">
          <div className="panel-hd">
            <h3>Class breakdown</h3>
            <div className="tools"><span>Value · share · positions</span></div>
          </div>
          <div className="panel-pad">
            <div style={{ display: "grid", gridTemplateColumns: "1fr auto auto auto", gap: "8px 16px", fontSize: 13, alignItems: "baseline" }}>
              <div className="tag">Class</div><div className="tag">Value</div><div className="tag">% of assets</div><div className="tag">Positions</div>
              {allocation.map((a) => (
                <React.Fragment key={a.id}>
                  <span><span className="dot" style={{ background: a.color, marginRight: 6 }}></span>{a.name}</span>
                  <span className="tnum">{fmtSGD(a.value, privacy)}</span>
                  <span className="mono">{((a.value / Math.max(1, totals.A)) * 100).toFixed(1)}%</span>
                  <span className="mono">{assets.filter((x) => x.kind === a.id).length}</span>
                </React.Fragment>
              ))}
            </div>
          </div>
        </div>
      </div>
      )}

      {sub === "pf-holdings" && (
      <>
      <div style={{ height: 28 }} />
      <div className="panel">
        <div className="panel-hd">
          <h3>Assets <em>· holdings</em></h3>
          <div className="tools" style={{ gap: 12 }}>
            <div className="filterbar" style={{ padding: 0 }}>
              <div className="seg">
                {[["all", "All"], ...Object.entries(assetKinds).map(([k, v]) => [k, v.name])].map(([k, lab]) => (
                  <button key={k} className={filter === k ? "on" : ""} onClick={() => setFilter(k)}>{lab}</button>
                ))}
              </div>
            </div>
            <button className="btn ghost" onClick={() => setManagingTypes(true)}>Manage types</button>
            <button className="btn" onClick={() => setAdding(adding === "asset" ? null : "asset")}>
              <Icon name="plus" size={12} stroke={2.2} /> Add asset
            </button>
          </div>
        </div>

        {adding === "asset" && (
          <AddRowForm kind="asset"
            assetKinds={assetKinds}
            onCreateAssetType={handleCreateAssetType}
            onSave={handleAddAsset}
            onCancel={() => setAdding(null)} />
        )}

        <div className="pf-table-hd">
          <div>Holding</div>
          <div>Class</div>
          <div className="num">First recorded</div>
          <div>Trend · 12M</div>
          <div className="num">Δ</div>
          <div className="num">Value</div>
        </div>
        <div className="pf-table">
          {filteredAssets.map((a) => {
            const k = assetKinds[a.kind] || { color: "var(--ink-3)", name: a.kind, glyph: "·" };
            const series = getPortfolioItemSeries(histories, "asset", a.id);
            const firstValue = series[0] ?? a.value;
            const delta = a.value - firstValue;
            const pct = (delta / Math.max(1, firstValue)) * 100;
            return (
              <div key={a.id} className={"pf-row" + (activeValuation?.itemType === "asset" && activeValuation.itemId === a.id ? " selected" : "")}>
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
                  {fmtSGD(firstValue, privacy)}
                </div>
                <div className="pf-cell">
                  {series.length > 1 ? <MiniSpark data={series} /> : <span className="hint">1 point</span>}
                </div>
                <div className={"pf-cell num pf-delta " + (delta >= 0 ? "up" : "down")}>
                  <span>{series.length > 1 ? `${delta >= 0 ? "+" : "−"}${Math.abs(pct).toFixed(2)}%` : "—"}</span>
                </div>
                <div className="pf-cell num pf-val">
                  <span>{fmtSGD(a.value, privacy)}</span>
                  <button className="pf-row-history" title="Record value and view history"
                    onClick={() => setActiveValuation({ itemType: "asset", itemId: a.id })}>
                    <Icon name="calendar" size={12} stroke={1.8} />
                  </button>
                  <button
                    className="pf-row-del" title="Remove" disabled={busyId === a.id}
                    onClick={(e) => { e.stopPropagation(); handleDeleteAsset(a.id); }}
                  ><Icon name="close" size={11} stroke={2} /></button>
                </div>
              </div>
            );
          })}
        </div>
        <div className="pf-table-summary">
          <div className="pf-table-summary-label">
            <strong>{assetSummaryLabel}</strong>
            <span>{filteredAssets.length} {filteredAssets.length === 1 ? "asset" : "assets"}</span>
          </div>
          <div className="pf-table-summary-value asset">{fmtSGD(filteredAssetTotal, privacy)}</div>
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
            onSave={handleAddDebt}
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
            const series = getPortfolioItemSeries(histories, "debt", d.id);
            const firstValue = series[0] ?? d.value;
            const delta = d.value - firstValue;
            const pct = (delta / Math.max(1, firstValue)) * 100;
            return (
              <div key={d.id} className={"pf-row debts" + (activeValuation?.itemType === "debt" && activeValuation.itemId === d.id ? " selected" : "")}>
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
                  {series.length > 1 ? <MiniSpark data={series} /> : <span className="hint">1 point</span>}
                </div>
                <div className={"pf-cell num pf-delta " + (delta <= 0 ? "up" : "down")}>
                  <span>{series.length > 1 ? `${delta >= 0 ? "+" : "−"}${Math.abs(pct).toFixed(2)}%` : "—"}</span>
                </div>
                <div className="pf-cell num pf-val" style={{ color: "var(--debit)" }}>
                  <span>−{fmtSGD(d.value, privacy)}</span>
                  <button className="pf-row-history" title="Record balance and view history"
                    onClick={() => setActiveValuation({ itemType: "debt", itemId: d.id })}>
                    <Icon name="calendar" size={12} stroke={1.8} />
                  </button>
                  <button
                    className="pf-row-del" title="Remove" disabled={busyId === d.id}
                    onClick={(e) => { e.stopPropagation(); handleDeleteDebt(d.id); }}
                  ><Icon name="close" size={11} stroke={2} /></button>
                </div>
              </div>
            );
          })}
        </div>
        <div className="pf-table-summary">
          <div className="pf-table-summary-label">
            <strong>Total debts</strong>
            <span>{debts.length} {debts.length === 1 ? "liability" : "liabilities"}</span>
          </div>
          <div className="pf-table-summary-value debt">{fmtSGD(-debtTotal, privacy)}</div>
        </div>
      </div>
      </>
      )}

      {sub === "pf-networth" && (
      <>
      <div style={{ height: 24 }} />
      <div className="grid-2">
        {(() => {
          const top = debts.reduce((m, d) => ((d.apr || 0) > (m?.apr || 0) ? d : m), null);
          return (
            <StatBlock
              label="Highest APR debt"
              value={top ? `${(top.apr || 0).toFixed(1)}%` : "—"}
              sub={top ? `${top.name} · pay first` : "No tracked debts"}
            />
          );
        })()}
        <StatBlock label="Net worth" value={fmtSGD(totals.net, privacy)} sub="Assets minus liabilities" accent />
      </div>
      </>
      )}

      {sub === "pf-allocation" && (
      <>
      <div style={{ height: 24 }} />
      <div className="grid-2">
        <StatBlock label="Equity exposure" value={`${(((allocation.find(x => x.id === "equities")?.value || 0) + (allocation.find(x => x.id === "crypto")?.value || 0)) / Math.max(1, totals.A) * 100).toFixed(1)}%`} sub="Equities + crypto · target 35%" />
        <StatBlock label="Liquidity" value={fmtSGD((allocation.find(x => x.id === "cash")?.value || 0), privacy)} sub="Cash & savings on hand" />
      </div>
      </>
      )}

      {sub === "pf-performance" && (
      <>
      <div style={{ height: 28 }} />
      <div className="panel">
        <div className="panel-hd">
          <h3>Performance <em>· by position</em></h3>
          <div className="tools">
            <div className="seg">
              {Object.keys(PERF_WINDOWS).map((w) => (
                <button key={w} className={perfWindow === w ? "on" : ""} onClick={() => setPerfWindow(w)}>{w}</button>
              ))}
            </div>
          </div>
        </div>
        <div className="panel-pad">
          <div style={{ display: "grid", gridTemplateColumns: "1fr auto auto auto auto", gap: "10px 18px", fontSize: 13, alignItems: "center" }}>
            <div className="tag">Item</div><div className="tag">Now</div><div className="tag">Change</div><div className="tag">%</div><div className="tag">Trend</div>
            {perfRows.items.map((row) => (
              <React.Fragment key={row.key}>
                <span>{row.itemType === "debt" ? <span className="hint">debt · </span> : null}{row.label}</span>
                <span className="tnum">{row.current == null ? "—" : fmtSGD(row.itemType === "debt" ? -row.current : row.current, privacy)}</span>
                <span className="tnum" style={{ color: row.delta == null ? "var(--ink-3)" : row.delta >= 0 ? "var(--credit)" : "var(--debit)" }}>
                  {row.delta == null ? "—" : `${row.delta >= 0 ? "+" : "−"}${fmtSGD(Math.abs(row.delta), privacy)}`}
                </span>
                <span className="mono" style={{ color: row.deltaPct == null ? "var(--ink-3)" : row.deltaPct >= 0 ? "var(--credit)" : "var(--debit)" }}>
                  {row.deltaPct == null ? "—" : `${row.deltaPct >= 0 ? "+" : "−"}${Math.abs(row.deltaPct).toFixed(1)}%`}
                </span>
                <span>{row.series.length > 1 ? <MiniSpark data={row.series} /> : <span className="hint">—</span>}</span>
              </React.Fragment>
            ))}
          </div>
          <div className="pf-table-summary" style={{ marginTop: 14 }}>
            <div className="pf-table-summary-label">
              <strong>Net worth</strong>
              <span>{perfWindow === "All" ? "since first valuation" : `over ${perfWindow}`}</span>
            </div>
            <div className="pf-table-summary-value" style={{ color: (perfRows.total.delta ?? 0) >= 0 ? "var(--credit)" : "var(--debit)" }}>
              {perfRows.total.delta == null ? "—"
                : `${perfRows.total.delta >= 0 ? "+" : "−"}${fmtSGD(Math.abs(perfRows.total.delta), privacy)}`}
              {perfRows.total.deltaPct != null && (
                <span className="mono" style={{ fontSize: 12, marginLeft: 8 }}>
                  {perfRows.total.deltaPct >= 0 ? "+" : "−"}{Math.abs(perfRows.total.deltaPct).toFixed(1)}%
                </span>
              )}
            </div>
          </div>
        </div>
      </div>
      </>
      )}
      </>
      )}
      {activeItem && activeValuation && (
        <ValuationPanel
          itemType={activeValuation.itemType}
          item={activeItem}
          history={histories[`${activeValuation.itemType}:${activeValuation.itemId}`] || []}
          busy={busyId === `valuation:${activeValuation.itemType}:${activeValuation.itemId}`}
          onSave={handleRecordValuation}
          onDelete={handleDeleteValuation}
          onUpdateMarket={handleUpdateAssetMarket}
          onClose={() => setActiveValuation(null)}
        />
      )}
      {managingTypes && (
        <AssetTypeManager
          assetTypes={assetTypes}
          assets={assets}
          busyId={busyId}
          onCreate={handleCreateAssetType}
          onUpdate={handleUpdateAssetType}
          onDelete={handleDeleteAssetType}
          onClose={() => setManagingTypes(false)}
        />
      )}
    </div>
  );
}

Object.assign(window, { PortfolioPage });

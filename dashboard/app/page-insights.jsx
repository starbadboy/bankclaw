// Insights page — charts, top merchants, category deep-dive
const { useMemo: useMemoIN, useState: useStateIN, useRef: useRefIN, useEffect: useEffectIN } = React;

// ── Category trend helpers ────────────────────────────────────────────────
const _CT_COLORS = [
  "oklch(0.45 0.09 145)", "oklch(0.48 0.11 35)", "oklch(0.55 0.09 250)",
  "oklch(0.6 0.12 70)",   "oklch(0.52 0.1 310)", "oklch(0.62 0.1 200)",
  "oklch(0.58 0.12 20)",  "oklch(0.5 0.08 90)",  "oklch(0.55 0.08 170)",
  "oklch(0.5 0.02 70)",
];

function _ctMonthInputValue(d) {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
}

function _ctParseMonth(s) {
  const [y, m] = String(s || "").split("-").map(Number);
  if (!y || !m) return null;
  return new Date(y, m - 1, 1);
}

function _ctMonthKey(d) {
  return `${d.getFullYear()}-${String(d.getMonth()).padStart(2, "0")}`;
}

function _ctMonthsBetween(start, end) {
  const out = [];
  const cur = new Date(start.getFullYear(), start.getMonth(), 1);
  const stop = new Date(end.getFullYear(), end.getMonth(), 1);
  while (cur <= stop && out.length < 60) {
    out.push({
      key: _ctMonthKey(cur),
      label: cur.toLocaleDateString("en-GB", { month: "short", year: "2-digit" }),
      date: new Date(cur),
    });
    cur.setMonth(cur.getMonth() + 1);
  }
  return out;
}

function CategoryTrendChart({ months, series, height = 280, privacy = false }) {
  const wrapRef = useRefIN(null);
  const [w, setW] = useStateIN(700);
  const [hoverIdx, setHoverIdx] = useStateIN(null);

  useEffectIN(() => {
    if (!wrapRef.current) return;
    const ro = new ResizeObserver((ents) => { for (const e of ents) setW(e.contentRect.width); });
    ro.observe(wrapRef.current);
    return () => ro.disconnect();
  }, []);

  const padL = 44, padR = 12, padTop = 14, padBottom = 28;
  const innerW = Math.max(50, w - padL - padR);
  const innerH = Math.max(40, height - padTop - padBottom);
  const maxVal = Math.max(1, ...series.flatMap((s) => s.values));
  const xAt = (i) => padL + (months.length <= 1 ? innerW / 2 : (i * innerW) / (months.length - 1));
  const yAt = (v) => padTop + (1 - v / maxVal) * innerH;
  const ticks = [0, 0.25, 0.5, 0.75, 1].map((t) => t * maxVal);
  const fmtTick = (t) => t >= 1000 ? `${(t / 1000).toFixed(t >= 10000 ? 0 : 1)}k` : Math.round(t).toString();

  const handleMove = (e) => {
    if (months.length === 0) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const step = months.length > 1 ? innerW / (months.length - 1) : innerW;
    const idx = Math.max(0, Math.min(months.length - 1, Math.round((x - padL) / Math.max(1, step))));
    setHoverIdx(idx);
  };

  return (
    <div ref={wrapRef} style={{ height, position: "relative", filter: privacy ? "blur(8px)" : "none" }}>
      <svg width={w} height={height} style={{ overflow: "visible", display: "block" }}
        onMouseMove={handleMove} onMouseLeave={() => setHoverIdx(null)}>
        {ticks.map((t, i) => (
          <g key={i}>
            <line x1={padL} x2={w - padR} y1={yAt(t)} y2={yAt(t)} stroke="oklch(0.9 0.008 80)" strokeDasharray="2 4" />
            <text x={padL - 6} y={yAt(t) + 3} fontSize="9" textAnchor="end" fill="var(--ink-4)">{fmtTick(t)}</text>
          </g>
        ))}
        {months.map((m, i) => (
          <text key={m.key} x={xAt(i)} y={height - 8} fontSize="10" textAnchor="middle" fill="var(--ink-4)">{m.label}</text>
        ))}
        {series.map((s) => {
          const path = s.values.map((v, i) => `${i === 0 ? "M" : "L"} ${xAt(i)} ${yAt(v)}`).join(" ");
          return (
            <g key={s.id}>
              <path d={path} fill="none" stroke={s.color} strokeWidth="1.6" />
              {s.values.map((v, i) => (
                <circle key={i} cx={xAt(i)} cy={yAt(v)} r="2.5" fill={s.color} />
              ))}
            </g>
          );
        })}
        {hoverIdx != null && months[hoverIdx] && (
          <line x1={xAt(hoverIdx)} x2={xAt(hoverIdx)} y1={padTop} y2={padTop + innerH} stroke="var(--ink-4)" strokeDasharray="2 3" />
        )}
      </svg>
      {hoverIdx != null && months[hoverIdx] && series.length > 0 && (
        <div style={{
          position: "absolute",
          left: Math.min(Math.max(8, xAt(hoverIdx) + 10), w - 180),
          top: 8, background: "var(--paper)", border: "1px solid var(--rule)",
          borderRadius: 4, padding: "8px 10px", fontSize: 11, minWidth: 160,
          boxShadow: "0 2px 6px rgba(0,0,0,0.06)", pointerEvents: "none",
        }}>
          <div style={{ fontWeight: 600, marginBottom: 6 }}>{months[hoverIdx].label}</div>
          {series.map((s) => (
            <div key={s.id} style={{ display: "flex", justifyContent: "space-between", gap: 12, marginTop: 2 }}>
              <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
                <span style={{ width: 8, height: 8, background: s.color, borderRadius: 2, display: "inline-block" }}></span>
                {s.name}
              </span>
              <span className="mono">{fmtSGD(s.values[hoverIdx], privacy).replace("−", "")}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// Detect recurring charges: same description appearing in 2+ distinct calendar months
// with a consistent amount (within 5%). Returns sorted by amount desc.
function detectRecurring(transactions) {
  const map = new Map();
  transactions.forEach((t) => {
    if (t.amount >= 0) return; // expenses only
    const key = t.description.trim().toLowerCase();
    if (!map.has(key)) map.set(key, { name: t.description, entries: [] });
    map.get(key).entries.push({ date: new Date(t.date), amount: -t.amount });
  });

  const results = [];
  map.forEach(({ name, entries }) => {
    if (entries.length < 2) return;
    // Check spans at least 2 distinct months
    const months = new Set(entries.map((e) => `${e.date.getFullYear()}-${e.date.getMonth()}`));
    if (months.size < 2) return;
    // Amount consistency: all within 5% of median
    const amounts = entries.map((e) => e.amount).sort((a, b) => a - b);
    const median = amounts[Math.floor(amounts.length / 2)];
    if (!amounts.every((a) => Math.abs(a - median) / median < 0.05)) return;
    // Estimate next charge: last occurrence + ~30 days
    const last = entries.reduce((mx, e) => e.date > mx ? e.date : mx, entries[0].date);
    const next = new Date(last); next.setDate(next.getDate() + 30);
    results.push({ name, amt: median, next, freq: "Monthly" });
  });

  return results.sort((a, b) => b.amt - a.amt);
}

const _IN_RANGES = [
  { id: "1m",  label: "Last month" },
  { id: "3m",  label: "Last 3 months" },
  { id: "6m",  label: "Last 6 months" },
  { id: "all", label: "All time" },
];

function insightsFilter(txns, rangeId) {
  if (rangeId === "all") return txns;
  const now = new Date();
  let cutoff = new Date(now);
  if (rangeId === "1m") cutoff = new Date(now.getFullYear(), now.getMonth() - 1, 1);
  if (rangeId === "3m") cutoff = new Date(now.getFullYear(), now.getMonth() - 3, 1);
  if (rangeId === "6m") cutoff = new Date(now.getFullYear(), now.getMonth() - 6, 1);
  return txns.filter((t) => new Date(t.date) >= cutoff);
}

function InsightsPage({ transactions, privacy }) {
  const [range, setRange] = useStateIN("6m");
  const [showRangeMenu, setShowRangeMenu] = useStateIN(false);
  const [excludedCats, setExcludedCats] = useStateIN(new Set());

  const filtered = useMemoIN(() => insightsFilter(transactions, range), [transactions, range]);

  const recurring = useMemoIN(() => detectRecurring(transactions), [transactions]);
  const byCat = useMemoIN(() => spendByCategory(filtered), [filtered]);
  const catColors = ["oklch(0.45 0.09 145)", "oklch(0.48 0.11 35)", "oklch(0.55 0.09 250)", "oklch(0.6 0.12 70)", "oklch(0.52 0.1 310)", "oklch(0.62 0.1 200)", "oklch(0.58 0.12 20)", "oklch(0.5 0.08 90)", "oklch(0.55 0.08 170)", "oklch(0.5 0.02 70)"];
  const allSegments = byCat.map((c, i) => ({ id: c.id, value: c.total, color: catColors[i % catColors.length], cat: c.cat }));
  const segments = allSegments.filter(s => !excludedCats.has(s.id));
  const totalSpend = segments.reduce((s, c) => s + c.value, 0) || 1;

  const toggleCat = (id) => setExcludedCats((prev) => {
    const next = new Set(prev);
    next.has(id) ? next.delete(id) : next.add(id);
    return next;
  });

  const activeRange = _IN_RANGES.find((r) => r.id === range);

  // Monthly bars — driven by filtered range, showing up to 12 buckets
  const months = useMemoIN(() => {
    const bucketMap = new Map();
    filtered.forEach((t) => {
      const d = new Date(t.date);
      const key = `${d.getFullYear()}-${String(d.getMonth()).padStart(2,"0")}`;
      const label = d.toLocaleDateString("en-GB", { month: "short" }).toUpperCase();
      if (!bucketMap.has(key)) bucketMap.set(key, { key, label, income: 0, spend: 0 });
      const b = bucketMap.get(key);
      if (t.amount > 0) b.income += t.amount; else b.spend += -t.amount;
    });
    return [...bucketMap.entries()]
      .sort((a, b) => a[0].localeCompare(b[0]))
      .map(([, v]) => v)
      .slice(-12);
  }, [filtered]);

  // ── Category trend (multi-line by month) ────────────────────────────────
  // Trend windows end at LAST month — current month is excluded since data is
  // only complete through the previous calendar month.
  const _ctNow = new Date();
  const _ctLastMonthStart = new Date(_ctNow.getFullYear(), _ctNow.getMonth() - 1, 1);
  const _ctLastMonthEnd = new Date(_ctNow.getFullYear(), _ctNow.getMonth(), 0); // last day of prev month
  const [trendMode, setTrendMode] = useStateIN("preset"); // "preset" | "custom"
  const [trendPreset, setTrendPreset] = useStateIN("6m"); // "3m" | "6m" | "12m" | "all"
  const [trendFrom, setTrendFrom] = useStateIN(_ctMonthInputValue(new Date(_ctNow.getFullYear(), _ctNow.getMonth() - 6, 1)));
  const [trendTo, setTrendTo] = useStateIN(_ctMonthInputValue(_ctLastMonthStart));
  const [trendCats, setTrendCats] = useStateIN(null); // null = auto top 3; otherwise Set<catId>

  const trendRange = useMemoIN(() => {
    if (trendMode === "custom") {
      const a = _ctParseMonth(trendFrom) || new Date(_ctNow.getFullYear(), _ctNow.getMonth() - 6, 1);
      const b = _ctParseMonth(trendTo) || _ctLastMonthStart;
      const start = a <= b ? a : b;
      const hi = a <= b ? b : a;
      const end = new Date(hi.getFullYear(), hi.getMonth() + 1, 0); // last day of hi month
      return { start, end };
    }
    if (trendPreset === "all") {
      if (transactions.length === 0) return { start: _ctLastMonthStart, end: _ctLastMonthEnd };
      const minTs = transactions.reduce((mn, t) => Math.min(mn, new Date(t.date).getTime()), Infinity);
      const minD = new Date(minTs);
      return { start: new Date(minD.getFullYear(), minD.getMonth(), 1), end: _ctLastMonthEnd };
    }
    const n = trendPreset === "3m" ? 3 : trendPreset === "12m" ? 12 : 6;
    // End at last full month; start n months before that.
    return {
      start: new Date(_ctLastMonthStart.getFullYear(), _ctLastMonthStart.getMonth() - (n - 1), 1),
      end: _ctLastMonthEnd,
    };
  }, [trendMode, trendPreset, trendFrom, trendTo, transactions]);

  const trendMonths = useMemoIN(() => _ctMonthsBetween(trendRange.start, trendRange.end), [trendRange]);

  const trendTxns = useMemoIN(() => transactions.filter((t) => {
    const d = new Date(t.date);
    return d >= trendRange.start && d <= trendRange.end;
  }), [transactions, trendRange]);

  const trendCatTotals = useMemoIN(() => {
    const map = new Map();
    trendTxns.forEach((t) => {
      if (t.amount >= 0) return;
      if (t.category === "Transfer") return;
      map.set(t.category, (map.get(t.category) || 0) + -t.amount);
    });
    return [...map.entries()]
      .map(([id, total]) => ({ id, total, cat: getCatInfo(id) }))
      .sort((a, b) => b.total - a.total);
  }, [trendTxns]);

  const effectiveTrendCats = useMemoIN(() => {
    if (trendCats) return trendCats;
    return new Set(trendCatTotals.slice(0, 3).map((c) => c.id));
  }, [trendCats, trendCatTotals]);

  const toggleTrendCat = (id) => {
    const next = new Set(effectiveTrendCats);
    next.has(id) ? next.delete(id) : next.add(id);
    setTrendCats(next);
  };

  const trendSeries = useMemoIN(() => {
    if (trendMonths.length === 0) return [];
    const idxByKey = new Map(trendMonths.map((m, i) => [m.key, i]));
    const orderedIds = trendCatTotals.map((c) => c.id);
    const perCat = new Map();
    orderedIds.forEach((id) => {
      if (effectiveTrendCats.has(id)) perCat.set(id, new Array(trendMonths.length).fill(0));
    });
    trendTxns.forEach((t) => {
      if (t.amount >= 0 || t.category === "Transfer") return;
      if (!effectiveTrendCats.has(t.category)) return;
      const d = new Date(t.date);
      const i = idxByKey.get(_ctMonthKey(d));
      if (i == null) return;
      perCat.get(t.category)[i] += -t.amount;
    });
    return [...perCat.entries()].map(([id, values]) => {
      const colorIdx = orderedIds.indexOf(id);
      return {
        id,
        name: getCatInfo(id)?.name || id,
        color: _CT_COLORS[(colorIdx >= 0 ? colorIdx : 0) % _CT_COLORS.length],
        values,
      };
    });
  }, [trendMonths, trendTxns, effectiveTrendCats, trendCatTotals]);

  const topMerchants = useMemoIN(() => {
    const map = new Map();
    filtered.forEach((t) => {
      if (t.amount >= 0) return;
      const k = t.description;
      if (!map.has(k)) map.set(k, { name: k, count: 0, total: 0, cat: t.category });
      const o = map.get(k); o.count++; o.total += -t.amount;
    });
    return [...map.values()].sort((a, b) => b.total - a.total).slice(0, 8);
  }, [filtered]);


  return (
    <div className="page">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end" }}>
        <div>
          <div className="page-kicker">Insights</div>
          <h1 className="page-title">The <i>shape</i> of your money.</h1>
          <div className="page-sub">{filtered.length} transactions · {activeRange.label.toLowerCase()}.</div>
        </div>
        <div style={{ position: "relative", marginBottom: 8 }}>
          <button
            className="btn"
            style={{ display: "flex", alignItems: "center", gap: 6 }}
            onClick={() => setShowRangeMenu(v => !v)}
          >
            <Icon name="clock" size={13} /> {activeRange.label} <Icon name="chevronD" size={12} />
          </button>
          {showRangeMenu && (
            <div style={{
              position: "absolute", top: "100%", right: 0, marginTop: 4,
              background: "var(--paper)", border: "1px solid var(--rule)",
              borderRadius: 6, boxShadow: "0 4px 12px rgba(0,0,0,0.08)",
              zIndex: 50, minWidth: 160,
            }}>
              {_IN_RANGES.map((r) => (
                <button key={r.id}
                  onClick={() => { setRange(r.id); setShowRangeMenu(false); setExcludedCats(new Set()); }}
                  style={{
                    display: "block", width: "100%", textAlign: "left",
                    padding: "9px 14px", fontSize: 13, border: "none", cursor: "pointer",
                    color: "var(--ink-1)",
                    fontWeight: range === r.id ? 600 : 400,
                    background: range === r.id ? "var(--surface)" : "transparent",
                  }}
                >
                  {r.label}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      <div style={{ height: 28 }} />

      {transactions.length === 0 && (
        <div className="panel panel-pad" style={{ textAlign: "center", padding: "80px 32px" }}>
          <div style={{ fontFamily: "Instrument Serif, serif", fontSize: 24, color: "var(--ink-3)" }}>No data yet.</div>
          <div style={{ fontSize: 13, color: "var(--ink-4)", marginTop: 8 }}>Import a bank statement to see your spending insights.</div>
        </div>
      )}
      {transactions.length > 0 && (<>

      <div className="grid-2">
        <div className="panel">
          <div className="panel-hd">
            <h3>Cash flow · {activeRange.label.toLowerCase()}</h3>
            <div className="legend">
              <span><span className="sw" style={{ background: "oklch(0.48 0.09 150)" }}></span>In</span>
              <span><span className="sw" style={{ background: "oklch(0.48 0.11 35)" }}></span>Out</span>
            </div>
          </div>
          <div className="panel-pad">
            <Bars data={months} height={220} privacy={privacy} />
            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 16, marginTop: 20, paddingTop: 20, borderTop: "1px solid var(--rule)" }}>
              <div><div className="tag">6-month income</div><div className="display tnum" style={{ fontSize: 24, color: "var(--credit)" }}>{fmtSGD(months.reduce((s,m)=>s+m.income,0), privacy)}</div></div>
              <div><div className="tag">6-month spend</div><div className="display tnum" style={{ fontSize: 24, color: "var(--debit)" }}>{fmtSGD(-months.reduce((s,m)=>s+m.spend,0), privacy)}</div></div>
              <div><div className="tag">Savings rate</div><div className="display tnum" style={{ fontSize: 24 }}>
                {(() => { const i = months.reduce((s,m)=>s+m.income,0), sp = months.reduce((s,m)=>s+m.spend,0); return Math.round(((i-sp)/i)*100)+"%"; })()}
              </div></div>
            </div>
          </div>
        </div>

        <div className="panel">
          <div className="panel-hd">
            <h3>Category split</h3>
            <div className="tools">
              {excludedCats.size > 0 && (
                <button className="btn ghost" style={{ fontSize: 11 }} onClick={() => setExcludedCats(new Set())}>
                  Reset ({excludedCats.size} hidden)
                </button>
              )}
              <span className="hint">Click to exclude</span>
            </div>
          </div>
          <div className="panel-pad" style={{ display: "grid", gridTemplateColumns: "200px 1fr", gap: 20, alignItems: "center" }}>
            <div style={{ filter: privacy ? "blur(8px)" : "none" }}>
              <Ring
                segments={segments}
                center={
                  segments.length > 0 ? (
                    <div>
                      <div style={{ fontFamily: "Instrument Serif, serif", fontSize: 28, lineHeight: 1 }}>
                        {Math.round((segments[0]?.value / totalSpend) * 100)}%
                      </div>
                      <div style={{ fontSize: 10, letterSpacing: "0.14em", textTransform: "uppercase", color: "var(--ink-4)" }}>
                        {segments[0]?.cat?.name}
                      </div>
                    </div>
                  ) : <div style={{ fontSize: 12, color: "var(--ink-4)" }}>All hidden</div>
                }
              />
            </div>
            <div>
              {allSegments.map((s) => {
                const excluded = excludedCats.has(s.id);
                return (
                  <div key={s.id}
                    onClick={() => toggleCat(s.id)}
                    style={{
                      display: "grid", gridTemplateColumns: "auto 1fr auto", gap: 10,
                      padding: "6px 4px", alignItems: "center", fontSize: 13,
                      cursor: "pointer", borderRadius: 4,
                      opacity: excluded ? 0.35 : 1,
                      transition: "opacity 0.15s",
                    }}
                  >
                    <span style={{ width: 9, height: 9, background: excluded ? "var(--ink-4)" : s.color, borderRadius: 2, transition: "background 0.15s" }}></span>
                    <span style={{ textDecoration: excluded ? "line-through" : "none", color: excluded ? "var(--ink-4)" : "var(--ink-1)" }}>
                      {s.cat?.name}
                    </span>
                    <span className="mono" style={{ fontSize: 12, color: "var(--ink-3)" }}>
                      {excluded ? "—" : fmtSGD(-s.value, privacy).replace("−","")}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>

      <div style={{ height: 24 }} />

      <div className="panel">
        <div className="panel-hd">
          <h3>Category trend</h3>
          <div className="tools" style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
            <div className="seg" style={{ marginRight: 4 }}>
              <button className={trendMode === "preset" ? "on" : ""} onClick={() => setTrendMode("preset")}>Preset</button>
              <button className={trendMode === "custom" ? "on" : ""} onClick={() => setTrendMode("custom")}>Custom</button>
            </div>
            {trendMode === "preset" ? (
              <div className="seg">
                {[["3m", "Last 3 mo"], ["6m", "Last 6 mo"], ["12m", "Last 12 mo"], ["all", "All time"]].map(([k, v]) => (
                  <button key={k} className={trendPreset === k ? "on" : ""} onClick={() => setTrendPreset(k)}>{v}</button>
                ))}
              </div>
            ) : (
              <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12 }}>
                <input type="month" value={trendFrom} onChange={(e) => setTrendFrom(e.target.value)}
                  style={{ padding: "5px 7px", border: "1px solid var(--rule)", borderRadius: 4, background: "var(--paper)", color: "var(--ink-1)", fontSize: 12 }} />
                <span style={{ color: "var(--ink-4)" }}>→</span>
                <input type="month" value={trendTo} onChange={(e) => setTrendTo(e.target.value)}
                  style={{ padding: "5px 7px", border: "1px solid var(--rule)", borderRadius: 4, background: "var(--paper)", color: "var(--ink-1)", fontSize: 12 }} />
              </div>
            )}
          </div>
        </div>
        <div className="panel-pad">
          {trendCatTotals.length === 0 ? (
            <div style={{ padding: "40px 0", textAlign: "center", fontSize: 13, color: "var(--ink-4)" }}>
              No spend in this range.
            </div>
          ) : (
            <>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 6, alignItems: "center", marginBottom: 14 }}>
                <span className="hint" style={{ marginRight: 4 }}>Categories:</span>
                {trendCatTotals.map((c, i) => {
                  const active = effectiveTrendCats.has(c.id);
                  const color = _CT_COLORS[i % _CT_COLORS.length];
                  return (
                    <button key={c.id} className="chip"
                      onClick={() => toggleTrendCat(c.id)}
                      style={{
                        cursor: "pointer",
                        opacity: active ? 1 : 0.45,
                        borderColor: active ? color : "var(--rule)",
                      }}>
                      <span className="sw" style={{ background: color }}></span>
                      {c.cat?.name || c.id}
                    </button>
                  );
                })}
                <div style={{ flex: 1 }}></div>
                <button className="btn ghost" style={{ fontSize: 11 }}
                  onClick={() => setTrendCats(new Set(trendCatTotals.map((c) => c.id)))}>
                  Select all
                </button>
                <button className="btn ghost" style={{ fontSize: 11 }}
                  onClick={() => setTrendCats(new Set())}>
                  Clear
                </button>
              </div>
              <CategoryTrendChart months={trendMonths} series={trendSeries} privacy={privacy} />
              {trendSeries.length === 0 && (
                <div style={{ padding: "12px 0 0", textAlign: "center", fontSize: 12, color: "var(--ink-4)" }}>
                  Pick a category to chart.
                </div>
              )}
            </>
          )}
        </div>
      </div>

      <div style={{ height: 24 }} />

      <div className="grid-2">
        <div className="panel">
          <div className="panel-hd">
            <h3>Top merchants</h3>
            <div className="tools"><span className="hint">By total spend</span></div>
          </div>
          <div style={{ padding: "4px 0 8px" }}>
            {topMerchants.map((m, i) => {
              const cat = getCatInfo(m.cat);
              const pct = Math.round((m.total / topMerchants[0].total) * 100);
              return (
                <div key={m.name} style={{ display: "grid", gridTemplateColumns: "28px 1fr auto", padding: "12px 20px", borderTop: "1px solid var(--rule)", alignItems: "center", gap: 12 }}>
                  <div className="mono" style={{ fontSize: 11, color: "var(--ink-4)" }}>{String(i+1).padStart(2,"0")}</div>
                  <div>
                    <div style={{ fontSize: 13 }}>{m.name}</div>
                    <div style={{ fontSize: 11, color: "var(--ink-4)", marginTop: 2 }}>{cat?.name} · {m.count}×</div>
                    <div className="cat-bar" style={{ "--w": `${pct}%`, marginTop: 6 }}></div>
                  </div>
                  <div className="mono tnum" style={{ fontSize: 13 }}>{fmtSGD(-m.total, privacy).replace("−","")}</div>
                </div>
              );
            })}
          </div>
        </div>

        <div className="panel">
          <div className="panel-hd">
            <h3>Recurring, watched</h3>
            <div className="tools"><span className="hint">Auto-detected · {recurring.length} found</span></div>
          </div>
          <div style={{ padding: "4px 0 8px" }}>
            {recurring.length === 0 && (
              <div style={{ padding: "32px 20px", fontSize: 13, color: "var(--ink-4)", textAlign: "center" }}>
                No recurring charges detected yet. Import more statements to see patterns.
              </div>
            )}
            {recurring.map((s) => (
              <div key={s.name} style={{ display: "grid", gridTemplateColumns: "1fr auto auto", padding: "14px 20px", borderTop: "1px solid var(--rule)", alignItems: "center", gap: 18 }}>
                <div>
                  <div style={{ fontSize: 13 }}>{s.name}</div>
                  <div style={{ fontSize: 11, color: "var(--ink-4)" }}>
                    Next charge · {s.next.toLocaleDateString("en-GB", { month: "short", day: "numeric" })}
                  </div>
                </div>
                <div className="chip" style={{ cursor: "default" }}>{s.freq}</div>
                <div className="mono tnum" style={{ fontSize: 13, color: "var(--debit)" }}>{fmtSGD(-s.amt, privacy)}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
      </>)}
    </div>
  );
}

Object.assign(window, { InsightsPage });

// Overview page
const { useState: useStateOV, useMemo: useMemoOV } = React;

const _OV_RANGES = [
  { id: "last_month", label: "Last month" },
  { id: "month",      label: "This month" },
  { id: "30d",        label: "Last 30 days" },
  { id: "90d",        label: "Last 90 days" },
  { id: "all",        label: "All time" },
];

function filterByRange(txns, rangeId) {
  const now = new Date();
  if (rangeId === "month") {
    return txns.filter((t) => {
      const d = new Date(t.date);
      return d.getFullYear() === now.getFullYear() && d.getMonth() === now.getMonth();
    });
  }
  if (rangeId === "last_month") {
    const lm = new Date(now.getFullYear(), now.getMonth() - 1, 1);
    return txns.filter((t) => {
      const d = new Date(t.date);
      return d.getFullYear() === lm.getFullYear() && d.getMonth() === lm.getMonth();
    });
  }
  if (rangeId === "30d" || rangeId === "90d") {
    const days = rangeId === "30d" ? 30 : 90;
    const cutoff = new Date(now); cutoff.setDate(cutoff.getDate() - days);
    return txns.filter((t) => new Date(t.date) >= cutoff);
  }
  return txns; // "all"
}

function OverviewPage({ transactions, privacy, onNav, onOpenTx }) {
  const [catRange, setCatRange] = useStateOV("last_month");
  const [showRangeMenu, setShowRangeMenu] = useStateOV(false);

  const catTxns = useMemoOV(() => filterByRange(transactions, catRange), [transactions, catRange]);
  const recent = useMemoOV(
    () => [...transactions].sort((a, b) => new Date(b.date) - new Date(a.date)).slice(0, 8),
    [transactions],
  );
  const totals = useMemoOV(() => totalsFor(transactions), [transactions]);
  const flow = useMemoOV(() => dailyFlow(transactions, 30), [transactions]);
  const byCat = useMemoOV(() => spendByCategory(catTxns).slice(0, 6), [catTxns]);
  const topSpend = byCat[0]?.total || 1;
  const activeRange = _OV_RANGES.find((r) => r.id === catRange);

  const statsThisMonth = useMemoOV(() => {
    const now = new Date();
    const thisMonth = transactions.filter((t) => {
      const d = new Date(t.date);
      return d.getFullYear() === now.getFullYear() && d.getMonth() === now.getMonth();
    });
    const biggest = thisMonth.filter(t => t.amount < 0).sort((a, b) => a.amount - b.amount)[0];
    const merchantMap = new Map();
    thisMonth.filter(t => t.amount < 0).forEach(t => {
      if (!merchantMap.has(t.description)) merchantMap.set(t.description, { count: 0, total: 0 });
      const m = merchantMap.get(t.description); m.count++; m.total += -t.amount;
    });
    const topM = [...merchantMap.entries()].sort((a, b) => b[1].total - a[1].total)[0];
    const spendDays = Math.min(now.getDate(), new Date(now.getFullYear(), now.getMonth()+1, 0).getDate());
    const totalSpend = thisMonth.filter(t => t.amount < 0).reduce((s, t) => s - t.amount, 0);
    const avgDaily = spendDays > 0 ? totalSpend / spendDays : 0;
    // Recurring: descriptions appearing in 2+ distinct months
    const descMonths = new Map();
    transactions.filter(t => t.amount < 0).forEach(t => {
      const key = t.description.trim().toLowerCase();
      if (!descMonths.has(key)) descMonths.set(key, new Set());
      const d = new Date(t.date);
      descMonths.get(key).add(`${d.getFullYear()}-${d.getMonth()}`);
    });
    const recurCount = [...descMonths.values()].filter(s => s.size >= 2).length;
    return { biggest, topM, avgDaily, spendDays, recurCount };
  }, [transactions]);

  const balance = totals.net;
  const absBalance = Math.abs(balance);
  const dollars = Math.floor(absBalance).toLocaleString("en-SG");
  const cents = (absBalance - Math.floor(absBalance)).toFixed(2).slice(1);
  const userName = (getEmail() || "").split("@")[0] || "there";

  return (
    <div className="page">
      <div className="page-kicker">Ledger · {new Date().toLocaleDateString("en-GB", { month: "long", year: "numeric" })}</div>
      <h1 className="page-title">Good morning, <i>{userName}.</i></h1>
      <div className="page-sub">
        {transactions.length > 0
          ? `${transactions.length} transactions loaded across your statements.`
          : "No transactions yet. Import a bank statement to get started."}
      </div>

      <div style={{ height: 28 }} />

      <div className="grid-2">
        {/* Hero */}
        <div className="hero">
          <div className="hero-row">
            <div>
              <div className="hero-label">Net Worth — Liquid</div>
              <div className="hero-amount tnum" style={{ filter: privacy ? "blur(10px)" : "none" }}>
                {balance < 0 ? "−" : ""}{dollars}<span className="cents">{cents}</span>
              </div>
              <div className="hero-delta">
                <Icon name={totals.net >= 0 ? "arrowUp" : "arrowDown"} size={12} stroke={2} />
                {totals.count} transactions loaded
              </div>
            </div>
            <div style={{ textAlign: "right" }}>
              <div className="hero-label">30-day cash flow</div>
              <div className="legend" style={{ marginTop: 8, justifyContent: "flex-end" }}>
                <span><span className="sw" style={{ background: "oklch(0.48 0.09 150)" }}></span>In</span>
                <span><span className="sw" style={{ background: "oklch(0.48 0.11 35)" }}></span>Out</span>
              </div>
            </div>
          </div>

          <div style={{ marginTop: 20 }}>
            <Sparkline data={flow} height={140} privacy={privacy} />
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 16, marginTop: 20, paddingTop: 20, borderTop: "1px solid var(--rule)" }}>
            <div>
              <div className="tag">Money in</div>
              <div className="display tnum" style={{ fontSize: 26, marginTop: 2, color: "var(--credit)" }}>
                {fmtSGD(totals.income, privacy)}
              </div>
            </div>
            <div>
              <div className="tag">Money out</div>
              <div className="display tnum" style={{ fontSize: 26, marginTop: 2, color: "var(--debit)" }}>
                {fmtSGD(-totals.spend, privacy)}
              </div>
            </div>
            <div>
              <div className="tag">Net</div>
              <div className="display tnum" style={{ fontSize: 26, marginTop: 2 }}>
                {fmtSGD(totals.net, privacy)}
              </div>
            </div>
          </div>
        </div>

        {/* Category breakdown */}
        <div className="panel">
          <div className="panel-hd">
            <h3>Where it goes</h3>
            <div className="tools" style={{ position: "relative" }}>
              <button
                className="btn ghost"
                style={{ fontSize: 12, display: "flex", alignItems: "center", gap: 4 }}
                onClick={() => setShowRangeMenu((v) => !v)}
              >
                {activeRange.label} <Icon name="chevronD" size={12} />
              </button>
              {showRangeMenu && (
                <div style={{
                  position: "absolute", top: "100%", right: 0, marginTop: 4,
                  background: "var(--paper)", border: "1px solid var(--rule)",
                  borderRadius: 6, boxShadow: "0 4px 12px rgba(0,0,0,0.08)",
                  zIndex: 50, minWidth: 140,
                }}>
                  {_OV_RANGES.map((r) => (
                    <button key={r.id}
                      onClick={() => { setCatRange(r.id); setShowRangeMenu(false); }}
                      style={{
                        display: "block", width: "100%", textAlign: "left",
                        padding: "8px 14px", fontSize: 13, background: "none",
                        border: "none", cursor: "pointer", color: "var(--ink-1)",
                        fontWeight: catRange === r.id ? 600 : 400,
                        background: catRange === r.id ? "var(--surface)" : "transparent",
                      }}
                    >
                      {r.label}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
          <div className="panel-pad" style={{ paddingTop: 16 }}>
            {byCat.map((r, i) => {
              const pct = Math.round((r.total / topSpend) * 100);
              return (
                <div key={r.id} className="cat-row">
                  <span className="cat-glyph">{r.cat?.glyph}</span>
                  <div>
                    <div className="cat-name">{r.cat?.name}</div>
                    <div className="cat-bar" style={{ "--w": `${pct}%` }}></div>
                  </div>
                  <div className="cat-amt">{fmtSGD(-r.total, privacy).replace("−","")}</div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Stat strip */}
      <div style={{ height: 20 }} />
      <div className="grid-4">
        <StatBlock
          label="Largest expense"
          value={statsThisMonth.biggest ? fmtSGD(statsThisMonth.biggest.amount, privacy) : "—"}
          sub={statsThisMonth.biggest ? `${statsThisMonth.biggest.description} · ${fmtDate(statsThisMonth.biggest.date)}` : "No expenses this month"}
        />
        <StatBlock
          label="Subscriptions"
          value={statsThisMonth.recurCount > 0 ? String(statsThisMonth.recurCount) : "—"}
          sub={statsThisMonth.recurCount > 0 ? "View recurring charges →" : "None detected yet"}
          onClick={statsThisMonth.recurCount > 0 ? () => onNav("insights") : undefined}
        />
        <StatBlock
          label="Top merchant"
          value={statsThisMonth.topM ? statsThisMonth.topM[0] : "—"}
          sub={statsThisMonth.topM ? `${statsThisMonth.topM[1].count}× · ${fmtSGD(-statsThisMonth.topM[1].total, privacy)}` : "No spend yet"}
        />
        <StatBlock
          label="Avg daily spend"
          value={statsThisMonth.avgDaily > 0 ? fmtSGD(-statsThisMonth.avgDaily, privacy) : "—"}
          sub={`based on ${statsThisMonth.spendDays} days this month`}
          accent
        />
      </div>

      {/* Recent transactions */}
      <div style={{ height: 28 }} />
      <div className="panel">
        <div className="panel-hd">
          <h3>Recent activity</h3>
          <div className="tools">
            <a className="btn ghost" onClick={() => onNav("transactions")} style={{ fontSize: 12 }}>
              View all <Icon name="arrowRight" size={12} />
            </a>
          </div>
        </div>
        <div className="ledger-hd">
          <div>Date</div>
          <div>Description</div>
          <div className="num">Category</div>
          <div className="num">Amount</div>
        </div>
        <div className="ledger">
          {recent.map((t) => {
            const cat = getCatInfo(t.category);
            return (
              <div key={t.id} className="row" onClick={() => onOpenTx(t)}>
                <div className="cell mono" style={{ color: "var(--ink-3)", fontSize: 12 }}>
                  {fmtDate(t.date)}
                </div>
                <div className="cell desc">
                  <div>{t.description}</div>
                  <div className="sub">
                    <BankBadge bankId={t.bank} /> · {t.reference}
                  </div>
                </div>
                <div className="cell num" style={{ justifyContent: "flex-end", color: "var(--ink-3)", fontSize: 12 }}>
                  <span>{cat?.glyph} {cat?.name}</span>
                </div>
                <div className={"cell num amt " + (t.amount > 0 ? "credit" : "debit")}>
                  {fmtSGD(t.amount, privacy)}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

Object.assign(window, { OverviewPage });

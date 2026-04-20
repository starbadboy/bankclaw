// Insights page — charts, top merchants, category deep-dive
const { useMemo: useMemoIN } = React;

function InsightsPage({ transactions, privacy }) {
  const byCat = useMemoIN(() => spendByCategory(transactions), [transactions]);
  const totalSpend = byCat.reduce((s, c) => s + c.total, 0) || 1;
  const catColors = ["oklch(0.45 0.09 145)", "oklch(0.48 0.11 35)", "oklch(0.55 0.09 250)", "oklch(0.6 0.12 70)", "oklch(0.52 0.1 310)", "oklch(0.62 0.1 200)", "oklch(0.58 0.12 20)", "oklch(0.5 0.08 90)", "oklch(0.55 0.08 170)", "oklch(0.5 0.02 70)"];
  const segments = byCat.map((c, i) => ({ id: c.id, value: c.total, color: catColors[i % catColors.length], cat: c.cat }));

  // Monthly bars — last 6 months
  const months = useMemoIN(() => {
    const buckets = [];
    const now = new Date();
    for (let i = 5; i >= 0; i--) {
      const d = new Date(now); d.setMonth(d.getMonth() - i);
      const y = d.getFullYear(), m = d.getMonth();
      const label = d.toLocaleDateString("en-GB", { month: "short" }).toUpperCase();
      let income = 0, spend = 0;
      transactions.forEach((t) => {
        const td = new Date(t.date);
        if (td.getFullYear() === y && td.getMonth() === m) {
          if (t.amount > 0) income += t.amount; else spend += -t.amount;
        }
      });
      buckets.push({ label, income, spend });
    }
    return buckets;
  }, [transactions]);

  const topMerchants = useMemoIN(() => {
    const map = new Map();
    transactions.forEach((t) => {
      if (t.amount >= 0) return;
      const k = t.description;
      if (!map.has(k)) map.set(k, { name: k, count: 0, total: 0, cat: t.category });
      const o = map.get(k); o.count++; o.total += -t.amount;
    });
    return [...map.values()].sort((a, b) => b.total - a.total).slice(0, 8);
  }, [transactions]);

  const topCat = byCat[0];
  const topPct = topCat ? Math.round((topCat.total / totalSpend) * 100) : 0;

  return (
    <div className="page">
      <div className="page-kicker">Insights</div>
      <h1 className="page-title">The <i>shape</i> of your money.</h1>
      <div className="page-sub">{transactions.length} transactions. Here&rsquo;s what the ledger says.</div>

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
            <h3>Cash flow · last 6 months</h3>
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
            <div className="tools"><span>This period</span></div>
          </div>
          <div className="panel-pad" style={{ display: "grid", gridTemplateColumns: "200px 1fr", gap: 20, alignItems: "center" }}>
            <div style={{ filter: privacy ? "blur(8px)" : "none" }}>
              <Ring
                segments={segments}
                center={
                  <div>
                    <div style={{ fontFamily: "Instrument Serif, serif", fontSize: 28, lineHeight: 1 }}>
                      {topPct}%
                    </div>
                    <div style={{ fontSize: 10, letterSpacing: "0.14em", textTransform: "uppercase", color: "var(--ink-4)" }}>
                      {topCat.cat?.name}
                    </div>
                  </div>
                }
              />
            </div>
            <div>
              {segments.map((s, i) => (
                <div key={s.id} style={{ display: "grid", gridTemplateColumns: "auto 1fr auto", gap: 10, padding: "6px 0", alignItems: "center", fontSize: 13 }}>
                  <span style={{ width: 9, height: 9, background: s.color, borderRadius: 2 }}></span>
                  <span>{s.cat?.name}</span>
                  <span className="mono" style={{ fontSize: 12, color: "var(--ink-3)" }}>{fmtSGD(-s.value, privacy).replace("−","")}</span>
                </div>
              ))}
            </div>
          </div>
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
              const cat = CATEGORIES.find((c) => c.id === m.cat);
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
            <div className="tools"><span className="hint">Auto-detected subscriptions</span></div>
          </div>
          <div style={{ padding: "4px 0 8px" }}>
            {[
              { name: "Spotify Premium", amt: 10.98, next: "Apr 24", cat: "entertainment" },
              { name: "Netflix Standard", amt: 19.98, next: "Apr 28", cat: "entertainment" },
              { name: "Singtel Fibre Broadband", amt: 59.90, next: "May 01", cat: "utilities" },
              { name: "StarHub Mobile", amt: 42.00, next: "May 03", cat: "utilities" },
              { name: "Rent — Tiong Bahru", amt: 3200.00, next: "May 01", cat: "utilities" },
            ].map((s) => (
              <div key={s.name} style={{ display: "grid", gridTemplateColumns: "1fr auto auto", padding: "14px 20px", borderTop: "1px solid var(--rule)", alignItems: "center", gap: 18 }}>
                <div>
                  <div style={{ fontSize: 13 }}>{s.name}</div>
                  <div style={{ fontSize: 11, color: "var(--ink-4)" }}>Next charge · {s.next}</div>
                </div>
                <div className="chip" style={{ cursor: "default" }}>Monthly</div>
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

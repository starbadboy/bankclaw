// Overview page
const { useState: useStateOV, useMemo: useMemoOV } = React;

function OverviewPage({ transactions, privacy, onNav, onOpenTx }) {
  const recent = transactions.slice(0, 8);
  const totals = useMemoOV(() => totalsFor(transactions), [transactions]);
  const flow = useMemoOV(() => dailyFlow(transactions, 30), [transactions]);
  const byCat = useMemoOV(() => spendByCategory(transactions).slice(0, 6), [transactions]);
  const topSpend = byCat[0]?.total || 1;

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
            <div className="tools">
              <span>This month</span><Icon name="chevronD" size={12} />
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
        <StatBlock label="Largest expense" value={fmtSGD(-2380.00, privacy)} sub="Singapore Airlines · Apr 02" />
        <StatBlock label="Subscriptions" value={fmtSGD(-89.88, privacy)} sub="4 recurring · next: Apr 24" />
        <StatBlock label="Top merchant" value="Grab" sub="24 visits · S$412 this month" />
        <StatBlock label="Avg daily spend" value={fmtSGD(-98.24, privacy)} sub="−12% vs last month" accent />
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
            const cat = CATEGORIES.find((c) => c.id === t.category);
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

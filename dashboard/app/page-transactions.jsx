// Transactions page — full filterable ledger
const { useState: useStateTX, useMemo: useMemoTX } = React;

function TransactionsPage({ transactions, privacy, query, onOpenTx, initialBank, initialCategory }) {
  const [activeCats, setActiveCats] = useStateTX(initialCategory ? [initialCategory] : []);
  const [activeBanks, setActiveBanks] = useStateTX(initialBank ? [initialBank] : []);
  const [range, setRange] = useStateTX("all");
  const [dir, setDir] = useStateTX("all"); // all | in | out

  const toggle = (arr, val, setter) => {
    setter(arr.includes(val) ? arr.filter((x) => x !== val) : [...arr, val]);
  };

  const filtered = useMemoTX(() => {
    const now = new Date();
    const cutoff = new Date(now);
    if (range === "7d") cutoff.setDate(cutoff.getDate() - 7);
    else if (range === "30d") cutoff.setDate(cutoff.getDate() - 30);
    else if (range === "90d") cutoff.setDate(cutoff.getDate() - 90);
    else cutoff.setFullYear(2000);

    return transactions.filter((t) => {
      if (new Date(t.date) < cutoff) return false;
      if (activeCats.length && !activeCats.includes(t.category)) return false;
      if (activeBanks.length && !activeBanks.includes(t.bank)) return false;
      if (dir === "in" && t.amount < 0) return false;
      if (dir === "out" && t.amount > 0) return false;
      if (query && !t.description.toLowerCase().includes(query.toLowerCase())
        && !t.reference.toLowerCase().includes(query.toLowerCase())) return false;
      return true;
    }).sort((a, b) => new Date(b.date) - new Date(a.date));
  }, [transactions, activeCats, activeBanks, range, dir, query]);

  const totals = useMemoTX(() => totalsFor(filtered), [filtered]);

  // Group by date divider
  const groups = useMemoTX(() => {
    const map = new Map();
    filtered.forEach((t) => {
      const k = relDateGroup(t.date);
      if (!map.has(k)) map.set(k, []);
      map.get(k).push(t);
    });
    return Array.from(map.entries());
  }, [filtered]);

  return (
    <div className="page">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end" }}>
        <div>
          <div className="page-kicker">Ledger</div>
          <h1 className="page-title"><i>Transactions.</i></h1>
          <div className="page-sub">
            {filtered.length} entries{range !== "all" ? ` · last ${range}` : " · all time"}. {query && `Matching "${query}".`}
          </div>
        </div>
        <div style={{ display: "flex", gap: 10 }}>
          <button className="btn" onClick={() => apiExportCsv()}>
            <Icon name="download" size={14} /> Export CSV
          </button>
          <button className="btn primary">
            <Icon name="plus" size={14} /> Import statement
          </button>
        </div>
      </div>

      <div style={{ height: 22 }} />

      {/* Stat strip */}
      <div className="grid-4">
        <StatBlock label="Entries" value={filtered.length.toString()} sub={`${activeCats.length ? activeCats.length + " categories" : "all categories"}`} />
        <StatBlock label="Money in" value={fmtSGD(totals.income, privacy)} sub="in selection" />
        <StatBlock label="Money out" value={fmtSGD(-totals.spend, privacy)} sub="in selection" />
        <StatBlock label="Net" value={fmtSGD(totals.net, privacy)} accent />
      </div>

      <div className="filterbar">
        <div className="seg">
          {["7d","30d","90d","all"].map((r) => (
            <button key={r} className={range === r ? "on" : ""} onClick={() => setRange(r)}>
              {r === "all" ? "All time" : r.toUpperCase()}
            </button>
          ))}
        </div>
        <div className="seg">
          {[["all","All"],["in","Money in"],["out","Money out"]].map(([k,v]) => (
            <button key={k} className={dir === k ? "on" : ""} onClick={() => setDir(k)}>{v}</button>
          ))}
        </div>
        <span style={{ width: 1, alignSelf: "stretch", background: "var(--rule)" }}></span>
        {CATEGORIES.map((c) => (
          <CategoryChip key={c.id} catId={c.id} active={activeCats.includes(c.id)}
            onClick={() => toggle(activeCats, c.id, setActiveCats)} />
        ))}
        <span style={{ width: 1, alignSelf: "stretch", background: "var(--rule)" }}></span>
        {BANKS.map((b) => (
          <span key={b.id}
            className={"chip" + (activeBanks.includes(b.id) ? " active" : "")}
            onClick={() => toggle(activeBanks, b.id, setActiveBanks)}>
            <span className="sw" style={{ background: b.color }}></span>{b.short}
          </span>
        ))}
        {(activeCats.length || activeBanks.length || dir !== "all") ? (
          <button className="btn ghost" style={{ fontSize: 12 }}
            onClick={() => { setActiveCats([]); setActiveBanks([]); setDir("all"); }}>
            Clear filters
          </button>
        ) : null}
      </div>

      <div className="panel">
        <div className="ledger-hd">
          <div>Date</div>
          <div>Description</div>
          <div className="num">Category</div>
          <div className="num">Amount</div>
        </div>

        {groups.length === 0 && <div className="empty">No transactions match your filters.</div>}

        {groups.map(([label, items]) => {
          const grpTotal = items.reduce((s, t) => s + t.amount, 0);
          return (
            <React.Fragment key={label}>
              <div className="date-divider">
                <div className="d">{label}</div>
                <div className="meta">{items.length} entries · net <span className="mono">{fmtSGD(grpTotal, privacy)}</span></div>
              </div>
              <div className="ledger">
                {items.map((t) => {
                  const cat = CATEGORIES.find((c) => c.id === t.category);
                  return (
                    <div key={t.id} className="row" onClick={() => onOpenTx(t)}>
                      <div className="cell mono" style={{ color: "var(--ink-3)", fontSize: 12 }}>
                        {fmtDate(t.date, { time: true })}
                      </div>
                      <div className="cell desc">
                        <div>{t.description}</div>
                        <div className="sub"><BankBadge bankId={t.bank} /> · {t.reference}</div>
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
            </React.Fragment>
          );
        })}
      </div>
    </div>
  );
}

Object.assign(window, { TransactionsPage });

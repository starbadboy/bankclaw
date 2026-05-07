// Transactions page — full filterable ledger
const { useState: useStateTX, useMemo: useMemoTX } = React;

function TransactionsPage({ transactions, privacy, query, onOpenTx, initialBank, initialCategory, availableCategories = [], onTxChanged, profiles = [], currentProfileId = "all" }) {
  const [addOpen, setAddOpen] = useStateTX(false);
  const [activeCats, setActiveCats] = useStateTX(initialCategory ? [initialCategory] : []);
  const [activeBanks, setActiveBanks] = useStateTX(initialBank ? [initialBank] : []);
  const [range, setRange] = useStateTX("all");
  const [dir, setDir] = useStateTX("all"); // all | in | out

  const toggle = (arr, val, setter) => {
    setter(arr.includes(val) ? arr.filter((x) => x !== val) : [...arr, val]);
  };

  const filtered = useMemoTX(() => {
    const now = new Date();
    let cutoff = new Date(now);
    if (range === "1m") cutoff = new Date(now.getFullYear(), now.getMonth() - 1, 1);
    else if (range === "3m") cutoff = new Date(now.getFullYear(), now.getMonth() - 3, 1);
    else if (range === "6m") cutoff = new Date(now.getFullYear(), now.getMonth() - 6, 1);
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

  const connectedBankIds = useMemoTX(
    () => new Set(transactions.map((t) => t.bank)),
    [transactions],
  );

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
            {filtered.length} entries{
            range === "1m" ? " · last month" :
            range === "3m" ? " · last 3 months" :
            range === "6m" ? " · last 6 months" :
            " · all time"
          }. {query && `Matching "${query}".`}
          </div>
        </div>
        <div style={{ display: "flex", gap: 10 }}>
          <button className="btn" onClick={() => apiExportCsv()}>
            <Icon name="download" size={14} /> Export CSV
          </button>
          <button className="btn" onClick={() => setAddOpen(true)}>
            <Icon name="plus" size={14} /> Add transaction
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
          {[
            ["1m", "Last month"],
            ["3m", "Last 3 months"],
            ["6m", "Last 6 months"],
            ["all", "All time"],
          ].map(([r, label]) => (
            <button key={r} className={range === r ? "on" : ""} onClick={() => setRange(r)}>
              {label}
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
        {(availableCategories || [])
          .filter((c) => c && c.custom)
          .map((c) => (
            <CategoryChip key={`custom-${c.name}`} catId={c.name} active={activeCats.includes(c.name)}
              onClick={() => toggle(activeCats, c.name, setActiveCats)} />
          ))}
        <span style={{ width: 1, alignSelf: "stretch", background: "var(--rule)" }}></span>
        {BANKS
          .filter((b) => connectedBankIds.has(b.id))
          .map((b) => (
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
                  const cat = getCatInfo(t.category);
                  return (
                    <div key={t.id} className="row" onClick={() => onOpenTx(t)}>
                      <div className="cell mono" style={{ color: "var(--ink-3)", fontSize: 12 }}>
                        {fmtDate(t.date)}
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

      {addOpen && (
        <AddTransactionModal
          onClose={() => setAddOpen(false)}
          availableCategories={availableCategories}
          onSaved={onTxChanged}
          profiles={profiles}
          currentProfileId={currentProfileId}
        />
      )}
    </div>
  );
}

function AddTransactionModal({ onClose, availableCategories = [], onSaved, profiles = [], currentProfileId = "all" }) {
  const today = new Date().toISOString().slice(0, 10);
  const defaultProfile = currentProfileId !== "all" && profiles.some((p) => p.id === currentProfileId)
    ? currentProfileId
    : (profiles.find((p) => p.is_main)?.id || profiles[0]?.id || "");
  const [date, setDate] = useStateTX(today);
  const [description, setDescription] = useStateTX("");
  const [amount, setAmount] = useStateTX("");
  const [direction, setDirection] = useStateTX("out"); // out = expense, in = income
  const [bank, setBank] = useStateTX("OCBC");
  const [categoryName, setCategoryName] = useStateTX("Other");
  const [profileId, setProfileId] = useStateTX(defaultProfile);
  const [busy, setBusy] = useStateTX(false);
  const [err, setErr] = useStateTX("");

  // Bank options: everything except the internal "other"
  const bankOptions = BANKS.filter((b) => b.id !== "other");
  const builtInCats = CATEGORIES.map((c) => ({ name: c.name, glyph: c.glyph }));
  const customCats = (availableCategories || []).filter((c) => c && c.custom).map((c) => ({ name: c.name, glyph: c.glyph || "•" }));
  const allCats = [...builtInCats, ...customCats];

  const submit = async (e) => {
    e.preventDefault();
    setErr("");
    const amt = parseFloat(amount);
    if (!description.trim()) { setErr("Description required"); return; }
    if (isNaN(amt) || amt === 0) { setErr("Amount must be a non-zero number"); return; }
    const signedAmount = direction === "out" ? -Math.abs(amt) : Math.abs(amt);
    setBusy(true);
    try {
      await apiCreateTransaction({
        date, description: description.trim(), amount: signedAmount,
        bank, category: categoryName,
        profile_id: profileId || undefined,
      });
      if (onSaved) await onSaved();
      onClose();
    } catch (e2) {
      setErr(e2.message || "Failed");
    } finally {
      setBusy(false);
    }
  };

  const inputStyle = {
    width: "100%", padding: "8px 10px", border: "1px solid var(--rule)",
    borderRadius: 4, background: "var(--paper)", color: "var(--ink-1)", fontSize: 13,
  };

  return (
    <>
      <div onClick={onClose} style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.35)", zIndex: 200 }} />
      <div style={{ position: "fixed", top: "50%", left: "50%", transform: "translate(-50%,-50%)", zIndex: 201, width: 420, maxWidth: "calc(100vw - 24px)", padding: "28px 32px", background: "var(--surface)", borderRadius: 8, boxShadow: "0 8px 40px rgba(0,0,0,0.18)", maxHeight: "90vh", overflow: "auto" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 18 }}>
          <div style={{ fontFamily: "Bodoni Moda, Georgia, serif", fontSize: 20, color: "var(--ink-1)" }}>Add transaction</div>
          <button className="icon-btn" onClick={onClose}><Icon name="close" size={14} /></button>
        </div>

        <form onSubmit={submit}>
          <div style={{ marginBottom: 12 }}>
            <div className="tag" style={{ marginBottom: 6 }}>Date</div>
            <input type="date" value={date} onChange={(e) => setDate(e.target.value)} style={inputStyle} />
          </div>

          <div style={{ marginBottom: 12 }}>
            <div className="tag" style={{ marginBottom: 6 }}>Description</div>
            <input value={description} onChange={(e) => setDescription(e.target.value)} placeholder="e.g. Coffee at Toby's" style={inputStyle} autoFocus />
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, marginBottom: 12 }}>
            <div>
              <div className="tag" style={{ marginBottom: 6 }}>Direction</div>
              <div className="seg" style={{ display: "flex" }}>
                <button type="button" className={direction === "out" ? "on" : ""} onClick={() => setDirection("out")} style={{ flex: 1 }}>Expense</button>
                <button type="button" className={direction === "in" ? "on" : ""} onClick={() => setDirection("in")} style={{ flex: 1 }}>Income</button>
              </div>
            </div>
            <div>
              <div className="tag" style={{ marginBottom: 6 }}>Amount (SGD)</div>
              <input type="number" step="0.01" value={amount} onChange={(e) => setAmount(e.target.value)} placeholder="0.00" style={inputStyle} />
            </div>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, marginBottom: 14 }}>
            <div>
              <div className="tag" style={{ marginBottom: 6 }}>Bank</div>
              <select value={bank} onChange={(e) => setBank(e.target.value)} style={inputStyle}>
                {bankOptions.map((b) => (
                  <option key={b.id} value={b.name}>{b.name}</option>
                ))}
              </select>
            </div>
            <div>
              <div className="tag" style={{ marginBottom: 6 }}>Category</div>
              <select value={categoryName} onChange={(e) => setCategoryName(e.target.value)} style={inputStyle}>
                {allCats.map((c) => (
                  <option key={c.name} value={c.name}>{c.glyph} {c.name}</option>
                ))}
              </select>
            </div>
          </div>

          {profiles.length > 1 && (
            <div style={{ marginBottom: 14 }}>
              <div className="tag" style={{ marginBottom: 6 }}>Profile</div>
              <select value={profileId} onChange={(e) => setProfileId(e.target.value)} style={inputStyle}>
                {profiles.map((p) => (
                  <option key={p.id} value={p.id}>{p.name}{p.is_main ? " (main)" : ""}</option>
                ))}
              </select>
            </div>
          )}

          {err && (
            <div style={{ marginBottom: 12, padding: "8px 10px", background: "var(--paper-2)", color: "var(--debit)", fontSize: 12, borderRadius: 4 }}>
              {err}
            </div>
          )}

          <button type="submit" disabled={busy} className="btn primary" style={{ width: "100%", padding: "11px" }}>
            {busy ? "Saving…" : "Add transaction"}
          </button>
        </form>
      </div>
    </>
  );
}

Object.assign(window, { TransactionsPage });

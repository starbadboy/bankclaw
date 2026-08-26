// Goals — kinds, projections, hero, cards and AI suggestions (rendered by PortfolioPage on the pf-goals sub-page)
const { useState: useStateGL, useMemo: useMemoGL, useEffect: useEffectGL } = React;

const GOAL_KINDS = [
  { id: "net_worth", label: "Net worth", tag: "Net worth" },
  { id: "debt_payoff", label: "Pay off a debt", tag: "Debt payoff" },
  { id: "allocation", label: "Asset allocation", tag: "Allocation" },
];

const goalKindTag = (kind) => (GOAL_KINDS.find((k) => k.id === (kind || "net_worth")) || GOAL_KINDS[0]).tag;

function goalTargetText(goal, result, assetKinds, privacy) {
  const kind = goal.kind || "net_worth";
  if (kind === "debt_payoff") {
    if (result.missing) return "Debt removed";
    return `${fmtSGD(result.current, privacy)} left of ${fmtSGD(goal.baseline, privacy)}`;
  }
  if (kind === "allocation") {
    const name = assetKinds?.[goal.asset_kind]?.name || goal.asset_kind;
    return `${name} ${result.current.toFixed(1)}% · target ${Number(goal.target_pct).toFixed(0)}%`;
  }
  return fmtSGD(goal.target_amount, privacy);
}

// Mini goal card for a draft: same bar / % / target text as a saved card, computed from today's portfolio.
function GoalPreview({ draft, goalCtx, assetKinds, privacy }) {
  const kind = draft.kind || "net_worth";
  const goal = kind === "debt_payoff" && draft.baseline == null ? { ...draft, baseline: goalCtx.debtsById?.[draft.debt_id]?.value } : draft;
  const hasTarget = kind === "net_worth" ? Number(draft.target_amount) > 0
    : kind === "debt_payoff" ? Boolean(goalCtx.debtsById?.[draft.debt_id])
    : Number(draft.target_pct) > 0;
  const result = computeGoalProgress(goal, goalCtx);
  const pct = !hasTarget ? "Enter a target" : result.done ? "Reached" : `${Math.round(result.progress * 100)}%`;
  const text = !hasTarget
    ? kind === "net_worth" ? `Net worth today ${fmtSGD(goalCtx.net, privacy)}`
      : kind === "debt_payoff" ? "Choose a debt to see its balance"
      : `${assetKinds?.[draft.asset_kind]?.name || draft.asset_kind} is ${result.current.toFixed(1)}% of assets today`
    : kind === "net_worth" ? `${fmtSGD(result.current, privacy)} of ${fmtSGD(result.target, privacy)}`
    : goalTargetText(goal, result, assetKinds, privacy) + (kind === "debt_payoff" && draft.baseline == null ? " · baseline set when you save" : "");
  return (
    <div className={"pf-goal-card pf-goal-preview" + (hasTarget && result.done ? " done" : "")}>
      <div className="pf-goal-head">
        <div className="pf-goal-title">
          <span className="tag">{goalKindTag(kind)}</span>
          <strong>{draft.name?.trim() || "Preview"}</strong>
        </div>
        <div className="pf-goal-pct tnum">{pct}</div>
      </div>
      <div className="pf-goal-bar"><div style={{ width: `${hasTarget ? result.progress * 100 : 0}%` }} /></div>
      <div className="pf-goal-meta"><span>{text}{draft.target_date ? ` · by ${draft.target_date}` : ""}</span></div>
    </div>
  );
}

function GoalForm({ debts, assetKinds, goalCtx, busy, onCreate, privacy }) {
  const [kind, setKind] = useStateGL("net_worth");
  const [name, setName] = useStateGL("");
  const [amount, setAmount] = useStateGL("");
  const [debtId, setDebtId] = useStateGL("");
  const [assetKind, setAssetKind] = useStateGL("equities");
  const [pct, setPct] = useStateGL("");
  const [targetDate, setTargetDate] = useStateGL("");
  const [error, setError] = useStateGL("");
  const canSubmit = kind === "net_worth" ? name.trim() && amount
    : kind === "debt_payoff" ? debtId
    : assetKind && pct;
  const draft = { kind, name, target_amount: amount, debt_id: debtId, asset_kind: assetKind, target_pct: pct, target_date: targetDate };
  const submit = async (e) => {
    e.preventDefault();
    setError("");
    const payload = { kind, target_date: targetDate || null };
    if (name.trim()) payload.name = name.trim();
    if (kind === "net_worth") payload.target_amount = Number(amount);
    if (kind === "debt_payoff") payload.debt_id = debtId;
    if (kind === "allocation") { payload.asset_kind = assetKind; payload.target_pct = Number(pct); }
    try {
      await onCreate(payload);
      setName(""); setAmount(""); setPct(""); setTargetDate(""); setDebtId("");
    } catch (err) { setError(err.message); }
  };
  return (
    <form onSubmit={submit} className="pf-add-row pf-goal-form">
      <div className="pf-add-grid">
        <label>
          <span>Goal kind</span>
          <select aria-label="Goal kind" value={kind} onChange={(e) => setKind(e.target.value)}>
            {GOAL_KINDS.map((k) => <option key={k.id} value={k.id}>{k.label}</option>)}
          </select>
        </label>
        {kind === "net_worth" && (
          <>
            <label>
              <span>Goal name</span>
              <input aria-label="Goal name" placeholder="e.g. First million" value={name} onChange={(e) => setName(e.target.value)} />
            </label>
            <label>
              <span>Target (S$)</span>
              <input aria-label="Target amount (S$)" type="number" min="1" step="any" placeholder="0.00" value={amount}
                onChange={(e) => setAmount(e.target.value)} />
            </label>
          </>
        )}
        {kind === "debt_payoff" && (
          <>
            <label>
              <span>Debt</span>
              <select aria-label="Debt" value={debtId} onChange={(e) => setDebtId(e.target.value)}>
                <option value="">Choose a debt…</option>
                {debts.map((d) => <option key={d.id} value={d.id}>{d.name} · {fmtSGD(d.value, false)}</option>)}
              </select>
            </label>
            <label>
              <span>Goal name <em>(optional)</em></span>
              <input aria-label="Goal name" placeholder="Pay off …" value={name} onChange={(e) => setName(e.target.value)} />
            </label>
          </>
        )}
        {kind === "allocation" && (
          <>
            <label>
              <span>Asset class</span>
              <select aria-label="Asset class" value={assetKind} onChange={(e) => setAssetKind(e.target.value)}>
                {Object.entries(assetKinds).map(([id, k]) => <option key={id} value={id}>{k.name}</option>)}
              </select>
            </label>
            <label>
              <span>Target %</span>
              <input aria-label="Target %" type="number" min="1" max="100" step="any" placeholder="e.g. 30" value={pct}
                onChange={(e) => setPct(e.target.value)} />
            </label>
            <label>
              <span>Goal name <em>(optional)</em></span>
              <input aria-label="Goal name" placeholder="Equities at 30%" value={name} onChange={(e) => setName(e.target.value)} />
            </label>
          </>
        )}
        <label>
          <span>Target date <em>(optional)</em></span>
          <input aria-label="Target date" type="date" value={targetDate} onChange={(e) => setTargetDate(e.target.value)} />
        </label>
      </div>
      <GoalPreview draft={draft} goalCtx={goalCtx} assetKinds={assetKinds} privacy={privacy} />
      <div className="pf-add-actions">
        {error && <div className="hint" style={{ color: "var(--debit)", marginRight: "auto" }}>{error}</div>}
        <button className="btn primary" type="submit" disabled={!canSubmit || busy}>
          <Icon name="plus" size={12} stroke={2.2} /> Add goal
        </button>
      </div>
    </form>
  );
}

function goalProjectionText(goal, result, projection, privacy) {
  if (result.missing) return null;
  if (result.done) return "Reached";
  const kind = goal.kind || "net_worth";
  if (kind === "allocation") return null;
  const parts = [];
  if (projection.reason === "ok") parts.push(`On this trend: ${projection.eta}`);
  else if (projection.reason === "not_enough_history") parts.push("Not enough history to project yet");
  else if (projection.reason === "not_on_track") parts.push("Not on track at the current trend");
  if (projection.monthlyNeeded != null && projection.monthlyNeeded > 0) {
    const pace = fmtSGD(Math.round(projection.monthlyNeeded), privacy);
    parts.push(kind === "debt_payoff" ? `Pay ${pace}/month to clear by ${goal.target_date}` : `Add ${pace}/month to reach it by ${goal.target_date}`);
  }
  return parts.join(" · ");
}

function GoalsHero({ goals, resultsById, projectionsById, privacy }) {
  const nearest = pickNearestGoal(goals, resultsById);
  const doneCount = goals.filter((g) => resultsById[g.id]?.done).length;
  const nearestResult = nearest ? resultsById[nearest.id] : null;
  const nearestProjection = nearest ? projectionsById[nearest.id] : null;
  return (
    <div className="pf-goal-hero">
      <StatBlock label="Next milestone" accent mono={false}
        value={nearest ? nearest.name : goals.length ? "All goals reached" : "No goals yet"}
        sub={nearest ? `${Math.round(nearestResult.progress * 100)}% there` : "Add one below or take a suggestion"} />
      <StatBlock label="Projected"
        value={nearestProjection?.reason === "ok" ? nearestProjection.eta : "—"}
        sub={nearestProjection?.reason === "not_enough_history" ? "Not enough history yet"
          : nearestProjection?.reason === "not_on_track" ? "Not on track at current trend"
          : nearestProjection?.reason === "ok" ? "On the current trend" : nearest ? "No projection for this kind" : ""} />
      <StatBlock label="Goals done" value={`${doneCount} / ${goals.length}`} sub={goals.length ? "Reached vs set" : "Nothing set yet"} />
    </div>
  );
}

function GoalRow({ goal, result, projection, assetKinds, goalCtx, busy, editing, draft, setDraft, onEdit, onSave, onCancel, onDelete, privacy }) {
  const kind = goal.kind || "net_worth";
  const kindTag = goalKindTag(kind);
  if (editing) {
    return (
      <div className="pf-goal-card editing">
        <div className="pf-add-grid">
          <label>
            <span>Goal name</span>
            <input aria-label="Goal name" value={draft.name} onChange={(e) => setDraft((cur) => ({ ...cur, name: e.target.value }))} />
          </label>
          {kind === "net_worth" && (
            <label>
              <span>Target (S$)</span>
              <input aria-label="Target amount (S$)" type="number" min="1" step="any" value={draft.target_amount}
                onChange={(e) => setDraft((cur) => ({ ...cur, target_amount: e.target.value }))} />
            </label>
          )}
          {kind === "allocation" && (
            <label>
              <span>Target %</span>
              <input aria-label="Target %" type="number" min="1" max="100" step="any" value={draft.target_pct}
                onChange={(e) => setDraft((cur) => ({ ...cur, target_pct: e.target.value }))} />
            </label>
          )}
          <label>
            <span>Target date <em>(optional)</em></span>
            <input aria-label="Target date" type="date" value={draft.target_date || ""}
              onChange={(e) => setDraft((cur) => ({ ...cur, target_date: e.target.value }))} />
          </label>
        </div>
        <GoalPreview draft={{ ...goal, ...draft }} goalCtx={goalCtx} assetKinds={assetKinds} privacy={privacy} />
        <div className="pf-add-actions">
          <button className="btn ghost" type="button" onClick={onCancel}>Cancel</button>
          <button className="btn primary" type="button" disabled={busy || !draft.name.trim()} onClick={onSave}>Save</button>
        </div>
      </div>
    );
  }
  const projectionText = goalProjectionText(goal, result, projection, privacy);
  return (
    <div className={"pf-goal-card" + (result.done ? " done" : "") + (result.missing ? " missing" : "")}>
      <div className="pf-goal-head">
        <div className="pf-goal-title">
          <span className="tag">{kindTag}</span>
          <strong>{result.done && <Icon name="check" size={12} stroke={2.2} />} {goal.name}</strong>
        </div>
        <div className="pf-goal-pct tnum">{result.missing ? "—" : result.done ? "Done" : `${Math.round(result.progress * 100)}%`}</div>
      </div>
      <div className="pf-goal-bar"><div style={{ width: `${result.progress * 100}%` }} /></div>
      <div className="pf-goal-meta">
        <span>{goalTargetText(goal, result, assetKinds, privacy)}{goal.target_date ? ` · by ${goal.target_date}` : ""}</span>
        <span className="tools">
          {!result.missing && <button className="btn ghost" type="button" disabled={busy} onClick={onEdit}>Edit</button>}
          <button className="btn ghost" type="button" disabled={busy} onClick={onDelete}>{result.missing ? "Remove goal" : "Remove"}</button>
        </span>
      </div>
      {projectionText && <div className="pf-goal-projection">{projectionText}</div>}
    </div>
  );
}

function suggestionTargetText(sug, debtsById, assetKinds, privacy) {
  if (sug.kind === "debt_payoff") return `Clear ${debtsById[sug.debt_id]?.name || "debt"}`;
  if (sug.kind === "allocation") return `${assetKinds[sug.asset_kind]?.name || sug.asset_kind} at ${Number(sug.target_pct).toFixed(0)}%`;
  return fmtSGD(sug.target_amount, privacy);
}

function GoalSuggestions({ goals, net, debtsById, assetKinds, onAdd, privacy }) {
  const [state, setState] = useStateGL({ loading: true, error: "", status: null, data: null });
  const [busyId, setBusyId] = useStateGL(null);
  const load = async (opts = {}) => {
    setState((cur) => ({ ...cur, loading: true, error: "" }));
    try {
      const data = await apiGoalSuggestions(opts);
      setState({ loading: false, error: "", status: null, data });
    } catch (e) {
      setState((cur) => ({ ...cur, loading: false, error: e.message || "Failed to load suggestions", status: e.status || null }));
    }
  };
  useEffectGL(() => { load(); }, []);

  const add = async (sug) => {
    setBusyId(sug.id);
    try {
      const payload = { kind: sug.kind, name: sug.name, target_date: sug.target_date || null };
      if (sug.kind === "net_worth") payload.target_amount = sug.target_amount;
      if (sug.kind === "debt_payoff") payload.debt_id = sug.debt_id;
      if (sug.kind === "allocation") { payload.asset_kind = sug.asset_kind; payload.target_pct = sug.target_pct; }
      await onAdd(payload);
      await load({ dismiss: sug.id });
    } catch (e) { setState((cur) => ({ ...cur, error: e.message || "Failed to add goal" })); }
    finally { setBusyId(null); }
  };
  const dismiss = async (sug) => { setBusyId(sug.id); try { await load({ dismiss: sug.id }); } finally { setBusyId(null); } };

  const data = state.data;
  const stale = data?.snapshot && (Math.round(data.snapshot.net) !== Math.round(net) || data.snapshot.goal_count !== goals.length);
  const notConfigured = state.status === 503 && /DEEPSEEK_API_KEY/.test(state.error || "");
  return (
    <div className="panel" style={{ marginTop: 18 }}>
      <div className="panel-hd">
        <h3>Suggested goals <em>· from your portfolio</em></h3>
        <div className="tools" style={{ display: "flex", gap: 10, alignItems: "center" }}>
          {data?.generated_at && !state.loading && (
            <span className="hint">{data.from_cache ? "Cached · " : ""}{new Date(data.generated_at).toLocaleString()}</span>
          )}
          {!notConfigured && (
            <button className="btn" type="button" disabled={state.loading} onClick={() => load({ force_refresh: true })}>
              <Icon name="sparkle" size={13} /> {state.loading ? "Thinking…" : "Refresh suggestions"}
            </button>
          )}
        </div>
      </div>
      <div className="panel-pad">
        {notConfigured && (
          <div className="hint">AI suggestions are not configured — set <code>DEEPSEEK_API_KEY</code> on the server to enable them. Everything else on this page works without it.</div>
        )}
        {!notConfigured && state.error && <div className="hint" style={{ color: "var(--debit)" }}>{state.error}</div>}
        {stale && !state.loading && (
          <div className="pf-sugg-stale">Your portfolio changed since these were generated — refresh for current advice.</div>
        )}
        {state.loading && !data && <div className="hint">Reading your portfolio and drafting goals…</div>}
        {data && !data.suggestions.length && !state.loading && !notConfigured && (
          <div className="hint">Nothing left to suggest right now — refresh after your portfolio changes.</div>
        )}
        {data && data.suggestions.length > 0 && (
          <div className="pf-sugg-grid">
            {data.suggestions.map((sug) => (
              <div key={sug.id} className={"pf-sugg-card prio-" + sug.priority}>
                <div className="pf-goal-head">
                  <div className="pf-goal-title">
                    <span className="tag">{goalKindTag(sug.kind)}</span>
                    <strong>{sug.name}</strong>
                  </div>
                  <span className={"pf-sugg-prio " + sug.priority}>{sug.priority}</span>
                </div>
                <div className="pf-sugg-target">{suggestionTargetText(sug, debtsById, assetKinds, privacy)}{sug.target_date ? ` · by ${sug.target_date}` : ""}</div>
                <p className="pf-sugg-why">{sug.rationale}</p>
                <div className="tools" style={{ display: "flex", gap: 6 }}>
                  <button className="btn primary" type="button" disabled={busyId === sug.id} onClick={() => add(sug)}>
                    <Icon name="plus" size={12} stroke={2.2} /> Add goal
                  </button>
                  <button className="btn ghost" type="button" disabled={busyId === sug.id} onClick={() => dismiss(sug)}>Dismiss</button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function GoalsCard({ goals, resultsById, projectionsById, goalCtx, net, debtsById, debts, assetKinds, busyId, onCreate, onUpdate, onDelete, privacy }) {
  const [editingId, setEditingId] = useStateGL(null);
  const [draft, setDraft] = useStateGL({});
  const [error, setError] = useStateGL("");
  const ordered = useMemoGL(() => [...goals].sort((a, b) => {
    const ra = resultsById[a.id], rb = resultsById[b.id];
    if (ra.done !== rb.done) return ra.done ? 1 : -1;
    return rb.progress - ra.progress;
  }), [goals, resultsById]);
  const saveEdit = async (goal) => {
    setError("");
    const payload = { name: draft.name, target_date: draft.target_date || null };
    if ((goal.kind || "net_worth") === "net_worth") payload.target_amount = Number(draft.target_amount);
    if (goal.kind === "allocation") payload.target_pct = Number(draft.target_pct);
    try { await onUpdate(goal.id, payload); setEditingId(null); }
    catch (err) { setError(err.message); }
  };
  return (
    <>
      <GoalsHero goals={goals} resultsById={resultsById} projectionsById={projectionsById} privacy={privacy} />
      <div className="panel" style={{ marginTop: 18 }}>
        <div className="panel-hd">
          <h3>Goals <em>· milestones, payoffs, allocation</em></h3>
          <div className="tools"><span>Progress vs what you hold today</span></div>
        </div>
        <div className="panel-pad">
          <div className="pf-goal-grid">
            {ordered.map((goal) => (
              <GoalRow key={goal.id} goal={goal} result={resultsById[goal.id]} projection={projectionsById[goal.id]}
                assetKinds={assetKinds} goalCtx={goalCtx} privacy={privacy} busy={busyId === `goal:${goal.id}`}
                editing={editingId === goal.id} draft={draft} setDraft={setDraft}
                onEdit={() => { setEditingId(goal.id); setDraft({ name: goal.name, target_amount: goal.target_amount, target_pct: goal.target_pct, target_date: goal.target_date }); }}
                onSave={() => saveEdit(goal)} onCancel={() => setEditingId(null)}
                onDelete={async () => { setError(""); try { await onDelete(goal.id); } catch (err) { setError(err.message); } }} />
            ))}
          </div>
          {!goals.length && <div className="hint" style={{ marginBottom: 10 }}>No goals yet — add a milestone, a debt payoff or an allocation target below.</div>}
          {error && <div className="hint" style={{ color: "var(--debit)", marginBottom: 10 }}>{error}</div>}
          <GoalForm debts={debts} assetKinds={assetKinds} goalCtx={goalCtx} busy={busyId === "goal:create"} onCreate={onCreate} privacy={privacy} />
        </div>
      </div>
      <GoalSuggestions goals={goals} net={net} debtsById={debtsById} assetKinds={assetKinds} onAdd={onCreate} privacy={privacy} />
    </>
  );
}

Object.assign(window, { GoalsCard });

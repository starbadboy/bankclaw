// Import page — drag → detect → extract → categorize → save (real API)
const { useState: useStateIM, useEffect: useEffectIM, useRef: useRefIM } = React;

function ImportPage({ privacy, onNav, onImportDone, profiles = [], currentProfileId = "all" }) {
  const [drag, setDrag] = useStateIM(false);
  const [stage, setStage] = useStateIM("drop"); // drop | processing | done | error
  const [files, setFiles] = useStateIM([]);
  const [progress, setProgress] = useStateIM({});
  const [result, setResult] = useStateIM(null);
  const [errorMsg, setErrorMsg] = useStateIM("");
  const [catPct, setCatPct] = useStateIM(0);
  const fileInputRef = useRefIM(null);
  const defaultProfile = currentProfileId !== "all" && profiles.some((p) => p.id === currentProfileId)
    ? currentProfileId
    : (profiles.find((p) => p.is_main)?.id || profiles[0]?.id || "");
  const [profileId, setProfileId] = useStateIM(defaultProfile);
  useEffectIM(() => { if (!profileId && defaultProfile) setProfileId(defaultProfile); }, [defaultProfile]);

  const processFiles = async (fileList) => {
    const arr = Array.from(fileList).filter((f) => f.name.endsWith(".pdf"));
    if (!arr.length) return;

    setFiles(arr.map((f) => ({ name: f.name, size: (f.size / 1024).toFixed(0) + " KB", status: "pending" })));
    setStage("processing");
    setProgress({});
    setCatPct(0);
    setErrorMsg("");
    setResult(null);

    // Show fake per-file progress animation while actual upload runs
    const intervals = arr.map((f, i) => {
      let p = 0;
      const iv = setInterval(() => {
        p = Math.min(p + 4 + Math.random() * 8, 90);
        setProgress((prev) => ({ ...prev, [f.name]: p }));
      }, 200 + i * 60);
      return iv;
    });

    try {
      const data = await apiImport(arr, { categorize: true, profile_id: profileId || undefined });

      // Flush all to 100%
      intervals.forEach(clearInterval);
      const done = {};
      arr.forEach((f) => { done[f.name] = 100; });
      setProgress(done);

      // Animate categorization bar
      let p = 0;
      const catIv = setInterval(() => {
        p = Math.min(p + 4 + Math.random() * 6, 100);
        setCatPct(p);
        if (p >= 100) {
          clearInterval(catIv);
          setResult(data);
          setStage("done");
          if (onImportDone) onImportDone();
        }
      }, 120);
    } catch (err) {
      intervals.forEach(clearInterval);
      setErrorMsg(err.message || "Import failed");
      setStage("error");
    }
  };

  const reset = () => {
    setStage("drop"); setFiles([]); setProgress({}); setCatPct(0); setResult(null); setErrorMsg("");
  };

  return (
    <div className="page">
      <div className="page-kicker">Ingest</div>
      <h1 className="page-title"><i>Import</i> statements.</h1>
      <div className="page-sub">
        Drop any bank PDF — Bankclaw reads 18 banks, unlocks password-protected files, runs OCR
        on scanned statements, and lets an LLM categorise every line.
      </div>

      <div style={{ height: 28 }} />

      {stage === "drop" && profiles.length > 1 && (
        <div className="panel panel-pad" style={{ marginBottom: 16, display: "flex", alignItems: "center", gap: 14, background: "var(--paper-2)" }}>
          <div className="tag" style={{ margin: 0 }}>Import into</div>
          <select value={profileId} onChange={(e) => setProfileId(e.target.value)}
            style={{ padding: "8px 10px", border: "1px solid var(--rule)", borderRadius: 4, background: "var(--paper)", color: "var(--ink-1)", fontSize: 13, minWidth: 200 }}>
            {profiles.map((p) => (
              <option key={p.id} value={p.id}>{p.name}{p.is_main ? " (main)" : ""}</option>
            ))}
          </select>
          <span style={{ fontSize: 11, color: "var(--ink-4)" }}>
            Statements will be saved under this profile.
          </span>
        </div>
      )}

      {stage === "drop" && (
        <>
          <input
            ref={fileInputRef} type="file" multiple accept=".pdf"
            style={{ display: "none" }}
            onChange={(e) => processFiles(e.target.files)}
          />
          <div className={"dropzone" + (drag ? " drag" : "")}
            onDragEnter={(e) => { e.preventDefault(); setDrag(true); }}
            onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
            onDragLeave={() => setDrag(false)}
            onDrop={(e) => { e.preventDefault(); setDrag(false); processFiles(e.dataTransfer.files); }}
            onClick={() => fileInputRef.current?.click()}>
            <div className="ic"><Icon name="upload" size={22} /></div>
            <div style={{ fontFamily: "Instrument Serif, serif", fontSize: 28, marginBottom: 6 }}>
              Drop PDFs here
            </div>
            <div className="hint">or click to browse · up to 20 files · S$0 per page</div>
            <div style={{ marginTop: 22, display: "flex", gap: 8, justifyContent: "center", flexWrap: "wrap" }}>
              {BANKS.map((b) => (
                <span key={b.id} className="chip" style={{ cursor: "default" }}>
                  <span className="sw" style={{ background: b.color }}></span>{b.name}
                </span>
              ))}
            </div>
          </div>

          <div style={{ height: 28 }} />

          <div className="grid-3">
            <div className="panel panel-pad">
              <div className="tag">01 · Detect</div>
              <div className="display" style={{ fontSize: 22, marginTop: 8, marginBottom: 6 }}>Bank auto-matched</div>
              <div style={{ fontSize: 13, color: "var(--ink-3)" }}>Fingerprints each PDF against 18 layouts. Falls back to a generic parser for unknowns.</div>
            </div>
            <div className="panel panel-pad">
              <div className="tag">02 · Extract</div>
              <div className="display" style={{ fontSize: 22, marginTop: 8, marginBottom: 6 }}>Lines reconstructed</div>
              <div style={{ fontSize: 13, color: "var(--ink-3)" }}>Preserves date, merchant, reference and amount even across multi-page layouts.</div>
            </div>
            <div className="panel panel-pad">
              <div className="tag">03 · Categorise</div>
              <div className="display" style={{ fontSize: 22, marginTop: 8, marginBottom: 6 }}>AI learns your ledger</div>
              <div style={{ fontSize: 13, color: "var(--ink-3)" }}>A small model assigns a category per line and remembers your corrections.</div>
            </div>
          </div>
        </>
      )}

      {(stage === "processing" || stage === "done") && (
        <>
          <div className="panel">
            <div className="panel-hd">
              <h3>
                {stage === "processing" && "Reading statements…"}
                {stage === "done" && "Import complete"}
              </h3>
              <div className="tools">
                {stage === "done" && <button className="btn ghost" onClick={reset}>Import more</button>}
              </div>
            </div>
            <div className="panel-pad">
              <div className="proc-list">
                {files.map((f) => {
                  const p = progress[f.name] || 0;
                  return (
                    <div key={f.name} className="proc">
                      <div className="pdf">PDF</div>
                      <div>
                        <div className="fname">{f.name}</div>
                        <div className="status">{f.size} · {p < 100 ? "Processing…" : "Done"}</div>
                        <div className="proc-bar"><div className="fill" style={{ width: `${p}%` }}></div></div>
                      </div>
                      <div className="pct">
                        {p < 100 ? `${Math.floor(p)}%` : <Icon name="check" size={16} />}
                      </div>
                    </div>
                  );
                })}
              </div>

              <div style={{ marginTop: 24, padding: 18, border: "1px solid var(--rule)", borderRadius: 6, background: "oklch(0.98 0.01 145)" }}>
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 10 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                    <Icon name="sparkle" size={16} />
                    <div style={{ fontFamily: "Instrument Serif, serif", fontSize: 18 }}>
                      {stage === "done"
                        ? `${result?.transactions?.length ?? 0} transactions imported`
                        : "DeepSeek is thinking…"}
                    </div>
                  </div>
                  <div className="mono" style={{ fontSize: 12, color: "var(--ink-3)" }}>
                    {stage === "done" ? "100%" : `${Math.floor(catPct)}%`}
                  </div>
                </div>
                <div className="proc-bar"><div className="fill" style={{ width: `${stage === "done" ? 100 : catPct}%` }}></div></div>
              </div>

              {stage === "done" && (
                <div style={{ marginTop: 24, display: "flex", gap: 10, justifyContent: "flex-end" }}>
                  <button className="btn" onClick={() => apiExportCsv()}>Download CSV</button>
                  <button className="btn primary" onClick={() => { onNav("transactions"); }}>
                    View in ledger <Icon name="arrowRight" size={12} />
                  </button>
                </div>
              )}
            </div>
          </div>
        </>
      )}

      {stage === "error" && (
        <div className="panel panel-pad" style={{ borderColor: "var(--debit)" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 16 }}>
            <Icon name="close" size={16} />
            <div style={{ fontFamily: "Instrument Serif, serif", fontSize: 20 }}>Import failed</div>
          </div>
          <div style={{ fontSize: 13, color: "var(--ink-2)", marginBottom: 20 }}>{errorMsg}</div>
          <button className="btn" onClick={reset}>Try again</button>
        </div>
      )}
    </div>
  );
}

Object.assign(window, { ImportPage });

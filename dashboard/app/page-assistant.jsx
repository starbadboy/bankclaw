// AI Assistant — free-form chat over the user's ledger and portfolio (read-only tools on the server).

const ASSISTANT_EXAMPLES = [
  "How much did I spend on food last month?",
  "What are my top 5 merchants in the last 3 months?",
  "Where could I cut back to save more each month?",
];

function AssistantChat({ messages, pending, error, draft, configured, onDraft, onSend }) {
  const canSend = configured && !pending && draft.trim().length > 0;
  const onKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); if (canSend) onSend(); }
  };
  return (
    <div className="chat panel">
      <div className="chat-log">
        {!configured && (
          <div className="chat-empty">
            <div className="chat-empty-title">AI assistant not configured.</div>
            <div className="hint">Set <code>DEEPSEEK_API_KEY</code> on the server to enable it.</div>
          </div>
        )}
        {configured && messages.length === 0 && !pending && (
          <div className="chat-empty">
            <div className="chat-empty-title">Ask anything about your money.</div>
            <div className="chat-examples">
              {ASSISTANT_EXAMPLES.map((q) => (
                <button key={q} className="chip" onClick={() => onDraft(q)}>{q}</button>
              ))}
            </div>
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} className={"chat-msg " + m.role}>{m.content}</div>
        ))}
        {pending && <div className="chat-msg assistant chat-thinking">Thinking…</div>}
      </div>
      {error && <div className="chat-error" role="alert">{error}</div>}
      <div className="chat-composer">
        <textarea
          value={draft}
          maxLength={2000}
          rows={2}
          placeholder={configured ? "Ask about your spending, goals or net worth…" : "AI assistant not configured"}
          disabled={!configured}
          onChange={(e) => onDraft(e.target.value)}
          onKeyDown={onKeyDown}
          aria-label="Message"
        />
        <button className="btn primary" disabled={!canSend} onClick={onSend}>
          <Icon name="sparkle" size={13} /> Send
        </button>
      </div>
    </div>
  );
}

function AssistantThreads({ threads, activeId, pending, onNew, onOpen, onDelete }) {
  return (
    <div className="chat-threads panel">
      <button className="btn" onClick={onNew} disabled={pending}><Icon name="plus" size={13} /> New chat</button>
      {threads.length === 0 && <div className="chat-threads-empty">No saved chats yet.</div>}
      {threads.map((t) => (
        <div key={t.id} className={"chat-thread" + (t.id === activeId ? " active" : "")}>
          <button className="chat-thread-title" onClick={() => onOpen(t.id)} disabled={pending} title={t.title}>{t.title}</button>
          <button className="chat-thread-delete" onClick={() => onDelete(t.id)} disabled={pending}
            aria-label={`Delete thread ${t.title}`} title="Delete">×</button>
        </div>
      ))}
    </div>
  );
}

function AssistantPage({ currentProfileId = "all" }) {
  const { useState: useStateAS, useEffect: useEffectAS } = React;
  const [messages, setMessages] = useStateAS([]);
  const [threadId, setThreadId] = useStateAS(null);
  const [threads, setThreads] = useStateAS([]);
  const [draft, setDraft] = useStateAS("");
  const [pending, setPending] = useStateAS(false);
  const [error, setError] = useStateAS("");
  const [configured, setConfigured] = useStateAS(true);

  const refreshThreads = async () => {
    try {
      const res = await apiAssistantThreads();
      setThreads(res.threads || []);
      setConfigured(res.configured !== false);
    } catch (e) {
      setError(e.message || "Failed to load chats");
    }
  };
  useEffectAS(() => { refreshThreads(); }, []);

  const newChat = () => { setMessages([]); setThreadId(null); setError(""); };

  const openThread = async (id) => {
    setError("");
    try {
      const thread = await apiAssistantThread(id);
      setMessages(thread.messages || []);
      setThreadId(thread.id);
    } catch (e) {
      setError(e.message || "Failed to load chat");
    }
  };

  const deleteThread = async (id) => {
    if (!window.confirm("Delete this chat? This cannot be undone.")) return;
    try {
      await apiAssistantDeleteThread(id);
      if (id === threadId) newChat();
      await refreshThreads();
    } catch (e) {
      setError(e.message || "Failed to delete chat");
    }
  };

  const send = async () => {
    const text = draft.trim();
    if (!text || pending) return;
    const before = messages;
    setMessages([...before, { role: "user", content: text }]);
    setDraft(""); setError(""); setPending(true);
    try {
      const res = await apiAssistantSend({ message: text, thread_id: threadId, profile_id: currentProfileId });
      setThreadId(res.thread.id);
      setMessages([...before, { role: "user", content: text }, { role: "assistant", content: res.reply }]);
      refreshThreads();
    } catch (e) {
      setMessages(before);
      setDraft(text);
      setError(e.message || "Assistant unavailable — try again");
    } finally {
      setPending(false);
    }
  };

  return (
    <div className="page">
      <div className="page-kicker">Ledger &amp; Wealth</div>
      <h1 className="page-title"><i>Assistant.</i></h1>
      <div className="page-sub">
        Ask questions about your transactions and portfolio. Totals are computed on the server; the model sees only
        the figures it asks for and a few example rows — never your full statements.
      </div>
      <div style={{ height: 20 }} />
      <div className="assistant-layout">
        <AssistantThreads threads={threads} activeId={threadId} pending={pending}
          onNew={newChat} onOpen={openThread} onDelete={deleteThread} />
        <AssistantChat messages={messages} pending={pending} error={error} draft={draft} configured={configured}
          onDraft={setDraft} onSend={send} />
      </div>
    </div>
  );
}

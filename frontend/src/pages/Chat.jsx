import { useCallback, useEffect, useState } from "react";
import { createThread, listThreads, resumeThread, streamMessage } from "../api.js";

export default function Chat() {
  const [threads, setThreads] = useState([]);
  const [threadId, setThreadId] = useState(null);
  const [input, setInput] = useState("");
  const [log, setLog] = useState([]);
  const [pendingApproval, setPendingApproval] = useState(null);
  const [busy, setBusy] = useState(false);
  const [editFields, setEditFields] = useState({});

  const refreshThreads = useCallback(async () => {
    const rows = await listThreads();
    setThreads(rows);
    if (!threadId && rows.length > 0) setThreadId(rows[0].id);
  }, [threadId]);

  useEffect(() => {
    refreshThreads().catch(console.error);
  }, [refreshThreads]);

  async function ensureThread() {
    if (threadId) return threadId;
    const t = await createThread();
    setThreadId(t.id);
    await refreshThreads();
    return t.id;
  }

  function pushLog(entry) {
    setLog((prev) => [...prev, entry]);
  }

  function handleSseEvent(ev) {
    if (ev.type === "approval_required") {
      setPendingApproval(ev.data?.pending || ev.data);
      setEditFields({});
      pushLog({ kind: "system", text: "Approval required — review the card below." });
      return;
    }
    if (ev.type === "tool_started") {
      pushLog({ kind: "tool", text: `Tool started: ${ev.data?.tool}` });
      return;
    }
    if (ev.type === "tool_result") {
      pushLog({ kind: "tool", text: `Tool result: ${JSON.stringify(ev.data)}` });
      return;
    }
    if (ev.type === "done") {
      pushLog({ kind: "assistant", text: ev.data?.message || "Done." });
      return;
    }
    if (ev.type === "error") {
      pushLog({ kind: "error", text: String(ev.data) });
    }
  }

  async function sendMessage(e) {
    e.preventDefault();
    if (!input.trim() || busy) return;
    setBusy(true);
    setPendingApproval(null);
    const text = input.trim();
    setInput("");
    pushLog({ kind: "user", text });
    try {
      const id = await ensureThread();
      await streamMessage(id, text, handleSseEvent);
    } catch (err) {
      pushLog({ kind: "error", text: err.message });
    } finally {
      setBusy(false);
    }
  }

  async function onApproval(decision) {
    if (!threadId || !pendingApproval) return;
    setBusy(true);
    try {
      const edits = decision === "edit" ? editFields : undefined;
      await resumeThread(threadId, decision, edits, handleSseEvent);
      if (decision === "reject") setPendingApproval(null);
      else if (decision === "approve") setPendingApproval(null);
      else setPendingApproval(null);
    } catch (err) {
      pushLog({ kind: "error", text: err.message });
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <h1>Chat</h1>
      <div style={{ display: "flex", gap: "1rem" }}>
        <aside style={{ minWidth: 160 }}>
          <button
            type="button"
            onClick={async () => {
              const t = await createThread();
              setThreadId(t.id);
              setLog([]);
              await refreshThreads();
            }}
          >
            New thread
          </button>
          <ul style={{ listStyle: "none", padding: 0 }}>
            {threads.map((t) => (
              <li key={t.id}>
                <button type="button" onClick={() => { setThreadId(t.id); setLog([]); }}>
                  #{t.id} {t.title}
                </button>
              </li>
            ))}
          </ul>
        </aside>
        <section style={{ flex: 1 }}>
          <div
            style={{
              border: "1px solid #ccc",
              minHeight: 240,
              padding: "0.75rem",
              marginBottom: "0.75rem",
              whiteSpace: "pre-wrap",
            }}
          >
            {log.map((row, i) => (
              <div key={i} style={{ marginBottom: "0.5rem" }}>
                <strong>{row.kind}:</strong> {row.text}
              </div>
            ))}
          </div>

          {pendingApproval && (
            <div
              style={{
                border: "3px solid #c62828",
                padding: "1rem",
                marginBottom: "1rem",
                background: "#ffebee",
              }}
            >
              <h2 style={{ marginTop: 0 }}>Approval required</h2>
              <pre style={{ fontSize: "0.85rem", overflow: "auto" }}>
                {JSON.stringify(pendingApproval, null, 2)}
              </pre>
              {pendingApproval.action_type === "order" && (
                <label>
                  Quantity (edit)
                  <input
                    type="number"
                    value={editFields.quantity ?? pendingApproval.quantity}
                    onChange={(e) =>
                      setEditFields({ ...editFields, quantity: Number(e.target.value) })
                    }
                  />
                </label>
              )}
              <div style={{ display: "flex", gap: "0.5rem", marginTop: "0.75rem" }}>
                <button type="button" disabled={busy} onClick={() => onApproval("approve")}>
                  Approve
                </button>
                <button type="button" disabled={busy} onClick={() => onApproval("edit")}>
                  Edit & approve
                </button>
                <button type="button" disabled={busy} onClick={() => onApproval("reject")}>
                  Reject
                </button>
              </div>
            </div>
          )}

          <form onSubmit={sendMessage} style={{ display: "flex", gap: "0.5rem" }}>
            <input
              style={{ flex: 1 }}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Message…"
              disabled={busy}
            />
            <button type="submit" disabled={busy}>
              Send
            </button>
          </form>
        </section>
      </div>
    </div>
  );
}

import { useCallback, useEffect, useState } from "react";
import { apiFetch, listAdminDocuments } from "../api.js";

export default function AdminDocuments() {
  const [docs, setDocs] = useState([]);
  const [error, setError] = useState("");
  const [title, setTitle] = useState("");
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);

  const refresh = useCallback(() => {
    listAdminDocuments()
      .then(setDocs)
      .catch((e) => setError(e.message));
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  async function onUpload(e) {
    e.preventDefault();
    if (!file || !title.trim()) return;
    setUploading(true);
    setError("");
    try {
      const form = new FormData();
      form.append("title", title.trim());
      form.append("file", file);
      const res = await fetch("/api/admin/documents", {
        method: "POST",
        credentials: "include",
        body: form,
      });
      if (!res.ok) {
        const text = await res.text();
        let detail = text;
        try {
          detail = JSON.parse(text).detail;
        } catch {
          /* keep */
        }
        throw new Error(detail);
      }
      setTitle("");
      setFile(null);
      refresh();
    } catch (err) {
      setError(err.message || "Upload failed");
    } finally {
      setUploading(false);
    }
  }

  async function onDelete(id) {
    if (!window.confirm("Delete this document from search?")) return;
    await apiFetch(`/api/admin/documents/${id}`, { method: "DELETE" });
    refresh();
  }

  return (
    <div>
      <h1>Documents</h1>
      {error && <p style={{ color: "#c62828" }}>{error}</p>}
      {docs.length === 0 ? (
        <p>No documents in the index yet. Run backend seed or upload below.</p>
      ) : (
        <ul>
          {docs.map((d) => (
            <li key={d.id}>
              {d.title} ({d.filename}) — {d.created_at}{" "}
              <button type="button" onClick={() => onDelete(d.id)}>
                Delete
              </button>
            </li>
          ))}
        </ul>
      )}
      <form onSubmit={onUpload} style={{ marginTop: "1rem", display: "flex", flexDirection: "column", gap: "0.5rem", maxWidth: 400 }}>
        <label>
          Title
          <input value={title} onChange={(e) => setTitle(e.target.value)} required />
        </label>
        <label>
          File
          <input type="file" accept=".md,.txt" onChange={(e) => setFile(e.target.files?.[0] || null)} required />
        </label>
        <button type="submit" disabled={uploading}>
          {uploading ? "Uploading…" : "Upload"}
        </button>
      </form>
    </div>
  );
}

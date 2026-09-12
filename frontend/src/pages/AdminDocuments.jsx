import { useEffect, useState } from "react";
import { listAdminDocuments } from "../api.js";

export default function AdminDocuments() {
  const [docs, setDocs] = useState([]);
  const [error, setError] = useState("");

  useEffect(() => {
    listAdminDocuments()
      .then(setDocs)
      .catch((e) => setError(e.message));
  }, []);

  if (error) return <p style={{ color: "#c62828" }}>{error}</p>;

  return (
    <div>
      <h1>Documents</h1>
      {docs.length === 0 ? (
        <p>No documents uploaded yet.</p>
      ) : (
        <ul>
          {docs.map((d) => (
            <li key={d.id}>
              {d.title} ({d.filename}) — {d.created_at}
            </li>
          ))}
        </ul>
      )}
      <p style={{ fontSize: "0.9rem", color: "#666" }}>
        Upload UI can POST multipart to /api/admin/documents (title + file).
      </p>
    </div>
  );
}

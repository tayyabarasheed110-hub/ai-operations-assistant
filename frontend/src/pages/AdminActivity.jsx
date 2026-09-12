import { useEffect, useState } from "react";
import { getAdminActivity } from "../api.js";

export default function AdminActivity() {
  const [kind, setKind] = useState("audit");
  const [rows, setRows] = useState([]);
  const [error, setError] = useState("");

  useEffect(() => {
    setError("");
    getAdminActivity(kind)
      .then(setRows)
      .catch((e) => setError(e.message));
  }, [kind]);

  return (
    <div>
      <h1>Activity</h1>
      <label>
        Kind{" "}
        <select value={kind} onChange={(e) => setKind(e.target.value)}>
          <option value="audit">audit</option>
          <option value="orders">orders</option>
          <option value="emails">emails</option>
        </select>
      </label>
      {error && <p style={{ color: "#c62828" }}>{error}</p>}
      <pre style={{ fontSize: "0.8rem", overflow: "auto", maxHeight: 400 }}>
        {JSON.stringify(rows, null, 2)}
      </pre>
    </div>
  );
}

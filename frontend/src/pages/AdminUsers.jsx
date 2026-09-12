import { useEffect, useState } from "react";
import { listAdminUsers } from "../api.js";

export default function AdminUsers() {
  const [users, setUsers] = useState([]);
  const [error, setError] = useState("");

  useEffect(() => {
    listAdminUsers()
      .then(setUsers)
      .catch((e) => setError(e.message));
  }, []);

  if (error) return <p style={{ color: "#c62828" }}>{error}</p>;

  return (
    <div>
      <h1>Users</h1>
      <table border="1" cellPadding="6" style={{ borderCollapse: "collapse", width: "100%" }}>
        <thead>
          <tr>
            <th>Email</th>
            <th>Admin</th>
            <th>Active</th>
            <th>Capabilities</th>
          </tr>
        </thead>
        <tbody>
          {users.map((u) => (
            <tr key={u.id}>
              <td>{u.email}</td>
              <td>{u.is_admin ? "yes" : "no"}</td>
              <td>{u.is_active ? "yes" : "no"}</td>
              <td>{(u.capabilities || []).join(", ") || "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

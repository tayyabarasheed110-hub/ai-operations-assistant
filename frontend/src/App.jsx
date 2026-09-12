import { Link, Outlet } from "react-router-dom";

export default function App() {
  return (
    <div style={{ fontFamily: "system-ui", margin: "1rem" }}>
      <header style={{ display: "flex", gap: "1rem", marginBottom: "1rem" }}>
        <Link to="/">Chat</Link>
        <Link to="/admin/users">Admin users</Link>
        <Link to="/admin/documents">Admin documents</Link>
        <Link to="/admin/activity">Admin activity</Link>
        <Link to="/login">Login</Link>
      </header>
      <Outlet />
    </div>
  );
}

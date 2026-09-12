import { Link, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "./auth/AuthContext.jsx";

export default function App() {
  const { user, signOut, isAdmin } = useAuth();
  const navigate = useNavigate();

  async function handleSignOut() {
    await signOut();
    navigate("/signed-out");
  }

  return (
    <div style={{ fontFamily: "system-ui", margin: "1rem", maxWidth: 960 }}>
      <header style={{ display: "flex", gap: "1rem", marginBottom: "1rem", flexWrap: "wrap" }}>
        <Link to="/">Chat</Link>
        {isAdmin && (
          <>
            <Link to="/admin/users">Admin users</Link>
            <Link to="/admin/documents">Admin documents</Link>
            <Link to="/admin/activity">Admin activity</Link>
          </>
        )}
        {user ? (
          <>
            <span style={{ marginLeft: "auto", color: "#555" }}>{user.email}</span>
            <button type="button" onClick={handleSignOut}>
              Sign out
            </button>
          </>
        ) : (
          <Link to="/login" style={{ marginLeft: "auto" }}>
            Login
          </Link>
        )}
      </header>
      <Outlet />
    </div>
  );
}

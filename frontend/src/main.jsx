import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider } from "./auth/AuthContext.jsx";
import AdminRoute from "./components/AdminRoute.jsx";
import RequireAuth from "./components/RequireAuth.jsx";
import App from "./App.jsx";
import Login from "./pages/Login.jsx";
import Chat from "./pages/Chat.jsx";
import AdminUsers from "./pages/AdminUsers.jsx";
import AdminDocuments from "./pages/AdminDocuments.jsx";
import AdminActivity from "./pages/AdminActivity.jsx";
import AccessDenied from "./pages/AccessDenied.jsx";
import SignedOut from "./pages/SignedOut.jsx";

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/" element={<App />}>
            <Route
              index
              element={
                <RequireAuth>
                  <Chat />
                </RequireAuth>
              }
            />
            <Route path="login" element={<Login />} />
            <Route
              path="admin/users"
              element={
                <AdminRoute>
                  <AdminUsers />
                </AdminRoute>
              }
            />
            <Route
              path="admin/documents"
              element={
                <AdminRoute>
                  <AdminDocuments />
                </AdminRoute>
              }
            />
            <Route
              path="admin/activity"
              element={
                <AdminRoute>
                  <AdminActivity />
                </AdminRoute>
              }
            />
            <Route path="access-denied" element={<AccessDenied />} />
            <Route path="signed-out" element={<SignedOut />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  </React.StrictMode>
);

import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
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
      <Routes>
        <Route path="/" element={<App />}>
          <Route index element={<Chat />} />
          <Route path="login" element={<Login />} />
          <Route path="admin/users" element={<AdminUsers />} />
          <Route path="admin/documents" element={<AdminDocuments />} />
          <Route path="admin/activity" element={<AdminActivity />} />
          <Route path="access-denied" element={<AccessDenied />} />
          <Route path="signed-out" element={<SignedOut />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  </React.StrictMode>
);

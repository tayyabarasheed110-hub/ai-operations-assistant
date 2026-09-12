const defaultHeaders = { "Content-Type": "application/json" };

export async function apiFetch(path, options = {}) {
  const res = await fetch(path, {
    credentials: "include",
    ...options,
    headers: { ...defaultHeaders, ...(options.headers || {}) },
  });
  if (res.status === 401 && !path.includes("/auth/sign-in")) {
    const err = new Error("Unauthorized");
    err.status = 401;
    throw err;
  }
  const text = await res.text();
  let data = null;
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = text;
    }
  }
  if (!res.ok) {
    const err = new Error(data?.detail || res.statusText || "Request failed");
    err.status = res.status;
    err.data = data;
    throw err;
  }
  return data;
}

export function signIn(email, password) {
  return apiFetch("/api/auth/sign-in", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export function signOut() {
  return apiFetch("/api/auth/sign-out", { method: "POST" });
}

export function getMe() {
  return apiFetch("/api/auth/me");
}

export function listThreads() {
  return apiFetch("/api/threads");
}

export function createThread(title = "New conversation") {
  return apiFetch("/api/threads", {
    method: "POST",
    body: JSON.stringify({ title }),
  });
}

export function listAdminUsers() {
  return apiFetch("/api/admin/users");
}

export function listAdminDocuments() {
  return apiFetch("/api/admin/documents");
}

export function getAdminActivity(kind = "audit") {
  return apiFetch(`/api/admin/activity?kind=${encodeURIComponent(kind)}`);
}

/** Parse SSE stream from POST endpoints (messages/stream, resume). */
export async function consumeSsePost(path, body, onEvent) {
  const res = await fetch(path, {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      Accept: "text/event-stream",
    },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const text = await res.text();
    let detail = text;
    try {
      detail = JSON.parse(text).detail;
    } catch {
      /* keep text */
    }
    throw new Error(detail || res.statusText);
  }
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split("\n\n");
    buffer = parts.pop() || "";
    for (const block of parts) {
      const lines = block.split("\n");
      let eventType = "message";
      let dataLine = "";
      for (const line of lines) {
        if (line.startsWith("event:")) eventType = line.slice(6).trim();
        if (line.startsWith("data:")) dataLine = line.slice(5).trim();
      }
      if (dataLine) {
        let payload = dataLine;
        try {
          payload = JSON.parse(dataLine);
        } catch {
          /* raw string */
        }
        onEvent({ type: eventType, data: payload });
      }
    }
  }
}

export function streamMessage(threadId, content, onEvent) {
  return consumeSsePost(`/api/threads/${threadId}/messages/stream`, { content }, onEvent);
}

export function resumeThread(threadId, decision, edits, onEvent) {
  return consumeSsePost(
    `/api/threads/${threadId}/resume`,
    { decision, edits: edits || undefined },
    onEvent
  );
}

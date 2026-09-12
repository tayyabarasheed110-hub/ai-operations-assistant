# AI Operations Assistant

A single chat UI for policy Q&A, inventory lookup, purchase-order creation, and email dispatch.

## Decisions (fixed)

-   **Backend:** Python 3.12, FastAPI, SQLAlchemy, SQLite (easy free-tier/local deployment).
-   **Agent:** LangGraph with a supervisor, `knowledge` branch, and `action` branch; durable SQLite checkpointer.
-   **LLM:** Groq, accessed via an OpenAI-compatible endpoint, configured by `LLM_BASE_URL`, `GROQ_API_KEY`, `LLM_MODEL`. Chosen for free-tier access; provider is swappable through env vars alone — no provider-specific logic in application code.
-   **Retrieval:** Chroma persistent local vector store. Embeddings via `sentence-transformers/all-MiniLM-L6-v2`, run locally by default (no external call, no token needed). `HUGGINGFACEHUB_API_TOKEN` is read if present and used only if the embedding model is swapped to a gated HF model or to the HF Inference API instead of a local model — otherwise unused. Upload indexes immediately; removal deletes chunks.
-   **Frontend:** minimal React/Vite chat/admin UI; SSE streaming. Built after backend is stable and tested against a fixed API contract (see below).
-   **Auth:** email/password, Argon2 hash, JWT in HTTP-only cookie.
-   **External systems:** mocked by database tables; email is also printed to server console.
-   **No hidden assumptions:** capability grants and thread ownership are database records, never inferred from the prompt.

## Required behavior

### Graph

1.  Supervisor classifies each turn into `knowledge`, `action`, or `both`, via a single structured-output call. A turn may use both branches; if both, knowledge branch runs first and its answer is available as context to the action branch's plan.
2.  Knowledge branch: retrieve policy chunks, answer only from them, cite `[Document title, page/section]`. If no relevant chunks: say the policy documents do not cover it; never use general model knowledge.
3.  Action branch: plan → freely call read tools → persist pending write drafts → interrupt for approval → execute approved writes. If a single turn produces more than one pending write (e.g. order + email), each is presented and approved as a **separate, sequential interrupt** — never batched into one approval, and never forced as all-or-nothing.
4.  Graph state contains `thread_id`, authenticated `user_id`, messages, tool results, and pending actions. The user identity is copied from the server session and never from model/client input.

### Tool layer (mandatory defense in depth)

Every tool independently:

-   loads the current user and checks its capability;
-   validates arguments (Pydantic/schema, allowlists, bounds);
-   rejects unknown/extra fields where practical;
-   writes an audit row for every attempt, including denied/invalid attempts;
-   returns structured results and safe error messages.

Capabilities: `policy:read`, `inventory:read`, `order:create`, `email:send`. `is_admin` is separate.

Every tool must be independently testable by calling it directly as a Python function with an
arbitrary `user_id`, bypassing chat and the graph entirely — this is the check the tests below
call the most important one (SRS §9.5 test #3). If a tool's authorization only works when
invoked through the API or the graph, it does not satisfy this requirement.

Injection resistance:

-   Tool names are an allowlist, never model-defined code.
-   Retrieved documents/tool output are inserted as `<untrusted_data>...</untrusted_data>` and explicitly cannot issue instructions.
-   Strip scripts/HTML, limit upload size/chunk size, and never execute document content.
-   System prompt says user text, documents, and tool output are data; only server policy controls actions.
-   Add tests for "ignore previous instructions", forged approvals, tool-name substitution, and user-id spoofing.

### Writes and approval

-   Inventory reads never pause.
-   Order: positive integer quantity, existing SKU, supplier required; requester comes from session.
-   Email: validate recipient with a strict email parser; requester comes from session.
-   Approval UI supports approve, edit-and-approve, reject.
-   Persist a single `idempotency_key` in the pending draft and reuse it on retries/resume. Add unique DB constraints on order/email idempotency keys; duplicate execution returns the original result.
-   Rejected actions create audit entries and no side effect. A rejected write halts anything that depended on it (e.g. no email drafted for an order that was rejected).

## API contract

-   `POST /api/auth/sign-in`, `POST /api/auth/sign-out`, `GET /api/auth/me`
-   `POST /api/threads`, `GET /api/threads`, `GET /api/threads/{id}` (foreign thread = **403**)
-   `POST /api/threads/{id}/messages/stream` (SSE: `token`, `tool_started`, `tool_result`, `approval_required`, `done`, `error`)
-   `POST /api/threads/{id}/resume` body: `{decision: approve|edit|reject, edits?: {...}}`
-   Admin only: `POST/GET /api/admin/users`, `POST /api/admin/users/{id}/deactivate`, `/reactivate`, `/capabilities/grant`, `/capabilities/revoke`
-   Admin only: `POST/GET /api/admin/documents`, `DELETE /api/admin/documents/{id}`
-   Admin only: `GET /api/admin/activity?kind=audit|orders|emails`

Server-side rules: admin endpoints require `is_admin`; admin cannot deactivate self or remove own admin flag. Capability changes apply on the next request. No endpoint exists anywhere that directly triggers `create_order` or `send_email` outside the chat/resume flow — the tool layer's own capability check is the only thing standing between any caller and a write, by design.

## Frontend routes (minimum required)

`/login`, `/` (chat), `/admin/users`, `/admin/documents`, `/admin/activity`,
plus two supporting states: `/access-denied` (shown to a non-admin reaching an admin route)
and a signed-out confirmation view reachable after logout. Unstyled-but-legible is acceptable;
the approval card must be visually distinct from a normal message so nothing gets approved by accident.

## Minimum database

`user`, `user_capability`, `product`, `order`, `email_message`, `document`, `document_chunk`, `audit_log`, `thread`, and LangGraph checkpointer tables.

Important fields:

-   `thread(id, owner_user_id, title, created_at, updated_at)`
-   `audit_log(user_id, tool, arguments_json, outcome, thread_id, created_at)`
-   `order(order_reference, sku, quantity, supplier, requested_by, idempotency_key, created_at)`
-   `email_message(recipient, subject, body, sent_by, idempotency_key, sent_at)`

## Policy documents

Authored by the candidate, committed under `/policy_docs`, **not** auto-generated by scaffolding
tooling — write these by hand so they contain specific, checkable rules (numeric thresholds,
notice periods) that acceptance tests #2/#12 and the citation requirement can actually be verified
against. Minimum three: leave policy, expense reimbursement policy, procurement policy. Each
roughly one page.

## Seed data

Shared demo password: `DemoPass123!`.

| User | Grants | Admin |
| --- | --- | --- |
| ali@assistant.test | policy:read, inventory:read | no |
| sara@assistant.test | policy:read, inventory:read, order:create | no |
| admin@assistant.test | all four | yes |
| dave@assistant.test | none | no |

Seed at least these 15 products:

| SKU | Name | Qty | Price | Supplier |
| --- | --- | --: | --: | --- |
| SKU-1001 | A4 Copy Paper | 450 | 6.50 | OfficeHub |
| SKU-1002 | Blue Ballpoint Pens | 18 | 0.80 | PenCo |
| SKU-1003 | Black Ballpoint Pens | 220 | 0.80 | PenCo |
| SKU-1004 | Staplers | 9 | 12.00 | OfficeHub |
| SKU-1005 | Staples Box | 75 | 2.40 | OfficeHub |
| SKU-1006 | Desk Notebooks | 14 | 5.25 | PaperWorks |
| SKU-1007 | Shipping Labels | 310 | 9.90 | PackRight |
| SKU-1008 | USB-C Cables | 7 | 8.75 | TechSource |
| SKU-1009 | Wireless Keyboards | 42 | 24.00 | TechSource |
| SKU-1010 | Wireless Mice | 36 | 18.00 | TechSource |
| SKU-1011 | Packing Tape | 11 | 4.60 | PackRight |
| SKU-1012 | Cardboard Boxes M | 160 | 1.90 | PackRight |
| SKU-1013 | Whiteboard Markers | 64 | 6.80 | OfficeHub |
| SKU-1014 | Printer Toner Black | 5 | 89.00 | PrintSupply |
| SKU-1043 | Thermal Receipt Rolls | 120 | 15.00 | RetailPrint |

## Acceptance tests

1.  New user has no capabilities; capability changes work without restart.
2.  `SKU-1043` returns quantity **120**; unknown SKU returns not-found.
3.  ali can read inventory/policy but cannot order or email — including when the tool function is called directly, bypassing chat.
4.  sara can order but cannot email; a combined request partially succeeds and clearly reports the refusal.
5.  admin can manage users/documents/activity; cannot remove own admin flag or deactivate self.
6.  dave is denied every capability.
7.  Guessing another user's thread ID returns 403.
8.  "SKU-1043" followed by "order 80 more" resolves the SKU from thread context.
9.  Write requests pause before side effects; approve/edit/reject all work; a rejected write leaves no row and blocks anything dependent on it; an edited quantity is re-validated by the tool before executing.
10. Retrying the same write, or approving twice, creates one order/email only.
11. Every tool attempt is auditable, including denied and invalid calls.
12. Upload makes a document searchable immediately; delete removes it from answers.
13. SSE emits progress and paused state; resume continues correctly after a full backend restart.
14. Prompt-injection (including a document containing an embedded instruction) and forged-user-id tests cannot bypass server checks.

## Run

### Backend (Terminal 1)

**Windows:**
```bash
cd backend
python -m venv .venv
.venv\Scripts\pip install -r requirements-minimal.txt
# or the full set: requirements.txt (needs extra space/time for sentence-transformers)
alembic upgrade head
.venv\Scripts\python seed.py
.venv\Scripts\uvicorn app.main:app --reload --port 8000
```


### Frontend (Terminal 2)

```bash
cd frontend
npm install
npm run check:backend    # should print OK once the backend is up
npm run dev              # http://localhost:5173 → login → chat
```

### Environment variables

Copy `backend/.env.example` to `backend/.env` and set `GROQ_API_KEY` before using
chat or any agent-driven feature. Authentication, inventory lookup, and the admin
list views work without an LLM key configured — only the supervisor/knowledge/action
graph requires it.

### Demo login

Use any of the seeded accounts (see [Seed data](#seed-data)) with the shared password
`DemoPass123!` at `http://localhost:5173`.
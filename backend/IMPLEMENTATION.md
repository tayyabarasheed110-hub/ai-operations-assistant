# Implementation notes

## Assumptions

1. **LangGraph checkpoint DB** lives at `./data/checkpoints.sqlite` (separate from SQLAlchemy `app.db`). LangGraph creates its own tables via `SqliteSaver.setup()`.
2. **Groq structured outputs** use the OpenAI-compatible `response_format` JSON schema path. If a given model rejects that parameter, set `LLM_MODEL` to a Groq model that supports JSON/schema mode or adjust the model slug in env only (no provider branches in code).
3. **Embeddings** load `sentence-transformers/all-MiniLM-L6-v2` locally on first retrieval/upload (full `requirements.txt`). Tests set `EMBEDDING_MODE=test` for deterministic hash embeddings without downloading weights. Use `requirements-minimal.txt` only when disk/network prevents installing `sentence-transformers` (production should use the full file).
4. **Policy Q&A** depends on candidate-authored files under `/policy_docs` and/or admin uploads. Placeholder markdown is intentionally not indexed until replaced or uploaded.
5. **Admin `is_admin`** is a column, not a revocable capability row. API prevents self-deactivation; there is no separate “remove own admin flag” endpoint in the README contract—admin flag changes would require a direct DB change or future endpoint.
6. **SSE** emits graph/tool events from server-side state; token streaming from the LLM is minimal (supervisor emits an empty token marker). Full token streaming can be added without changing the API event names.
7. **Resume `edit`** merges `edits` into the pending payload, then re-validates through execute tools (Pydantic + capability checks + audit).

## Run locally

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
python seed.py
uvicorn app.main:app --reload
```

Tests:

```bash
pytest
```

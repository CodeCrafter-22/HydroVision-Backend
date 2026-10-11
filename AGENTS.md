# HydroVision Backend — Persistent Development Rules & Invariants

This file defines the mandatory rules, boundaries, and invariants for all engineers and AI assistants working on the HydroVision backend.

## 1. Team Ownership Boundaries
- **Bagul (Backend)**: Canonical Supabase database schema, RLS policies, Python FastAPI base service, data ingestion workers, baseline risk calculation, signal fusion, geospatial queries, people-at-risk SQL views, source health tracking, and backtesting.
- **Svi (Frontend)**: React/Next.js dashboard (O1–O10) and Resident/Field UI (R0–R4). Reads directly from Supabase under RLS or calls FastAPI.
- **Rathod (Automation)**: n8n workflow schedules, Telegram bot alert delivery, acknowledgement funnel, and SOS escalation.
- **Purvika (AI/Vision/Replay)**: RAG knowledge assistant (`/ask`), Rumor check (`/rumor-check`), Copilot summary (`/copilot`), Photo water-level vision (`/report/photo`), and Replay engine (`/replay/*`).

## 2. Core Architectural Invariants
1. **Never Invent Contracts**: Do not invent database columns, API endpoints, risk thresholds, or role names without team confirmation. Refer to files in `/docs`.
2. **Deny-by-Default Security**: Security is enforced at the database level via PostgreSQL Row-Level Security (RLS) and server-side FastAPI dependencies. UI hiding or frontend route guards are never considered security.
3. **Never Expose Service Secrets**: The Supabase `service_role` key must remain server-side only. Never expose it in client code, public repositories, or API responses.
4. **Isolate Simulated Data**:
   - Every simulated record must carry `is_simulated = true` and `replay_run_id`.
   - Replay reset operations must **only** delete records where `is_simulated = true`.
   - Simulated alerts must never be sent to real recipients unless `ALLOW_SIM_DELIVERY=true` is explicitly enabled.
5. **No Unsupported ML Claims**:
   - NASA GPM IMERG is a precipitation input, not a flood-event label.
   - Do not claim predictive ML accuracy without independently verified historical flood outcomes and leakage-free temporal splits.
   - Baseline threshold rules must always exist as the transparent ground floor.
6. **Atomic Task Acceptance**: Task assignment must be atomic (`UPDATE tasks SET status='assigned' WHERE id = :id AND status='open'`) to guarantee first-accept-wins.
7. **Consistent Envelopes & Time**:
   - All timestamps must be stored in UTC (`timestamptz`) and formatted as ISO 8601.
   - API responses must use standard JSON envelopes: `{ "data": ..., "meta": ... }` and `{ "error": ... }`.
   - Distinguish observation time (`observed_at`) from processing time (`ingested_at`).

## 3. Working Commands (Windows PowerShell)
- **Activate Virtual Environment**: `.\.venv\Scripts\Activate.ps1`
- **Run API Server**: `uvicorn app.main:app --reload --port 8000`
- **Run Tests**: `pytest -v`

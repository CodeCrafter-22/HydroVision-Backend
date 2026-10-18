# HydroVision

> Flood-Detection, Baseline Risk Scoring & Early-Warning Platform  
> **Architecture**: Monorepo (Next.js Dashboard, FastAPI Backend, Supabase PostGIS, n8n Automation, AI/Vision)

---

## 1. Monorepo Structure

```text
HydroVision/
├── frontend/                    # Svi: Next.js / React dashboard & resident UI
├── backend/                     # Bagul: Python FastAPI service, workers & ingestion
│   ├── app/                     # FastAPI core, endpoints, schemas, workers
│   ├── tests/                   # Pytest automated test suite
│   ├── requirements.txt         # Python dependencies
│   ├── .env.example             # Backend environment template
│   └── README.md                # Backend service setup & guide
├── supabase/                    # Canonical database migrations & config
├── automation/                  # Rathod: n8n workflow schedules & alert handlers
├── ai/                          # Purvika: RAG assistant, rumor checks, copilot, replay
├── docs/                        # Shared integration contracts & specs
├── AGENTS.md                    # Persistent development rules and team invariants
├── README.md                    # Root monorepo overview (this file)
└── .gitignore                   # Workspace gitignore rules
```

---

## 2. Team Ownership Boundaries

| Member | Focus Area | Directory | Interface / Contract |
| :--- | :--- | :--- | :--- |
| **Bagul** | Backend, Database, Ingestion, Risk & Geo | `backend/`, `supabase/` | Base API, schema migrations, views, ingest workers |
| **Svi** | Frontend Dashboard & Field UI | `frontend/` | Next.js app, consumes SQL views & REST endpoints |
| **Rathod** | n8n Automation, Telegram & SOS | `automation/` | Triggers 15-min ingest, alert dispatch, task accept |
| **Purvika** | AI / RAG, Replay & Vision | `ai/` | Registers feature routers (`/ask`, `/copilot`, `/replay`) |

---

## 3. Getting Started with the Backend

Follow these instructions to set up and run the FastAPI backend locally:

### Step 1: Navigate to the Backend Directory
```powershell
cd d:\HydroVision-Backend\backend
```

### Step 2: Create & Activate Virtual Environment
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```
*(If activating from repository root: `.\.venv\Scripts\Activate.ps1`)*

### Step 3: Install Dependencies
```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### Step 4: Configure Local Environment Variables
```powershell
Copy-Item .env.example .env
```
Populate `.env` with your Supabase credentials and API tokens. Never commit `.env` files to git.

### Step 5: Start the API Server
From `backend/`:
```powershell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
Interactive docs:
- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Health Check**: [http://localhost:8000/health](http://localhost:8000/health)

### Step 6: Run Backend Automated Tests
From the `backend/` directory:
```powershell
pytest -v
```
Or from the monorepo root:
```powershell
pytest -v backend/tests
```

---

## 4. Integration Contract & Response Format

All API endpoints strictly follow the **HydroVision Integration Contract**:

### Standard Success Response
```json
{
  "data": {
    "status": "healthy",
    "service": "HydroVision Backend API",
    "version": "0.1.0",
    "environment": "development",
    "database": "connected"
  },
  "meta": {
    "request_id": "req_a1b2c3d4e5f6",
    "generated_at": "2026-10-18T11:30:00.000000+00:00"
  }
}
```

### Standard Error Response
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Validation failed at 'query -> village_id': Field required",
    "request_id": "req_a1b2c3d4e5f6"
  }
}
```

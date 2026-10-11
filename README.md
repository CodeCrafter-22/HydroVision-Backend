# HydroVision Backend

> Flood-Detection, Baseline Risk Scoring & Early-Warning Platform Backend  
> **Tech Stack**: Python 3.11+ · FastAPI · PostgreSQL / PostGIS (Supabase) · Pytest

---

## 1. Project Overview

HydroVision is an early-warning flood intelligence platform. This backend repository provides:
* **Base REST API**: High-performance asynchronous FastAPI service.
* **Database Foundation**: Supabase PostgreSQL with PostGIS spatial extensions and Row-Level Security (RLS).
* **Data Ingestion**: 15-minute scheduled workers fetching river water levels and rainfall.
* **Risk Engine & Signal Fusion**: Deterministic baseline threshold rules and weighted multi-source fusion.
* **Geospatial & People-at-Risk Engine**: Inundated ward spatial queries and population impact metrics.

---

## 2. Directory Structure

```text
HydroVision-Backend/
├── .env.example                 # Safe environment configuration template
├── .gitignore                   # Excludes virtual environments, .env files, caches
├── AGENTS.md                    # Persistent development rules and invariants
├── README.md                    # This getting-started and developer guide
├── requirements.txt             # Locked Python dependencies for Phase 0 & 1
│
├── app/                         # Application source code
│   ├── main.py                  # FastAPI application entry point, CORS & middleware
│   ├── api/
│   │   ├── router.py            # Central router (allows team feature routers)
│   │   └── v1/
│   │       └── health.py        # /health endpoint implementation
│   ├── core/
│   │   ├── config.py            # Configuration loader using Pydantic Settings
│   │   ├── errors.py            # Standard exception handlers and envelopes
│   │   └── security.py          # Auth & role dependency placeholders
│   └── schemas/
│       ├── envelope.py          # Standard { data, meta } and { error } models
│       └── health.py            # Health payload Pydantic models
│
├── tests/                       # Automated test suite
│   ├── conftest.py              # Pytest fixtures
│   └── test_health.py           # Health endpoint and envelope tests
│
└── docs/                        # Team contracts and project specifications
```

---

## 3. Getting Started on Windows PowerShell (Step-by-Step)

Follow these beginner-friendly instructions to set up and run the backend locally.

### Step 1: Open PowerShell in the Project Directory
Ensure your terminal is in the project root:
```powershell
cd d:\HydroVision-Backend
```

### Step 2: (Optional) Allow Script Execution for the Current Terminal
If PowerShell restricts running activation scripts, allow it for your current session:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
```

### Step 3: Create a Python Virtual Environment
A virtual environment keeps your project dependencies isolated from the rest of your computer:
```powershell
python -m venv .venv
```

### Step 4: Activate the Virtual Environment
Activate the isolated environment:
```powershell
.\.venv\Scripts\Activate.ps1
```
*(When activated, you will see `(.venv)` at the beginning of your terminal prompt).*

### Step 5: Upgrade Pip & Install Dependencies
Install all required libraries into your virtual environment:
```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### Step 6: Create Your Local Environment File
Copy the provided `.env.example` template into a local `.env` file:
```powershell
Copy-Item .env.example .env
```
*(Your `.env` file is ignored by Git, so your local secrets will never be accidentally committed).*

---

## 4. Running the API Server

Start the local FastAPI development server with auto-reload:
```powershell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Once running, access:
* **Service Health Check**: [http://localhost:8000/health](http://localhost:8000/health) or [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)
* **Interactive OpenAPI Docs (Swagger UI)**: [http://localhost:8000/docs](http://localhost:8000/docs)
* **Alternative ReDoc UI**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## 5. Running Automated Tests

Run the test suite using `pytest`:
```powershell
pytest -v
```

Expected output:
```text
tests/test_health.py::test_root_health_endpoint PASSED
tests/test_health.py::test_api_v1_health_endpoint PASSED
tests/test_health.py::test_request_id_header_propagation PASSED
```

---

## 6. Integration Contract & Response Format

All API endpoints strictly follow the agreed **HydroVision Integration Contract**:

### Standard Success Response
```json
{
  "data": {
    "status": "healthy",
    "service": "HydroVision Backend",
    "version": "0.1.0",
    "environment": "development",
    "database": "pending_phase_2"
  },
  "meta": {
    "request_id": "req_a1b2c3d4e5f6",
    "generated_at": "2026-10-11T05:05:00.000000+00:00"
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

---

## 7. Team Responsibility Boundaries

| Member | Focus Area | Interface / Contract |
| :--- | :--- | :--- |
| **Bagul** | Backend, Database, Ingestion, Risk & Geo | Base API, schema migrations, views, ingest workers |
| **Svi** | Frontend Dashboard & Field UI | Consumes SQL views & REST endpoints |
| **Rathod** | n8n Automation, Telegram & SOS | Triggers 15-min ingest, alert dispatch, task accept |
| **Purvika** | AI / RAG, Replay & Vision | Registers feature routers (`/ask`, `/copilot`, `/replay`) |

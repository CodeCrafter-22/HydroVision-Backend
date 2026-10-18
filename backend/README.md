# HydroVision Backend Service

FastAPI backend service for the HydroVision flood-detection, baseline risk scoring, and early-warning intelligence platform.

---

## 1. Directory Structure

```text
backend/
├── .env.example             # Safe environment configuration template
├── README.md                # Backend service documentation (this file)
├── requirements.txt         # Python dependencies
├── app/                     # FastAPI application source code
│   ├── main.py              # Application entry point, CORS & middleware
│   ├── api/
│   │   ├── router.py        # Central API router
│   │   └── v1/              # Version 1 API routes (health, readings, alerts, etc.)
│   ├── core/                # Core configuration, errors, security & clients
│   ├── schemas/             # Pydantic schemas and standard response envelopes
│   └── workers/             # Ingestion workers, adapters & queue processing
└── tests/                   # Automated pytest suite
```

---

## 2. Setup & Installation

### Step 1: Virtual Environment
From the monorepo root or backend directory:
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### Step 2: Install Dependencies
```powershell
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 3: Configure Environment Variables
Copy the template and fill in local Supabase / service values:
```powershell
Copy-Item .env.example .env
```

---

## 3. Running the Server

Start the FastAPI development server with auto-reload:
```powershell
uvicorn app.main:app --reload --port 8000
```

The interactive API documentation is accessible at:
- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **Health Check**: [http://localhost:8000/health](http://localhost:8000/health)

---

## 4. Running Tests

Run the backend test suite:
```powershell
pytest -v
```

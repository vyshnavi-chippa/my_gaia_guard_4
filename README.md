# GaiaGuard

AI-based Geospatial Monitoring and User Alert System (MVP).

## Folder Structure

```text
my_gaia_guard_4/
├─ backend/
│  └─ app/
│     ├─ api/
│     ├─ core/
│     │  └─ config.py
│     ├─ db/
│     │  └─ session.py
│     ├─ models/
│     │  └─ event.py
│     ├─ services/
│     ├─ __init__.py
│     └─ main.py
├─ frontend/
│  └─ app.py
├─ ml/
├─ data/
├─ tests/
├─ .env.example
├─ requirements.txt
└─ README.md
```

## Prerequisites (Windows)

- Python 3.11+ installed
- PostgreSQL installed locally (pgAdmin or psql available)

## Setup (No Docker)

1. Open PowerShell in project root:

```powershell
cd C:\Users\chipp\Downloads\my_gaia_guard_4
```

2. Create and activate virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

3. Install dependencies:

```powershell
pip install -r requirements.txt
```

4. Create local PostgreSQL database:

```powershell
psql -U postgres -h localhost -p 5432 -c "CREATE DATABASE gaiaguard_db;"
```

5. Create environment file from example:

```powershell
copy .env.example .env
```

6. Edit `.env` and set your real PostgreSQL password in `DATABASE_URL`.

Example:

```env
DATABASE_URL=postgresql+psycopg2://postgres:my_real_password@localhost:5432/gaiaguard_db
```

## Run Backend (FastAPI)

```powershell
uvicorn app.main:app --reload --app-dir backend
```

Backend API:
- http://127.0.0.1:8000/
- http://127.0.0.1:8000/health
- http://127.0.0.1:8000/docs

## Run Frontend (Streamlit)

Open a second PowerShell terminal in project root:

```powershell
.\.venv\Scripts\Activate.ps1
streamlit run frontend\app.py
```

Frontend:
- http://localhost:8501

## Optional Twilio Alerts

Add these values in `.env` only if you want SMS alerts:
- `TWILIO_ACCOUNT_SID`
- `TWILIO_AUTH_TOKEN`
- `TWILIO_FROM_NUMBER`
- `ALERT_TO_NUMBER`

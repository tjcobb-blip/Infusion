# Infusion Referral Orchestration Platform — Demo Script

## Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL running locally (or adjust DATABASE_URL)

## Setup

### 1. Database

```bash
# Create Postgres database
createdb infusion
# Or via psql:
# CREATE DATABASE infusion;
# CREATE USER infusion WITH PASSWORD 'infusion';
# GRANT ALL PRIVILEGES ON DATABASE infusion TO infusion;
```

### 2. Backend

```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Configure env (edit .env if needed)
cp .env.example .env

# Run migrations
alembic upgrade head

# Seed data (2 orgs, 2 users, 10 cases)
python seed.py

# Start backend
uvicorn app.main:app --reload --port 8000
```

### 3. Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start dev server
npm run dev
```

Frontend runs at http://localhost:5173, backend at http://localhost:8000.

## Demo Accounts

| Role           | Email                  | Password    |
|----------------|------------------------|-------------|
| Provider       | provider@example.com   | password123 |
| Infusion Admin | admin@example.com      | password123 |

---

## Walkthrough: Provider Creates Referral

1. Open http://localhost:5173/login
2. Login as **provider@example.com / password123**
3. You see "My Referrals" — a list of cases created by your org
4. Click **"+ New Referral"**
5. Fill in:
   - Patient: John Test, DOB 1980-01-01
   - Drug: Infliximab, 5mg/kg, Every 8 weeks, IV
   - Diagnosis: M05.79
   - Insurance: Aetna, MEM-999, GRP-100
6. Click **Submit Referral**
7. New case appears in list with status "Referral Received"
8. Click into the case to view patient, Rx, insurance summary
9. Go to **Documents** tab and upload a document (file name: "referral.pdf")
10. Go to **Timeline** tab to see CASE_CREATED event

---

## Walkthrough: Infusion Admin Processes Through Therapy

1. **Sign out**, then login as **admin@example.com / password123**
2. You see "Intake Queue" — all cases including unassigned ones
3. Use status filter to view by status
4. Click into the new referral (REFERRAL_RECEIVED)

### Advance through workflow:

5. Click **"Advance to Clinical Completeness Check"**
6. Click **"Advance to Benefits Investigation"**
7. Click **"Advance to Prior Auth Submitted"**
8. Click **"Advance to Prior Auth Approved"**
9. Click **"Advance to Financial Counseling Pending"**

### Financial Clearance (Step 6A):

10. Go to **Financial** tab
11. Enter cost estimate: 2500
12. Check "Patient acknowledged cost"
13. Click **"Mark Cleared"**
14. Back on overview, click **"Advance to Financial Cleared"**

### Welcome Call (Step 6B):

15. Click **"Advance to Welcome Call Pending"**
16. Go to **Welcome Call** tab
17. Check "Patient reached"
18. Select outcome: "Reached"
19. Add patient questions and next steps
20. Click **"Mark Complete"**
21. Back on overview, click **"Advance to Welcome Call Completed"**

### Scheduling:

22. Click **"Advance to Scheduling Ready"**
23. Go to **Scheduling** tab
24. Set date, location, duration (120 min)
25. Click **"Set Schedule"**
26. Back on overview, click **"Advance to Scheduled"**

### Pharmacy Push (Step 6C):

27. Click **"Advance to Pharmacy Push Pending"**
28. Go to **Pharmacy** tab
29. Enter ship-to address and arrival date
30. Click **"Push to Pharmacy"**
31. Back on overview, click **"Advance to Pharmacy Pushed"**
32. Click **"Advance to Drug Fulfillment In Progress"**
33. Go to **Pharmacy** tab, change fulfillment status to "Ready"
34. Click **"Update Fulfillment"**
35. Back on overview, click **"Advance to Drug Ready"**

### Complete Infusion:

36. Click **"Advance to Infusion Completed"**
37. Click **"Advance to On Therapy"**

### Verify:

38. Check the **Timeline** tab — full audit trail of all status changes
39. Check the **sidebar** — blockers panel should show "No blockers"
40. Check the **sidebar** — SLA timer shows time in current status

---

## Running Tests

```bash
cd backend
python -m pytest tests/ -v
```

All 26 tests should pass, covering:
- Workflow transition validation (valid/invalid transitions)
- Financial clearance rules (acknowledgement + cleared_at required)
- Welcome call completion requirement (task must be DONE)
- Pharmacy push status coupling (fulfillment drives case status)
- Blockers panel logic

---

## API Quick Reference

```bash
# Health check
curl http://localhost:8000/health

# Login
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"password123"}'

# List cases (use token from login)
curl http://localhost:8000/cases \
  -H "Authorization: Bearer <token>"

# Create case
curl -X POST http://localhost:8000/cases \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"patient":{"first_name":"Test","last_name":"Patient"}}'

# Advance status
curl -X PATCH http://localhost:8000/cases/<id>/status \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"new_status":"CLINICAL_COMPLETENESS_CHECK"}'
```

## Architecture

```
/backend               FastAPI + SQLAlchemy + Alembic
  /app
    /api               Route handlers (auth, cases, tasks, etc.)
    /core              Config, database, security, deps
    /models            SQLAlchemy ORM models + enums
    /schemas           Pydantic request/response schemas
    /services          Business logic (workflow state machine)
  /migrations          Alembic migration files
  /tests               Pytest unit tests
  seed.py              Seed data script

/frontend              React + TypeScript + Vite
  /src
    /pages             LoginPage, CaseListPage, CaseDetailPage
    api.ts             Axios client with JWT interceptor
    AuthContext.tsx     Auth state management
    types.ts           TypeScript types matching backend models

/docs                  Documentation
  demo.md              This file
```

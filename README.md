# PATHMIND

An evidence-informed career counseling and assessment engine.

## Problem
Traditional career assessments rely heavily on self-reported personality quizzes. PATHMIND solves this by combining standardized assessments (RIASEC, SCCT) with observable behavioral evidence (projects, hackathons) to provide highly personalized, data-driven career counseling.

## Core Experience
Profile → Counseling → Assessment → Candidate Paths → Progressive Learning Roadmap

## Architecture
```text
Frontend (Next.js)
       ↓
Backend (FastAPI)
       ↓
Google ADK (Agent Development Kit)
       ↓
Gemini 2.5 Flash
       ↓
Knowledge Layer (ESCO / NCO Adapters)
       ↓
Firestore Database
```

## Tech Stack
- **Frontend**: Next.js 15 (Turbopack, App Router), Tailwind CSS, Framer Motion
- **Backend**: Python 3.14, FastAPI, google-generativeai, google-cloud-firestore
- **Deployment**: GitHub Pages (Frontend), Cloud Run (Backend)

## Local Development

### Frontend
```bash
cd frontend
npm install
npm run dev
```

### Backend
```bash
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --reload
```

## Environment Variables
Create a `.env` file in the `backend` directory based on `.env.example`:
- `GEMINI_API_KEY=`
- `FIRESTORE_PROJECT_ID=`

## Deployment
- **Frontend**: Automatically deployed to GitHub Pages via `.github/workflows/deploy-frontend.yml` upon push to `main` or `test/hackathon-demo`.
- **Backend**: Deployed to Google Cloud Run.

## Demo
- **Frontend**: `https://akshat2685.github.io/pathmind`
- **Backend API**: `Pending Deployment (Cloud Run Billing Issue)`

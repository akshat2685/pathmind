# Deploying the College MVP to Vercel

Two Vercel projects, one repo (`college-mvp` branch or this fix branch).

## 1. Backend project

- **Root Directory:** repository root (`.`).
- **Entrypoint:** `api/index.py` (Mangum wraps the FastAPI `app`; every route is served through it — see `vercel.json` rewrites).
- **Install:** project-root `requirements.txt` (pulls in `backend/requirements.txt` + `mangum`).
- **Env vars (Vercel dashboard → Settings → Environment Variables):**
  - `SUPABASE_URL`
  - `SUPABASE_SECRET_KEY` (service-role key — server only, never expose to the frontend)
  - `GEMINI_API_KEY`
- **Timeout note:** `vercel.json` sets `maxDuration: 60` because plan/activity generation calls take 19–45s. **60s needs a Pro plan** — on Hobby the cap is 10s and long generations will be cut off. Either upgrade or keep generations short.

## 2. Frontend project

- **Root Directory:** `frontend/`. Framework preset: Next.js.
- **Env vars:**
  - `NEXT_PUBLIC_SUPABASE_URL`
  - `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` (publishable/anon key only)
  - `NEXT_PUBLIC_API_URL` = the backend project URL, e.g. `https://pathmind-college-api.vercel.app`

## 3. Pre-deploy checklist

- [ ] Backend contract fixes merged (this branch).
- [ ] Knowledge tables seeded (universities / programs / subjects / curricula / units) — without this, search returns `[]` and curriculum lookups 404.
- [ ] `pytest backend/tests/test_college_mvp.py` passes against Supabase (11/11).

## 4. What NOT to do

- Do not put `SUPABASE_SECRET_KEY` in the frontend project.
- Do not run migrations again — the 28 tables already exist in Supabase.
- Do not seed fake PYQs. `PYQ_NOT_AVAILABLE` is the honest state until real question sets are verified.

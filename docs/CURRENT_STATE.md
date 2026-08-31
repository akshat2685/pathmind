# Current State

## Stack Overview

### Frontend
- **Framework**: Next.js 15 (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS v4
- **Component Library**: shadcn/ui
- **Animation/Interaction**: Framer Motion, KokonutUI (to be integrated)
- **Path**: `/frontend`

### Backend
- **Framework**: FastAPI
- **Language**: Python 3.14
- **Server**: Uvicorn
- **AI/Agents**: Google Gen AI SDK, Google ADK (to be integrated)
- **Database**: Firestore (to be integrated)
- **Path**: `/backend`

## Entry Points
- **Frontend**: `http://localhost:3000` (development server via `npm run dev`)
- **Backend**: `http://localhost:8000` (development server via `uvicorn main:app --reload`)

## Credential & Environment Handling
- **Backend**: Controlled via `.env` (validated by Pydantic settings). Currently tracks only `PROJECT_NAME`. **No secrets are hardcoded.**
- **Frontend**: Standard Next.js environment handling.

## Known Gaps
- ADK agent orchestration is missing.
- Firestore integration is missing.
- Premium UI components (AppShell, ContextRail, etc.) are scaffolded but not implemented.

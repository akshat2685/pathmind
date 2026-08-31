# Technical Decisions

## 1. Project Architecture (FastAPI + Next.js)
**Context**: PATHMIND requires complex agent orchestration (Google ADK) and an interactive, highly responsive frontend.
**Decision**: Separate the stack into a Next.js 15 frontend and a Python FastAPI backend.
**Reasoning**: Python is the primary language for Google ADK and advanced Gen AI workflows. Next.js provides the best ecosystem for premium, animated web interfaces (framer-motion, shadcn). This separation prevents the frontend from being bogged down by heavy Python agent logic.

## 2. Design System and UI Component Strategy
**Context**: The PRD explicitly forbids generic "AI slop" (excessive glassmorphism, rainbow gradients, fake terminals).
**Decision**: Use `shadcn/ui` for accessible, unopinionated base components, augmented selectively with `Framer Motion` and `KokonutUI` for specific, intentional microinteractions (e.g., stage unlocking, evidence transitions).
**Reasoning**: This allows us to build a sophisticated, editorial "learning OS" feel rather than a typical SaaS dashboard.

## 3. Strict Credential Discipline
**Context**: Avoiding hardcoded credentials and fake integration keys.
**Decision**: All backend secrets will be managed by `pydantic-settings` via a `.env` file. We will explicitly block implementation and request real keys from the developer when required by a feature (e.g., Firestore, Gemini).
**Reasoning**: Ensures the MVP is production-ready, secure, and adheres strictly to Prompt 13 rules.

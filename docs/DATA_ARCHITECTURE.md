# Pathmind Data Architecture

The PATHMIND Knowledge Foundation is designed to act as a resilient, unified bridge between external career/education data providers and reasoning agents (via ADK Tools).

## Architecture Flow

```text
External Source (e.g. ESCO, NCO)
      ↓
Provider Adapter (`backend/providers/`)
      ↓
Normalization (`backend/core/schemas.py`)
      ↓
Knowledge Service (`backend/services/knowledge.py`)
      ↓
Knowledge Store / Cache (`backend/services/store.py` - Firestore)
      ↓
ADK Tool (`backend/tools/knowledge_tools.py`)
      ↓
ADK Agent (Gemini Reasoning)
```

## Key Principles

1. **Provider Isolation**: Frontend and Agents NEVER communicate directly with external APIs. All requests route through `KnowledgeService`.
2. **Provenance**: Every piece of returned data includes a `ProviderContext` indicating its source, version, and retrieval time.
3. **Caching**: External APIs are not called unnecessarily. Responses are hashed and cached in Firestore.
4. **Memory Separation**: General knowledge (occupations, skills) is strictly isolated from Private Student Memory.

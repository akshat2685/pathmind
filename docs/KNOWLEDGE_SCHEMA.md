# Knowledge Schema

This document defines the canonical schemas used across PATHMIND. All external provider data is normalized into these structures before being returned to agents.

## Core Models

### `ProviderContext`
Enforces provenance and source priority.
- `provider` (str): Identifier of the provider (e.g., "esco", "india_nco")
- `retrieved_at` (str): ISO 8601 timestamp.
- `version` (str, optional): The dataset or API version.
- `source_id` / `source_url` (str, optional): Original identifiers in the provider system.

### `Occupation`
- `id` (str): Internal ID.
- `title` (str): Canonical title.
- `description` (str): Occupation summary.
- `alternate_titles` (List[str])
- `tasks` (List[str])
- `skills` (List[Skill])
- `source_context` (ProviderContext)

### `KnowledgeResponse`
The standard tool response contract wrapping the results.
- `results` (List[Any]): The returned entities.
- `sources` (List[ProviderContext]): Accumulated provenance contexts.
- `confidence` (str): "source-backed" or "no-results".

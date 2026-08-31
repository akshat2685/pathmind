# ADK Knowledge Tools

This document outlines the tools exposed to the Reasoning Agent via Google ADK.

## Current Tools

### `search_occupations_tool`
- **Purpose**: Search for occupations across configured knowledge providers.
- **Input**: `query` (str), `limit` (int)
- **Output**: JSON string matching the `KnowledgeResponse` contract, which includes normalized occupation data and explicit `sources` provenance arrays.

## Planned Tools
- `get_occupation_profile`
- `find_skills_for_occupation`
- `find_related_careers`
- `find_education_paths`
- `find_credentials_for_goal`
- `search_trajectory_patterns`
- `find_similar_trajectories`
- `get_market_information`
- `search_learning_resources`

*Note: All ADK tools MUST interact exclusively with `KnowledgeService` and NEVER directly with external APIs.*

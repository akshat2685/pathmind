# Data Sources

This document tracks the actual connected providers versus planned providers for the PATHMIND knowledge foundation.

## Connected Providers

- **ESCO (European Skills, Competences, Qualifications and Occupations)**
  - **Status**: Connected via `backend/providers/esco.py`.
  - **Capabilities**: Occupation search, skill retrieval.
  - **Authentication**: None required (Public REST API).

- **India NCO (National Classification of Occupations)**
  - **Status**: Configured for local ingestion via `backend/providers/nco.py`.
  - **Capabilities**: Controlled file-based ingestion (JSON/CSV) for localized Indian career mapping.
  - **Authentication**: Local file access (`NCO_DATA_PATH`).

## Planned Providers (Not Yet Configured)

- **O*NET**
  - **Status**: Excluded per current configuration (requires API key).
  - **Planned Capabilities**: Occupation details, Interest Profiler, work styles.

- **AISHE / NIRF**
  - **Status**: Pending controlled ingestion.

- **BLS (Bureau of Labor Statistics)**
  - **Status**: Pending configuration.

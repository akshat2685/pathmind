# Credentials & Environment configuration

This document tracks the required credentials and configuration settings needed for PATHMIND.

## General Configuration
- `PROJECT_NAME`: Name of the API (Default: "PATHMIND MVP API")
- `GEMINI_API_KEY`: Required for ADK tool reasoning.

## Provider Configuration
- `ESCO_API_URL`: Base URL for ESCO (Default: "https://ec.europa.eu/esco/api")
- `NCO_DATA_PATH`: Path to the controlled ingestion source (Default: "data/nco_2015.json")

## Storage Configuration
- `FIRESTORE_PROJECT_ID`: GCP Project ID for Firestore.
- `GOOGLE_APPLICATION_CREDENTIALS`: Path to the service account JSON for local Firestore connectivity.

## Excluded Config
- `ONET_USERNAME` / `ONET_PASSWORD`: Excluded from current setup per requirements (requires commercial/API agreement).

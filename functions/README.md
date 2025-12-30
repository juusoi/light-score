# ESPN Parser Functions

Utilities for fetching and parsing NFL data from ESPN APIs.

## Overview

This directory contains Python functions that fetch and process NFL data from ESPN APIs. The parsed data is cached locally as JSON files for the backend to serve.

## Getting Started

### Prerequisites

- Python 3.13 or higher
- uv package manager

### Installation

From project root:

```bash
make dev-setup
# or manually:
uv venv
./scripts/uv-sync.sh --all
```

### Run Locally

Fetch and cache current standings:

```bash
python functions/src/main.py
```

This writes standings data to `backend/src/data/standings_cache.json`.

### Run Tests

```bash
cd functions/src
../../.venv/bin/python -m pytest
```

Or from project root:

```bash
make test
```

## ESPN API Integration

ESPN NFL endpoints reference:

- <https://gist.github.com/nntrn/ee26cb2a0716de0947a0a4e9a157bc1c>

ESPN API integration is implemented in `src/espn_integration.py`.

## Functions

### Standings Parser (`src/standings_parser.py`)

Fetches and processes NFL standings data from ESPN.

**API Endpoint**: <https://cdn.espn.com/core/nfl/standings?xhr=1>

**Output**: Writes minimal standings data (team, wins, losses, ties, division) to `backend/src/data/standings_cache.json`.

**Data Models**:
- `ConferenceGroup` - AFC/NFC conference grouping
- `TeamStandingInfo` - Individual team record info

### Main Entry (`src/main.py`)

Orchestrates the data fetching workflow using `EspnClient`.

## Architecture

```
ESPN API → functions/src → backend/src/data/*.json → FastAPI Backend
```

The functions serve as the data ingestion layer, fetching fresh NFL data and caching it locally for the FastAPI backend to serve.

## Mock Mode

The backend supports `MOCK_ESPN=true` for testing with fixture data in `backend/src/fixtures/` instead of live ESPN calls.

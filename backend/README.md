# Backend Service for NFL Scores and Standings

## Overview

This document provides information about the backend service of the NFL Scores and Standings project. The backend is built using FastAPI and serves as the primary API for fetching and processing NFL data.

## Getting Started

### Prerequisites

- Python 3.13 or higher
- uv (https://docs.astral.sh/uv/)

### Installation

1. Clone the repository:

```bash
git clone https://github.com/juusoi/light-score
```

2. Set up a virtual environment and sync deps (pyproject-first):

```bash
cd light-score
uv venv
./scripts/uv-sync.sh --all
```

3. Navigate to the backend directory:

```bash
cd backend
```

## Running the Service Locally

To run the backend service locally, use the following command:

```bash
cd src
../../.venv/bin/uvicorn main:app --reload
```

The service will be available at http://localhost:8000.

## API Endpoints

The backend provides the following endpoints:

- /games: Fetches the latest NFL game scores.
- /standings: Provides current NFL team standings.

## Testing

To run the unit tests, execute:

```bash
cd src
../../.venv/bin/python -m pytest
```

## Development Guidelines

Ensure code adheres to PEP 8 standards.
Write unit tests for new features and bug fixes.
Document new API endpoints clearly in this README.

## Continuous Integration

GitHub Actions are set up for continuous integration, running lint checks and tests on every push.

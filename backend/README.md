# Backend Service for NFL Scores and Standings

## Overview

This document provides information about the backend service of the NFL Scores and Standings project. The backend is built using FastAPI and serves as the primary API for fetching and processing NFL data.

## Getting Started

### Prerequisites

- Python 3.12 or higher
- pip (Python package manager)

### Installation

1. Clone the repository:

```bash
git clone https://github.com/juusoi/light-score
```

2. Set up a virtual environment:

```bash
cd light-score
python -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip
```

3. Navigate to the backend directory:

```bash
cd backend
```

4. Install dependencies:

```bash
pip install -r requirements.txt
```

## Running the Service Locally

To run the backend service locally, use the following command:

```bash
cd src
uvicorn main:app --reload
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
python -m pytest
```

## Development Guidelines

Ensure code adheres to PEP 8 standards.
Write unit tests for new features and bug fixes.
Document new API endpoints clearly in this README.

## Continuous Integration

GitHub Actions are set up for continuous integration, running lint checks and tests on every push.

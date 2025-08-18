# AWS Lambda Functions

ESPN API parsers that will be deployed as AWS Lambda functions for serverless data processing.

## Overview

This directory contains AWS Lambda functions that fetch and process NFL data from ESPN APIs. The functions are designed to run on a schedule and update the DynamoDB database with the latest scores and standings.

## Getting Started

### Prerequisites

- Python 3.13 or higher
- AWS CLI configured with appropriate permissions
- AWS Lambda deployment tools (optional)

### Installation

From project root (pyproject-first):

```bash
uv venv
./scripts/uv-sync.sh --all
```

### Local Development

To test functions locally:

```bash
cd src
../../.venv/bin/python -m pytest  # Run tests
../../.venv/bin/python main.py     # Run main function locally
```

## ESPN API Integration

All ESPN NFL endpoints are documented here:

- <https://gist.github.com/nntrn/ee26cb2a0716de0947a0a4e9a157bc1c>
- <https://gist.github.com/nntrn/ee26cb2a0716de0947a0a4e9a157bc1c/cd7462cd365e516d7499b43f027db4b8b1a2d6c0>

ESPN API integration is implemented in `src/espn_integration.py`

## Functions

### Standings Parser

An ESPN API parser implemented in `src/standings_parser.py` that fetches and processes NFL standings data.

**API Endpoint**: <https://cdn.espn.com/core/nfl/standings?xhr=1>

**Data Location**: The current standings information is available in the `response.content.standings.groups` field.

**Function**: Processes standings data and updates DynamoDB with team records, wins, losses, and rankings.

### Latest Games

**Status**: TODO - Implementation planned for fetching recent game scores and results.

## Deployment

Functions are designed to be deployed to AWS Lambda with:

- **Runtime**: Python 3.13
- **Trigger**: CloudWatch Events (scheduled)
- **Storage**: DynamoDB integration
- **Monitoring**: CloudWatch Logs

## Architecture

```
ESPN API → AWS Lambda Functions → DynamoDB → FastAPI Backend
```

The functions serve as the data ingestion layer, fetching fresh NFL data and storing it in DynamoDB for the FastAPI backend to serve.

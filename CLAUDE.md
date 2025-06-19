# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**us-flag-status** is a Python project in early development phase. The project appears to be focused on tracking or monitoring US flag status, though specific functionality is not yet implemented.

## Current Project State

This is a minimal Python project setup with:
- Git repository initialized
- Comprehensive Python-focused `.gitignore` 
- VS Code workspace configuration
- No source code or dependencies yet

## Technology Stack

- **Language:** Python (primary)
- **Supported Tools:** The `.gitignore` indicates support for multiple Python tools including:
  - Package managers: pip, pipenv, poetry, PDM, UV
  - Testing: pytest, coverage, tox, nox
  - Type checking: mypy, pyre, pytype
  - Documentation: Sphinx, mkdocs
  - Web frameworks: Django, Flask
  - Data science: Jupyter, IPython

## Development Commands

**No commands available yet** - the project lacks:
- Dependency management files (requirements.txt, pyproject.toml)
- Test configuration
- Build scripts
- Linting configuration

## Project Structure

Currently minimal structure:
```
├── .gitignore                     # Python development exclusions
├── README.md                      # Basic project title only
├── us-flag-status.code-workspace  # VS Code workspace
└── CLAUDE.md                      # This file
```

## Development Setup

Since no dependencies or build system is configured yet, standard Python development practices apply:
1. Create virtual environment
2. Install dependencies when added
3. Follow Python project conventions for directory structure (src/, tests/, docs/)

## Architecture Notes

**US Flag Half-Staff Status API** - Cost-optimized AWS serverless architecture planned:
- Lambda functions for API endpoints and web scraping
- API Gateway with caching
- DynamoDB on-demand for data persistence
- EventBridge for scheduled scraping
- Data source: whitehouse.gov proclamations

## Data Storage Cost Analysis

**DynamoDB On-Demand (Selected)**: ~$1.50/month
- Storage: <1GB = $0.25/month
- Writes: ~30/month = $0.04
- Reads: ~10K/month = $1.25
- No provisioned capacity charges
- Built-in backup/restore

**Alternative Options Considered**:
- S3 + JSON files: ~$0.50/month (cheapest but no querying)
- RDS Aurora Serverless v2: ~$25-50/month (too expensive)
- SQLite in Lambda: ~$0.10/month (complex coordination issues)

**Total estimated monthly cost**: ~$5-12 (DynamoDB + Lambda + API Gateway)
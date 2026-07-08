# SaaS API Research Pipeline

This is an automated research pipeline that extracts API and authentication information for a list of SaaS applications. It uses DuckDuckGo for documentation discovery and Groq's Llama 3.3 70B for structured data extraction.

## Features
- Discovers API docs via DuckDuckGo search.
- Extracts and standardizes data using a Pydantic schema and Groq's LLM.
- Resilient to failures (saves intermediate results incrementally).
- Provides a verification script to manually re-run specific apps.

## Setup

1. **Install Python 3.9+** (if not already installed).
2. **Set up a virtual environment (optional but recommended):**
   ```bash
   python -m venv venv
   source venv/bin/activate
   ```
3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
4. **Configure Environment Variables:**
   - Copy `.env.example` to `.env`:
     ```bash
     cp .env.example .env
     ```
   - Edit `.env` and add your `GROQ_API_KEY`.

## Usage

### Run the Full Batch

To research all apps listed in `apps_seed.json`:

```bash
python runner.py
```

This will:
- Iterate through each app in `apps_seed.json`.
- Perform the search, fetch the docs, and run the LLM extraction.
- Save the results incrementally to `results.json` to prevent data loss.
- Output a final `results.csv` for easy skimming.
- Print a summary of apps that could not be processed and need human review.

*Note: If the script is stopped and restarted, it will skip apps that were already successfully processed in `results.json`.*

### Re-run Specific Apps

If you want to manually fix a URL or just retry an app that failed/needs human review, use the `recheck.py` script:

```bash
python recheck.py --ids 5 12 15
```

This will run the research module just for those specific IDs, update `results.json`, and regenerate `results.csv`.

## Output Schema

The extracted data follows this schema:
- `id`: The app's ID from the seed.
- `category`: App category.
- `app`: App name.
- `description`: A one-line description of the app.
- `auth_methods`: List of authentication methods (e.g., OAuth2, API key).
- `self_serve`: One of `self-serve`, `gated-paid`, `gated-approval`, `gated-partnership`.
- `api_surface`: Short description of the API surface.
- `buildability_verdict`: `buildable-now`, `buildable-with-friction`, or `not-buildable`.
- `verdict_reason`: Reason for the buildability verdict.
- `evidence_url`: The URL used to extract this information.
- `confidence`: `high`, `medium`, or `low`.
- `needs_human_review`: Boolean indicating if the automated process struggled.

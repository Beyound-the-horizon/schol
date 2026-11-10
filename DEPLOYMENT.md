# Deployment Guide: Autonomous Scholarship Research Agents

This project provides two enterprise-grade, serverless deployment methods for running the scholarship research agent autonomously on a daily schedule, with full concurrency locks to protect against rate limits and duplicate executions.

---

## Concurrency & Rate Limit Mitigations

The pipeline includes a **3-tier concurrency mitigation architecture**:
1. **GitHub Actions Concurrency Lock**: `concurrency: group: autonomous-scholarship-pipeline-lock, cancel-in-progress: false` prevents any overlapping GitHub Action executions.
2. **Cloud Run Single Worker Constraints**: Configured with `--tasks=1 --parallelism=1 --max-retries=1` guaranteeing strictly 1 container task per execution.
3. **PostgreSQL Advisory Lock (`pg_try_advisory_lock`)**: Inside `core/tools/db.py`, the runner claims a database-level lock (`SCHOLARSHIP_RUNNER_LOCK_ID = 884729103`). If another run is in progress from any environment, it safely skips execution with an exit code of `0`.
4. **Adaptive Rate Pacing**: `AGENT_DELAY_SECONDS=3` between queries and `AGENT_ERROR_DELAY_SECONDS=5` with exponential backoff on retry.

---

## Method 1: GitHub Actions (Recommended - Zero Infrastructure Setup)

The repository includes a ready-to-run GitHub Actions workflow at [`.github/workflows/autonomous_agents.yml`](.github/workflows/autonomous_agents.yml).

### 1. Add Repository Secrets
Navigate to your GitHub repository: **Settings ➔ Secrets and variables ➔ Actions ➔ New repository secret** and add:

| Secret Name | Description | Example |
| :--- | :--- | :--- |
| `GOOGLE_GEMINI_API` | Your Google Gemini API Key | `AIzaSy...` |
| `DB_USER` | Supabase / PostgreSQL Username | `postgres.yourproject` |
| `DB_PASSWORD` | Supabase / PostgreSQL Password | `YourSecurePassword` |
| `DB_HOST` | Supabase Database Host | `aws-0-eu-central-1.pooler.supabase.com` |
| `DB_PORT` | PostgreSQL Port (optional, defaults to 5432) | `5432` or `6543` |
| `DB_NAME` | Database Name (optional, defaults to postgres) | `postgres` |
| `SCHOLARSHIP_CATALOG_URL` | *(Optional)* Google Doc list URL | `https://docs.google.com/document/d/...` |

### 2. Automatic Schedule
The workflow automatically executes **daily at 06:00 UTC** (`cron: '0 6 * * *'`).

### 3. Manual On-Demand Trigger
1. Go to the **Actions** tab in GitHub.
2. Select **Autonomous Scholarship Agents**.
3. Click **Run workflow**, set the batch limit (default: 5), and click **Run workflow**.

---

## Method 2: Google Cloud Run Jobs & Cloud Scheduler

Runs as an on-demand container job on Google Cloud Platform (zero idle cost; spins up for ~2 minutes, saves to Supabase, then shuts down).

### 1. Store Secrets in GCP Secret Manager
```bash
gcloud services enable secretmanager.googleapis.com

# Create the secrets
echo -n "YOUR_GEMINI_KEY" | gcloud secrets create GOOGLE_GEMINI_API --data-file=-
echo -n "YOUR_DB_USER"    | gcloud secrets create DB_USER --data-file=-
echo -n "YOUR_DB_PASS"    | gcloud secrets create DB_PASSWORD --data-file=-
echo -n "YOUR_DB_HOST"    | gcloud secrets create DB_HOST --data-file=-
echo -n "5432"             | gcloud secrets create DB_PORT --data-file=-
echo -n "postgres"         | gcloud secrets create DB_NAME --data-file=-
```

### 2. Deploy
Run the automated deployment script:
* **Linux / macOS**:
  ```bash
  chmod +x cloudrun/deploy.sh
  ./cloudrun/deploy.sh
  ```
* **Windows (PowerShell)**:
  ```powershell
  .\cloudrun\deploy.ps1
  ```

### 3. Triggering Cloud Run Job Manually
```bash
gcloud run jobs execute autonomous-scholarship-agent --region=us-central1
```


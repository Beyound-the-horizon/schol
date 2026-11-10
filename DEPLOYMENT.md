# Deployment Guide: Autonomous Scholarship Research Agents

This project provides two enterprise-grade, serverless deployment methods for running the scholarship research agent autonomously on a daily schedule, with full concurrency locks to protect against rate limits and duplicate executions.

---

## ⚠️ Important: Supabase IPv4 vs. IPv6 (GitHub Actions & Serverless)

GitHub Actions runners operate on an **IPv4-only network**. 
- Supabase's **Direct Connection** (`db.[project-ref].supabase.co`) resolves to an **IPv6-only** address (`2a05:d018:...`), causing `psycopg.OperationalError: Network is unreachable`.
- **Solution**: Always use Supabase's **Connection Pooler (Supavisor)**, which supports IPv4.

### Where to Find the IPv4 Pooler in Supabase:
1. Open your **Supabase Dashboard** ➔ Click the **Connect** button at the top (or go to **Project Settings ➔ Database**).
2. Under the **Connection string** tab, select **Session pooler** (recommended, Port `5432`):
   * **Host**: `aws-0-[region].pooler.supabase.com` (e.g. `aws-0-eu-central-1.pooler.supabase.com`)
   * **Port**: `5432`
   * **User**: `postgres.[YOUR-PROJECT-REF]` *(Notice the project reference is attached to the username!)*
   * **Password**: Your database password
   * **Database**: `postgres`

---

## Method 1: GitHub Actions (Recommended)

The repository includes a ready-to-run GitHub Actions workflow at [`.github/workflows/autonomous_agents.yml`](.github/workflows/autonomous_agents.yml).

### Option A: Using Discrete Secrets in GitHub (Recommended)
Navigate to **Settings ➔ Secrets and variables ➔ Actions ➔ New repository secret** and add:

| Secret Name | Value Description | Example / Notes |
| :--- | :--- | :--- |
| `DB_HOST` | **Pooler Host** (IPv4) | `aws-0-eu-central-1.pooler.supabase.com` |
| `DB_USER` | **Pooler User** with project ref | `postgres.yourprojectref` |
| `DB_PASSWORD` | Database Password | `YourSecretPassword` |
| `DB_PORT` | Pooler Port | `5432` (or `6543`) |
| `DB_NAME` | Database Name | `postgres` |
| `GOOGLE_GEMINI_API` | Google Gemini API Key | `AIzaSy...` |
| `SCHOLARSHIP_CATALOG_URL` | *(Optional)* Google Doc list URL | `https://docs.google.com/document/d/...` |

### Option B: Using a Single `DATABASE_URL` Secret
Alternatively, you can add a single secret named `DATABASE_URL`:
```
postgresql://postgres.YOUR_PROJECT_REF:YOUR_PASSWORD@aws-0-YOUR_REGION.pooler.supabase.com:5432/postgres?sslmode=require
```

### Automatic Schedule & Manual Trigger
* **Daily Cron**: Automatically executes every day at **06:00 UTC** (`cron: '0 6 * * *'`).
* **Manual UI Trigger**: Go to **Actions ➔ Autonomous Scholarship Agents ➔ Run workflow**.

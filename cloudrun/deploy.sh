#!/usr/bin/env bash
set -e

# ==============================================================================
# Deploy Autonomous Scholarship Agent to Google Cloud Run Jobs & Cloud Scheduler
# ==============================================================================

# Configurations (customize as needed)
PROJECT_ID=$(gcloud config get-value project)
REGION="${REGION:-us-central1}"
JOB_NAME="autonomous-scholarship-agent"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${JOB_NAME}:latest"
SCHEDULER_JOB_NAME="autonomous-agent-daily-trigger"
CRON_SCHEDULE="0 6 * * *" # Daily at 06:00 UTC

echo "========================================================"
echo "Deploying ${JOB_NAME} to Google Cloud Run Jobs"
echo "Project: ${PROJECT_ID} | Region: ${REGION}"
echo "========================================================"

# 1. Enable required GCP services
echo "[1/4] Enabling required Google Cloud APIs..."
gcloud services enable \
    run.googleapis.com \
    cloudbuild.googleapis.com \
    cloudscheduler.googleapis.com \
    secretmanager.googleapis.com \
    --project="${PROJECT_ID}"

# 2. Build container image using Cloud Build
echo "[2/4] Building container image via Google Cloud Build..."
gcloud builds submit --tag "${IMAGE_NAME}" . --project="${PROJECT_ID}"

# 3. Create or update Cloud Run Job with concurrency mitigation
# Notice: --tasks=1 --parallelism=1 --max-retries=1 prevents overlapping execution
echo "[3/4] Creating/updating Cloud Run Job with single-concurrency guard..."
gcloud run jobs deploy "${JOB_NAME}" \
    --image="${IMAGE_NAME}" \
    --region="${REGION}" \
    --tasks=1 \
    --parallelism=1 \
    --max-retries=1 \
    --task-timeout=900s \
    --cpu=1 \
    --memory=1Gi \
    --set-env-vars="AGENT_DELAY_SECONDS=3,AGENT_ERROR_DELAY_SECONDS=5" \
    --set-secrets="GOOGLE_GEMINI_API=GOOGLE_GEMINI_API:latest,user=DB_USER:latest,password=DB_PASSWORD:latest,host=DB_HOST:latest,dbname=DB_NAME:latest,port=DB_PORT:latest" \
    --project="${PROJECT_ID}"

# 4. Configure automatic trigger with Cloud Scheduler
echo "[4/4] Setting up Cloud Scheduler for automatic daily trigger..."
SERVICE_ACCOUNT="cloud-run-invoker@${PROJECT_ID}.iam.gserviceaccount.com"

# Ensure invoker service account exists
if ! gcloud iam service-accounts describe "${SERVICE_ACCOUNT}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
    gcloud iam service-accounts create cloud-run-invoker \
        --display-name="Cloud Run Jobs Invoker" \
        --project="${PROJECT_ID}"
fi

gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/run.invoker" >/dev/null

# Create or update Cloud Scheduler job
if gcloud scheduler jobs describe "${SCHEDULER_JOB_NAME}" --location="${REGION}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
    gcloud scheduler jobs update http "${SCHEDULER_JOB_NAME}" \
        --location="${REGION}" \
        --schedule="${CRON_SCHEDULE}" \
        --uri="https://${REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${PROJECT_ID}/jobs/${JOB_NAME}:run" \
        --http-method=POST \
        --oauth-service-account-email="${SERVICE_ACCOUNT}" \
        --project="${PROJECT_ID}"
else
    gcloud scheduler jobs create http "${SCHEDULER_JOB_NAME}" \
        --location="${REGION}" \
        --schedule="${CRON_SCHEDULE}" \
        --uri="https://${REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${PROJECT_ID}/jobs/${JOB_NAME}:run" \
        --http-method=POST \
        --oauth-service-account-email="${SERVICE_ACCOUNT}" \
        --project="${PROJECT_ID}"
fi

echo "========================================================"
echo "Deployment Successful!"
echo "Job Name: ${JOB_NAME}"
echo "Schedule: ${CRON_SCHEDULE} (Cloud Scheduler: ${SCHEDULER_JOB_NAME})"
echo "To test run manually: gcloud run jobs execute ${JOB_NAME} --region=${REGION}"
echo "========================================================"


# Deploy Autonomous Scholarship Agent to Google Cloud Run Jobs (PowerShell)
param(
    [string]$Region = "us-central1",
    [string]$JobName = "autonomous-scholarship-agent",
    [string]$CronSchedule = "0 6 * * *"
)

$ErrorActionPreference = "Stop"

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "Deploying $JobName to Google Cloud Run Jobs (PowerShell)" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan

$ProjectId = (gcloud config get-value project).Trim()
if (-not $ProjectId) {
    Write-Error "No active GCP project found. Run 'gcloud config set project <PROJECT_ID>' first."
}

$ImageName = "gcr.io/$ProjectId/${JobName}:latest"
$SchedulerJobName = "autonomous-agent-daily-trigger"

Write-Host "[1/3] Building image via Cloud Build..." -ForegroundColor Yellow
gcloud builds submit --tag $ImageName . --project $ProjectId

Write-Host "[2/3] Deploying Cloud Run Job with concurrency mitigation..." -ForegroundColor Yellow
gcloud run jobs deploy $JobName `
    --image $ImageName `
    --region $Region `
    --tasks 1 `
    --parallelism 1 `
    --max-retries 1 `
    --task-timeout 900s `
    --cpu 1 `
    --memory 1Gi `
    --set-env-vars "AGENT_DELAY_SECONDS=3,AGENT_ERROR_DELAY_SECONDS=5" `
    --set-secrets "GOOGLE_GEMINI_API=GOOGLE_GEMINI_API:latest,user=DB_USER:latest,password=DB_PASSWORD:latest,host=DB_HOST:latest,dbname=DB_NAME:latest,port=DB_PORT:latest" `
    --project $ProjectId

Write-Host "[3/3] Setting up Cloud Scheduler automatic trigger ($CronSchedule)..." -ForegroundColor Yellow
$ServiceAccount = "cloud-run-invoker@$ProjectId.iam.gserviceaccount.com"

# Check if scheduler job exists
$jobExists = gcloud scheduler jobs describe $SchedulerJobName --location $Region --project $ProjectId 2>$null
if ($jobExists) {
    gcloud scheduler jobs update http $SchedulerJobName `
        --location $Region `
        --schedule $CronSchedule `
        --uri "https://${Region}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/$ProjectId/jobs/${JobName}:run" `
        --http-method POST `
        --oauth-service-account-email $ServiceAccount `
        --project $ProjectId
} else {
    gcloud scheduler jobs create http $SchedulerJobName `
        --location $Region `
        --schedule $CronSchedule `
        --uri "https://${Region}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/$ProjectId/jobs/${JobName}:run" `
        --http-method POST `
        --oauth-service-account-email $ServiceAccount `
        --project $ProjectId
}

Write-Host "========================================================" -ForegroundColor Green
Write-Host "Deployment completed successfully!" -ForegroundColor Green
Write-Host "Manual trigger test command: gcloud run jobs execute $JobName --region=$Region" -ForegroundColor Green
Write-Host "========================================================" -ForegroundColor Green


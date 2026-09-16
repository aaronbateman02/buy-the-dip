# Deploy dashboard to EC2 (btd.nostrabotus.com).
# Usage: powershell -File nba_favorites/deploy/deploy.ps1
# Rule: run this after EVERY dashboard change. No local serving needed.
$ErrorActionPreference = "Stop"
$KEY = "$env:USERPROFILE\.ssh\ArbAgentKeyPair1.pem"
$HOST_ = "ec2-user@77.112.201.29"
$LOCAL = "C:\Users\User\OneDrive\Desktop\Projects\SmartMoney\nba_favorites\dashboard\index.html"
$REMOTE = "/opt/nba-favorites/dashboard/index.html"

scp -i $KEY -o StrictHostKeyChecking=no $LOCAL "${HOST_}:${REMOTE}"
if ($LASTEXITCODE -ne 0) { throw "scp failed" }
Write-Host "Deployed index.html to btd.nostrabotus.com"

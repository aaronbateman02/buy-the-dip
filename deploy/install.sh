#!/bin/bash
# Deploy NBA favorites dashboard to /opt/nba-favorites + nginx vhost.
# Safe: only touches /opt/nba-favorites, /etc/nginx/conf.d/btd.conf, and the
# btd.nostrabotus.com cert. Existing fwr.nostrabotus.com config untouched.
set -euo pipefail

APP_DIR=/opt/nba-favorites
SERVICE=nba-fetch

echo "== create app dir =="
sudo mkdir -p "$APP_DIR/dashboard" "$APP_DIR/data"
sudo chown -R ec2-user:ec2-user "$APP_DIR"

echo "== install nginx vhost (port 80; certbot upgrades to TLS) =="
sudo cp ~/deploy-staging/btd.conf /etc/nginx/conf.d/btd.conf
sudo nginx -t
sudo systemctl reload nginx

echo "== TLS cert for btd.nostrabotus.com =="
if [ ! -d /etc/letsencrypt/live/btd.nostrabotus.com ]; then
  sudo certbot --nginx -d btd.nostrabotus.com --non-interactive --agree-tos \
    --register-unsafely-without-email --redirect
else
  echo "cert already exists, skipping"
fi

echo "== fetch service =="
sudo cp ~/deploy-staging/nba-fetch.service /etc/systemd/system/nba-fetch.service
sudo systemctl daemon-reload
sudo systemctl enable --now "$SERVICE"

echo "== status =="
sudo systemctl is-active "$SERVICE"
curl -s -o /dev/null -w "local dashboard: %{http_code}\n" http://127.0.0.1/dashboard/index.html

# Buy The Dip — NBA Favorite Comebacks

Live: https://btd.nostrabotus.com/dashboard/

## Deploy rule

**After EVERY dashboard change, deploy to EC2 immediately:**

```powershell
powershell -File nba_favorites/deploy/deploy.ps1
```

No local serving needed — EC2 is the source of truth for viewing.

## Data (SQLite)

- `data/games.db` — source of truth (`games` + `walked` tables, committed immediately)
- `data/games.csv` — live export of the db for the dashboard (rewritten every 10 days)
- Restarts lose nothing: walked days are skipped, pending odds re-queued

## Layout

- `dashboard/index.html` — the whole UI (stats + simulator, no build step)
- `fetch.py` — ESPN pull (scoreboards + closing odds), runs as `nba-fetch` systemd service on EC2
- `data/games.csv` — pulled games (checkpointed; service resumes from here)
- `data/progress.json` — pull progress for the dashboard progress bar
- `analyze.py`, `sweep.py`, `sweep2.py` — one-off analysis scripts
- `deploy/` — `btd.conf` (nginx vhost), `nba-fetch.service`, `install.sh`, `deploy.ps1`

## Server (i-0bc615a44196ecb51, 77.112.201.29)

- App: `/opt/nba-favorites/` (`dashboard/`, `data/`, `fetch.py`)
- Nginx vhost: `/etc/nginx/conf.d/btd.conf` (TLS via certbot)
- Pull service: `nba-fetch` (systemd, auto-restart)
- Existing `fwr.nostrabotus.com` site untouched (separate vhost, node API on :3001)

## Strategy (locked defaults)

Simulator defaults: Q1 · spread ≥8 · deficit ≤9 → 81% win (46/57).
Presets: Q1 ≥8 ≤9 · Q1 ≥8 ≤12 (83%, n=63) · Half ≥8 ≤6 (80%, n=30).

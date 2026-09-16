"""Fetch every NBA game (2023-24, 2024-25, 2025-26) with quarter scores + pre-game favorite.

Sources (all ESPN, free, no key):
  - Scoreboard API (per day): game ids, teams, quarter linescores, final, winner
  - Core API odds endpoint (per game): closing moneyline favorite + spread + total

Storage: data/games.db (SQLite, committed immediately — restarts lose nothing).
data/games.csv is a live export of the db for the dashboard.
"""
import csv
import datetime as dt
import json
import os
import queue
import sqlite3
import time
import urllib.error
import urllib.request

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
GAMES_JSON = os.path.join(DATA, "games.json")  # legacy, no longer written
GAMES_CSV = os.path.join(DATA, "games.csv")  # live export of SQLite for dashboard
DB_PATH = os.path.join(DATA, "games.db")
PROGRESS_JSON = os.path.join(DATA, "progress.json")


def report_progress(**kw):
    """Write a small JSON status file the dashboard polls for its progress bar."""
    try:
        kw["updated"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
        with open(PROGRESS_JSON, "w") as f:
            json.dump(kw, f)
    except Exception:
        pass

SEASONS = [
    ("2023-24", "2023-10-01", "2024-06-30"),
    ("2024-25", "2024-10-01", "2025-06-30"),
    ("2025-26", "2025-10-01", "2026-06-30"),
]

CSV_FIELDS = [
    "game_id", "season", "date", "seasontype", "home", "away",
    "home_q1", "home_q2", "home_q3", "home_q4",
    "away_q1", "away_q2", "away_q3", "away_q4",
    "home_final", "away_final", "home_winner",
    "fav", "provider", "home_ml", "away_ml", "spread", "total", "details",
]


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
}

REQUEST_GAP = 1.2  # seconds between requests; keeps ESPN from rate-limiting
_last_req = [0.0]
import threading as _th
_req_lock = _th.Lock()


def pace():
    import time as _t
    with _req_lock:
        wait = REQUEST_GAP - (_t.time() - _last_req[0])
        if wait > 0:
            _t.sleep(wait)
        _last_req[0] = _t.time()


def get(url, retries=6):
    for i in range(retries):
        pace()
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            return json.loads(urllib.request.urlopen(req, timeout=30).read())
        except urllib.error.HTTPError as e:
            if e.code == 403:  # rate-limited: back off hard, then retry
                time.sleep(30 * (i + 1))
                continue
            if i == retries - 1:
                raise
            time.sleep(2 * (i + 1))
        except Exception:
            if i == retries - 1:
                raise
            time.sleep(2 * (i + 1))


def daterange(a, b):
    d = dt.date.fromisoformat(a)
    end = dt.date.fromisoformat(b)
    while d <= end:
        yield d.strftime("%Y%m%d")
        d += dt.timedelta(days=1)


def parse_game(ev, season):
    """Parse one scoreboard event into a game dict, or None to skip."""
    try:
        comp = ev["competitions"][0]
        if not comp["status"]["type"].get("completed"):
            return None
        comps = {c["homeAway"]: c for c in comp["competitors"]}
        if "home" not in comps or "away" not in comps:
            return None

        def qs(c):
            return {
                x["period"]: float(x["value"])
                for x in (c.get("linescores") or [])
                if "period" in x and x.get("value") is not None
            }

        hq, aq = qs(comps["home"]), qs(comps["away"])
        if not all(p in hq and p in aq for p in (1, 2, 3, 4)):
            return None
        return dict(
            game_id=ev["id"],
            season=season,
            date=ev["date"][:10],
            seasontype=(ev.get("season") or {}).get("slug", ""),
            home=comps["home"]["team"]["abbreviation"],
            away=comps["away"]["team"]["abbreviation"],
            home_q1=hq[1], home_q2=hq[2], home_q3=hq[3], home_q4=hq[4],
            away_q1=aq[1], away_q2=aq[2], away_q3=aq[3], away_q4=aq[4],
            home_final=float(comps["home"]["score"]),
            away_final=float(comps["away"]["score"]),
            home_winner=comps["home"].get("winner"),
        )
    except Exception:
        return None


COLUMNS = [
    "game_id", "season", "date", "seasontype", "home", "away",
    "home_q1", "home_q2", "home_q3", "home_q4",
    "away_q1", "away_q2", "away_q3", "away_q4",
    "home_final", "away_final", "home_winner",
    "fav", "provider", "home_ml", "away_ml", "spread", "total", "details",
]
CSV_FIELDS = COLUMNS  # dashboard export keeps the same columns


def db():
    con = sqlite3.connect(DB_PATH, timeout=30)
    con.execute("PRAGMA journal_mode=WAL")
    cols = ", ".join(f"{c} TEXT" for c in COLUMNS if c != "game_id")
    con.execute(f"CREATE TABLE IF NOT EXISTS games (game_id TEXT PRIMARY KEY, {cols})")
    con.execute("CREATE TABLE IF NOT EXISTS walked (day TEXT PRIMARY KEY)")
    con.commit()
    return con


def migrate_csv(con):
    """One-time import of any existing games.csv rows into SQLite."""
    if not os.path.exists(GAMES_CSV):
        return 0
    n = 0
    with open(GAMES_CSV, newline="") as f:
        for row in csv.DictReader(f):
            vals = [row.get(c, "") for c in COLUMNS]
            try:
                con.execute(f"INSERT OR IGNORE INTO games VALUES ({','.join('?' * len(COLUMNS))})", vals)
                n += con.total_changes and 1 or 0
            except Exception:
                pass
    con.commit()
    return n


def export_csv(con):
    """Rewrite games.csv from SQLite so the dashboard always sees everything."""
    rows = con.execute(f"SELECT {','.join(COLUMNS)} FROM games ORDER BY date, game_id").fetchall()
    tmp = GAMES_CSV + ".tmp"
    with open(tmp, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(COLUMNS)
        w.writerows(rows)
    os.replace(tmp, GAMES_CSV)
    return len(rows)


def main():
    os.makedirs(DATA, exist_ok=True)
    all_days = [(season, ds) for season, start, end in SEASONS for ds in daterange(start, end)]
    total_days = len(all_days)

    con = db()
    imported = migrate_csv(con)
    done = {r[0] for r in con.execute("SELECT game_id FROM games")}
    walked = {r[0] for r in con.execute("SELECT day FROM walked")}
    print(f"{len(done)} games in db ({imported} migrated from csv), {len(walked)} days walked", flush=True)

    # Pipeline: scoreboard walk inserts games immediately (odds pending);
    # 2 odds threads fill in odds via UPDATE the moment each fetch lands.
    import threading as _th2
    work_q = queue.Queue()
    stop_event = _th2.Event()

    def odds_updater():
        wcon = db()
        while not stop_event.is_set() or not work_q.empty():
            try:
                gid = work_q.get(timeout=1)
            except queue.Empty:
                continue
            try:
                odd = fetch_odds(gid)
            except Exception:
                odd = {"fav": "UNKNOWN", "provider": "error"}
            wcon.execute(
                "UPDATE games SET fav=?, provider=?, home_ml=?, away_ml=?, spread=?, total=?, details=? "
                "WHERE game_id=?",
                (str(odd.get("fav", "")), str(odd.get("provider", "")),
                 str(odd.get("home_ml", "")), str(odd.get("away_ml", "")),
                 str(odd.get("spread", "")), str(odd.get("total", "")),
                 str(odd.get("details", "")), gid),
            )
            wcon.commit()
            work_q.task_done()
        wcon.close()

    workers = [_th2.Thread(target=odds_updater, daemon=True) for _ in range(2)]
    for t in workers:
        t.start()

    # Re-queue games that still lack odds.
    pending = [r[0] for r in con.execute(
        "SELECT game_id FROM games WHERE fav IS NULL OR fav = ''")]
    for gid in pending:
        work_q.put(gid)
    print(f"Re-queued {len(pending)} games still lacking odds", flush=True)

    report_progress(phase="both", day_done=len(walked), day_total=total_days,
                    games_found=len(done), odds_done=len(done) - len(pending),
                    odds_total=len(done))

    for i, (season, ds) in enumerate(all_days, 1):
        if ds in walked:
            continue  # already walked in a previous run
        try:
            d = get(
                "http://site.api.espn.com/apis/site/v2/sports/basketball/nba"
                f"/scoreboard?dates={ds}"
            )
        except Exception as e:
            print(f"  scoreboard fail {ds}: {e}", flush=True)
            continue
        new = 0
        for ev in d.get("events", []):
            if ev["id"] in done:
                continue
            g = parse_game(ev, season)
            if g is None:
                continue
            cur = con.execute(
                f"INSERT OR IGNORE INTO games VALUES ({','.join('?' * len(COLUMNS))})",
                [str(g.get(c, "")) for c in COLUMNS],
            )
            if cur.rowcount:
                new += 1
                done.add(ev["id"])
                work_q.put(ev["id"])
        con.execute("INSERT OR IGNORE INTO walked VALUES (?)", (ds,))
        walked.add(ds)
        con.commit()
        if i % 10 == 0 or i == total_days:
            n_games = con.execute("SELECT COUNT(*) FROM games").fetchone()[0]
            n_odds = con.execute(
                "SELECT COUNT(*) FROM games WHERE fav IS NOT NULL AND fav != ''").fetchone()[0]
            export_csv(con)
            report_progress(phase="both", day_done=len(walked), day_total=total_days,
                            games_found=n_games, odds_done=n_odds, odds_total=n_games)
            print(f"{season} {ds}: walked {len(walked)}/{total_days}, "
                  f"games {n_games}, odds {n_odds}", flush=True)

    # Scoreboards done; let the odds queue drain, then finish.
    print("Scoreboards complete — draining odds queue...", flush=True)
    work_q.join()
    stop_event.set()
    for t in workers:
        t.join()
    n = export_csv(con)
    report_progress(phase="done", day_done=total_days, day_total=total_days,
                    games_found=n, odds_done=n, odds_total=n)
    print(f"Done. Total rows in db/csv: {n}", flush=True)
    con.close()


def fetch_odds(gid):
    """Return dict with pre-game favorite (closing lines) for one game."""
    try:
        d = get(
            "http://sports.core.api.espn.com/v2/sports/basketball/leagues/nba"
            f"/events/{gid}/competitions/{gid}/odds"
        )
    except Exception:
        return {"fav": "UNKNOWN", "provider": "fetch-error"}
    items = d.get("items") or []
    if not items:
        return {"fav": "UNKNOWN", "provider": "none"}
    ref, pname = None, ""
    for it in items:  # prefer a major book for consistency
        nm = (it.get("provider") or {}).get("name", "")
        if "Caesars" in nm:
            ref, pname = it["$ref"], nm
            break
    if ref is None:
        ref = items[0]["$ref"]
        pname = (items[0].get("provider") or {}).get("name", "")
    try:
        o = get(ref)
    except Exception:
        return {"fav": "UNKNOWN", "provider": pname}
    h, a = o.get("homeTeamOdds") or {}, o.get("awayTeamOdds") or {}
    hf, af = h.get("favorite"), a.get("favorite")
    hml, aml = h.get("moneyLine"), a.get("moneyLine")
    if hf and not af:
        fav = "HOME"
    elif af and not hf:
        fav = "AWAY"
    elif isinstance(hml, (int, float)) and isinstance(aml, (int, float)):
        if hml < aml:
            fav = "HOME"
        elif aml < hml:
            fav = "AWAY"
        else:
            fav = "PICKEM"
    else:
        fav = "UNKNOWN"
    return {
        "fav": fav,
        "provider": pname,
        "home_ml": hml if isinstance(hml, (int, float)) else "",
        "away_ml": aml if isinstance(aml, (int, float)) else "",
        "spread": o.get("spread", ""),
        "total": o.get("overUnder", ""),
        "details": o.get("details", ""),
    }


if __name__ == "__main__":
    main()

"""Analyze: how often does the pre-game favorite trail at Q1/Half/Q3, and still win?

Reads data/games.csv produced by fetch.py. Prints tables + writes data/report.md.
"""
import csv
import os
from collections import Counter

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
CSV = os.path.join(DATA, "games.csv")
REPORT = os.path.join(DATA, "report.md")


def load():
    rows = []
    with open(CSV, newline="") as f:
        for r in csv.DictReader(f):
            if r.get("fav") not in ("HOME", "AWAY"):
                continue  # skip pick'ems / unknowns
            try:
                for k in ("home_q1", "home_q2", "home_q3", "home_q4",
                          "away_q1", "away_q2", "away_q3", "away_q4",
                          "home_final", "away_final"):
                    r[k] = float(r[k])
            except (ValueError, TypeError):
                continue
            r["home_winner"] = r["home_winner"] in ("True", "true", "1", True)
            rows.append(r)
    return rows


def fav_scores(r):
    """Return (fav_q1, fav_q2, fav_q3, fav_q4, fav_final, dog_final, fav_won)."""
    if r["fav"] == "HOME":
        f = [r["home_q1"], r["home_q2"], r["home_q3"], r["home_q4"], r["home_final"]]
        d = [r["away_q1"], r["away_q2"], r["away_q3"], r["away_q4"], r["away_final"]]
        won = r["home_winner"]
    else:
        f = [r["away_q1"], r["away_q2"], r["away_q3"], r["away_q4"], r["away_final"]]
        d = [r["home_q1"], r["home_q2"], r["home_q3"], r["home_q4"], r["home_final"]]
        won = not r["home_winner"]
    return f, d, won


def cum(scores, n):
    return sum(scores[:n])


def pct(a, b):
    return 100.0 * a / b if b else 0.0


def main():
    rows = load()
    print(f"Games with a listed favorite: {len(rows)}")
    by_season = Counter(r["season"] for r in rows)
    print("By season:", dict(by_season))

    fav_wins = sum(1 for r in rows if fav_scores(r)[2])
    print(f"\nFavorite wins outright: {fav_wins}/{len(rows)} = {pct(fav_wins, len(rows)):.1f}%")

    checkpoints = [("End of Q1", 1), ("Halftime (Q2)", 2), ("End of Q3", 3)]
    out = []
    out.append("# NBA pre-game favorite: trailing splits & comeback rates\n")
    out.append(f"_{len(rows)} games with a listed favorite "
               f"({', '.join(f'{k}: {v}' for k, v in sorted(by_season.items()))}). "
               "Favorite from ESPN closing moneyline (Caesars preferred)._\n")
    out.append(f"**Favorite wins outright: {fav_wins}/{len(rows)} ({pct(fav_wins, len(rows)):.1f}%)**\n")

    for label, nq in checkpoints:
        trail = tied = lead = 0
        trail_win = tied_win = lead_win = 0
        trail_margin_sum = 0
        for r in rows:
            f, d, won = fav_scores(r)
            diff = cum(f, nq) - cum(d, nq)  # + means favorite leads
            if diff < 0:
                trail += 1
                trail_margin_sum += -diff
                trail_win += won
            elif diff == 0:
                tied += 1
                tied_win += won
            else:
                lead += 1
                lead_win += won
        print(f"\n--- {label} ---")
        print(f"  Fav trailing: {trail}/{len(rows)} ({pct(trail, len(rows)):.1f}%), "
              f"avg deficit {trail_margin_sum / trail if trail else 0:.1f} pts")
        print(f"    -> still wins: {trail_win}/{trail} = {pct(trail_win, trail):.1f}%")
        print(f"  Fav tied:     {tied}/{len(rows)} ({pct(tied, len(rows)):.1f}%)"
              f" -> wins {pct(tied_win, tied):.1f}%")
        print(f"  Fav leading:  {lead}/{len(rows)} ({pct(lead, len(rows)):.1f}%)"
              f" -> wins {pct(lead_win, lead):.1f}%")
        out.append(f"## {label}\n")
        out.append(f"- Favorite trailing: **{trail}/{len(rows)} ({pct(trail, len(rows)):.1f}%)**, "
                   f"avg deficit {trail_margin_sum / trail if trail else 0:.1f} pts")
        out.append(f"  - Still wins: **{trail_win}/{trail} ({pct(trail_win, trail):.1f}%)**")
        out.append(f"- Tied: {tied}/{len(rows)} ({pct(tied, len(rows)):.1f}%) "
                   f"-> wins {pct(tied_win, tied):.1f}%")
        out.append(f"- Leading: {lead}/{len(rows)} ({pct(lead, len(rows)):.1f}%) "
                   f"-> wins {pct(lead_win, lead):.1f}%\n")

    # Deficit-size buckets at each checkpoint
    out.append("## Comeback rate by deficit size\n")
    for label, nq in checkpoints:
        print(f"\n--- {label} by deficit ---")
        out.append(f"### {label}\n")
        out.append("| Deficit (pts) | Games | Fav wins | Win % |")
        out.append("|---|---|---|---|")
        buckets = [(1, 3), (4, 6), (7, 9), (10, 12), (13, 100)]
        for lo, hi in buckets:
            g = w = 0
            for r in rows:
                f, d, won = fav_scores(r)
                deficit = cum(d, nq) - cum(f, nq)
                if lo <= deficit <= hi:
                    g += 1
                    w += won
            tag = f"{lo}-{hi}" if hi < 100 else f"{lo}+"
            print(f"  down {tag}: {w}/{g} = {pct(w, g):.1f}%")
            out.append(f"| Down {tag} | {g} | {w} | {pct(w, g):.1f}% |")
        out.append("")

    with open(REPORT, "w") as f:
        f.write("\n".join(out) + "\n")
    print(f"\nReport written to {REPORT}")


if __name__ == "__main__":
    main()

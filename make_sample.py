"""Generate sample_data.csv (synthetic but realistic) so the dashboard works before the pull finishes."""
import csv
import os
import random

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "sample_data.csv")

random.seed(42)
TEAMS = ["BOS", "NYK", "PHI", "CLE", "MIL", "IND", "MIA", "ORL", "DEN", "MIN",
         "OKC", "PHX", "DAL", "LAC", "LAL", "GSW", "SAC", "MEM", "HOU", "SAS"]

FIELDS = ["game_id", "season", "date", "seasontype", "home", "away",
          "home_q1", "home_q2", "home_q3", "home_q4",
          "away_q1", "away_q2", "away_q3", "away_q4",
          "home_final", "away_final", "home_winner",
          "fav", "provider", "home_ml", "away_ml", "spread", "total", "details"]


def quarters(total):
    qs = [random.randint(22, 34) for _ in range(4)]
    diff = total - sum(qs)
    qs[3] += diff
    return qs


def one(i):
    spread_mag = random.choice([1.5, 2, 2.5, 3, 3.5, 4, 4.5, 5, 5.5, 6, 7, 8, 9, 10, 12, 14])
    fav_home = random.random() < 0.6
    ml = -int(110 + spread_mag * 32 + random.randint(-15, 15))
    dog_ml = int(abs(ml) * 0.75 + random.randint(0, 40))
    # favorite wins ~68%, stronger favs more likely
    p_win = min(0.55 + spread_mag * 0.02, 0.88)
    fav_wins = random.random() < p_win
    base = random.randint(108, 122)
    margin = abs(random.gauss(4 + spread_mag * 0.4, 6)) + 1
    if fav_wins:
        fav_total, dog_total = base + int(margin), base
    else:
        fav_total, dog_total = base, base + int(margin)
    if fav_home:
        hq, aq = quarters(fav_total), quarters(dog_total)
        # sometimes make fav trail early: shift points from early to late quarters
        if random.random() < 0.45:
            shift = random.randint(3, 9)
            hq[0] -= shift
            hq[3] += shift
        home, away, hf, af = fav_total, dog_total, True, False
        fav, hml, aml, spread = "HOME", ml, dog_ml, -spread_mag
    else:
        aq, hq = quarters(fav_total), quarters(dog_total)
        if random.random() < 0.45:
            shift = random.randint(3, 9)
            aq[0] -= shift
            aq[3] += shift
        home, away, hf, af = dog_total, fav_total, False, True
        fav, hml, aml, spread = "AWAY", dog_ml, ml, spread_mag
    home_team, away_team = random.sample(TEAMS, 2)
    return [f"S{i:05d}", "2024-25", f"2025-01-{(i % 28) + 1:02d}", "Regular Season",
            home_team, away_team] + hq + aq + [home, away, hf, fav,
            "SampleBook", hml, aml, spread, 224.5, f"{home_team} ({spread:+g})"]


with open(OUT, "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(FIELDS)
    for i in range(600):
        w.writerow(one(i))
print(f"Wrote {OUT} (600 rows)")

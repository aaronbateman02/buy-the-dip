import csv
import math

P = r'C:\Users\User\OneDrive\Desktop\Projects\SmartMoney\nba_favorites\data\games.csv'
rows = [r for r in csv.DictReader(open(P))
        if 'regular' in (r.get('seasontype') or '') and r.get('fav') in ('HOME', 'AWAY')]


def num(x):
    try:
        return float(x)
    except (ValueError, TypeError):
        return None


def favline(r):
    hq = [num(r[f'home_q{i}']) for i in (1, 2, 3, 4)]
    aq = [num(r[f'away_q{i}']) for i in (1, 2, 3, 4)]
    hw = (r['home_winner'] or '').lower() == 'true'
    if r['fav'] == 'HOME':
        return hq, aq, hw
    return aq, hq, not hw


def cum(a, n):
    return sum(a[:n])


def wilson_lo(w, n, z=1.645):  # 90% lower bound
    if not n:
        return 0.0
    p = w / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    m = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return max(0.0, (c - m) / d)


seasons = sorted({r['season'] for r in rows})
nseasons = len(seasons)
print(f'games: {len(rows)} over {nseasons} season(s): {seasons}')

LAB = {1: 'Q1', 2: 'Half', 3: 'Q3'}
res = []
for nq in (1, 2, 3):
    for minsp in (1, 3, 5, 8, 10, 12):
        for maxd in (3, 6, 9, 12):
            g = w = 0
            for r in rows:
                sp = num(r['spread'])
                if sp is None or abs(sp) < minsp:
                    continue
                F, D, won = favline(r)
                d = cum(D, nq) - cum(F, nq)
                if 1 <= d <= maxd:
                    g += 1
                    w += won
            if g >= 10:
                p = w / g
                lo = wilson_lo(w, g)
                # breakeven YES price (cents) before fees; margin over 50c fair coin
                res.append(dict(p=p, g=g, w=w, nq=nq, minsp=minsp, maxd=maxd,
                                lo=lo, be=p * 100, freq=g / nseasons))

print(f'\n{len(res)} combos n>=10. Ranked by Wilson-90 lower bound (conservative margin):')
print(f'{"cp":4s} {"spread":>8s} {"def":>6s} {"w/n":>9s} {"win%":>6s} {"lo90":>6s} {"breakeven":>9s} {"/season":>7s}')
for r in sorted(res, key=lambda x: -x['lo'])[:25]:
    print(f'{LAB[r["nq"]]:4s} {r["minsp"]:>8.1f} {r["maxd"]:>6d} '
          f'{r["w"]:>3d}/{r["g"]:<3d} {100*r["p"]:>5.1f}% {100*r["lo"]:>5.1f}% '
          f'{r["be"]:>8.1f}c {r["freq"]:>7.1f}')

print('\nRanked by frequency (most chances per season), min 60% win rate:')
freq = [r for r in res if r['p'] >= 0.60]
for r in sorted(freq, key=lambda x: -x['freq'])[:15]:
    print(f'{LAB[r["nq"]]:4s} {r["minsp"]:>8.1f} {r["maxd"]:>6d} '
          f'{r["w"]:>3d}/{r["g"]:<3d} {100*r["p"]:>5.1f}% lo90 {100*r["lo"]:>5.1f}% '
          f'breakeven {r["be"]:>5.1f}c {r["freq"]:>5.1f}/season')

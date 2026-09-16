import csv

P = r'C:\Users\User\OneDrive\Desktop\Projects\SmartMoney\nba_favorites\data\games.csv'
rows = [r for r in csv.DictReader(open(P))
        if 'regular' in (r.get('seasontype') or '') and r.get('fav') in ('HOME', 'AWAY')]
print('regular fav games:', len(rows))


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
                res.append((w / g, g, w, nq, minsp, maxd))
res.sort(reverse=True)
print(len(res), 'combos with n>=10. Top 20 by win rate:')
for pp, g, w, nq, minsp, maxd in res[:20]:
    print(f'  {LAB[nq]:4s} spread>={minsp:4.1f} def<={maxd:2d}: {w}/{g}={100*pp:.1f}%')

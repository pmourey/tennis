from random import choice

from common import round_robin

def are_distinct(matches):
    # Concaténer chaque équipe dans chaque match en une seule chaîne
    s = ''.join(f"{team1}{team2}" for team1, team2 in matches)
    return len(s) == len(set(s))

n = 5
matchdays_count = n - 1 if n % 2 == 0 else n
schedule = {}
matchs_data = round_robin(n)
for i in range(matchdays_count):
    matches = matchs_data[i * n // 2: (i + 1) * n // 2]
    print(f'MATCHDAY {i + 1} = {matches}')
    schedule[i + 1] = matches

print(schedule)

new_schedule = {}
if n % 2:
    num_matches_per_day = n // 2
    finished = False

    while not finished:
        data = matchs_data[:]
        distinct = True
        i = 0
        while i < matchdays_count:
            for _ in range(num_matches_per_day):
                m = choice(data)
                data.remove(m)
                new_schedule[i + 1] = new_schedule.get(i + 1, []) + [m]
            distinct = are_distinct(new_schedule[i + 1])
            if not distinct:
                break
            i += 1
        if distinct:
            finished = True

    for matchday, matches in new_schedule.items():
        print(f'MATCHDAY {matchday}: {matches}')

from random import choice

from common import round_robin


def distribute_matches(matches, Q, num_match_per_pool):
    # Répartition des matchs$
    done = False
    while not done:
        # Initialiser le calendrier
        schedule = {day: [] for day in range(1, Q + 1)}
        teams_played_per_day = {day: set() for day in range(1, Q + 1)}
        match_copy = matches[:]
        is_duplicate = False
        for day in range(1, Q + 1):
            if is_duplicate:
                continue
            for _ in range(num_match_per_pool):
                if is_duplicate:
                    continue
                team1, team2 = choice(match_copy)
                match_copy.remove((team1, team2))
                if team1 not in teams_played_per_day[day] and team2 not in teams_played_per_day[day]:
                    schedule[day].append((team1, team2))
                    teams_played_per_day[day].add(team1)
                    teams_played_per_day[day].add(team2)
                else:
                    is_duplicate = True
        if not is_duplicate:
            done = True
    return schedule


def calculate_min_teams(M):
    # Pour que chaque équipe joue un match par journée pendant M journées, il doit y avoir suffisamment de matchs.
    # Nous cherchons le plus petit n tel que le nombre de journées possibles (n-1) soit au moins M.
    # Formule pour déterminer le nombre d'équipes: n = 2M + 1 (le nombre d'équipes nécessaire pour avoir M journées est 2M + 1)

    return 2 * M + 1


# Exemple d'utilisation
n = 25
M = 6
min_teams = calculate_min_teams(M)
num_teams_per_pool = M + 1 if M % 2 == 0 else M
num_pools = n // num_teams_per_pool
remaining_teams = n % num_teams_per_pool
teams = list(range(1, n + 1))
selected_teams = teams[:num_pools * num_teams_per_pool]
exempted_teams = teams[num_pools * num_teams_per_pool:]
print(f'remaining teams: {remaining_teams} - pools: {num_pools} - num_teams_per_pool: {num_teams_per_pool}')
pools = [selected_teams[i:i + num_teams_per_pool] for i in range(0, len(selected_teams), num_teams_per_pool)]
print(f'pools: {pools}')
print(f'exempted teams: {exempted_teams}')

for pool in pools:
    matches = round_robin(num_teams_per_pool)
    pool_schedule = {}
    for i in range(M):
        pass


    # Redistribuer les matchs pour que chaque équipe joue au maximum une fois par jour
    balanced_schedule = distribute_matches(matches, M, 2)

    # Afficher le nouveau calendrier équilibré
    for day, day_matches in balanced_schedule.items():
        print(f"MATCHDAY {day} = {day_matches}")

def redistribute_matches(schedule):
    all_matches = []
    total_days = len(schedule)

    # Collect all matches into a single list
    for matches in schedule.values():
        all_matches.extend(matches)

    # Calculate the total number of matches
    total_matches = len(all_matches)

    # Calculate the number of matches per day for a uniform distribution
    matches_per_day = total_matches // total_days

    # Initialize a set to keep track of teams that have already played
    teams_played = set()

    # Redistribute matches while ensuring each team plays only once
    for match in all_matches:
        team1, team2 = match
        assigned = False
        for day in range(1, total_days + 1):
            if len(schedule[day]) < matches_per_day and team1 not in teams_played and team2 not in teams_played:
                schedule[day].append(match)
                teams_played.add(team1)
                teams_played.add(team2)
                assigned = True
                break

        # If a match couldn't be assigned to any day, add it to the first available day
        if not assigned:
            for day in range(1, total_days + 1):
                if len(schedule[day]) < matches_per_day:
                    schedule[day].append(match)
                    teams_played.add(team1)
                    teams_played.add(team2)
                    break

    return schedule

# Exemple d'utilisation
schedule = {
    1: [(1, 2), (3, 4), (3, 5)],
    2: [(4, 5), (2, 3)],
    3: [(1, 5), (2, 4)],
    4: [(1, 4), (2, 5)],
    5: [(1, 3)],
}


# Redistribuer les matchs pour que chaque équipe joue une seule fois par jour
balanced_schedule = redistribute_matches(schedule)

# Afficher le nouveau calendrier équilibré
for day, matches in balanced_schedule.items():
    print(f"MATCHDAY {day} = {matches}")

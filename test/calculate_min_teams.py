def calculate_min_teams(M):
    # Pour que chaque équipe joue un match par journée pendant M journées, il doit y avoir suffisamment de matchs.
    # Nous cherchons le plus petit n tel que le nombre de journées possibles (n-1) soit au moins M.
    # Formule pour déterminer le nombre d'équipes: n = 2M + 1 (le nombre d'équipes nécessaire pour avoir M journées est 2M + 1)

    min_teams = 2 * M + 1

    return min_teams

# Exemple d'utilisation:
M = 4  # Nombre de journées
min_teams = calculate_min_teams(M)
print(f"Minimum number of teams needed: {min_teams}")

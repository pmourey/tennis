def determine_min_poules(N, Q):
    def can_play_in_exact_days(equipes, Q):
        matchs = (equipes * (equipes - 1)) // 2
        return matchs == Q * (equipes // 2)

    # Essayer avec le nombre total d'équipes puis en réduisant si nécessaire
    for P in range(1, N + 1):
        if N % P == 0:
            equipes_par_poule = N // P
            if can_play_in_exact_days(equipes_par_poule, Q):
                return P, [equipes_par_poule] * P

    # Si aucune répartition parfaite n'est trouvée, essayer avec moins d'équipes pour avoir des poules équilibrées
    for P in range(1, N):
        max_equipes = (N // P) * P
        if max_equipes < N:
            equipes_par_poule = max_equipes // P
            if can_play_in_exact_days(equipes_par_poule, Q):
                return P, [equipes_par_poule] * P

    return None, []

# Exemple d'utilisation
N = 16  # Nombre total d'équipes
Q = 4   # Nombre de journées

P, distribution = determine_min_poules(N, Q)
print(f"Nombre minimal de poules: {P}")
print(f"Répartition des équipes par poule: {distribution}")

def determine_min_poules(N, Q):
    def can_play_in_days(equipes, Q):
        matchs = (equipes * (equipes - 1)) // 2
        return matchs <= Q * (equipes // 2)

    for P in range(1, N + 1):
        equipes_par_poule = N // P
        reste = N % P

        if reste == 0:
            if can_play_in_days(equipes_par_poule, Q):
                return P, [equipes_par_poule] * P
        else:
            plus_grande_poule = equipes_par_poule + 1
            poules_plus_grandes = reste
            poules_plus_petites = P - reste

            if can_play_in_days(equipes_par_poule, Q) and can_play_in_days(plus_grande_poule, Q):
                distribution = [equipes_par_poule] * poules_plus_petites + [plus_grande_poule] * poules_plus_grandes
                return P, distribution

    return None, []


# Exemple d'utilisation
N = 21  # Nombre total d'équipes
Q = 7  # Nombre de journées

P, distribution = determine_min_poules(N, Q)
print(f"Nombre minimal de poules: {P}")
print(f"Répartition des équipes par poule: {distribution}")

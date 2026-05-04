"""
    Calculate the minimum number of teams needed to play a given number of matchdays.

    Pour déterminer le nombre minimum d'équipes nécessaires pour garantir que chaque équipe dans une poule rencontre au plus un adversaire par journée de championnat comportant M journées,
    nous devons tenir compte du fait qu'il y a une seule rencontre par équipe et par journée.

    Voici l'algorithme pour calculer ce nombre minimum :

    1 - Pour chaque journée de championnat, chaque équipe doit jouer exactement un match contre une autre équipe.
    2 - Donc, le nombre total de matchs joués dans une journée de championnat est égal au nombre d'équipes divisé par 2 (puisque chaque match implique deux équipes).
    3 - Le nombre total de matchs sur M journées est donc M multiplié par le nombre total de matchs par journée.

    Cet algorithme calcule le nombre minimum d'équipes nécessaires pour garantir que chaque équipe dans une poule rencontre au plus un adversaire par journée de championnat comportant M journées.
    Il prend en compte le fait qu'il y a une seule rencontre par équipe et par journée, en multipliant le nombre total de matchs par journée par le nombre de journées pour obtenir le nombre total de matchs sur toutes les journées.
"""
import math


def calculate_min_teams(M):
    # Calculate the total number of matches across all matchdays
    num_teams_per_pool = M + 1
    total_matches = M * num_teams_per_pool // 2

    # Calculate the minimum number of teams needed
    min_teams = total_matches * 2

    return min_teams


# Example usage:
M = 4  # Number of matchdays
N = 17 # Number of teams

min_teams = calculate_min_teams(M)
print(f"Minimum number of teams needed: {min_teams}")

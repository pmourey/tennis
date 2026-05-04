import math
from random import random, choices


def calculate_strength(rank_difference: int):
    # Convertir la différence de classement en un facteur de force
    # Plus la différence est grande, plus le joueur avec le classement le plus bas est désavantagé
    strength_factor = 1 / (1 + 10 ** (rank_difference / 400))
    # strength_factor = 1 / math.log(rank_difference + 2)
    # strength_factor = 1 / (rank_difference + 1) ** 0.5
    return strength_factor

def test(player1_strength: float, player2_strength: float):
    player1_score = player2_score = 0
    while True:
        dice = random()
        player1_score += 1 if dice < player1_strength else 0
        player2_score += 1 if dice < player2_strength else 0
        pass

def simulate_set(player1_strength: float, player2_strength: float):
    # Calcul de la probabilité pour chaque score possible
    probabilities = []
    for score in sets:
        player1_games, player2_games = score
        # Ici, player1_strength et player2_strength représentent les forces des joueurs
        # Plus la force est élevée, plus le joueur a de chances de gagner un jeu
        # Par exemple, une force de 0.8 signifie que le joueur a 80% de chances de gagner un jeu
        player1_win_probability = player1_strength * (player1_games + 1)
        player2_win_probability = player2_strength * (player2_games + 1)
        # La probabilité que ce score spécifique se produise est le produit des probabilités de chaque joueur de gagner ses jeux
        score_probability = player1_win_probability * player2_win_probability
        probabilities.append(score_probability)

    # Sélection aléatoire d'un score en fonction des probabilités calculées
    selected_score = choices(sets, weights=probabilities, k=1)[0]
    return selected_score

# Liste des scores possibles pour un set
sets = [(6, i) for i in range(5)]
sets += [(7, 6), (6, 7)]
sets += [(i, 6) for i in range(4, -1, -1)]
print(sets)

# Exemple d'utilisation
nc_rank = 223
rank_15 = 210
rank_30 = 216
player1_rank = (nc_rank - rank_15) * 50 # Classement du joueur 1
player2_rank = (nc_rank - rank_30) * 50  # Classement du joueur 2
# player1_rank = rank_15
# player2_rank = rank_30
rank_difference = abs(player1_rank - player2_rank)  # Différence de classement entre les joueurs
strength_factor = calculate_strength(rank_difference)
print("Facteur de force :", strength_factor)
if player1_rank < player2_rank:
    player1_strength, player2_strength = strength_factor, 1 - strength_factor
else:
    player1_strength, player2_strength = 1 - strength_factor, strength_factor
print("Force du joueur 1 :", player1_strength)
print("Force du joueur 2 :", player2_strength)

# Exemple d'utilisation
# player1_strength = 0.9  # Force du joueur 1
# player2_strength = 0.3  # Force du joueur 2
results = []
for _ in range(100):
    set_result = simulate_set(player1_strength, player2_strength)
    results.append(set_result)
    # print("Résultat du set simulé :", set_result)

# Calculer le nombre de victoires pour chaque joueur
for set in sets:
    result_count = results.count(set)
    print(f"Nombre de victoires pour le set {set}: {result_count}")

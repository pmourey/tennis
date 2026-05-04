import random

def calculate_set_probability(player1_strength: float, player2_strength: float, is_third_set: bool = False):
    # Initialiser les scores des joueurs
    player1_score = 0
    player2_score = 0
    is_tiebreak = False

    # Parcourir les jeux jusqu'à ce qu'un joueur atteigne 6 jeux avec un écart de 2 jeux OU que les deux joueurs soient à égalité à 6 jeux
    while (max(player1_score, player2_score) < 6 or abs(player1_score - player2_score) < 2) and not (player1_score == player2_score == 6):
        # Calculer la probabilité de remporter le prochain jeu pour chaque joueur
        player1_win_probability = player1_strength / (player1_strength + player2_strength)
        player2_win_probability = 1 - player1_win_probability

        # Simuler le résultat du jeu en fonction des probabilités calculées
        if random.random() < player1_win_probability:
            player1_score += 1
        else:
            player2_score += 1

    # Si aucun joueur n'a un écart de 2 jeux après avoir atteint 6 jeux, jouer un jeu décisif
    if player1_score == player2_score == 6:
        is_tiebreak = True
        while abs(player1_score - player2_score) < 2:
            # Calculer la probabilité de remporter le prochain point pour chaque joueur
            player1_point_probability = player1_strength / (player1_strength + player2_strength)
            player2_point_probability = 1 - player1_point_probability

            # Simuler le résultat du point en fonction des probabilités calculées
            if random.random() < player1_point_probability:
                player1_score += 1
            else:
                player2_score += 1

            # Vérifier si un joueur a atteint 10 points avec au moins 2 points d'écart (uniquement pour le 3ème set si is_third_set est True)
            if is_third_set and (player1_score >= 10 or player2_score >= 10) and abs(player1_score - player2_score) >= 2:
                return player1_score, player2_score, is_tiebreak

    return player1_score, player2_score, is_tiebreak

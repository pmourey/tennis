def calculate_score_probability(player1_strength: float, player2_strength: float):
    scores = [(6, 0), (6, 1), (6, 2), (6, 3), (6, 4), (7, 6), (6, 7), (4, 6), (3, 6), (2, 6), (1, 6), (0, 6)]
    total_probability = 0

    for score in scores:
        p1_wins, p2_wins = score
        # Calculer la probabilité du score en utilisant les forces des joueurs
        score_probability = (player1_strength ** p1_wins) * (player2_strength ** p2_wins)
        print(score, round(score_probability * 100, 2))
        # total_probability += score_probability

    # return total_probability

# Exemple d'utilisation
player1_strength = 0.7  # Force du joueur 1
player2_strength = 0.5  # Force du joueur 2

probability = calculate_score_probability(player1_strength, player2_strength)
print("Probabilité totale du match:", probability)

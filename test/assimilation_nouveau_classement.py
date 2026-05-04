def calculate_rank_for_retired_player(old_rank, age, best_rank_age, age_decay_rate):
    age_diff = age - best_rank_age
    age_factor = 1 + age_diff * age_decay_rate
    new_rank = old_rank / age_factor
    return new_rank

# Exemple d'utilisation
old_rank = 1500          # Ancien classement du joueur
age = 70                # Âge actuel du joueur
best_rank_age = 25       # Âge au moment où le joueur avait son meilleur classement
age_decay_rate = 0.02    # Taux de décroissance du classement par an

new_rank = calculate_rank_for_retired_player(old_rank, age, best_rank_age, age_decay_rate)
print("Nouveau classement actualisé du joueur :", new_rank)

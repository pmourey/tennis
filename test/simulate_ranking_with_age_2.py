def calculate_rank_for_retired_player(old_rank: int, current_rank: int, age: int, best_rank_age: int, age_decay_rate: int = 0.015):
    """
        Affiner le classement par rapport au meilleur ancien classement du joueur et âge passé/actuel
    :param old_rank:
    :param current_rank:
    :param age:
    :param best_rank_age:
    :param age_decay_rate:
    :return:
    """
    if old_rank <= current_rank:
        return current_rank

    age_diff = age - best_rank_age
    age_factor = 1 - age_diff * age_decay_rate
    estimated_rank = old_rank * age_factor
    new_rank = max(current_rank, estimated_rank)

    return new_rank


# Exemple d'utilisation
old_rank = 1500  # Ancien classement du joueur
current_rank = 500  # Classement actuel du joueur
age = 75  # Âge actuel du joueur
best_rank_age = 25  # Âge au moment où le joueur avait son meilleur classement
age_decay_rate = 0.015  # Taux de décroissance du classement par an

new_rank = calculate_rank_for_retired_player(old_rank, current_rank, age, best_rank_age, age_decay_rate)
print("Nouveau classement actualisé du joueur :", new_rank)

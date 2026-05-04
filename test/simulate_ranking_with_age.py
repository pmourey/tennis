import math

def calculate_new_rank(old_rank, age, k, alpha):
    # Calculer la progression du classement en fonction de l'âge
    rank_progression = k * math.exp(-alpha * age)
    # Nouveau classement = Ancien meilleur classement + progression du classement
    new_rank = old_rank + rank_progression
    return new_rank

# Exemple d'utilisation
old_rank = 1000  # Ancien meilleur classement
age = 25         # Âge du joueur
k = 100          # Facteur d'ajustement de la progression du classement
alpha = 0.05     # Paramètre de décroissance de la progression avec l'âge

new_rank = calculate_new_rank(old_rank, age, k, alpha)
print("Nouveau classement du joueur :", new_rank)

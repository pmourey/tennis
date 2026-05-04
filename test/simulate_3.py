from random import random


def calculate_strength(rank_difference: int):
    # Convertir la différence de classement en un facteur de force
    # Plus la différence est grande, plus le joueur avec le classement le plus bas est désavantagé
    strength_factor = 1 / (1 + 10 ** (rank_difference / 400))
    return strength_factor


def game(player1_strength: float, player2_strength: float) -> str:
    player1_score = 0
    player2_score = 0

    while max(player1_score, player2_score) < 4 or abs(player1_score - player2_score) < 2:
        player1_point_probability = player1_strength / (player1_strength + player2_strength)
        player2_point_probability = 1 - player1_point_probability

        if random() < player1_point_probability:
            player1_score += 1
        else:
            player2_score += 1

    return 'player1' if player1_score > player2_score else 'player2'


def tie_break(player1_strength: float, player2_strength: float, max_points: int):
    player1_score = 0
    player2_score = 0

    while max(player1_score, player2_score) < max_points or abs(player1_score - player2_score) < 2:
        player1_point_probability = player1_strength / (player1_strength + player2_strength)
        player2_point_probability = 1 - player1_point_probability

        if random() < player1_point_probability:
            player1_score += 1
        else:
            player2_score += 1

    return player1_score, player2_score


def calculate_set_probability(player1_strength: float, player2_strength: float, is_third_set: bool = False):
    # Si c'est le 3ème set (super tie-break), jouer un seul jeu
    if is_third_set:
        player1_score, player2_score = tie_break(player1_strength, player2_strength, 10)
        is_tiebreak = True
    else:
        # Initialiser les scores des joueurs
        player1_score = 0
        player2_score = 0
        is_tiebreak = False

        # Parcourir les jeux jusqu'à ce qu'un joueur atteigne 6 jeux avec un écart de 2 jeux OU que les deux joueurs soient à égalité à 6 jeux
        while (max(player1_score, player2_score) < 6 or abs(player1_score - player2_score) < 2) and not (player1_score == player2_score == 6):
            winning_player = game(player1_strength, player2_strength)
            if winning_player == 'player1':
                player1_score += 1
            else:
                player2_score += 1

        # Si aucun joueur n'a un écart de 2 jeux après avoir atteint 6 jeux, jouer un jeu décisif
        if player1_score == player2_score == 6:
            player1_score, player2_score = tie_break(player1_strength, player2_strength, 7)
            is_tiebreak = True

    return player1_score, player2_score, is_tiebreak


def play_game(player1_strength, player2_strength):
    """
        Simule une partie de tennis avec les forces de chaque joueur (en 2 sets gagnants)
    :param player1_strength:
    :param player2_strength:
    :return:
    """

    winning_player = None
    player1_sets = []
    player2_sets = []
    sets = []
    while not winning_player:
        is_third_set: bool = True if len(player1_sets) == len(player2_sets) == 1 else False
        player1_set_score, player2_set_score, is_tiebreak = calculate_set_probability(player1_strength, player2_strength, is_third_set)
        if player1_set_score > player2_set_score:
            player1_sets += [(player1_set_score, player2_set_score, is_tiebreak)]
        else:
            player2_sets += [(player1_set_score, player2_set_score, is_tiebreak)]
        sets += [(player1_set_score, player2_set_score, is_tiebreak)]
        winning_player = "player1" if len(player1_sets) == 2 else "player2" if len(player2_sets) == 2 else None
    return winning_player, sets


def format_score(sets):
    score = []
    for i, (player1_set_score, player2_set_score, is_tiebreak) in enumerate(sets):
        if is_tiebreak and i < 2:
            tb_score = min(player1_set_score, player2_set_score)
            set_score = '7/6' if player1_set_score > player2_set_score else '6/7'
            score += [f"{set_score}({tb_score})"]
        else:
            score += [f"{player1_set_score}/{player2_set_score}"]
    return score


def play_games(player1_strength, player2_strength, num_games):
    for i in range(num_games):
        player1_set_score, player2_set_score, is_tiebreak = calculate_set_probability(player1_strength, player2_strength)
        if not is_tiebreak:
            print("Score final du set:", player1_set_score, "-", player2_set_score)
        else:
            print(f"Score final du tie-break game {i}: {player1_set_score}-{player2_set_score}")


# Exemple d'utilisation
nc_rank = 223
rank_player1_tuple = ('15', 210)
# rank_player1_tuple = ('15/1', 211)
# rank_player1_tuple = ('15/2', 212)
# rank_player1_tuple = ('15/3', 213)
# rank_player1_tuple = ('15/4', 214)
# rank_player1_tuple = ('15/5', 215)
# rank_player1_tuple = ('30', 216)
rank_player2_tuple = ('30', 216)
elo_weight = 15  # to better fit with ELO rating system (10 is better)
player1_rank = (nc_rank - rank_player1_tuple[1]) * elo_weight  # Classement du joueur 1
player2_rank = (nc_rank - rank_player2_tuple[1]) * elo_weight  # Classement du joueur 2
rank_difference = abs(player1_rank - player2_rank)  # Différence de classement entre les joueurs
strength_factor = calculate_strength(rank_difference)
print("Facteur de force :", strength_factor)
if player1_rank < player2_rank:
    player1_strength, player2_strength = strength_factor, 1 - strength_factor
else:
    player1_strength, player2_strength = 1 - strength_factor, strength_factor
print(f"Force du joueur 1 classé {rank_player1_tuple[0]} :", player1_strength)
print(f"Force du joueur 2 classé {rank_player2_tuple[0]} :", player2_strength)

num_games = 100
players = [0] * 2
three_sets = [0] * 2
for _ in range(num_games):
    # play_games(player1_strength, player2_strength, 10)
    winning_player, sets = play_game(player1_strength, player2_strength)
    score = format_score(sets)
    # print(f"sets: {sets}")
    print(f"Joueur gagnant: {winning_player} - Score: {' - '.join(score)}")
    players[int(winning_player[-1]) - 1] += 1
    three_sets[int(winning_player[-1]) - 1] += 1 if len(sets) == 3 else 0

pct = lambda x: round(100 * x / num_games, 2)
print(f"Joueur 1 gagne {pct(players[0])} % de parties sur {num_games} parties, dont {pct(three_sets[0])} % en 3 sets")
print(f"Joueur 2 gagne {pct(players[1])} % de parties sur {num_games} parties,  dont {pct(three_sets[1])} % en 3 sets")

# tie_breaks = 0
# num_games = 10000
# for i in range(num_games):
#     player1_set_score, player2_set_score, is_tiebreak = calculate_set_probability(player1_strength, player2_strength)
#     # if not is_tiebreak:
#     #     print("Score final du set:", player1_set_score, "-", player2_set_score)
#     if is_tiebreak:
#         tie_breaks += 1
#         print(f"Score final du tie-break game {i}: {player1_set_score}-{player2_set_score}")
#
# print(f'num_games = {num_games} - tie breaks = {round(100 * (tie_breaks / num_games), 2)}%')

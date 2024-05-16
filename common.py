from __future__ import annotations

import json
import logging
from multiprocessing import Pool
import os
import csv
import re
from datetime import datetime, timedelta
from enum import Enum
from random import shuffle, choice, random
from typing import List, Optional

import pandas as pd
from sqlalchemy import desc, asc, and_

from random import random
from typing import List

from TennisModel import Club, Player, AgeCategory, Division, Ranking, License, Championship, BestRanking, Team, Pool, Match, Matchday, Single, Score, Double, Injury, InjurySite
from tools.import_csv import extract

from mapbox import Directions
from geojson import Feature, Point


class CatType(Enum):
    Youth = 0
    Senior = 1
    Veteran = 2


class DivType(Enum):
    National = 0
    Prenational = 1
    Regional = 2
    Departmental = 3


class Series(Enum):
    First = 1
    Second = 2
    Third = 3
    Fourth = 4


class Gender(Enum):
    Male = 0
    Female = 1
    Mixte = 2

class BodyPart(Enum):
    Head = 0
    Body = 1
    Leg = 2
    Arm = 3
    Hand = 4
    Foot = 5
    Back = 6
    Neck = 7
    Shoulder = 8
    Chest = 9
    Waist = 10
    Hip = 11
    Knee = 12
    Ankle = 13
    Elbow = 14
    Wrist = 15
    Finger = 16
    Toe = 17
    Nose = 18
    Ear = 19
    Eye = 20
    Mouth = 21
    Face = 22
    Tongue = 23
    Throat = 24
    Lip = 25
    Chin = 26

class InjuryType(Enum):
    Acute = 0
    OverUse = 1


def count_sundays_between_dates(start_date, end_date):
    current_date = start_date
    count = 0
    while current_date <= end_date:
        if current_date.weekday() == 6:  # Dimanche a l'indice 6
            count += 1
        current_date += timedelta(days=1)
    return count


def import_all_data(app, db) -> str:
    # Si pas de club en base de données, on les créé!
    message: List[str] = []
    # Vérifier si les catégories d'âge existent en base de données
    age_categories = AgeCategory.query.all()
    if not age_categories:
        # Si aucune catégorie d'âge n'existe, créer les catégories d'âge
        load_age_categories(db)
    message += [f"{AgeCategory.query.count()} catégories d'âge créées!"]

    # Vérifier si les divisions existent en base de données
    divisions = Division.query.all()
    if not divisions:
        # Si aucune division n'existe, créer les divisions
        load_divisions(db)
    message += [f"{Division.query.count()} divisions de championnat créées!"]

    # Vérifier si les classements de tennis existent en base de données
    rankings = Ranking.query.all()
    if not rankings:
        load_rankings(db, Ranking)
        load_rankings(db, BestRanking)
    message += [f"{Ranking.query.count()} classements insérés en bdd!"]

    # chargement de la base des blessures sportives
    injuries = Injury.query.all()
    if not injuries:
        load_injuries(app, db)
    message += [f"{Injury.query.count()} pathologies sportives insérés en bdd!<br>"]

    for club_info in app.config['CLUBS']:
        # récupération autres infos dans fichier csv du club
        BASE_PATH = os.path.dirname(__file__)
        csv_file = os.path.join(BASE_PATH, f'static/data/clubs.csv')
        df = pd.read_csv(csv_file)
        colonnes_a_recuperer = ['name', 'city', 'tennis_courts', 'padel_courts', 'beach_courts', 'latitude', 'longitude']
        club_tenup = extract(df=df, field_criteria='id', field_value=club_info['id'], columns=colonnes_a_recuperer)
        app.logger.debug(f'club_tenup: {club_tenup}')
        if club_tenup is None:
            club = Club(id=club_info['id'], name=club_info['name'], city=club_info['city'])
        else:
            club = Club(id=club_info['id'], name=club_tenup['name'], city=club_tenup['city'], tennis_courts=club_tenup['tennis_courts'],
                        padel_courts=club_tenup['padel_courts'], beach_courts=club_tenup['beach_courts'], latitude=club_tenup['latitude'], longitude=club_tenup['longitude'])
        db.session.add(club)
        app.logger.debug(f'default_club: {club}')
        db.session.commit()
        message += [f'Club {club} créé avec succès!']
        # Chargement des joueurs du club
        for gender, gender_label in enumerate(['men', 'women']):
            players_csvfile = f"static/data/players/{club_info['csvfile']}_{gender_label}.csv"
            file_path = os.path.join(app.config['BASE_PATH'], players_csvfile)
            import_players(app=app, gender=gender, csvfile=file_path, club=club, db=db)
            players_count = Player.query.join(Player.license).filter(Player.clubId == club.id, License.gender == gender).count()
            # db.session.flush()
            message += [f"{players_count} {'joueuses ajoutées' if gender else 'joueurs ajoutés'}!"]
        message += ['<br>']
    message += ['<br>']
    # app.logger.debug(message)
    return '<br>'.join(message)


def load_age_categories(db):
    age_categories = [
        AgeCategory(type=CatType.Youth.value, minAge=6, maxAge=10),
        AgeCategory(type=CatType.Youth.value, minAge=11, maxAge=12),
        AgeCategory(type=CatType.Youth.value, minAge=13, maxAge=14),
        AgeCategory(type=CatType.Youth.value, minAge=15, maxAge=16),
        AgeCategory(type=CatType.Youth.value, minAge=17, maxAge=18),
        AgeCategory(type=CatType.Senior.value, minAge=18, maxAge=99),
        AgeCategory(type=CatType.Veteran.value, minAge=35, maxAge=99),
        AgeCategory(type=CatType.Veteran.value, minAge=45, maxAge=99),
        AgeCategory(type=CatType.Veteran.value, minAge=55, maxAge=99),
        AgeCategory(type=CatType.Veteran.value, minAge=65, maxAge=99),
        AgeCategory(type=CatType.Veteran.value, minAge=75, maxAge=99),
    ]
    db.session.add_all(age_categories)
    db.session.commit()


def load_divisions(db):
    divisions = []
    # TODO: rajouter les compétitions mixtes
    # Catégorie d'âge: SENIORS
    age_categories = AgeCategory.query.filter(AgeCategory.type == CatType.Senior.value).all()
    # app.logger.info(age_categories)
    for age_category in age_categories:
        for gender in range(2):
            for i in range(4):
                divisions += [Division(type=DivType.National.value, number=i + 1, ageCategoryId=age_category.id, gender=gender)]
            divisions += [Division(type=DivType.Prenational.value, ageCategoryId=age_category.id, gender=gender)]
            for i in range(3):
                divisions += [Division(type=DivType.Regional.value, number=i + 1, ageCategoryId=age_category.id, gender=gender)]
            for i in range(5):
                divisions += [Division(type=DivType.Departmental.value, ageCategoryId=age_category.id, number=i + 1, gender=gender)]
    # Catégorie d'âge: JEUNES
    age_categories = AgeCategory.query.filter(AgeCategory.type == CatType.Youth.value).all()
    for age_category in age_categories:
        for gender in range(2):
            divisions += [Division(type=DivType.National.value, ageCategoryId=age_category.id, gender=gender)]
            divisions += [Division(type=DivType.Regional.value, ageCategoryId=age_category.id, gender=gender)]
            divisions += [Division(type=DivType.Departmental.value, ageCategoryId=age_category.id, gender=gender)]
    # Catégorie d'âge: VETERANS
    age_categories = AgeCategory.query.filter(AgeCategory.type == CatType.Veteran.value).all()
    for age_category in age_categories:
        for gender in range(2):
            divisions += [Division(type=DivType.National.value, ageCategoryId=age_category.id, gender=gender)]
            divisions += [Division(type=DivType.Prenational.value, ageCategoryId=age_category.id, gender=gender)]
            divisions += [Division(type=DivType.Regional.value, ageCategoryId=age_category.id, gender=gender)]
            for i in range(2):
                divisions += [Division(type=DivType.Departmental.value, ageCategoryId=age_category.id, number=i + 1, gender=gender)]
    db.session.add_all(divisions)
    db.session.commit()


def load_rankings(db, Model: Ranking | BestRanking):
    rankings = []
    # 1ère série
    for i in range(100):
        rankings += [Model(value=f'N{i + 1}', series=Series.First.value)]
        rankings += [Model(value=f'T{i + 1}', series=Series.First.value)]
    # 2ème/3ème/4ème série
    second_series = ['-15', '-4/6', '-2/6', '0', '1/6', '2/6', '3/6', '4/6', '5/6', '15']
    third_series = ['15/1', '15/2', '15/3', '15/4', '15/5', '30']
    fourth_series = ['30/1', '30/2', '30/3', '30/4', '30/5', '40', 'NC']
    other = 'ND'
    for i, series in enumerate([second_series, third_series, fourth_series]):
        for value in series:
            rankings += [Model(value=value, series=i + 2)]
    rankings += [Model(value=other, series=None)]
    db.session.add_all(rankings)
    db.session.commit()

def load_injuries(app, db):
    static_folder = app.blueprints['medical'].static_folder
    file_path = os.path.join(static_folder, 'data', 'injuries_fr.json')
    with open(file_path, 'r') as file:
        injuries_data = json.load(file)
    injury_types = {'Acute':  InjuryType.Acute.value, 'Overuse': InjuryType.OverUse.value}
    for injury_data in injuries_data:
        site = InjurySite(name=injury_data['site'])
        db.session.add(site)
        db.session.commit()
        for k, v in injury_types.items():
            for injury_name in injury_data[k]:
                injury = Injury(
                    siteId=site.id,
                    type=v,
                    name=injury_name
                )
                db.session.add(injury)
    db.session.commit()

def import_players(app, gender, csvfile, club, db):
    with open(csvfile, 'r', newline='') as file:
        reader = csv.DictReader(file, delimiter='\t')
        for row in reader:
            # app.logger(f'row: {row}')
            # Formatting player data
            first_name = row['Prénom']
            last_name = row['Nom']
            birth_year = row['Né en']
            license_info = row['Licence']
            ranking_value = row['C. Tennis']
            # Utilisation d'une expression régulière pour extraire les deux parties
            ranking_list = ranking_value.split(' ')
            if len(ranking_list) > 1:
                a, b, c = ranking_list
                current_ranking_value = a
                best_ranking_value = c[:-1]
            else:
                current_ranking_value = ranking_list[0]
                best_ranking_value = None
            current_ranking = Ranking.query.filter(Ranking.value == current_ranking_value).first()
            best_ranking = BestRanking.query.filter(BestRanking.value == best_ranking_value).first() if best_ranking_value else None
            # app.logger.debug(f'current_ranking: {current_ranking} - best_ranking: {best_ranking}')
            match = re.match(r'(\d+)\s*(\w)', license_info)
            if not match:
                continue
            lic_number = int(match.group(1))  # Récupère le nombre comme entier
            lic_letter = match.group(2)  # Récupère la lettre
            # Convertir la chaîne en objet datetime
            year_date = datetime.strptime(birth_year, '%Y')
            # Ajuster le mois et le jour pour démarrer au 1er janvier
            year_start_date = year_date.replace(month=1, day=1)
            # logger.info(f'player: {(first_name, last_name)} - ranking: {current_ranking}')
            license = License(id=lic_number, gender=gender, firstName=first_name, lastName=last_name, letter=lic_letter, year=year_start_date.year,
                              rankingId=current_ranking.id, bestRankingId=best_ranking.id if best_ranking else current_ranking.id)
            player = Player(birthDate=year_start_date, weight=None, height=None, isActive=True)
            player.clubId, player.licenseId = club.id, license.id
            db.session.add(license)
            db.session.add(player)
        db.session.commit()
        players_count = Player.query.join(Player.license).filter(Player.clubId == club.id, License.gender == gender).count()
        app.logger.debug(f'COMMIT PLAYERS DONE = {players_count}')


def get_players_order_by_ranking(gender: int, club_id: str, asc_param=True, age_category=None, is_active=True) -> List[Player]:
    order = asc if asc_param else desc
    if gender in [Gender.Male.value, Gender.Female.value]:
        players = Player.query \
            .join(Player.license) \
            .join(License.ranking) \
            .filter(Player.isActive == is_active, License.gender == gender, Player.clubId == club_id) \
            .order_by(Ranking.id) \
            .all()
        if age_category:
            # Filter players based on age category using Python
            players = [player for player in players if player.has_valid_age(age_category)]
    else:
        players = Player.query \
            .join(Player.license) \
            .join(License.ranking) \
            .filter(Player.isActive == is_active, Player.clubId == club_id) \
            .order_by(Ranking.id) \
            .all()
        if age_category:
            # Filter players based on age category using Python
            players = [player for player in players if player.has_valid_age(age_category)]
    return players


def get_championships(gender: int) -> List[Championship]:
    if gender in [Gender.Male.value, Gender.Female.value]:
        championships = Championship.query \
            .join(Championship.division) \
            .filter(Division.gender == gender) \
            .order_by(desc(Division.id)) \
            .all()
    else:
        championships = Championship.query \
            .order_by(desc(Division.id)) \
            .all()
    return championships


def ranking(player: Player) -> Ranking:
    return Ranking.query.get(player.license.rankingId)


def check_license(license_number: str) -> Optional[tuple[int, str]]:
    """
        Check if the license number is valid
    :param license_number: 
    :return: 
    """""
    # Utilisation d'une expression régulière pour vérifier le format
    pattern = r'^(\d{1,10})([A-Za-z])$'
    # Vérification si la license_number correspond au format
    match = re.match(pattern, license_number.replace(' ', ''))
    if match:
        return int(match.group(1)), match.group(2)
    else:
        return None


def keys_with_same_value(d):
    return [value for value in set(d.values()) if list(d.values()).count(value) > 1]


def remove_text_between_parentheses(text):
    # Utilise une expression régulière pour rechercher et remplacer le contenu entre parenthèses
    return re.sub(r'\([^()]*\)', '', text).strip()


def populate_championship(app, db, championship: Championship):
    # Constitution des poules et journées de championnat
    teams = []
    try:
        for club in Club.query.all():
            # app.logger.debug(f'Détermination équipe: {club} - championnat: {championship}')
            players = get_players_order_by_ranking(gender=championship.division.gender, club_id=club.id, asc_param=True, age_category=championship.age_category, is_active=True)
            # app.logger.debug(f'Nombre joueurs éligibles du club {club}: {len(players)}')
            if len(players) < championship.singlesCount:
                continue
            captain = min(players, key=lambda p: p.ranking.id)
            club_name = remove_text_between_parentheses(club.name)
            team = Team(name=f'{club_name} 1', captainId=captain.id)
            team.players = players[:10]
            teams.append(team)
            # app.logger.debug(f'Equipe {team} de poids {team.weight(championship)} créée avec succès composée de {len(team.players)} joueurs! {team.players}')
        # Create pools and assign teams to each pool
        M = min(len(teams) - 1, len(championship.match_dates))
        num_teams_per_pool = M + 1
        num_pools = len(teams) // num_teams_per_pool
        teams.sort(key=lambda t: t.weight(championship))
        selected_teams = teams[:num_pools * num_teams_per_pool]
        exempted_teams = teams[num_pools * num_teams_per_pool:]
        shuffle(selected_teams)
        # app.logger.debug(f'{championship} - Nombre équipes par poule: {num_teams_per_pool} - Nombre de journées: {M}')
        # app.logger.debug(f'{len(selected_teams)} équipes sélectionnées pour la phase de poules')
        for i in range(0, len(selected_teams), num_teams_per_pool):
            pool = Pool(letter=chr(ord('A') + i // num_teams_per_pool), championshipId=championship.id)
            db.session.add(pool)
            db.session.commit()
            for j in range(i, i + num_teams_per_pool):
                selected_teams[j].poolId = pool.id
        exempted_pool = Pool(championshipId=championship.id)
        db.session.add(exempted_pool)
        db.session.commit()
        for team in exempted_teams:
            team.poolId = exempted_pool.id
        teams = selected_teams + exempted_teams
        db.session.add_all(teams)
    except Exception as e:
        app.logger.debug(f"Erreur dans la fonction 'populate_championship'!")
    finally:
        db.session.commit()
    pools = Pool.query.filter(Pool.championshipId == championship.id).all()
    app.logger.debug(f'COMMIT DONE = {len(pools)} POOLS for {championship}')
    # Génération des feuilles de matches
    for pool in championship.pools:
        if pool.letter is None:
            continue
        play(app, db, pool)
        app.logger.debug(f'COMMIT DONE = {len(pool.matches)} MATCHES for pool {pool}')
    # Tableau final
    final_teams = exempted_pool.teams
    min_teams_count = len(championship.pools)
    n = min_teams_count + len(final_teams)
    p = n // 2 + 1
    qualified_teams = {}
    for pool in championship.pools:
        if pool.letter is None:
            continue
        pool_rankings = calculer_classement(pool)
        qualified_teams[pool.id] = [team_id for team_id, ranking in pool_rankings]
        app.logger.debug(f'{len(qualified_teams[pool.id])} TEAMS for pool {pool}: {qualified_teams[pool.id]}')
    while len(final_teams) < 2 ** p:
        for pool in championship.pools:
            if pool.letter is None:
                continue
            team_id = qualified_teams[pool.id].pop(0)
            final_teams += [Team.query.get(team_id)]
            if len(final_teams) == 2 ** p:
                break
    app.logger.debug(f'COMMIT DONE = {len(final_teams)} TEAMS for FINALS of {championship}: {final_teams}')




def round_robin(n):
    a = []
    b = []
    c = (n * (n - 1)) / 2
    c = int(c)
    e = []
    f = []
    result = []
    result1 = []

    # creating (0,1), (0,2) ··· (n-1, n)
    for i1 in range(n):
        for i2 in range(n):
            if i1 < i2:
                f.append((i1, i2))

                # creating list of waiting time a = [0,1,2, ··· , n-1] and b = [0,0, ··· , 0]
    for i in range(n):
        a.append(i)
        b.append(0)

    # main dish
    for i1 in range(c):
        d1 = b.copy()
        d2 = a.copy()
        e = []

        # ordering from largest waiting time to smallest waiting time e = [largest to smallest] in index
        # d1 is the waiting time list
        # d2 is [0,1,···,n-1] but decreases gradually
        for j in range(n):
            m = max(d1)
            for k in range(n):
                if b[k] == m and k not in e:
                    n1 = k
                    e.append(n1)
                    d1.remove(m)
                    d2.remove(n1)
                    break
                else:
                    continue

        for (p, q) in f:
            if (e[p], e[q]) not in result and (e[q], e[p]) not in result:
                result.append((e[p], e[q]))
                for i in range(n):
                    if i != e[p] and i != e[q]:
                        b[i] = b[i] + 1
                    else:
                        b[i] = 0
                break
            else:
                continue

    # making (2,0)s into (0,2)s
    for (k1, k2) in result:
        if k1 < k2:
            result1.append((k1 + 1, k2 + 1))
        else:
            result1.append((k2 + 1, k1 + 1))

    return result1


def paires_avec_somme_N(liste, N):
    paires = []
    for i in range(len(liste)):
        for j in range(i, len(liste)):  # Modifier la boucle pour inclure aussi i
            if liste[i] + liste[j] == N:
                paires.append((liste[i], liste[j]))
    return paires


def simulate_score_old(home_team, visitor_team, pool):
    num_matches = pool.championship.num_matches
    liste_entiers = list(range(num_matches + 1))
    scores = paires_avec_somme_N(liste_entiers, num_matches)
    home_score, visitor_score = home_team.weight(pool.championship), visitor_team.visitorTeam.weight(pool.championship)
    winnerId = home_team.id if home_score > visitor_score else visitor_team.id if visitor_score > home_score else None
    filtered_scores = list(filter(lambda x: x[0] != x[1], scores)) if winnerId else scores
    score = choice(filtered_scores)
    sorted_score = tuple(sorted(score, reverse=True)) if winnerId == home_team.id else tuple(sorted(score))
    return f'{sorted_score[0]}-{sorted_score[1]}'


def simulate_set(player1: Player, player2: Player):
    sets = [(6, i) for i in range(4)]
    sets += [(7, 6), (6, 7)]
    sets += [(i, 6) for i in range(4)]


### New simulation

def calculate_strength(rank_difference: int) -> float:
    # Convertir la différence de classement en un facteur de force
    # Plus la différence est grande, plus le joueur avec le classement le plus bas est désavantagé
    return 1 / (1 + 10 ** (rank_difference / 400))


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
        super_tie_break_score_p1, super_tie_break_score_p2 = tie_break(player1_strength, player2_strength, 10)
        if super_tie_break_score_p1 > super_tie_break_score_p2:
            return 1, 0, super_tie_break_score_p2
        else:
            return 0, 1, super_tie_break_score_p1
    else:
        # Initialiser les scores des joueurs
        player1_score = 0
        player2_score = 0

        # Parcourir les jeux jusqu'à ce qu'un joueur atteigne 6 jeux avec un écart de 2 jeux OU que les deux joueurs soient à égalité à 6 jeux
        while (max(player1_score, player2_score) < 6 or abs(player1_score - player2_score) < 2) and not (player1_score == player2_score == 6):
            winning_player = game(player1_strength, player2_strength)
            if winning_player == 'player1':
                player1_score += 1
            else:
                player2_score += 1

        # Si aucun joueur n'a un écart de 2 jeux après avoir atteint 6 jeux, jouer un jeu décisif
        if player1_score == player2_score == 6:
            tie_break_score_p1, tie_break_score_p2 = tie_break(player1_strength, player2_strength, 7)
            if tie_break_score_p1 > tie_break_score_p2:
                return 7, 6, tie_break_score_p2
            else:
                return 6, 7, tie_break_score_p1
        else:
            return player1_score, player2_score, None


def play_game(app, home_players: List[Player], visitor_players: List[Player], home_team: Team, visitor_team: Team):
    """
        Simulate a game between two players.
    :param app:
    :param home_players: selected players for the home team
    :param visitor_players: selected players for the visitor team
    :param home_team:
    :param visitor_team:
    :return: winning team, final score
    """
    home_team_rank = sum([player.refined_elo for player in home_players])
    visitor_team_rank = sum([player.refined_elo for player in visitor_players])
    rank_difference = abs(home_team_rank - visitor_team_rank)  # Différence de classement ELO entre les joueurs
    # app.logger.debug(f"Classement ELO : {player1_rank} - {player2_rank}")
    strength_factor = calculate_strength(rank_difference)
    # app.logger.debug(f"Facteur de force : {strength_factor}")
    if home_team_rank < visitor_team_rank:
        home_strength, visitor_strength = strength_factor, 1 - strength_factor
    else:
        home_strength, visitor_strength = 1 - strength_factor, strength_factor
    winning_team = None
    home_sets = []
    visitor_sets = []
    final_score = []
    while not winning_team:
        is_third_set: bool = True if len(home_sets) == len(visitor_sets) == 1 else False
        result = calculate_set_probability(home_strength, visitor_strength, is_third_set)
        # app.logger.debug(f"Score set : {result} - is_third_set: {is_third_set}")
        home_set_score, visitor_set_score, tie_break_score = result
        if home_set_score > visitor_set_score:
            home_sets += [(home_set_score, visitor_set_score, tie_break_score)]
        else:
            visitor_sets += [(home_set_score, visitor_set_score, tie_break_score)]
        final_score += [(home_set_score, visitor_set_score, tie_break_score)]
        winning_team = home_team if len(home_sets) == 2 else visitor_team if len(visitor_sets) == 2 else None
    return winning_team, final_score


def simulate_score(app, db, home_players: List[Player], visitor_players: List[Player], match: Match):
    """
        Simulate the score of a match
    :param app:
    :param db:
    :param home_players: selected players for the match
    :param visitor_players: selected players for the match
    :param match:
    :return:
    """
    # app.logger.debug(f'Simulating score for {match.homeTeam} vs {match.visitorTeam} - match sheet: {match}')
    pool = match.homeTeam.pool
    # app.logger.debug(f'Poule {pool} : {pool.championship.singlesCount} singles - {pool.championship.doublesCount} doubles')
    home_score = visitor_score = 0
    # SIMPLES
    home_singles_players = []
    visitor_singles_players = []
    home_singles_players = sorted(home_players, key=lambda player: player.current_elo, reverse=True)
    visitor_singles_players = sorted(visitor_players, key=lambda player: player.current_elo, reverse=True)
    for i in range(pool.championship.singlesCount):
        player1, player2 = home_singles_players[i], visitor_singles_players[i]
        result = play_game(app, home_players=[player1], visitor_players=[player2], home_team=match.homeTeam, visitor_team=match.visitorTeam)
        # app.logger.debug(f'result play_game single {i + 1}: {result}')
        winning_team = result[0]
        final_score = result[1]
        # app.logger.debug(f'final_score: {final_score}')
        first_set = final_score[0]
        second_set = final_score[1]
        third_set = final_score[2] if len(final_score) == 3 else (None, None, False)
        # app.logger.debug(f'{len(final_score)} sets -> first_set: {first_set}, second_set: {second_set}, third_set: {third_set}')
        firstSetP1, firstSetP2, firstTieBreak = first_set
        secondSetP1, secondSetP2, secondTieBreak = second_set
        thirdSetP1, thirdSetP2, superTieBreak = third_set
        score = Score(firstSetP1=firstSetP1, firstSetP2=firstSetP2, firstTieBreak=firstTieBreak, secondSetP1=secondSetP1, secondSetP2=secondSetP2,
                      secondTieBreak=secondTieBreak, thirdSetP1=thirdSetP1, thirdSetP2=thirdSetP2, superTieBreak=superTieBreak)
        db.session.add(score)
        db.session.commit()
        if winning_team == match.homeTeam:
            home_score += 1
        else:
            visitor_score += 1
        # app.logger.debug(f'home_score: {home_score}, visitor_score: {visitor_score}')
        single = Single(player1Id=player1.id, player2Id=player2.id, scoreId=score.id, matchId=match.id)
        db.session.add(single)
        db.session.commit()
        match.singles += [single]
        # home_singles_players += [player1]
        # visitor_singles_players += [player2]
    # DOUBLES
    # home_candidates = [player for player in match.homeTeam.players if player not in home_singles_players]
    # visitor_candidates = [player for player in match.visitorTeam.players if player not in visitor_singles_players]
    home_doublers_candidates = sorted(home_players, key=lambda player: player.refined_elo, reverse=True)
    visitor_doublers_candidates = sorted(visitor_players, key=lambda player: player.refined_elo, reverse=True)
    for i in range(pool.championship.doublesCount):
        home_doublers, visitor_doublers = home_doublers_candidates[2 * i:2 * i + 2], visitor_doublers_candidates[2 * i:2 * i + 2]
        result = play_game(app, home_doublers, visitor_doublers, match.homeTeam, match.visitorTeam)
        # app.logger.debug(f'result play_game double {i + 1}: {result}')
        winning_team = result[0]
        final_score = result[1]
        first_set = final_score[0]
        second_set = final_score[1]
        third_set = final_score[2] if len(final_score) == 3 else (None, None, False)
        firstSetP1, firstSetP2, firstTieBreak = first_set
        secondSetP1, secondSetP2, secondTieBreak = second_set
        thirdSetP1, thirdSetP2, superTieBreak = third_set
        score = Score(firstSetP1=firstSetP1, firstSetP2=firstSetP2, firstTieBreak=firstTieBreak, secondSetP1=secondSetP1, secondSetP2=secondSetP2,
                      secondTieBreak=secondTieBreak, thirdSetP1=thirdSetP1, thirdSetP2=thirdSetP2, superTieBreak=superTieBreak)
        # app.logger.debug(f'Score = {score}')
        db.session.add(score)
        db.session.commit()
        if winning_team == match.homeTeam:
            home_score += 1
        else:
            visitor_score += 1
        # app.logger.debug(f'home_score: {home_score}, visitor_score: {visitor_score}')
        player1, player2 = home_doublers
        player3, player4 = visitor_doublers
        double = Double(player1Id=player1.id, player2Id=player2.id, player3Id=player3.id, player4Id=player4.id, scoreId=score.id, matchId=match.id)
        db.session.add(double)
        match.doubles += [double]
    match.homeScore, match.visitorScore = home_score, visitor_score
    # app.logger.debug(f'home_score: {home_score}, visitor_score: {visitor_score}')
    db.session.add(match)
    db.session.commit()


def play(app, db, pool: Pool):
    try:
        teams = {i + 1: team for i, team in enumerate(pool.teams)}
        app.logger.debug(f'TEAMS = {teams}')
        n = len(teams)
        num_days = n - 1 if n % 2 == 0 else n
        matchs_data = round_robin(n)
        # app.logger.debug(f'MATCHS = {matchs_data}')
        matchdays = Matchday.query.filter_by(championshipId=pool.championship.id).all()
        # app.logger.debug(f'{len(matchdays)} MATCHDAYS = {matchdays}')
        for i in range(len(matchdays)):
            matchdays = Matchday.query.filter_by(championshipId=pool.championship.id).all()
            matchday = matchdays[i]
            matches = matchs_data[i * n // 2: (i + 1) * n // 2]
            # app.logger.debug(f'MATCHDAY {i + 1} = {matches}')
            matches = [Match(poolId=pool.id, matchdayId=matchday.id, homeTeamId=teams[j].id, visitorTeamId=teams[k].id, date=matchday.date) for j, k in matches]
            db.session.add_all(matches)
            # db.session.commit()
            # matchday.matches = matches
            # db.session.add(matchday)
            db.session.commit()
            # matchdays = Matchday.query.filter_by(championshipId=pool.championship.id).all()
            # matchday = matchdays[i]
            matchdays = Matchday.query.filter_by(championshipId=pool.championship.id).all()
            matchday = matchdays[i]
            # app.logger.debug(f'PROUT MATCHDAY {i + 1} = {len(matchday.matches)} matches')
            for match in matchday.matches:
                if match.poolId != pool.id:
                    continue
                # score = simulate_score(home_team=match.homeTeam, visitor_team=match.awayTeam, championship=pool.championship)
                # Select Players for both teams
                num_players = pool.championship.singlesCount + 2 * pool.championship.doublesCount
                home_players = sorted(match.homeTeam.players, key=lambda player: player.refined_elo, reverse=True)[:num_players]
                # home_players.sort(key=lambda player: player.current_elo, reverse=True)
                visitor_players = sorted(match.visitorTeam.players, key=lambda player: player.refined_elo, reverse=True)[:num_players]
                # visitor_players.sort(key=lambda player: player.current_elo, reverse=True)
                simulate_score(app=app, db=db, home_players=home_players, visitor_players=visitor_players, match=match)
                match = Match.query.get(match.id)
                app.logger.debug(f'MATCH {match.id} = {match.homeTeam} - {match.score} - {match.visitorTeam}')
    except Exception as e:
        app.logger.debug(f"Erreur dans la fonction 'play'!\n{e}")


def extract_courts(club_json):
    # Expression régulière pour extraire le nombre de terrains de tennis, padel et beach
    regex = r"Tennis : (\d+) terrains, Padel : (\d+), Beach Tennis : (\d+)"
    # Rechercher les correspondances dans la chaîne 'terrainPratiqueLibelle'
    matches = re.search(regex, club_json['terrainPratiqueLibelle'])
    if matches:
        tennis_count = int(matches.group(1))
        padel_count = int(matches.group(2))
        beach_count = int(matches.group(3))
        return [tennis_count, padel_count, beach_count]
    return [0] * 3


def calculer_classement(pool):
    classement = dict()  # Liste pour stocker les détails du classement de chaque équipe
    num_matches = pool.championship.singlesCount + pool.championship.doublesCount
    # Parcourir toutes les équipes de la poule
    for team in pool.teams:
        # Requête pour récupérer les matchs de l'équipe donnée dans la poule donnée
        matches = Match.query \
            .join(Match.pool) \
            .filter(
            (Match.homeTeamId == team.id) |
            (Match.visitorTeamId == team.id)) \
            .filter(Match.poolId == pool.id) \
            .all()
        # matches = Match.query.filter(Match.poolId == pool.id, Match.homeTeamId == team.id).all()
        logging.info(f'{team} : {len(matches)} matches')

        team_matches_played: int = len(matches)
        # matches_played = len(pool.teams) - 1
        team_matches_won: int = (sum(1 for m in matches if team.is_visitor(match=m) and m.homeScore < m.visitorScore)
                                 + sum(1 for m in matches if not team.is_visitor(match=m) and m.homeScore > m.visitorScore))
        team_matches_lost: int = (sum(1 for m in matches if team.is_visitor(match=m) and m.homeScore > m.visitorScore)
                                  + sum(1 for m in matches if not team.is_visitor(match=m) and m.homeScore < m.visitorScore))
        team_matches_draw: int = sum(1 for m in matches if m.homeScore == m.visitorScore)
        points = 3 * team_matches_won + 2 * team_matches_draw + team_matches_lost

        won_matches: int = 0
        lost_matches: int = 0
        for m in matches:
            if m.visitorTeamId == team.id:
                team_is_visitor = True
                visitor_score = m.visitorScore
            elif m.homeTeamId == team.id:
                team_is_visitor = False
                home_score = m.homeScore
            won_matches += visitor_score if team_is_visitor else home_score
            # lost_matches += home_score if team_is_visitor else visitor_score
        lost_matches: int = team_matches_played * num_matches - won_matches
        diff_matchs = won_matches - lost_matches  # Différence de matchs

        sets_won = sets_lost = 0
        games_won = games_lost = 0
        for m in matches:
            if not (m.visitorTeamId == team.id or m.homeTeamId == team.id):
                continue
            home_sets, visitor_sets = m.sets_count
            home_games, visitor_games = m.games_count
            sets_won += visitor_sets if team.is_visitor(match=m) else home_sets
            sets_lost += home_sets if team.is_visitor(match=m) else visitor_sets
            games_won += visitor_games if team.is_visitor(match=m) else home_games
            games_lost += home_games if team.is_visitor(match=m) else visitor_games
        diff_sets = sets_won - sets_lost  # Différence de sets
        diff_games = games_won - games_lost  # Différence de jeux

        # Ajouter les détails de l'équipe au classement
        # logging.info(classement)
        matches_details: List[str] = []
        if team_matches_won: matches_details += [f'{team_matches_won}V']
        if team_matches_draw: matches_details += [f'{team_matches_draw}N']
        if team_matches_lost: matches_details += [f'{team_matches_lost}D']
        team_matches_played = f"{team_matches_played} ({'/'.join(matches_details)})"
        matches_details = f'{diff_matchs} (+{won_matches}/-{lost_matches})'
        sets_details = f'{diff_sets} (+{sets_won}/-{sets_lost})'
        games_details = f'{diff_games} (+{games_won}/-{games_lost})'
        classement.update({team.id: {
            'team': team.name,
            'points': points,
            'matches_played': team_matches_played,
            'diff_matchs_sort': diff_matchs,
            'diff_matchs': matches_details,
            'diff_sets_sort': diff_sets,
            'diff_sets': sets_details,
            'diff_games_sort': diff_games,
            'diff_games': games_details
        }})
    # classement = sorted(classement.items(), key=lambda x: x[1]['points'], reverse=True)
    classement = sorted(classement.items(), key=lambda x: (x[1]['points'], x[1]['diff_matchs_sort'], x[1]['diff_sets_sort'], x[1]['diff_games_sort']), reverse=True)

    return classement


#
# Some basic tutorial on using Directions Mapbox API :-)
#   - https://github.com/mapbox/mapbox-sdk-py/blob/master/docs/directions.md#directions
# et une doc plus générale pour décrire les différentes fonctionalités exploitables par l'API:
#   - https://docs.mapbox.com/help/how-mapbox-works/directions/
#
# Paramètres d'entrée: Location Object Source, Location Object Destination, Mapbox API key
#         N.B. en fait on a besoin seulement des attributs (Longitude, Latitude).
#              On utilise ici le module geojson pour créer nos objets de type Feature GEOJSON et accessoirement pour extraire plus aisément (ou pas) les données en sortie :-D
#               Consultable ici: https://pypi.org/project/geojson/
# Paramètres de sortie: JSON Object {'distance': 9176.91, 'duration': 1263.044} ou code d'erreur HTTP si pas d'objet JSON retourné par l'API Mapbox
#
def get_Directions_Mapbox(visitor: Club, home: Club, api_key):
    service = Directions(access_token=api_key)
    origin = Feature(geometry=Point((visitor.longitude, visitor.latitude)))
    destination = Feature(geometry=Point((home.longitude, home.latitude)))
    # my_profile = 'mapbox/driving'
    my_profile = 'mapbox/driving-traffic'
    response = service.directions([origin, destination], profile=my_profile, geometries=None, annotations=['duration', 'distance'])
    driving_routes = response.geojson()
    # print("JSON Object: ", driving_routes, file=sys.stderr)
    # new_json = driving_routes['features'][0]['properties']
    # pprint.pprint(new_json)
    if response.status_code == 200:
        return driving_routes['features'][0]['properties']
    else:
        return response.status_code


def calculate_distance_and_duration(visitor: Club, home: Club, api_key):
    directions_json = get_Directions_Mapbox(visitor, home, api_key)
    if directions_json['distance'] > 0:
        return (directions_json['distance'], directions_json['duration'])
    else:
        return (0, 0)

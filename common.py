from __future__ import annotations

from multiprocessing import Pool
import os
import csv
import re
from datetime import datetime
from enum import Enum
from random import shuffle, choice
from typing import List, Optional

import pandas as pd
from sqlalchemy import desc, asc, and_

from TennisModel import Club, Player, AgeCategory, Division, Ranking, License, Championship, BestRanking, Team, Pool, Match, Matchday, MatchSheet
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


def import_all_data(app, db) -> str:
    # Si pas de club en base de données, on les créé!
    message: str = ''
    # Vérifier si les catégories d'âge existent en base de données
    age_categories = AgeCategory.query.all()
    if not age_categories:
        # Si aucune catégorie d'âge n'existe, créer les catégories d'âge
        load_age_categories(db)
    message += f"{AgeCategory.query.count()} catégories d'âge créées!\n"

    # Vérifier si les divisions existent en base de données
    divisions = Division.query.all()
    if not divisions:
        # Si aucune division n'existe, créer les divisions
        load_divisions(db)
    message += f"{Division.query.count()} divisions de championnat créées!\n"

    # Vérifier si les classements de tennis existent en base de données
    rankings = Ranking.query.all()
    if not rankings:
        load_rankings(db, Ranking)
        load_rankings(db, BestRanking)
    message += f"{Ranking.query.count()} classements insérés en bdd!\n"

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
        message += f'Club {club} créé avec succès!\n'
        # Chargement des joueurs du club
        for gender, gender_label in enumerate(['men', 'women']):
            players_csvfile = f"static/data/players/{club_info['csvfile']}_{gender_label}.csv"
            file_path = os.path.join(app.config['BASE_PATH'], players_csvfile)
            import_players(app=app, gender=gender, csvfile=file_path, club=club, db=db)
            players_count = Player.query.join(Player.license).filter(Player.clubId == club.id, License.gender == gender).count()
            # db.session.flush()
            message += f"{players_count} {'joueuses ajoutées' if gender else 'joueurs ajoutés'}!\n"
    app.logger.debug(message)
    return message


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
    rankings += [Ranking(value=other, series=None)]
    db.session.add_all(rankings)
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
    teams = []
    try:
        for club in Club.query.all():
            # app.logger.debug(f'Détermination équipe: {club} - championnat: {championship}')
            players = get_players_order_by_ranking(gender=championship.division.gender, club_id=club.id, asc_param=True, age_category=championship.age_category, is_active=True)
            # app.logger.debug(f'Nombre joueurs éligibles du club {club}: {len(players)}')
            if len(players) < 4:
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
        app.logger.debug(f'{championship} - Nombre équipes par poule: {num_teams_per_pool} - Nombre de journées: {M}')
        app.logger.debug(f'{len(selected_teams)} équipes sélectionnées pour la phase de poules')
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
    for pool in championship.pools:
        if pool.letter is None:
            continue
        play(app, db, pool)
        app.logger.debug(f'COMMIT DONE = {len(pool.matches)} MATCHES for pool {pool}')


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


def play(app, db, pool: Pool):
    try:
        num_matches = pool.championship.num_matches
        liste_entiers = list(range(num_matches + 1))
        scores = paires_avec_somme_N(liste_entiers, num_matches)
        app.logger.debug(f'SCORES = {scores}')
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
            matches = [Match(poolId=pool.id, matchdayId=matchday.id, homeTeamId=teams[j].id, awayTeamId=teams[k].id, date=matchday.date) for j, k in matches]
            db.session.add_all(matches)
            # db.session.commit()
            # matchday.matches = matches
            # db.session.add(matchday)
            db.session.commit()
            # matchdays = Matchday.query.filter_by(championshipId=pool.championship.id).all()
            # matchday = matchdays[i]
            matchdays = Matchday.query.filter_by(championshipId=pool.championship.id).all()
            matchday = matchdays[i]
            # app.logger.debug(f'PROUT MATCHDAY {i + 1} = {matchday.matches}')
            for match in matchday.matches:
                home_score, visitor_score = match.homeTeam.weight(pool.championship), match.awayTeam.weight(pool.championship)
                winnerId = match.homeTeamId if home_score > visitor_score else match.awayTeamId if visitor_score > home_score else None
                filtered_scores = list(filter(lambda x: x[0] != x[1], scores)) if winnerId else scores
                score = choice(filtered_scores)
                sorted_score = tuple(sorted(score, reverse=True)) if winnerId == match.homeTeamId else tuple(sorted(score))
                formatted_score = f'{sorted_score[0]}-{sorted_score[1]}'
                match_sheet = MatchSheet(matchId=match.id, score=formatted_score, winnerId=winnerId)
                db.session.add(match_sheet)
                db.session.commit()
                match_sheet = MatchSheet.query.filter_by(matchId=match.id).first()
                # app.logger.debug(f'MATCH {match.id} = {match.homeTeam} - {match_sheet.score} - {match.awayTeam}')
    except Exception as e:
        app.logger.debug(f"Erreur dans la fonction 'play'!")

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
    classement = {}  # Dictionnaire pour stocker le nombre de points de chaque équipe

    # Parcourir tous les matchs de la poule
    for match in pool.matches:
        if match.match_sheet is not None:  # Vérifier si la feuille de match existe
            home_team = match.homeTeam
            away_team = match.awayTeam
            home_score, away_score = map(int, match.match_sheet.score.split('-'))

            # Déterminer le résultat du match
            if home_score > away_score:
                result_home_team = 'win'
                result_away_team = 'loss'
            elif home_score < away_score:
                result_home_team = 'loss'
                result_away_team = 'win'
            else:
                result_home_team = result_away_team = 'draw'

            # Mettre à jour le nombre de points des équipes
            classement[home_team.id] = classement.get(home_team.id, 0) + {'win': 3, 'draw': 2, 'loss': 1}[result_home_team]
            classement[away_team.id] = classement.get(away_team.id, 0) + {'win': 3, 'draw': 2, 'loss': 1}[result_away_team]

    # Trier les équipes en fonction de leur nombre de points (en ordre décroissant)
    classement = sorted(classement.items(), key=lambda x: x[1], reverse=True)

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
    #my_profile = 'mapbox/driving'
    my_profile = 'mapbox/driving-traffic'
    response = service.directions([origin, destination], profile=my_profile, geometries=None, annotations=['duration', 'distance'])
    driving_routes = response.geojson()
    #print("JSON Object: ", driving_routes, file=sys.stderr)
    #new_json = driving_routes['features'][0]['properties']
    #pprint.pprint(new_json)
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

    # geojson_object_prop = direction_api.get_Directions_Mapbox(from_location, to_location, MAPBOX_API_KEY)
    # courses_object_list[i].distance = geojson_object_prop['distance']
    # courses_object_list[i].duration = geojson_object_prop['duration']
    # elapsed_hours = course_object.duration / 3600
    # elapsed_minutes = (elapsed_hours - int(elapsed_hours)) * 60

import os
import csv
import re
from datetime import datetime
from enum import Enum
from typing import List, Optional

from sqlalchemy import desc, asc, and_

from TennisModel import Club, Player, AgeCategory, Division, Ranking, License, Championship


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
        load_rankings(db)
    message += f"{Ranking.query.count()} classements insérés en bdd!\n"

    for club_info in app.config['CLUBS']:
        club = Club(id=club_info['id'], name=club_info['name'], city=club_info['city'])
        db.session.add(club)
        app.logger.debug(f'default_club: {club}')
        db.session.commit()
        message += f'Club {club} créé avec succès!\n'
        # Chargement des joueurs du club
        for gender, gender_label in enumerate(['men', 'women']):
            players_csvfile = f"static/data/{club_info['csvfile']}_{gender_label}.csv"
            file_path = os.path.join(app.config['BASE_PATH'], players_csvfile)
            import_players(app=app, gender=gender, csvfile=file_path, club=club, db=db)
            players_count = Player.query.join(Player.license).filter(Player.clubId == club.id, License.gender == gender).count()
            # db.session.flush()
            message += f"{players_count} {'joueuses' if gender else 'joueurs'} ajoutés au club {club.name}!\n"
    app.logger.debug(message)
    return message

def load_age_categories(db):
    age_categories = [
        AgeCategory(type=CatType.Youth.value, minAge=10, maxAge=11),
        AgeCategory(type=CatType.Youth.value, minAge=12, maxAge=13),
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


def load_rankings(db):
    rankings = []
    # 1ère série
    for i in range(100):
        rankings += [Ranking(value=f'N{i + 1}', series=Series.First.value)]
        rankings += [Ranking(value=f'T{i + 1}', series=Series.First.value)]
    # 2ème/3ème/4ème série
    second_series = ['-15', '-4/6', '-2/6', '0', '1/6', '2/6', '3/6', '4/6', '5/6', '15']
    third_series = ['15/1', '15/2', '15/3', '15/4', '15/5', '30']
    fourth_series = ['30/1', '30/2', '30/3', '30/4', '30/5', '40', 'NC']
    other = 'ND'
    for i, series in enumerate([second_series, third_series, fourth_series]):
        for value in series:
            rankings += [Ranking(value=value, series=i + 2)]
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
            best_ranking = Ranking.query.filter(Ranking.value == best_ranking_value).first() if best_ranking_value else None
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
                              rankingId=current_ranking.id)  # , bestRankingId=best_ranking.id)
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
            .order_by(order(Ranking.id)) \
            .all()
        if age_category:
            # Filter players based on age category using Python
            players = [player for player in players if player.has_valid_age(age_category)]
    else:
        players = Player.query \
            .join(Player.license) \
            .join(License.ranking) \
            .filter(Player.isActive == is_active, Player.clubId == club_id) \
            .order_by(order(Ranking.id)) \
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
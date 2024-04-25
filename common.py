import csv
import logging
import re
from datetime import datetime
from enum import Enum

from TennisModel import AgeCategory, Division, License, Player, Ranking

import os


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


def import_players(app, men_players_csvfile, women_players_csvfile, default_club, db):
    logger = logging.getLogger(__name__)
    for gender, csvfile in enumerate([men_players_csvfile, women_players_csvfile]):
        file_path = os.path.join(os.path.dirname(__file__), csvfile)
        with open(file_path, 'r', newline='') as file:
            reader = csv.DictReader(file, delimiter='\t')
            for row in reader:
                logger.info(f'row: {row}')
                # app.logger(f'row: {row}')
                # Formatting player data
                first_name = row['Prénom']
                last_name = row['Nom']
                birth_year = row['Né en']
                license_info = row['Licence']
                club_name = row['Club']
                ranking_value = row['C. Tennis']
                # license_info
                # Nom Prénom  Né en   Licence	Club    C. Tennis
                # ABDERRAHIM	Idris	2015	3182789 C - 2024	US CAGNES TENNIS	NC
                # ALENDA	Alexis	2010	3193949 H - 2024	US CAGNES TENNIS	NC
                # ALGRAIN	Jerome	1965	6681557 L - 2024	US CAGNES TENNIS	15/4 (ex 15)
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
                logger.info(f'current_ranking: {current_ranking} - best_ranking: {best_ranking}')
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
                license = License(id=lic_number, gender=gender, firstName=first_name, lastName=last_name, letter=lic_letter, year=lic_number,
                                  rankingId=current_ranking.id)#, bestRankingId=best_ranking.id)
                player = Player(birthDate=year_start_date, clubId=default_club.id, isActive=True, licenseId=license.id)
                db.session.add(license)
                db.session.add(player)
            db.session.commit()

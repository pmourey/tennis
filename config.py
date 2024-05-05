# config.py
import os

from pytz import timezone


class Config:
    DEBUG = False
    # TESTING = True
    SECRET_KEY = 'fifa 2022'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///tennis.sqlite3'
    CLUBS = [{'name': 'US CAGNES TENNIS', 'city': 'Cagnes-sur-Mer', 'id': '62 06 0107', 'csvfile': 'us_cagnes_tennis'},
             {'name': 'TC MOUGINS', 'city': 'Mougins', 'id': '62 06 0108', 'csvfile': 'tc_mougins'},
             {'name': 'ASLM TENNIS CANNES', 'city': 'Cannes', 'id': '62 06 0109', 'csvfile': 'aslm_tennis_cannes'},
             {'name': 'NICE LAWN TENNIS CLUB', 'city': 'Nice', 'id': '62 06 0110', 'csvfile': 'nice_lawn_tennis_club'},
             {'name': 'RIORGEOIS (TENNIS CLUB DE)', 'city': 'Roanne', 'id': '62 06 0111', 'csvfile': 'tc_riorgeois'},
             {'name': 'LA RAQUETTE ROQUEFORTOISE', 'city': 'Roquefort-les-Pins', 'id': '62 06 0112', 'csvfile': 'la_raquette_roquefortoise'},
             {'name': 'TC ANTIBES JUAN LES PINS', 'city': 'Antibes', 'id': '62 06 0113', 'csvfile': 'tc_antibes'},
             {'name': 'MONTPON', 'city': 'Montpon-Ménestérol', 'id': '62 06 0114', 'csvfile': 'montpon'},
             {'name': 'TC MARSEILLE', 'city': 'Marseille', 'id': '62 06 0115', 'csvfile': 'tc_marseille'},
             {'name': 'TC BRIANCON', 'city': 'Briançon', 'id': '62 06 0116', 'csvfile': 'tc_briancon'},
             {'name': 'TC HYEROIS', 'city': 'Hyères', 'id': '62 06 0117', 'csvfile': 'tc_hyerois'},
             {'name': 'TENNIS C.B PLAN DE CUQUES', 'city': 'Plan de Cuques', 'id': '62 06 0118', 'csvfile': 'tc_cb_plan_de_cuques'},
             {'name': 'TC CANNES MONFLEURY', 'city': 'Cannes', 'id': '62 06 0119', 'csvfile': 'tc_cannes_montfleury'},
             {'name': 'T.C SAINT-JULIEN', 'city': 'Saint-Julien', 'id': '62 06 0120', 'csvfile': 'tc_saint_julien'}
             ]
    PARIS = timezone('Europe/Paris')
    BASE_PATH = os.path.dirname(__file__)


class DevelopmentConfig(Config):
    DEBUG = True
    DEBUG_TB_INTERCEPT_REDIRECTS = True
    ENV = 'development'


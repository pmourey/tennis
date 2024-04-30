# config.py
import os

from pytz import timezone


class Config:
    DEBUG = False
    # TESTING = True
    SECRET_KEY = 'fifa 2022'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///tennis.sqlite3'
    CLUBS = [{'name': 'US CAGNES TENNIS', 'city': 'Cagnes-sur-Mer', 'id': '62 06 0107', 'csvfile': 'us_cagnes'},
             {'name': 'TC MOUGINS', 'city': 'Mougins', 'id': '62 06 0108', 'csvfile': 'tc_mougins'},
             {'name': 'ASLM TENNIS CANNES', 'city': 'Cannes', 'id': '62 06 0109', 'csvfile': 'aslm_tennis_cannes'},
             {'name': 'NICE LAWN TENNIS CLUB', 'city': 'Nice', 'id': '62 06 0110', 'csvfile': 'nice_lawn_tennis'},
             {'name': 'RIORGEOIS (TENNIS CLUB DE)', 'city': 'Nice', 'id': '62 06 0111', 'csvfile': 'tc_riorgeois'},
             {'name': 'LA RAQUETTE ROQUEFORTOISE', 'city': 'Nice', 'id': '62 06 0112', 'csvfile': 'la_raquette_roquefortoise'}
             ]
    PARIS = timezone('Europe/Paris')
    BASE_PATH = os.path.dirname(__file__)


class DevelopmentConfig(Config):
    DEBUG = True
    DEBUG_TB_INTERCEPT_REDIRECTS = True
    ENV = 'development'


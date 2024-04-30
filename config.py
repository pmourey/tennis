# config.py
from pytz import timezone


class Config:
    DEBUG = False
    # TESTING = True
    SECRET_KEY = 'fifa 2022'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///tennis.sqlite3'
    CLUBS = [{'name': 'US CAGNES TENNIS', 'city': 'Cagnes-sur-Mer', 'id': '62 06 0107'},
             {'name': 'TC MOUGINS', 'city': 'Mougins', 'id': '62 06 0108'},
             {'name': 'ASLM TENNIS CANNES', 'city': 'Cannes', 'id': '62 06 0109'},
             {'name': 'NICE LAWN TENNIS CLUB', 'city': 'Nice', 'id': '62 06 0110'}
             ]
    PARIS = timezone('Europe/Paris')


class DevelopmentConfig(Config):
    DEBUG = True
    DEBUG_TB_INTERCEPT_REDIRECTS = True
    ENV = 'development'


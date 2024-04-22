# config.py
from pytz import timezone


class Config:
    DEBUG = False
    # TESTING = True
    SECRET_KEY = 'fifa 2022'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///tennis.sqlite3'
    DEFAULT_CLUB = {'name': 'USC Tennis', 'city': 'Cagnes-sur-Mer'}
    PARIS = timezone('Europe/Paris')


class DevelopmentConfig(Config):
    DEBUG = True
    DEBUG_TB_INTERCEPT_REDIRECTS = True
    ENV = 'development'


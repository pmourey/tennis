# config.py
import os

from pytz import timezone


class Config:
    DEBUG = True
    # TESTING = True
    SECRET_KEY = 'fifa 2022'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///tennis.sqlite3'
    CLUBS = [{'id': '62060107', 'active': True, 'name': 'US CAGNES TENNIS', 'city': 'Cagnes-sur-Mer', 'csvfile': 'us_cagnes_tennis'},
             {'id': '62060207', 'active': False, 'name': 'TC MOUGINS', 'city': 'Mougins', 'csvfile': 'tc_mougins'},
             {'id': '62060137', 'active': False, 'name': 'ASLM TENNIS CANNES', 'city': 'Cannes', 'csvfile': 'aslm_tennis_cannes'},
             {'id': '62060001', 'active': False, 'name': 'NICE LAWN TENNIS CLUB', 'city': 'Nice', 'csvfile': 'nice_lawn_tennis_club'},
             {'id': '50420420', 'active': False, 'name': 'RIORGEOIS (TENNIS CLUB DE)', 'city': 'Roanne',  'csvfile': 'tc_riorgeois'},
             {'id': '62060418', 'active': False, 'name': 'LA RAQUETTE ROQUEFORTOISE', 'city': 'Roquefort-les-Pins', 'csvfile': 'la_raquette_roquefortoise'},
             {'id': '62060016', 'active': True, 'name': 'TC ANTIBES JUAN LES PINS', 'city': 'Antibes', 'csvfile': 'tc_antibes'},
             {'id': '59240142', 'active': False, 'name': 'MONTPON', 'city': 'Montpon-Ménestérol', 'csvfile': 'montpon'},
             {'id': '62130002', 'active': False, 'name': 'TC MARSEILLE', 'city': 'Marseille', 'csvfile': 'tc_marseille'},
             {'id': '62050086', 'active': False, 'name': 'TC BRIANCON', 'city': 'Briançon', 'csvfile': 'tc_briancon'},
             {'id': '62830031', 'active': False, 'name': 'TC HYEROIS', 'city': 'Hyères', 'csvfile': 'tc_hyerois'},
             {'id': '62130193', 'active': False, 'name': 'TENNIS C.B PLAN DE CUQUES', 'city': 'Plan de Cuques', 'csvfile': 'tc_cb_plan_de_cuques'},
             {'id': '62060449', 'active': True, 'name': 'TC CANNES MONFLEURY', 'city': 'Cannes', 'csvfile': 'tc_cannes_montfleury'},
             {'id': '62130226', 'active': False, 'name': 'T.C SAINT-JULIEN', 'city': 'Saint-Julien', 'csvfile': 'tc_saint_julien'},
             {'id': '62060315', 'active': False, 'name': 'TC ACACIAS', 'city': 'CAGNES SUR MER', 'csvfile': 'tc_acacias'},
             {'id': '62060195', 'active': False, 'name': 'AGASC TC MONTALEIGNE', 'city': 'CAGNES SUR MER', 'csvfile': 'agasc_montaleigne'},
             {'id': '62050084', 'active': False, 'name': 'TC GAP', 'city': 'GAP', 'csvfile': 'tc_gap'},
             {'id': '62130030', 'active': False, 'name': 'COUNTRY CLUB AIXOIS', 'city': 'AIX-EN-PROVENCE', 'csvfile': 'country_club_aixois'},
             {'id': '62130136', 'active': False, 'name': 'TENNIS CLUB PENNES - MIRABEAU', 'city': 'LES PENNES MIRABEAU', 'csvfile': 'tc_pennes_mirabeau'},
             {'id': '62130567', 'active': False, 'name': 'TENNIS CLUB ROUVIERE', 'city': 'MARSEILLE', 'csvfile': 'tc_rouviere'},
             {'id': '62130054', 'active': False, 'name': 'TENNIS CLUB PORT-DE-BOUC', 'city': 'PORT-DE-BOUC', 'csvfile': 'tc_port_de_bouc'},
             {'id': '62130274', 'active': False, 'name': 'TENNIS CLUB DE GEMENOS', 'city': 'GEMENOS', 'csvfile': 'tc_gemenos'},
             {'id': '62060022', 'active': True, 'name': 'TC NICE GIORDAN', 'city': 'NICE', 'csvfile': 'tc_nice_giordan'},
             {'id': '62060005', 'active': True, 'name': 'TC BEAULIEU', 'city': 'BEAULIEU', 'csvfile': 'tc_beaulieu'},
             {'id': '57750283', 'active': True, 'name': 'CA VINCENNES', 'city': 'VINCENNES', 'csvfile': 'ca_vincennes'},
             ]
    YEARS = [2023, 2024]
    PARIS = timezone('Europe/Paris')
    BASE_PATH = os.path.dirname(__file__)
    MAPBOX_API_KEY = 'pk.eyJ1IjoicG1vdXJleSIsImEiOiJjbHZ4dnJ3bGMwNDBzMmlxeXBnZDJtYzVrIn0.yxrohiV1L6c89UY6PvPHGw'


class DevelopmentConfig(Config):
    DEBUG = True
    DEBUG_TB_INTERCEPT_REDIRECTS = True
    ENV = 'development'


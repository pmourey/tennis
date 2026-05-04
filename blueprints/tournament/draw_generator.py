# Source Generated with Decompyle++
# File: draw_generator.cpython-310.pyc (Python 3.10)

'''
Générateur de tableaux de tournoi conforme aux règles FFT (Articles 45-50).
- Art. 47 : tableau à départ en ligne → draw_size = next_power_of_2(n), BYES = draw_size - n
- Art. 46 : têtes de série dans moitiés/quarts opposés
- Qualifying par tranche de TRANCHE_SIZE niveaux de classement
- Têtes de série directement en tableau final
'''
from __future__ import annotations
import logging
import math
import random
from datetime import datetime
from extensions import db
from models import TournamentDraw, TournamentMatch
logger = logging.getLogger(__name__)
MAX_MAIN_DRAW = 32
TRANCHE_SIZE = 3
MAX_SECTION_SIZE = 8

def next_power_of_2(n = None):
    if n <= 4:
        return 4
    return None ** math.ceil(math.log2(n))


def can_generate_draw(category = None):
    """
    Vérifie si la génération (ou régénération) d'un tableau est autorisée
    selon le statut du tournoi (Art. 50-3 FFT).

    Règles :
    - DRAFT / OPEN       : toujours autorisé.
    - IN_PROGRESS        : autorisé UNIQUEMENT si aucun match n'est dans
      l'état COMPLETED ou WALKOVER (Art. 50-3 : le tableau peut être refait
      tant qu'aucune partie n'a commencé).
    - CLOSED             : toujours interdit.

    Retourne (ok: bool, message: str).
    """
    tournament = category.tournament
    status = tournament.status
    if status == 'CLOSED':
        return (False, 'Le tournoi est terminé (CLOSED) — modification du tableau interdite.')
    if None == 'IN_PROGRESS':
        played = TournamentMatch.query.join(TournamentMatch.draw).filter(TournamentDraw.category_id == category.id, TournamentMatch.status.in_([
            'COMPLETED',
            'WALKOVER'])).count()
        if played > 0:
            return (False, f'''Le tournoi est en cours et {played} match(s) ont déjà été joués — régénération interdite (Art. 50-3 FFT).''')
        return None


def nb_seeds_for_draw(draw_size = None, n = None):
    return min(n // 2, max(2, draw_size // 4))


def seed_positions(draw_size = None, nb_seeds = None):

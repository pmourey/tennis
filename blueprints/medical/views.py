# Source Generated with Decompyle++
# File: views.cpython-310.pyc (Python 3.10)

import os
from flask import render_template, current_app, request
import json
from sqlalchemy import func
from models import Player, License, Injury, InjurySite
from blueprints.medical import medical_management_bp

def index():
    return render_template('medical_index.html')

index = medical_management_bp.route('/')(index)

def injuries_old():
    static_folder = current_app.blueprints['medical'].static_folder
    file_path = os.path.join(static_folder, 'data', 'injuries_fr.json')
    with open(file_path, 'r') as file:
        data = json.load(file)
        None(None, None, None)
    with None:
        if not None:
            pass
    return render_template('injuries_classification.html', data, **('data',))

injuries_old = medical_management_bp.route('/injuries_old')(injuries_old)

def injuries():
    injury_sites = InjurySite.query.all()
    for site in injury_sites:
        site.injuries = Injury.query.filter_by(site.id, **('siteId',)).all()
    return render_template('injuries_classification.html', injury_sites, **('injury_sites',))

injuries = medical_management_bp.route('/injuries')(injuries)

def injured_players():
    players = Player.query.filter(Player.injuries.any()).all()
    sort_criteria = 'best_elo'
    return render_template('players.html', players, f'''Liste de {len(players)} joueurs/joueuses blessé(e)s''', sort_criteria, **('players', 'caption', 'sort_criteria'))

injured_players = medical_management_bp.route('/injured_players')(injured_players)

def search_players():
    search_query = request.args.get('search_query')
    if search_query:
        players = Player.query.join(License).filter(func.lower(License.lastName).like(f'''{search_query.lower()}''')).all()
        return render_template('search_results.html', players, **('players',))
    return None('search_players.html')

search_players = medical_management_bp.route('/search', [
    'GET'], **('methods',))(search_players)

# medical/views.py
import os

from flask import url_for, render_template, current_app, render_template_string, request
import json

from sqlalchemy import func

from TennisModel import Player, License, Injury, InjurySite
from medical import medical_management_bp


# Define routes for medical management
@medical_management_bp.route('/')
def index():
    return render_template('medical_index.html')


@medical_management_bp.route('/injuries_old')
def injuries_old():
    static_folder = current_app.blueprints['medical'].static_folder
    file_path = os.path.join(static_folder, 'data', 'injuries_fr.json')
    with open(file_path, 'r') as file:
        data = json.load(file)
    return render_template('injuries_classification.html', data=data)

@medical_management_bp.route('/injuries')
def injuries():
    injury_sites = InjurySite.query.all()
    for site in injury_sites:
        site.injuries = Injury.query.filter_by(siteId=site.id).all()
    return render_template('injuries_classification.html', injury_sites=injury_sites)

@medical_management_bp.route('/injured_players')
def injured_players():
    players = Player.query.filter(Player.injuries.any()).all()
    sort_criteria = 'best_elo'
    return render_template('players.html', players=players, caption=f'Liste de {len(players)} joueurs/joueuses blessé(e)s', sort_criteria=sort_criteria)

@medical_management_bp.route('/search', methods=['GET'])
def search_players():
    search_query = request.args.get('search_query')
    if search_query:
        players = Player.query.join(License).filter(func.lower(License.lastName).like(f'{search_query.lower()}')).all()
        # current_app.logger.info(f'players: {players}')
        return render_template('search_results.html', players=players)
    else:
        return render_template('search_players.html')


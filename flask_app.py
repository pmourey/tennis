"""
Copyright © 2023 Philippe Mourey

This script provides CRUD features inside a Flask application for job's research follow-up and contact recruiters at monthly basis using a scheduler

"""
from __future__ import annotations

from logging import basicConfig, DEBUG
import locale
from datetime import datetime, timedelta
from flask import Flask, request, flash, url_for, redirect, render_template, session, send_file
from flask_debugtoolbar import DebugToolbarExtension
from sqlalchemy import DateTime, desc, not_

from TennisModel import Player, db, Team

from flask import render_template, redirect, url_for, flash

app = Flask(__name__, static_folder='static', static_url_path='/static')
# Set the environment (development, production, etc.)
# Replace 'development' with the appropriate value for your environment
app.config.from_object('config.Config')
# app.config.from_pyfile(config_filename)

db.init_app(app)

toolbar = DebugToolbarExtension(app)

locale.setlocale(locale.LC_TIME, 'fr_FR')
basicConfig(level=DEBUG)

# Set the secret key to some random bytes. Keep this really secret!
app.secret_key = b'_5#y2L"F4Q8z\n\xec]/'


# app.config['SECRET_KEY'] = 'fifa2022'
# app.config['SESSION_TYPE'] = 'filesystem'


@app.route('/')
def welcome():
    return render_template('index.html')


@app.route('/players')
def show_players():
    # Reverse order query
    # players = Player.query.filter(Player.isActive).order_by(desc(Player.birthDate)).all()
    players = Player.query.filter(Player.isActive).all()
    # players = Player.query.all()
    app.logger.debug(f'players: {players}')
    return render_template('players.html', players=players, statut='actifs')

@app.route('/invalid_players')
def show_invalid_players():
    # Reverse order query
    # players = Player.query.filter(Player.isActive).order_by(desc(Player.birthDate)).all()
    inactive_players = Player.query.filter(not_(Player.isActive)).all()
    # players = Player.query.all()
    app.logger.debug(f'invalid players: {inactive_players}')
    return render_template('players.html', players=inactive_players, statut='inactifs')

@app.route('/teams')
def show_teams():
    # Récupérer toutes les équipes avec le nombre de joueurs
    teams = Team.query.all()
    team_info = []
    for team in teams:
        # Compter le nombre de joueurs dans l'équipe
        num_players = Player.query.filter_by(teamId=team.id).count()
        # Récupérer le nom du capitaine s'il existe
        captain = Player.query.filter_by(teamId=team.id, isCaptain=True).first()
        captain_name = captain.name if captain else None
        # Ajouter les informations de l'équipe à la liste
        team_info.append({'team_name': team.name, 'num_players': num_players, 'captain_name': captain_name})

    return render_template('teams.html', team_info=team_info)


@app.route('/new_player/', methods=['GET', 'POST'])
def new_player():
    app.logger.debug(f'request.method: {request.method}')
    if request.method == 'POST':
        if not (request.form['name'] and request.form['birth_date']):
            flash('Veuillez renseigner tous les champs, svp!', 'error')
        else:
            birth_date: datetime = datetime.strptime(request.form['birth_date'], '%Y-%m-%d')
            # is_captain: bool = request.form.get('is_captain') == 'on'
            is_captain = False if request.form.get('is_captain') is None else True
            app.logger.debug(f'is_captain: {is_captain}')
            player = Player(name=request.form['name'], birthDate=birth_date,
                            height=request.form['height'], weight=request.form['weight'], teamId=request.form['team_id'],
                            isCaptain=is_captain, isActive=True)
            # logging.warning("See this message in Flask Debug Toolbar!")
            db.session.add(player)
            db.session.commit()
            team = Team.query.get(player.teamId)
            player_type: str =  'capitaine' if player.isCaptain else 'joueur'
            flash(f'{player.name} ajouté avec succès à l\'équipe {team.name} en tant que {player_type}!')
            return redirect(url_for('show_players'))
    teams = Team.query.all()
    app.logger.debug(f'teams: {teams}')
    return render_template('new_player.html', teams=teams)

@app.route('/update_player/<int:id>', methods=['GET', 'POST'])
def update_player(id):
    player: Player = Player.query.get_or_404(id)
    if request.method == 'POST':
        player.name = request.form.get('name')
        birth_date = request.form.get('birth_date')
        app.logger.debug(f'birthDate: {birth_date}')
        player.birthDate = datetime.strptime(birth_date, '%Y-%m-%d') if birth_date else None
        player.height = request.form.get('height')
        player.weight = request.form.get('weight')
        player.isCaptain = False if request.form.get('is_captain') is None else True
        player.isActive = False if request.form.get('is_active') is None else True
        app.logger.debug(f'is_captain: {player.isCaptain}')
        player.teamId = request.form.get('team_id')
        db.session.commit()
        player_type: str = 'capitaine' if player.isCaptain else 'joueur'
        flash(f'Infos {player_type} {player.name} mises à jour avec succès!')
        return redirect(url_for('show_players'))
    else:
        teams = Team.query.all()
        return render_template('update_player.html', player=player, teams=teams)

@app.route('/delete/<int:id>', methods=['GET', 'POST'])
def delete(id):
    app.logger.debug(f'Delete job #{id}')
    if request.method == 'GET':
        player = Player.query.get_or_404(id)
        app.logger.debug(f'Player debug: {player}')
        # db.session.delete(job)
        player.isActive = False
        db.session.commit()
        flash(f'Joueur \"{player.name}\" supprimé de l\'équipe  \"{player.team}\"!')
        return redirect(url_for('show_players'))


@app.before_request
def create_tables():
    db.create_all()

# app.run()
# toolbar.init_app(app)
# app.run(debug=True, use_debugger=True, use_reloader=False)

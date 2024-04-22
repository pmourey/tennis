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

from TennisModel import Player, db, Team, Club

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
    # Vérifier si le club par défaut existe dans la base de données
    default_club = Club.query.filter_by(name=app.config['DEFAULT_CLUB']['name']).first()
    if not default_club:
        # Si le club par défaut n'existe pas, l'ajouter à la base de données
        default_club = Club(name=app.config['DEFAULT_CLUB']['name'], city=app.config['DEFAULT_CLUB']['city'])
        db.session.add(default_club)
        db.session.commit()
        message = f'Club {default_club} créé avec succès ! Veuillez créer des joueurs dans le club, avant de créér les équipes :-D'
        flash(message, 'error')

    return render_template('index.html')


@app.route('/players')
def show_players():
    # Reverse order query
    # players = Player.query.filter(Player.isActive).order_by(desc(Player.birthDate)).all()
    players = Player.query.filter(Player.isActive).all()
    # players = Player.query.all()
    app.logger.debug(f'players: {players}')
    return render_template('players.html', players=players, active_players=True)

@app.route('/invalid_players')
def show_invalid_players():
    # Reverse order query
    # players = Player.query.filter(Player.isActive).order_by(desc(Player.birthDate)).all()
    inactive_players = Player.query.filter(not_(Player.isActive)).all()
    # players = Player.query.all()
    app.logger.debug(f'invalid players: {inactive_players}')
    return render_template('players.html', players=inactive_players, active_players=False)

@app.route('/teams_old')
def show_teams_old():
    # Récupérer toutes les équipes avec le nombre de joueurs
    teams = Team.query.all()
    team_info = []
    for team in teams:
        # Compter le nombre de joueurs dans l'équipe
        num_active_players = Player.query.filter_by(teamId=team.id, isActive=True).count()
        # Récupérer le nom du capitaine s'il existe
        captain = Player.query.filter_by(teamId=team.id, isCaptain=True, isActive=True).first()
        captain_name = captain.name if captain else None
        # Ajouter les informations de l'équipe à la liste
        team_info.append({'team_name': team.name, 'num_players': num_active_players, 'captain_name': captain_name})

    return render_template('teams.html', team_info=team_info)

@app.route('/teams')
def show_teams():
    teams = Team.query.order_by(desc(Team.name)).all()
    return render_template('teams.html', teams=teams)

def keys_with_same_value(d):
    return [value for value in set(d.values()) if list(d.values()).count(value) > 1]
    # return {value: [key for key, val in d.items() if val == value] for value in set(d.values()) if list(d.values()).count(value) > 1}


@app.route('/new_team/', methods=['GET', 'POST'])
def new_team():
    players_dict = {}
    if request.method == 'POST':
        # Parcourir les données pour récupérer les noms des joueurs
        for key, value in request.form.items():
            if value and key.startswith('player_name_'):
                players_dict[key] = Player.query.get(value)
        # test doublons
        duplicates = keys_with_same_value(players_dict)
        if not request.form['name']:
            flash('Veuillez renseigner tous les champs, svp!', 'error')
        elif duplicates:
            if len(duplicates) == 1:
                flash(f'Le joueur {duplicates[0]} est en doublon, veuillez en sélectionner un autre!', 'error')
            else:
                flash(f'Les joueurs {duplicates} sont en doublons, veuillez en sélectionner d\'autres!', 'error')
        else:
            # Récupérer les données du formulaire
            team_name = request.form.get('name')
            captain_id = request.form.get('captain_id')

            # Créer l'équipe avec les informations fournies
            # Vous pouvez ajouter le code pour enregistrer l'équipe dans la base de données ici

            team = Team(name=team_name, captainId=captain_id, players=list(players_dict.values()))
            db.session.add(team)
            db.session.commit()
            flash(f'L\'équipe {team.name} a été créée avec succès avec {len(team.players)} joueurs!')
            return redirect(url_for('show_teams'))
    default_club = Club.query.filter_by(name=app.config['DEFAULT_CLUB']['name']).first()
    active_players = Player.query.filter_by(clubId=default_club.id, isActive=True).all()  # US Cagnes only :-)
    if active_players:
        app.logger.debug(f'players: {active_players}')
        app.logger.debug(f'request.form: {request.form}')
        max_players = min(10, len(active_players))
        return render_template('new_team.html', active_players=active_players, max_players=max_players, form=request.form)
    else:
        flash(f'Tâche impossible! Veuillez créer des joueurs dans le club {default_club} au préalable!', 'error')
        return render_template('index.html')

@app.route('/update_team/<int:id>', methods=['GET', 'POST'])
def update_team(id):
    team: Team = Team.query.get_or_404(id)
    app.logger.debug(f'team: {(team.id, id, team.name)} - players: {team.players}')
    players_dict = {}
    if request.method == 'POST':
        # Parcourir les données pour récupérer les noms des joueurs
        for key, value in request.form.items():
            if value and key.startswith('player_name_'):
                players_dict[key] = Player.query.get(value)
        # test doublons
        duplicates = keys_with_same_value(players_dict)
        if not request.form['name']:
            flash('Veuillez renseigner tous les champs, svp!', 'error')
        elif duplicates:
            if len(duplicates) == 1:
                flash(f'Le joueur {duplicates[0]} est en doublon, veuillez en sélectionner un autre!', 'error')
            else:
                flash(f'Les joueurs {duplicates} sont en doublons, veuillez en sélectionner d\'autres!', 'error')
        else:
            team.name = request.form.get('name')
            team.captainId = request.form.get('captain_id')
            team.players = list(players_dict.values())
            db.session.commit()
            flash(f'Equipe {team.name} mise à jour avec succès!')
            return redirect(url_for('show_teams'))
    default_club = Club.query.filter_by(name=app.config['DEFAULT_CLUB']['name']).first()
    app.logger.debug(f'default_club: {default_club}')
    active_players = Player.query.filter_by(clubId=default_club.id, isActive=True).all()  # US Cagnes only :-)
    app.logger.debug(f'active players: {active_players}')
    if active_players:
        max_players = min(10, len(active_players))
        return render_template('update_team.html', team=team, active_players=active_players, max_players=max_players)
    else:
        flash(f'Tâche impossible! Aucun joueur existant ou disponible dans le club {default_club}!', 'error')
        return render_template('index.html')

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
            player = Player(name=request.form['name'], birthDate=birth_date, height=request.form['height'],
                            weight=request.form['weight'], clubId=request.form['club_id'], isActive=True)
            # logging.warning("See this message in Flask Debug Toolbar!")
            db.session.add(player)
            db.session.commit()
            club = Club.query.get(player.clubId)
            flash(f'{player.name} ajouté avec succès dans le club {club.name}!')
            return redirect(url_for('show_players'))
    clubs = Club.query.all()
    app.logger.debug(f'clubs: {clubs}')
    return render_template('new_player.html', clubs=clubs)

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
        player.isActive = False if request.form.get('is_active') is None else True
        player.clubId = request.form.get('club_id')
        db.session.commit()
        flash(f'Infos {player.name} mises à jour avec succès!')
        return redirect(url_for('show_players'))
    else:
        clubs = Club.query.all()
        return render_template('update_player.html', player=player, clubs=clubs)

@app.route('/delete_player/<int:id>', methods=['GET', 'POST'])
def delete_player(id):
    if request.method == 'GET':
        player = Player.query.get_or_404(id)
        db.session.delete(player)
        db.session.commit()
        app.logger.debug(f'Joueur {player} supprimé!')
        flash(f"Joueur \"{player.name}\" ne fait plus partie du club \"{app.config['DEFAULT_CLUB']['name']}\"!")
        return redirect(url_for('show_players'))

@app.route('/delete_team/<int:id>', methods=['GET', 'POST'])
def delete_team(id):
    if request.method == 'GET':
        team = Team.query.get_or_404(id)
        db.session.delete(team)
        db.session.commit()
        app.logger.debug(f'Equipe {team} supprimé!')
        flash(f"L'équipe \"{team.name}\" ne fait plus partie du club \"{app.config['DEFAULT_CLUB']['name']}\"!")
        return redirect(url_for('show_teams'))

@app.before_request
def create_tables():
    db.create_all()

# app.run()
# toolbar.init_app(app)
# app.run(debug=True, use_debugger=True, use_reloader=False)

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

from TennisModel import Player, db, Team, Club, Championship, AgeCategory, Division, Pool, Matchday

from flask import render_template, redirect, url_for, flash

from common import CatType, DivType

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

    # Vérifier si les catégories d'âge existent en base de données
    age_categories = AgeCategory.query.all()
    if not age_categories:
        # Si aucune catégorie d'âge n'existe, créer les catégories d'âge
        age_categories = [
            AgeCategory(type=CatType.Youth.value, minAge=10, maxAge=11),
            AgeCategory(type=CatType.Youth.value, minAge=12, maxAge=13),
            AgeCategory(type=CatType.Youth.value, minAge=15, maxAge=16),
            AgeCategory(type=CatType.Youth.value, minAge=17, maxAge=18),
            AgeCategory(type=CatType.Senior.value, minAge=18, maxAge=99),
            AgeCategory(type=CatType.Veteran.value, minAge=35, maxAge=99),
            AgeCategory(type=CatType.Veteran.value, minAge=45, maxAge=99),
            AgeCategory(type=CatType.Veteran.value, minAge=55, maxAge=99),
            AgeCategory(type=CatType.Veteran.value, minAge=65, maxAge=99),
            AgeCategory(type=CatType.Veteran.value, minAge=75, maxAge=99),
        ]
        db.session.add_all(age_categories)
        db.session.commit()

    # Vérifier si les divisions existent en base de données
    divisions = Division.query.all()
    if not divisions:
        # Si aucune division n'existe, créer les divisions
        divisions = []
        # TODO: rajouter les compétitions mixtes
        # Catégorie d'âge: SENIORS
        age_categories = AgeCategory.query.filter(AgeCategory.type == CatType.Senior.value).all()
        app.logger.info(age_categories)
        for age_category in age_categories:
            for gender in range(2):
                for i in range(4):
                    divisions += [Division(type=DivType.National.value, number=i + 1, ageCategoryId=age_category.id, gender=gender)]
                divisions += [Division(type=DivType.Prenational.value, ageCategoryId=age_category.id, gender=gender)]
                for i in range(3):
                    divisions += [Division(type=DivType.Regional.value, number=i + 1, ageCategoryId=age_category.id, gender=gender)]
                for i in range(5):
                    divisions += [Division(type=DivType.Departmental.value, ageCategoryId=age_category.id, number=i + 1, gender=gender)]
        # Catégorie d'âge: JEUNES
        age_categories = AgeCategory.query.filter(AgeCategory.type == CatType.Youth.value).all()
        for age_category in age_categories:
            for gender in range(2):
                divisions += [Division(type=DivType.National.value, ageCategoryId=age_category.id, gender=gender)]
                divisions += [Division(type=DivType.Regional.value, ageCategoryId=age_category.id, gender=gender)]
                divisions += [Division(type=DivType.Departmental.value, ageCategoryId=age_category.id, gender=gender)]
        # Catégorie d'âge: VETERANS
        age_categories = AgeCategory.query.filter(AgeCategory.type == CatType.Veteran.value).all()
        for age_category in age_categories:
            for gender in range(2):
                divisions += [Division(type=DivType.National.value, ageCategoryId=age_category.id, gender=gender)]
                divisions += [Division(type=DivType.Prenational.value, ageCategoryId=age_category.id, gender=gender)]
                divisions += [Division(type=DivType.Regional.value, ageCategoryId=age_category.id, gender=gender)]
                for i in range(2):
                    divisions += [Division(type=DivType.Departmental.value, ageCategoryId=age_category.id, number=i + 1, gender=gender)]
        db.session.add_all(divisions)
        db.session.commit()

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
            championship_id = request.form.get('championship')
            championship = Championship.query.get(championship_id)
            pool = Pool(championshipId=championship_id) # poule non connue lors de la phase d'inscription de l'équipe au championnat
            # Création des journées de championnat pour la saison en cours
            for date in championship.match_dates:
                matchday = Matchday(date=date, poolId=pool.id)
                # pool.matchdays.append(matchday)
                db.session.add(matchday)
                db.session.add(pool)
                db.session.commit()
            # Créer l'équipe avec les informations fournies
            # Vous pouvez ajouter le code pour enregistrer l'équipe dans la base de données ici

            team = Team(name=team_name, captainId=captain_id, poolId=pool.id, players=list(players_dict.values()))
            db.session.add(team)
            db.session.commit()
            flash(f'L\'équipe "{team.name}" a été créée avec succès avec {len(team.players)} joueurs et associé au championnat {championship} qui a lieu du {championship.startDate} au {championship.endDate}!')
            return redirect(url_for('show_teams'))
    default_club = Club.query.filter_by(name=app.config['DEFAULT_CLUB']['name']).first()
    active_players = Player.query.filter_by(clubId=default_club.id, isActive=True).all()  # US Cagnes only :-)
    championships = Championship.query.all()
    if not active_players:
        flash(f'Tâche impossible! Vous devez ajouter des joueurs dans le club {default_club} au préalable!', 'error')
        return render_template('index.html')
    elif not championships:
        flash(f'Tâche impossible! Vous devez ajouter un type de championnat pour la saison en cours!', 'error')
        return render_template('index.html')
    else:
        app.logger.debug(f'players: {active_players}')
        app.logger.debug(f'request.form: {request.form}')
        max_players = min(10, len(active_players))
        return render_template('new_team.html', championships=championships, active_players=active_players, max_players=max_players, form=request.form)


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
            pool = Pool.query.get(team.poolId)
            pool.letter = request.form.get('letter')
            db.session.commit()
            flash(f'Equipe {team.name} mise à jour avec succès!')
            return redirect(url_for('show_teams'))
    default_club = Club.query.filter_by(name=app.config['DEFAULT_CLUB']['name']).first()
    app.logger.debug(f'default_club: {default_club}')
    active_players = Player.query.filter_by(clubId=default_club.id, isActive=True).all()  # US Cagnes only :-)
    app.logger.debug(f'active players: {active_players}')
    championships = Championship.query.all()
    if active_players:
        max_players = min(10, len(active_players))
        return render_template('update_team.html', team=team, active_players=active_players, max_players=max_players, championships=championships)
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


# @app.route('/select_age_category', methods=['GET', 'POST'])
# def select_age_category():
#     if request.method == 'POST':
#         selected_age_category_id = request.form['age_category']
#         selected_age_category = AgeCategory.query.get(selected_age_category_id)
#         # Utilisez l'identifiant de la catégorie d'âge sélectionnée pour générer la liste des divisions possibles
#         divisions = Division.query.filter_by(ageCategoryId=selected_age_category_id).all()
#         return redirect(url_for('select_division', divisions))
#         return render_template('select_division.html', divisions=divisions, selected_age_category=selected_age_category)
#     age_categories = AgeCategory.query.all()
#     return render_template('select_age_category.html', age_categories=age_categories)
#
# @app.route('/select_division', methods=['GET', 'POST'])
# def select_division():
#     if request.method == 'POST':
#         selected_division_id = request.form['division']
#         selected_division = Division.query.get(selected_division_id)
#         return render_template('new_championship.html', selected_division=selected_division)
#     divisions = Division.query.filter_by(ageCategoryId=selected_age_category_id).all()
#     return render_template('select_division.html', divisions=divisions)


@app.route('/select_age_category', methods=['GET', 'POST'])
def select_age_category():
    if request.method == 'POST':
        selected_age_category_id = request.form['age_category']
        return redirect(url_for('select_division', selected_age_category_id=selected_age_category_id))
    age_categories = AgeCategory.query.all()
    return render_template('select_age_category.html', age_categories=age_categories)


@app.route('/select_division', methods=['GET', 'POST'])
def select_division():
    if request.method == 'POST':
        selected_division_id = request.form['division']
        selected_division = Division.query.get(selected_division_id)
        return render_template('new_championship.html', selected_division=selected_division)

    # Retrieve the selected age category ID from the URL parameters
    selected_age_category_id = request.args.get('selected_age_category_id')

    divisions = Division.query.filter_by(ageCategoryId=selected_age_category_id).order_by(desc(Division.type)).all()
    # divisions = Division.query.filter_by(ageCategoryId=selected_age_category_id).all()
    app.logger.debug(f'divisions: {divisions}')
    return render_template('select_division.html', divisions=divisions)


@app.route('/new_championship', methods=['GET', 'POST'])
def new_championship():
    if request.method == 'POST':
        start_date = datetime.strptime(request.form['start_date'], '%Y-%m-%d')
        end_date = datetime.strptime(request.form['end_date'], '%Y-%m-%d')
        singles_count = int(request.form['singles_count'])
        doubles_count = int(request.form['doubles_count'])
        division_id = int(request.form['division'])  # Récupérer l'identifiant de la division sélectionnée

        championship = Championship(startDate=start_date, endDate=end_date, singlesCount=singles_count, doublesCount=doubles_count,
                                    divisionId=division_id)
        db.session.add(championship)
        db.session.commit()

        flash('Championnat créé avec succès!', 'success')
        return render_template('index.html')
    divisions = AgeCategory.query.all()
    return render_template('new_championship.html', divisions=divisions)


@app.route('/list_championships')
def list_championships():
    championships = Championship.query.all()
    app.logger.debug(f'championships: {championships}')
    return render_template('list_championships.html', championships=championships)


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

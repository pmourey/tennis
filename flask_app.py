"""
Copyright © 2023 Philippe Mourey

This script provides CRUD features inside a Flask application for job's research follow-up and contact recruiters at monthly basis using a scheduler

"""
from __future__ import annotations

from logging import basicConfig, DEBUG
import locale
from datetime import datetime

from flask import Flask, request, flash, url_for, redirect, render_template, session, send_file
from flask_debugtoolbar import DebugToolbarExtension
from sqlalchemy import not_, desc

from flask import render_template, redirect, url_for, flash
from sqlalchemy.orm import joinedload

from TennisModel import *
# from TennisModel import Player, db, Team, Club, Championship, AgeCategory, Division, Pool, Matchday, Ranking

from common import load_age_categories, load_divisions, import_players, load_rankings, get_players_order_by_ranking, get_championships, Gender, check_license

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
        default_club = Club(id=app.config['DEFAULT_CLUB']['id'], name=app.config['DEFAULT_CLUB']['name'], city=app.config['DEFAULT_CLUB']['city'])
        app.logger.debug(f'default_club: {default_club}')
        db.session.add(default_club)
        db.session.commit()
        message = f'Club {default_club} créé avec succès ! Veuillez créer des joueurs dans le club, avant de créér les équipes :-D'
        flash(message, 'error')

    # Vérifier si les catégories d'âge existent en base de données
    age_categories = AgeCategory.query.all()
    if not age_categories:
        # Si aucune catégorie d'âge n'existe, créer les catégories d'âge
        load_age_categories(db)

    # Vérifier si les divisions existent en base de données
    divisions = Division.query.all()
    if not divisions:
        # Si aucune division n'existe, créer les divisions
        load_divisions(db)

    # Vérifier si les classements de tennis existent en base de données
    rankings = Ranking.query.all()
    if not rankings:
        load_rankings(db)

    # Vérifier si les joueurs existent en base de données
    players = Player.query.all()
    if not players:
        # Si aucun joueur n'existe, les importer des fichiers csv du club par défaut
        men_players_csvfile = f'static/data/uscagnes_men.csv'
        women_players_csvfile = f'static/data/uscagnes_women.csv'
        import_players(app, men_players_csvfile, women_players_csvfile, default_club, db)

    return render_template('index.html')


@app.route('/select_gender', methods=['GET', 'POST'])
def select_gender():
    if request.method == 'POST':
        gender = int(request.form['gender'])
        players = get_players_order_by_ranking(gender=gender)
        return render_template('players.html', gender=gender, players=players, active_players=True)
    return render_template('select_gender.html')


@app.route('/select_championship_new_team', methods=['GET', 'POST'])
def select_championship_new_team():
    if request.method == 'POST':
        app.logger.debug(f"gender = {request.form['gender']}")
        gender = int(request.form['gender'])
        championship_id = request.form['championship']
        return redirect(url_for('new_team', championship_id=championship_id, gender=gender))
    selected_gender = int(request.args.get('gender'))
    championships = get_championships(gender=selected_gender)
    return render_template('select_championship_new_team.html', championships=championships, gender=selected_gender)


@app.route('/select_gender_new_team', methods=['GET', 'POST'])
def select_gender_new_team():
    if request.method == 'POST':
        gender = int(request.form['gender'])
        return redirect(url_for('select_championship_new_team', gender=gender))
    return render_template('select_gender_new_team.html')


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
            gender = int(request.form['gender'])
            championship_id = request.form.get('championship_id')
            team_name = request.form.get('name')
            captain_id = request.form.get('captain_id')
            championship = Championship.query.get(championship_id)
            pool = Pool(championshipId=championship_id)  # poule non connue lors de la phase d'inscription de l'équipe au championnat
            # Création des journées de championnat pour la saison en cours
            for date in championship.match_dates:
                matchday = Matchday(date=date, poolId=pool.id)
                # pool.matchdays.append(matchday)
                db.session.add(matchday)
                db.session.add(pool)
                db.session.commit()
            # Créer l'équipe avec les informations fournies
            team_players = list(players_dict.values())
            team_players.sort(key=lambda p: p.ranking_id)
            team = Team(name=team_name, captainId=captain_id, poolId=pool.id, players=team_players)
            db.session.add(team)
            db.session.commit()
            flash(
                f"L'équipe '{team.name}' a été créée avec succès avec {len(team.players)} {'joueuses' if gender else 'joueurs'} et associé au championnat {championship} qui a lieu du {championship.startDate} au {championship.endDate}!")
            return redirect(url_for('show_teams'))
    championship_id = int(request.args.get('championship_id'))
    gender = int(request.args.get('gender'))
    championship = Championship.query.get(championship_id)
    age_category = championship.division.ageCategory
    app.logger.debug(f"championship = {championship} - age_category = {age_category}")
    active_players = get_players_order_by_ranking(gender=gender, age_category=age_category)
    app.logger.debug(f"{len(active_players)} players = {active_players}")
    if not active_players:
        default_club = Club.query.filter_by(name=app.config['DEFAULT_CLUB']['name']).first()
        flash(f'Tâche impossible! Vous devez ajouter des joueurs dans le club {default_club} au préalable!', 'error')
        return render_template('index.html')
    else:
        app.logger.debug(f'players: {active_players}')
        app.logger.debug(f'request.form: {request.form}')
        max_players = min(10, len(active_players))
        return render_template('new_team.html', gender=gender, championship=championship, players=active_players, max_players=max_players, form=request.form)


@app.route('/update_team/<int:id>', methods=['GET', 'POST'])
def update_team(id):
    team: Team = Team.query.get_or_404(id)
    app.logger.debug(f'team in database: {(team.id, id, team.name)} - players: {team.players}')
    players_dict = {}
    if request.method == 'POST':
        # Parcourir les données pour récupérer les noms des joueurs
        for key, value in request.form.items():
            if value and key.startswith('player_name_'):
                players_dict[key] = Player.query.get(value)
        app.logger.debug(f'players_dict: {players_dict}')
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
            team.name = request.form.get('name')
            team.captainId = request.form.get('captain_id')
            team.players = list(players_dict.values())
            app.logger.debug(f'PROUT -> {len(team.players)} players: {team.players}')
            pool = Pool.query.get(team.poolId)
            pool.letter = request.form.get('letter')
            db.session.commit()
            flash(f'Equipe {team.name} mise à jour avec succès!')
            return redirect(url_for('show_teams'))
    age_category = team.age_category
    app.logger.debug(f"gender = {team.gender} - age_category = {age_category}")
    active_players = get_players_order_by_ranking(gender=team.gender, age_category=age_category)
    app.logger.debug(f"{len(active_players)} players = {active_players}")
    sorted_team_players = sorted(team.players, key=lambda p: p.ranking)
    if active_players:
        max_players = min(10, len(active_players))
        return render_template('update_team.html', team=team, sorted_team_players=sorted_team_players, players=active_players, max_players=max_players, form=request.form)
    else:
        default_club = Club.query.filter_by(name=app.config['DEFAULT_CLUB']['name']).first()
        flash(f'Tâche impossible! Aucun joueur existant ou disponible dans le club {default_club}!', 'error')
        return render_template('index.html')



@app.route('/new_player/', methods=['GET', 'POST'])
def new_player():
    app.logger.debug(f'request.method: {request.method}')
    if request.method == 'POST':
        license_number = request.form['license_number']
        license_info = check_license(license_number)
        if not (request.form['first_name'] and request.form['last_name'] and request.form['birth_date'] and request.form['license_number']):
            flash('Veuillez renseigner tous les champs, svp!', 'error')
        else:
            if not license_info:
                flash('N° de license invalide!', 'error')
            else:
                lic_num, lic_letter = license_info
                existing_license = License.query.filter_by(id=lic_num).first()
                if existing_license:
                    player = Player.query.filter_by(licenseId=existing_license.id).first()
                    club = Club.query.get(player.clubId)
                    gender = Gender(existing_license.gender)
                    if gender == Gender.Male:
                        flash(f"N° de license <{lic_num} {lic_letter}> déjà utilisé par le joueur {player.name} classé {player.ranking}, âgé de {player.age} ans et licencié au club de {club.name}!", 'error')
                    else:
                        flash(f"N° de license <{lic_num} {lic_letter}> déjà utilisée par la joueuse {player.name} classée {player.ranking}, âgée de {player.age} ans et licenciée au club de {club.name}!", 'error')
                else:
                    first_name = request.form['first_name']
                    last_name = request.form['last_name']
                    birth_date: datetime = datetime.strptime(request.form['birth_date'], '%Y-%m-%d')
                    height = request.form.get('height')
                    weight = request.form.get('weight')
                    ranking_id = int(request.form['ranking'])
                    is_active = False if request.form.get('is_active') is None else True
                    gender = int(request.form['gender'])
                    club_id = request.form['club_id']
                    license = License(id=lic_num, firstName=first_name, lastName=last_name, letter=lic_letter, gender=gender, year=birth_date.year)
                    license.rankingId = ranking_id
                    db.session.add(license)
                    player = Player(birthDate=birth_date, height=weight, weight=height, isActive=is_active)
                    player.licenseId, player.clubId = license.id, club_id
                    db.session.add(player)
                    db.session.commit()
                    club = Club.query.get(player.clubId)
                    flash(f'{player.name} ajouté avec succès dans le club {club.name}!')
                    return redirect(url_for('welcome'))
    clubs = Club.query.all()
    genders = [Gender.Male.value, Gender.Female.value]
    rankings = Ranking.query.order_by(desc(Ranking.id)).all()
    app.logger.debug(f'clubs: {clubs}')
    return render_template('new_player.html', clubs=clubs, genders=genders, rankings=rankings)


@app.route('/update_player/<int:id>', methods=['GET', 'POST'])
def update_player(id):
    player: Player = Player.query.get_or_404(id)
    if request.method == 'POST':
        birth_date = request.form.get('birth_date')
        app.logger.debug(f'birthDate: {birth_date}')
        player.birthDate = datetime.strptime(birth_date, '%Y-%m-%d') if birth_date else None
        player.height = request.form.get('height')
        player.weight = request.form.get('weight')
        player.isActive = False if request.form.get('is_active') is None else True
        player.clubId = request.form.get('club_id')
        db.session.commit()
        flash(f'Infos {player.name} mises à jour avec succès!')
        return redirect(url_for('welcome'))
    else:
        clubs = Club.query.all()
        return render_template('update_player.html', player=player, clubs=clubs)


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
        championship = Championship.query.filter_by(divisionId=selected_division.id).first()
        if championship:
            flash(f"Le championnat {championship} a déjà été créé dans l'application!")
            return redirect(url_for('select_division', selected_age_category_id=selected_division.ageCategoryId))
        else:
            return render_template('new_championship.html', selected_division=selected_division)
    # Retrieve the selected age category ID from the URL parameters
    selected_age_category_id = request.args.get('selected_age_category_id')
    divisions = Division.query.filter_by(ageCategoryId=selected_age_category_id).order_by(desc(Division.type)).all()
    new_divisions = []
    for division in divisions:
        championship_with_division = Championship.query.filter_by(divisionId=division.id).first()
        if championship_with_division:
            continue
        new_divisions.append(division)
    app.logger.debug(f'divisions: {new_divisions}')
    return render_template('select_division.html', divisions=new_divisions)


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

# club/views.py
from __future__ import annotations

import itsdangerous
from flask import jsonify
from flask import current_app

from functools import wraps

from flask import request
from sqlalchemy import desc, asc, Date

from flask import render_template, redirect, url_for, flash

from models import *
from blueprints.club import club_management_bp

from common import get_players_order_by_ranking, get_championships, Gender, check_license, keys_with_same_value, calculate_distance_and_duration, \
    CatType


def check_club_cookie(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Vérifier si le cookie club_id est défini
        if 'club_id' not in request.cookies:
            # Rediriger vers la route select_club si le cookie n'est pas défini
            return redirect(url_for('admin.select_club'))
        # Sinon, exécuter la fonction de vue normalement
        return func(*args, **kwargs)

    return wrapper


@club_management_bp.route('/')
@check_club_cookie
def index():
    clubs = Club.query.all()
    # Récupérer le club_id à partir du cookie
    signed_club_id = request.cookies.get('club_id')
    current_app.logger.debug(f'index -> signed club_id: {signed_club_id}')
    if signed_club_id and clubs:
        try:
            # Vérifier et décoder le club_id signé
            club_id = current_app.serializer.loads(signed_club_id)
            current_app.logger.debug(f'signed club_id: {club_id}')
            club = Club.query.get(club_id)
            if club:
                logging.info(f'Club sélectionné: {club.name}')
                return render_template('club_index.html', club=club)
            else:
                return redirect(url_for('admin.select_club'))
        except Exception as e:
            flash("Erreur lors du décodage du cookie signé! Prière de sélectionner un club :-)", 'error')
    return redirect(url_for('admin.select_club'))


@club_management_bp.route('/select_gender', methods=['GET', 'POST'])
@check_club_cookie
def select_gender():
    if request.method == 'POST':
        gender = int(request.form['gender'])
        signed_club_id = request.cookies.get('club_id')
        try:
            club_id = current_app.serializer.loads(signed_club_id)
        except itsdangerous.exc.BadSignature:
            return redirect(url_for('admin.select_club'))
        players = get_players_order_by_ranking(gender=gender, club_id=club_id)
        club = Club.query.get(club_id)
        caption = f"Liste des { len(players) } {'joueuses' if gender == 1 else 'joueurs'} disponibles de {club.name}"
        return render_template('players.html', gender=gender, players=players, club=club, active_players=True, caption=caption)
    return render_template('select_gender.html')


@club_management_bp.route('/select_championship_new_team', methods=['GET', 'POST'])
def select_championship_new_team():
    if request.method == 'POST':
        current_app.logger.debug(f"gender = {request.form['gender']}")
        gender = int(request.form['gender'])
        championship_id = request.form['championship']
        return redirect(url_for('club.new_team', championship_id=championship_id, gender=gender))
    selected_gender = int(request.args.get('gender'))
    championships = get_championships(gender=selected_gender)
    return render_template('select_championship_new_team.html', championships=championships, gender=selected_gender)


@club_management_bp.route('/select_gender_new_team', methods=['GET', 'POST'])
def select_gender_new_team():
    if request.method == 'POST':
        gender = int(request.form['gender'])
        return redirect(url_for('club.select_championship_new_team', gender=gender))
    return render_template('select_gender_new_team.html')


@club_management_bp.route('/invalid_players')
@check_club_cookie
def show_invalid_players():
    signed_club_id = request.cookies.get('club_id')
    try:
        club_id = current_app.serializer.loads(signed_club_id)
    except itsdangerous.exc.BadSignature:
        return redirect(url_for('admin.select_club'))
    current_app.logger.debug(f'club_id: {club_id} - route: show_invalid_players')
    inactive_club_players = get_players_order_by_ranking(gender=Gender.Mixte.value, club_id=club_id, is_active=False)
    club = Club.query.get(club_id)
    current_app.logger.debug(f'invalid players: {inactive_club_players} in club {club.name}')
    caption = f"Liste des {len(inactive_club_players)} joueurs et joueuses indisponibles de {club.name}"
    return render_template('players.html', players=inactive_club_players, club=club, active_players=False, caption=caption)


@club_management_bp.route('/teams')
@check_club_cookie
def show_teams():
    signed_club_id = request.cookies.get('club_id')
    try:
        club_id = current_app.serializer.loads(signed_club_id)
    except itsdangerous.exc.BadSignature:
        return redirect(url_for('admin.select_club'))
    # teams = Team.query.order_by(desc(Team.name)).all()
    club_teams = Team.query.join(Player).filter(Player.clubId == club_id).order_by(desc(Team.name)).all()
    return render_template('teams.html', teams=club_teams)


@club_management_bp.route('/new_team/', methods=['GET', 'POST'])
@check_club_cookie
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
            championship_id = int(request.form.get('championship_id'))
            team_name = request.form.get('name')
            captain_id = request.form.get('captain_id')
            # pool = Pool.query.join(Championship).filter(Championship.id == championship_id, Pool.letter is None).first()
            pool = Pool.query.join(Championship).filter(Championship.id == championship_id).first()
            championship = Championship.query.get(championship_id)
            current_app.logger.debug(f"gender: {gender} - championship: {championship} - team_name: {team_name} - pool: {pool}")
            # Créer l'équipe avec les informations fournies
            team_players = list(players_dict.values())
            team_players.sort(key=lambda p: p.ranking_id)
            team = Team(name=team_name, captainId=int(captain_id) if captain_id else None, poolId=pool.id, players=team_players)
            db.session.add(team)
            db.session.commit()
            flash(f"L'équipe '{team.name}' a été créée avec succès avec {len(team.players)} {'joueuses' if gender else 'joueurs'} et associé au championnat {championship} "
                  f"qui a lieu du {championship.start_date} au {championship.end_date}!")
            return redirect(url_for('club.show_teams'))
    else:
        current_app.logger.debug(f"request.args GET = {request.args}")
        championship_id = int(request.args.get('championship_id'))
        gender = int(request.args.get('gender'))
        current_app.logger.debug(f"championship_id = {championship_id} - gender = {gender}")
        championship = Championship.query.get(championship_id)
        age_category = championship.division.ageCategory
        current_app.logger.debug(f"championship = {championship} - age_category = {age_category}")
        signed_club_id = request.cookies.get('club_id')
        try:
            club_id = current_app.serializer.loads(signed_club_id)
        except itsdangerous.exc.BadSignature:
            return redirect(url_for('admin.select_club'))
        active_players = get_players_order_by_ranking(gender=gender, club_id=club_id, age_category=age_category)
        current_app.logger.debug(f"{len(active_players)} players = {active_players}")
        if not active_players:
            club = Club.query.get(club_id)
            flash(f'Tâche impossible! Vous devez ajouter des joueurs dans le club {club} au préalable!', 'error')
            return render_template('index.html')
        else:
            current_app.logger.debug(f'players: {active_players}')
            current_app.logger.debug(f'request.form: {request.form}')
            max_players = min(15, len(active_players))
            return render_template('new_team.html', gender=gender, championship=championship, players=active_players, max_players=max_players, form=request.form)


@club_management_bp.route('/update_team/<int:id>', methods=['GET', 'POST'])
def update_team(id):
    team: Team = Team.query.get_or_404(id)
    current_app.logger.debug(f'team in database: {(team.id, id, team.name)} - players: {team.players}')
    players_dict = {}
    if request.method == 'POST':
        # Parcourir les données pour récupérer les noms des joueurs
        for key, value in request.form.items():
            if value and key.startswith('player_name_'):
                players_dict[key] = Player.query.get(value)
        # current_app.logger.debug(f'players_dict: {players_dict}')
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
            # current_app.logger.debug(f"request.form: {request.form}")
            team.name = request.form.get('name')
            captain_id = request.form.get('captain_id')
            team.captainId = int(captain_id) if captain_id else None
            team.players = []
            for player in players_dict.values():
                team.players.append(player)
                player.initialize_matchday_availability(team.championship)
            # team.players = list(players_dict.values())
            # current_app.logger.debug(f'{len(team.players)} players: {team.players}')
            team.pool = Pool.query.get(int(request.form.get('pool_id')))
            # current_app.logger.debug(f"Before update: (pool_id in form = {request.form.get('pool_id')}) Team {team.id} in pool {team.pool.id if team.pool else 'None'}")
            # db.session.update(team)
            db.session.commit()
            team.initialize_player_availability()
            # current_app.logger.debug(f"After update: Team {team.id} in pool {team.pool.id if team.pool else 'None'}")
            flash(f'Equipe {team.name} mise à jour avec succès!')
            return redirect(url_for('club.show_teams'))
    age_category = team.championship.division.ageCategory
    other_age_categories = []
    if age_category.type == CatType.Senior.value:
        other_age_categories = [cat for cat in AgeCategory.query.filter(AgeCategory.type == CatType.Youth.value).all() if cat.minAge >= 15 and cat.maxAge <= 18]
    # current_app.logger.debug(f"gender = {team.gender} - age_category = {age_category}")
    # signed_club_id = request.cookies.get('club_id')
    # try:
    #     club_id = current_app.serializer.loads(signed_club_id)
    # except itsdangerous.exc.BadSignature:
    #     return redirect(url_for('admin.select_club'))
    active_players = get_players_order_by_ranking(gender=team.gender, club_id=team.club.id, age_category=age_category)
    if other_age_categories:
        for cat in other_age_categories:
            active_players += get_players_order_by_ranking(gender=team.gender, club_id=team.club.id, age_category=cat)
        active_players = list(set(active_players))
    active_players.sort(key=lambda p: p.ranking)
    # current_app.logger.debug(f"{len(active_players)} players = {active_players}")
    sorted_team_players = sorted(team.players, key=lambda p: p.ranking)
    # current_app.logger.debug(f"sorted_team_players = {sorted_team_players}")
    if active_players:
        max_players = min(15, len(active_players))
        return render_template('update_team.html', team=team, sorted_team_players=sorted_team_players, players=active_players, max_players=max_players, form=request.form)
    else:
        club = Club.query.get(team.club.id)
        flash(f'Tâche impossible! Aucun joueur existant ou disponible dans le club {club}!', 'error')
        return render_template('index.html')

@club_management_bp.route('/infos_club/<int:id>', methods=['GET', 'POST'])
def infos_club(id):
    if request.method == 'GET':
        club = Club.query.get_or_404(id)
        return render_template('infos_club.html', club=club)


# Définissez la route pour afficher les détails de l'équipe
@club_management_bp.route('/show_team/<int:id>')
def show_team(id: int):
    # Récupérez l'objet de l'équipe à partir de la base de données
    team = Team.query.get(id)
    sorted_team_players = sorted(team.players, key=lambda p: p.ranking)
    # Info trajet
    signed_club_id = request.cookies.get('club_id')
    try:
        club_id = current_app.serializer.loads(signed_club_id)
        visitor_club = Club.query.get(club_id)
    except itsdangerous.exc.BadSignature:
        flash(f"Pas de club sélectionné pour les infos d'itinéraire! (aller dans 'Menu principal -> Gestion club')", 'warning')
        visitor_club = None
    except Exception as e:
        flash(f"Erreur inattendue! {e}", 'error')
        visitor_club = None
    current_app.logger.debug(f"visitor_club = {visitor_club} - home_club = {team.club}")
    if visitor_club:
        distance_obj = Distance.query.filter_by(from_club_id=visitor_club.id, to_club_id=team.club.id).first()
        if not distance_obj:
            distance, duration = calculate_distance_and_duration(visitor=visitor_club, home=team.club, api_key=current_app.config['MAPBOX_API_KEY'])
            current_app.logger.debug(f"distance = {distance} - duration = {duration}")
            distance_obj = Distance(from_club_id=visitor_club.id, to_club_id=team.club.id, distance=distance, duration=duration)
            db.session.add(distance_obj)
            db.session.commit()
        else:
            distance = distance_obj.distance
            duration = distance_obj.duration
        distance = round(distance / 1000, 1)
        elapsed_hours = duration / 3600
        elapsed_minutes = (elapsed_hours - int(elapsed_hours)) * 60
    else:
        distance = elapsed_hours = elapsed_minutes = 0
    return render_template('show_team.html', team=team, sorted_team_players=sorted_team_players,
                           visitor_club=visitor_club, distance=distance, duration=(int(elapsed_hours), round(elapsed_minutes)))


@club_management_bp.route('/save_availability/<int:team_id>', methods=['POST'])
def save_availability(team_id):
    data = request.get_json()
    availability = data.get('availability', [])
    # current_app.logger.debug(f'availability: {availability}')

    try:
        for item in availability:
            player_id = int(item['player_id'])
            date: Date = datetime.strptime(item['date'], '%Y-%m-%d').date()
            is_available = item['available']
            # current_app.logger.debug(f"player_id: {player_id} - date: {date} - is_available: {is_available}")

            # Get the player and matchday objects
            player = Player.query.get_or_404(player_id)
            matchday = Matchday.query.filter_by(date=date).first()

            if not matchday:
                current_app.logger.warning(f"No matchday found for date: {date}")
                continue

            # Check if relationship already exists
            existing_availability = PlayerMatchdayAvailability.query.filter_by(
                player_id=player_id,
                matchday_id=matchday.id
            ).first()

            if existing_availability:
                # Update existing relationship
                existing_availability.is_available = is_available
                existing_availability.updated_at = datetime.utcnow()
            else:
                # Create new relationship
                new_availability = PlayerMatchdayAvailability(
                    player_id=player_id,
                    matchday_id=matchday.id,
                    is_available=is_available
                )
                db.session.add(new_availability)

        # Check available players for each matchday before committing
        matchdays_with_issues = []
        team = Team.query.get_or_404(team_id)

        # Get unique dates from the availability data
        unique_dates = set(datetime.strptime(item['date'], '%Y-%m-%d').date()
                          for item in availability)

        current_app.logger.debug(f"unique_dates: {unique_dates}")

        for date in unique_dates:
            matchday = Matchday.query.filter_by(date=date).first()
            current_app.logger.debug(f"matchday: {matchday}")
            if matchday:
                available_players = team.get_available_players(matchday)
                # We need at least singles_count * 2 players (2 players per singles match)
                min_players_needed = matchday.singles_count
                current_app.logger.debug(f"min_players_needed = {min_players_needed} - available_players_count: {len(available_players)}")

                if len(available_players) < min_players_needed:
                    matchdays_with_issues.append({
                        'date': date.strftime('%Y-%m-%d'),
                        'available_players': len(available_players),
                        'required_players': min_players_needed
                    })

        current_app.logger.debug(f"matchdays_with_issues: {matchdays_with_issues}")

        if matchdays_with_issues:
            db.session.rollback()
            return jsonify({
                'success': False,
                'error': 'insufficient_players',
                'details': '\n'.join([str(m) for m in matchdays_with_issues])
            }), 400

        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})


@club_management_bp.route('/new_player/', methods=['GET', 'POST'])
def new_player():
    current_app.logger.debug(f'request.method: {request.method}')
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
                        flash(
                            f"N° de license <{lic_num} {lic_letter}> déjà utilisé par le joueur {player.name} classé {player.ranking}, âgé de {player.age} ans et licencié au club de {club.name}!",
                            'error')
                    else:
                        flash(
                            f"N° de license <{lic_num} {lic_letter}> déjà utilisée par la joueuse {player.name} classée {player.ranking}, âgée de {player.age} ans et licenciée au club de {club.name}!",
                            'error')
                else:
                    first_name = request.form['first_name']
                    last_name = request.form['last_name']
                    birth_date: datetime = datetime.strptime(request.form['birth_date'], '%Y-%m-%d')
                    height = request.form.get('height')
                    weight = request.form.get('weight')
                    ranking_id = int(request.form['ranking'])
                    is_active = False if request.form.get('is_active') is None else True
                    gender = int(request.form['gender'])
                    # club_id = request.form['club_id']
                    signed_club_id = request.cookies.get('club_id')
                    club_id = current_app.serializer.loads(signed_club_id)
                    license = License(id=lic_num, firstName=first_name, lastName=last_name, letter=lic_letter, gender=gender, year=birth_date.year)
                    license.rankingId = ranking_id
                    db.session.add(license)
                    player = Player(birthDate=birth_date, height=weight, weight=height, isActive=is_active)
                    player.licenseId, player.clubId = license.id, club_id
                    db.session.add(player)
                    db.session.commit()
                    club = Club.query.get(player.clubId)
                    flash(f'{player.name} ajouté avec succès dans le club {club.name}!')
                    return redirect(url_for('club.index'))
    signed_club_id = request.cookies.get('club_id')
    try:
        club_id = current_app.serializer.loads(signed_club_id)
        current_app.logger.debug(f"club_id: {club_id}")
    except itsdangerous.exc.BadSignature:
        return redirect(url_for('admin.select_club'))
    club = Club.query.get(club_id)
    genders = [Gender.Male.value, Gender.Female.value]
    rankings = Ranking.query.order_by(desc(Ranking.id)).all()
    return render_template('new_player.html', club=club, genders=genders, rankings=rankings)


@club_management_bp.route('/update_player/<int:id>', methods=['GET', 'POST'])
def update_player(id):
    player: Player = Player.query.get_or_404(id)
    if request.method == 'POST':
        birth_date = request.form.get('birth_date')
        current_app.logger.debug(f'birthDate: {birth_date}')
        player.birthDate = datetime.strptime(birth_date, '%Y-%m-%d') if birth_date else None
        player.height = request.form.get('height')
        player.weight = request.form.get('weight')
        license = License.query.get(player.licenseId)
        license.rankingId = int(request.form['ranking'])
        license.bestRankingId = int(request.form['best_ranking'])
        db.session.add(license)
        # db.session.add(license)
        current_app.logger.debug(f'license best ranking: {license.bestRanking}')
        player.isActive = False if request.form.get('is_active') is None else True
        # Récupérez les valeurs sélectionnées dans le formulaire
        selected_injuries = request.form.getlist('injuries[]')
        current_app.logger.debug(f'selected_injuries: {selected_injuries}')
        # Mettez à jour les blessures du joueur
        player.injuries = []
        db.session.add(player)
        for injury_id in selected_injuries:
            injury = Injury.query.get(injury_id)
            if injury:  # Vérifiez si l'ID de la blessure est valide
                player.injuries.append(injury)
        db.session.commit()
        flash(f'Infos {player.name} mises à jour avec succès!')
        return redirect(url_for('medical.index'))
    else:
        # signed_club_id = request.cookies.get('club_id')
        # try:
        #     club_id = current_app.serializer.loads(signed_club_id)
        # except itsdangerous.exc.BadSignature:
        #     return redirect(url_for('admin.select_club'))
        # club_id = current_app.serializer.loads(signed_club_id)
        # club = Club.query.get(club_id)
        injuries = Injury.query.join(InjurySite).order_by(asc(InjurySite.name), asc(Injury.type), asc(Injury.name)).all()
        rankings = Ranking.query.order_by(desc(Ranking.id))
        bestRankings = BestRanking.query.order_by(desc(BestRanking.id))
        return render_template('update_player.html', player=player, injuries=injuries, rankings=rankings, best_rankings=bestRankings)

@club_management_bp.route('/player/<int:id>')
def show_player(id):
    return render_template('show_player.html', player=Player.query.get_or_404(id))

@club_management_bp.route('/delete_player/<int:id>', methods=['GET', 'POST'])
def delete_player(id):
    if request.method == 'GET':
        player = Player.query.get_or_404(id)
        current_app.logger.debug(f'Joueur {player} supprimé!')
        db.session.delete(player)
        db.session.commit()
        current_app.logger.debug(f'Joueur {player} supprimé!')
        club = Club.query.get(player.clubId)
        flash(f"Joueur \"{player.name}\" ne fait plus partie du club {club}!")
        return redirect(url_for('club.index'))


@club_management_bp.route('/delete_team/<int:id>', methods=['GET', 'POST'])
def delete_team(id):
    if request.method == 'GET':
        team = Team.query.get_or_404(id)
        db.session.delete(team)
        db.session.commit()
        current_app.logger.debug(f'Equipe {team} supprimé!')
        flash(f"L'équipe \"{team.name}\" ne fait plus partie du club {team.club}!")
        return redirect(url_for('club.show_teams'))

# @club_management_bp.route('/map_data')
# def map_data():
#     # Utilisez la clé API Mapbox stockée côté serveur
#     api_key = current_app.config['MAPBOX_API_KEY']
#
#     # Faites une requête à l'API Mapbox pour obtenir les données de carte
#     # Exemple de requête fictive
#     response = requests.get(f'https://api.mapbox.com/some_endpoint?access_token={api_key}')
#
#     # Traitez la réponse de l'API Mapbox comme requis
#     map_data = response.json()
#
#     return jsonify(map_data)

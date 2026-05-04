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
    CatType, update_players


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
        return render_template('players.html', gender=gender, players=players, club=club, active_players=True, caption=caption, sort_criteria='ranking_id')
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
    return render_template('players.html', players=inactive_club_players, club=club, active_players=False, caption=caption, sort_criteria='ranking_id')


@club_management_bp.route('/teams')
@check_club_cookie
def show_teams():
    signed_club_id = request.cookies.get('club_id')
    current_season = AppSettings.get_season()
    try:
        club_id = current_app.serializer.loads(signed_club_id)
    except itsdangerous.exc.BadSignature:
        return redirect(url_for('admin.select_club'))
    # teams = Team.query.order_by(desc(Team.name)).all()
    # club_teams = Team.query.join(Player).filter(Player.clubId == club_id).order_by(desc(Team.name)).all()
    # jointure interne vers Pool + Championship pour les équipes bien associées
    teams = Team.query.filter(Team.clubId == club_id, Championship.season == current_season).join(Pool).join(Championship).all()
    # all_club_teams = Team.query.filter(Team.clubId == club_id).all()
    # for t in all_club_teams:
    #     current_app.logger.debug(f"Team #{t.id}: {t.name} - poolId: {t.poolId} - championship's season: {getattr(t.pool.championship, 'season', None)}")
    return render_template('teams.html', teams=teams)


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

        # Helper pour réafficher le formulaire avec les données actuelles
        def _redisplay_form(error_msg):
            flash(error_msg, 'error')
            championship_id = int(request.form.get('championship_id'))
            gender = int(request.form.get('gender', 0))
            championship = Championship.query.get(championship_id)
            signed_club_id = request.cookies.get('club_id')
            try:
                club_id = current_app.serializer.loads(signed_club_id)
            except itsdangerous.exc.BadSignature:
                return redirect(url_for('admin.select_club'))
            age_category = championship.division.ageCategory
            active_players = get_players_order_by_ranking(gender=gender, club_id=club_id, age_category=age_category)
            max_players = min(15, len(active_players))
            return render_template('new_team.html', gender=gender, championship=championship,
                                   players=active_players, max_players=max_players, form=request.form)

        if not request.form.get('name'):
            return _redisplay_form('Veuillez renseigner tous les champs, svp!')
        elif duplicates:
            msg = (f'Le joueur {duplicates[0]} est en doublon, veuillez en sélectionner un autre!'
                   if len(duplicates) == 1
                   else f'Les joueurs {duplicates} sont en doublons, veuillez en sélectionner d\'autres!')
            return _redisplay_form(msg)
        else:
            # Récupérer les données du formulaire
            gender = int(request.form['gender'])
            championship_id = int(request.form.get('championship_id'))
            team_name = request.form.get('name')
            captain_id = request.form.get('captain_id')
            pool = Pool.query.join(Championship).filter(Championship.id == championship_id).first()
            championship = Championship.query.get(championship_id)
            current_app.logger.debug(f"gender: {gender} - championship: {championship} - team_name: {team_name} - pool: {pool}")
            # Récupérer le club_id depuis le cookie
            signed_club_id = request.cookies.get('club_id')
            try:
                club_id = current_app.serializer.loads(signed_club_id)
            except itsdangerous.exc.BadSignature:
                return redirect(url_for('admin.select_club'))
            # Créer l'équipe avec les informations fournies
            team_players = list(players_dict.values())
            team_players.sort(key=lambda p: p.ranking_id)
            team = Team(name=team_name, captainId=int(captain_id) if captain_id else None,
                        poolId=pool.id, clubId=club_id, players=team_players)
            db.session.add(team)
            db.session.commit()
            flash(f"L'équipe '{team.name}' a été créée avec succès avec {len(team.players)} "
                  f"{'joueuses' if gender else 'joueurs'} et associée au championnat {championship} "
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
            return render_template('new_team.html', gender=gender, championship=championship,
                                   players=active_players, max_players=max_players, form=request.form)


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
        # Permettre l'ajout de joueurs U13 et plus dans les équipes Seniors
        other_age_categories = [cat for cat in AgeCategory.query.filter(AgeCategory.type == CatType.Youth.value).all() if cat.minAge >= 13 and cat.maxAge <= 18]
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
    active_players.sort(key=lambda p: p.ranking.id)
    # current_app.logger.debug(f"{len(active_players)} players = {active_players}")
    sorted_team_players = sorted(team.players, key=lambda p: p.ranking.id)
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
    sorted_team_players = sorted(team.players, key=lambda p: p.ranking.id)
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
    # Joueurs du club non dans l'équipe (candidats jokers), même genre
    team_player_ids = {p.id for p in team.players}
    singles_count = team.championship.singlesCount if team.championship else 4

    # Dernier joueur brûlé = le N-ième joueur de la liste nominative classée
    # (les N premiers sont "brûlés", le joker ne peut pas être meilleur que le dernier)
    last_burned = sorted_team_players[singles_count - 1] if len(sorted_team_players) >= singles_count else None
    burned_ranking_id = last_burned.ranking.id if last_burned else None  # id plus grand = moins bon classement

    joker_query = Player.query.join(Player.license).filter(
        Player.clubId == team.club.id,
        License.gender == team.gender,
        ~Player.id.in_(team_player_ids)
    )
    if burned_ranking_id is not None:
        # Garder uniquement les joueurs dont le classement est >= au dernier brûlé
        # (ranking.id plus élevé = classement moins bon → joker ne peut pas être meilleur)
        joker_query = joker_query.filter(License.rankingId >= burned_ranking_id)

    joker_candidates = joker_query.order_by(License.rankingId).all()

    # Jokers actuels par journée {matchday_id: {player, plays_single, plays_double}}
    current_jokers = {
        j.matchday_id: {
            'player':       j.player,
            'plays_single': j.plays_single,
            'plays_double': j.plays_double,
        }
        for j in team.jokers if j.player
    }

    # Construire avail_map : {player_id: {matchday_id: PlayerMatchdayAvailability}}
    # pour éviter le bug Jinja dict.update() qui retourne None
    match_day_ids = {md.id for md in team.match_days}
    avail_map = {}
    for player in team.players:
        avail_map[player.id] = {
            a.matchday_id: a
            for a in player.matchday_availabilities
            if a.matchday_id in match_day_ids
        }

    return render_template('show_team.html', team=team, sorted_team_players=sorted_team_players,
                           visitor_club=visitor_club, distance=distance,
                           duration=(int(elapsed_hours), round(elapsed_minutes)),
                           joker_candidates=joker_candidates,
                           current_jokers=current_jokers,
                           last_burned=last_burned,
                           singles_count=singles_count,
                           avail_map=avail_map)


@club_management_bp.route('/save_joker/<int:team_id>', methods=['POST'])
def save_joker(team_id):
    """Enregistre ou supprime le joueur joker d'une équipe pour une journée donnée."""
    team = Team.query.get_or_404(team_id)
    data = request.get_json()
    matchday_id  = data.get('matchday_id')
    player_id    = data.get('player_id')   # None = suppression du joker
    plays_single = bool(data.get('plays_single', False))
    plays_double = bool(data.get('plays_double', False))

    try:
        existing = TeamMatchdayJoker.query.filter_by(
            team_id=team_id, matchday_id=matchday_id
        ).first()

        if player_id:
            player_id = int(player_id)
            # Vérifier que le joueur n'est pas déjà dans l'équipe
            if any(p.id == player_id for p in team.players):
                return jsonify({'success': False,
                                'error': 'Ce joueur est déjà dans la liste nominative de l\'équipe.'}), 400
            # Vérifier la règle de classement : le joker ne peut pas être meilleur que le dernier brûlé
            singles_count = team.championship.singlesCount if team.championship else 4
            sorted_players = sorted(team.players, key=lambda p: p.ranking.id)
            if len(sorted_players) >= singles_count:
                last_burned = sorted_players[singles_count - 1]
                joker_player = Player.query.get(player_id)
                if joker_player and joker_player.ranking.id < last_burned.ranking.id:
                    return jsonify({
                        'success': False,
                        'error': f'Le joker ({joker_player.ranking}) ne peut pas être meilleur '
                                 f'que le {singles_count}e joueur brûlé ({last_burned.name} – {last_burned.ranking}).'
                    }), 400
            if existing:
                existing.player_id    = player_id
                existing.plays_single = plays_single
                existing.plays_double = plays_double
            else:
                db.session.add(TeamMatchdayJoker(
                    team_id=team_id, matchday_id=matchday_id, player_id=player_id,
                    plays_single=plays_single, plays_double=plays_double
                ))
        else:
            # Suppression du joker
            if existing:
                db.session.delete(existing)

        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@club_management_bp.route('/save_availability/<int:team_id>', methods=['POST'])
def save_availability(team_id):
    data = request.get_json()
    availability = data.get('availability', [])

    try:
        for item in availability:
            player_id     = int(item['player_id'])
            date          = datetime.strptime(item['date'], '%Y-%m-%d').date()
            is_available  = item.get('available', False)
            plays_single  = item.get('plays_single', False)
            plays_double  = item.get('plays_double', False)
            is_substitute = item.get('is_substitute', False)

            Player.query.get_or_404(player_id)
            # Chercher la journée correspondant à la date ET au championnat de l'équipe
            team = Team.query.get_or_404(team_id)
            matchday = Matchday.query.filter(
                Matchday.date == date,
                Matchday.championshipId == team.championship.id
            ).first()
            if not matchday:
                current_app.logger.warning(f"Aucune journée trouvée pour date={date} championnat={team.championship.id}")
                continue

            existing = PlayerMatchdayAvailability.query.filter_by(
                player_id=player_id, matchday_id=matchday.id
            ).first()
            if existing:
                existing.is_available  = is_available
                existing.plays_single  = plays_single
                existing.plays_double  = plays_double
                existing.is_substitute = is_substitute
                existing.updated_at    = datetime.utcnow()
            else:
                db.session.add(PlayerMatchdayAvailability(
                    player_id=player_id,
                    matchday_id=matchday.id,
                    is_available=is_available,
                    plays_single=plays_single,
                    plays_double=plays_double,
                    is_substitute=is_substitute,
                ))

        # Commit d'abord — les sélections sont toujours sauvegardées
        db.session.commit()

        # Vérification informative (non bloquante) du nombre minimum de joueurs en simple
        team = Team.query.get_or_404(team_id)
        unique_dates = {datetime.strptime(item['date'], '%Y-%m-%d').date() for item in availability}
        warnings = []
        for date in unique_dates:
            matchday = Matchday.query.filter(
                Matchday.date == date,
                Matchday.championshipId == team.championship.id
            ).first()
            if matchday:
                needed = matchday.singles_count
                # Joueurs nominatifs de l'équipe en simple
                nb_singles = PlayerMatchdayAvailability.query.filter_by(
                    matchday_id=matchday.id, plays_single=True
                ).filter(PlayerMatchdayAvailability.player_id.in_(
                    [p.id for p in team.players]
                )).count()
                # Ajouter le joueur joker s'il est sélectionné en simple pour cette journée
                joker_entry = TeamMatchdayJoker.query.filter_by(
                    team_id=team_id, matchday_id=matchday.id
                ).first()
                if joker_entry and joker_entry.player_id and joker_entry.plays_single:
                    nb_singles += 1
                if nb_singles < needed:
                    warnings.append(
                        f"{date.strftime('%d/%m/%Y')} : {nb_singles}/{needed} joueur(s) sélectionné(s) en simple"
                    )

        return jsonify({'success': True, 'warnings': warnings})

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"save_availability error: {e}")
        return jsonify({'success': False, 'error': str(e)})


@club_management_bp.route('/update_players', methods=['GET', 'POST'])
@check_club_cookie
def update_players_route():
    signed_club_id = request.cookies.get('club_id')
    try:
        club_id = current_app.serializer.loads(signed_club_id)
    except itsdangerous.exc.BadSignature:
        return redirect(url_for('admin.select_club'))
    club = Club.query.get(club_id)

    if request.method == 'POST':
        import tempfile, os

        # Sauvegarder les fichiers uploadés dans des fichiers temporaires
        tmp_paths = {}
        for gender, gender_label in enumerate(['men', 'women']):
            file_key = f'csv_{gender_label}'
            uploaded_file = request.files.get(file_key)
            if uploaded_file and uploaded_file.filename != '':
                with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as tmp:
                    uploaded_file.save(tmp.name)
                    tmp_paths[gender] = tmp.name

        if not tmp_paths:
            flash("Aucun fichier CSV fourni.", 'error')
            return render_template('update_players.html', club=club)

        all_conflicts = []
        all_deleted = []
        total_updated = 0
        messages = []

        try:
            for gender, tmp_path in tmp_paths.items():
                success, conflicts, deleted_players, updated_count = update_players(
                    app=current_app, gender=gender, csvfile=tmp_path, club=club, db=db
                )
                all_conflicts.extend(conflicts)
                all_deleted.extend(deleted_players)
                total_updated += updated_count
                label = 'joueuses' if gender else 'joueurs'
                messages.append(f"{updated_count} {label} mis à jour.")
        finally:
            for tmp_path in tmp_paths.values():
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass

        msg = ' '.join(messages)
        if all_conflicts:
            msg += f" {len(all_conflicts)} conflit(s) détecté(s)."
        if all_deleted:
            msg += f" {len(all_deleted)} joueur(s) supprimé(s) (absents du CSV)."
        flash(msg, 'success' if not all_conflicts else 'warning')
        return render_template(
            'update_players_result.html',
            club=club,
            conflicts=all_conflicts,
            deleted_players=all_deleted,
            total_updated=total_updated
        )

    return render_template('update_players.html', club=club)


@club_management_bp.route('/transfer_player', methods=['POST'])
@check_club_cookie
def transfer_player():
    """Transfère un ou plusieurs joueurs en conflit vers leur nouveau club."""
    import json
    # Les données sont envoyées sous forme de liste JSON via le champ 'transfers'
    transfers_json = request.form.get('transfers', '[]')
    try:
        transfers = json.loads(transfers_json)
    except ValueError:
        flash("Données invalides.", 'error')
        return redirect(url_for('club.index'))

    if not transfers:
        flash("Aucun joueur sélectionné.", 'warning')
        return redirect(request.referrer or url_for('club.index'))

    done = []
    errors = []
    for t in transfers:
        license_id   = t.get('license_id')
        new_club_id  = t.get('new_club_id')
        ranking_id   = t.get('ranking_id')
        best_ranking_id = t.get('best_ranking_id')

        lic = License.query.get(license_id)
        player = Player.query.filter_by(licenseId=license_id).first() if lic else None
        new_club = Club.query.get(new_club_id)

        if not lic or not player or not new_club:
            errors.append(f"Licence {license_id} introuvable.")
            continue

        old_club = Club.query.get(player.clubId)
        old_club_name = old_club.name if old_club else 'inconnu'
        player.clubId = new_club.id
        if ranking_id:
            lic.rankingId = ranking_id
        if best_ranking_id:
            lic.bestRankingId = best_ranking_id
        db.session.add(player)
        db.session.add(lic)
        done.append(f"{lic.firstName} {lic.lastName} ({old_club_name} → {new_club.name})")

    db.session.commit()

    if done:
        flash(f"✅ {len(done)} transfert(s) effectué(s) : {', '.join(done)}.", 'success')
    for err in errors:
        flash(err, 'error')

    return redirect(request.referrer or url_for('club.index'))


@club_management_bp.route('/new_player/', methods=['GET', 'POST'])
def new_player():
    current_app.logger.debug(f'request.method: {request.method}')
    if request.method == 'POST':
        license_number = request.form['license_number']
        license_info = check_license(license_number)
        if not (request.form['first_name'] and request.form['last_name'] and request.form['birth_date'] and request.form['license_number'] and request.form.get('ranking') and request.form.get('best_ranking')):
            flash('Veuillez renseigner tous les champs obligatoires, svp!', 'error')
        else:
            if not license_info:
                flash('N° de license invalide!', 'error')
            else:
                lic_num, lic_letter = license_info
                first_name = request.form['first_name']
                last_name = request.form['last_name']
                birth_date = datetime.strptime(request.form['birth_date'], '%Y-%m-%d')
                gender = int(request.form['gender'])
                ranking_id = int(request.form['ranking'])
                best_ranking_id = int(request.form['best_ranking'])
                weight = request.form.get('weight')
                height = request.form.get('height')
                is_active = False if request.form.get('is_active') is None else True
                signed_club_id = request.cookies.get('club_id')
                club_id = current_app.serializer.loads(signed_club_id)
                existing_license = License.query.filter_by(id=lic_num).first()
                if existing_license:
                    # Utiliser la licence existante
                    license = existing_license
                else:
                    license = License(id=lic_num, firstName=first_name, lastName=last_name, letter=lic_letter, gender=gender, year=birth_date.year)
                    license.rankingId = ranking_id
                    license.bestRankingId = best_ranking_id
                    db.session.add(license)
                player = Player(birthDate=birth_date, height=height, weight=weight, isActive=is_active)
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
    best_rankings = BestRanking.query.order_by(desc(BestRanking.id)).all()
    return render_template('new_player.html', club=club, genders=genders, rankings=rankings, best_rankings=best_rankings)


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
        club = Club.query.get(player.clubId)
        player_name = player.name

        # Nullifier les références dans Single (simples) sans supprimer les résultats
        Single.query.filter(Single.player1Id == id).update({'player1Id': None})
        Single.query.filter(Single.player2Id == id).update({'player2Id': None})

        # Nullifier les références dans Double sans supprimer les résultats
        Double.query.filter(Double.player1Id == id).update({'player1Id': None})
        Double.query.filter(Double.player2Id == id).update({'player2Id': None})
        Double.query.filter(Double.player3Id == id).update({'player3Id': None})
        Double.query.filter(Double.player4Id == id).update({'player4Id': None})

        # Nullifier le capitaine d'équipe si nécessaire
        Team.query.filter(Team.captainId == id).update({'captainId': None})

        db.session.delete(player)
        db.session.commit()

        current_app.logger.debug(f'Joueur {player_name} supprimé (Single/Double/Captain nullifiés).')
        flash(f'Joueur "{player_name}" supprimé du club {club}.', 'success')
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

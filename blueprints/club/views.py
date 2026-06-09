# club/views.py
from __future__ import annotations

import itsdangerous
from flask import jsonify
from flask import current_app

from functools import wraps

from flask import request
from sqlalchemy import desc, asc, Date

from flask import render_template, redirect, url_for, flash

from datetime import date as date_type

from models import *
from blueprints.club import club_management_bp
from blueprints.shop.models import Racquet

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

@club_management_bp.route('/delete_team/<int:id>', methods=['GET'])
def delete_team(id):
    team = Team.query.get_or_404(id)
    team_name = team.name
    # Supprimer les associations joueurs, jokers, disponibilités
    team.players = []
    TeamMatchdayJoker.query.filter_by(team_id=id).delete()
    # Nullifier les références dans les matchs (sans supprimer les résultats)
    Match.query.filter_by(homeTeamId=id).update({'homeTeamId': None})
    Match.query.filter_by(visitorTeamId=id).update({'visitorTeamId': None})
    db.session.delete(team)
    db.session.commit()
    flash(f"Équipe « {team_name} » supprimée avec succès.")
    return redirect(url_for('club.show_teams'))


@club_management_bp.route('/infos_club/<int:id>', methods=['GET', 'POST'])
def infos_club(id):
    if request.method == 'GET':
        club = Club.query.get_or_404(id)
        return render_template('infos_club.html', club=club)


# Définissez la route pour afficher les détails de l'équipe
@club_management_bp.route('/show_team/<int:id>')
def show_team(id: int):
    # Charger l'équipe avec les relations nécessaires en eager-loading pour éviter les N+1
    from sqlalchemy.orm import joinedload, subqueryload
    import time
    start_total = time.perf_counter()
    current_app.logger.debug(f"show_team start for team={id}")
    # Use a consistent loader for Team.players (subqueryload) and apply nested loaders
    team = (
        Team.query
        .options(
            # Load players via subquery to avoid row explosion, then eager-load nested relations
            subqueryload(Team.players).joinedload(Player.license).joinedload(License.ranking),
            subqueryload(Team.players).joinedload(Player.license).joinedload(License.bestRanking),
            subqueryload(Team.players).subqueryload(Player.racquet_history).joinedload(PlayerRacquet.racquet),
            subqueryload(Team.players).subqueryload(Player.matchday_availabilities),
        )
        .get(id)
    )
    t0 = time.perf_counter()
    current_app.logger.debug(f"loaded team in {t0 - start_total:.3f}s")
    # Utiliser ranking via la licence déjà préchargée pour éviter des requêtes supplémentaires
    sorted_team_players = sorted(team.players, key=lambda p: p.license.rankingId if p.license and p.license.rankingId else 0)
    t1 = time.perf_counter()
    current_app.logger.debug(f"sorted players in {t1 - t0:.3f}s (players={len(team.players)})")
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
    burned_ranking_id = last_burned.license.rankingId if last_burned and last_burned.license else None  # id plus grand = moins bon classement

    joker_query = Player.query.join(Player.license).filter(
        Player.clubId == team.club.id,
        License.gender == team.gender,
        ~Player.id.in_(team_player_ids)
    )
    if burned_ranking_id is not None:
        # Garder uniquement les joueurs dont le classement est >= au dernier brûlé
        # (ranking.id plus élevé = classement moins bon → joker ne peut pas être meilleur)
        joker_query = joker_query.filter(License.rankingId >= burned_ranking_id)

    # Limit candidates returned to avoid huge template rendering cost when clubs have many players
    MAX_JOKER_CANDIDATES = 200
    joker_candidates_all = joker_query.order_by(License.rankingId)
    joker_candidates = joker_candidates_all.limit(MAX_JOKER_CANDIDATES).all()
    joker_truncated = joker_candidates_all.count() > MAX_JOKER_CANDIDATES
    t2 = time.perf_counter()
    current_app.logger.debug(f"joker candidates query in {t2 - t1:.3f}s -> {len(joker_candidates)} candidates (truncated={joker_truncated})")

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

    # Tooltip raquette/cordage pour affichage au survol du nom joueur
    racquet_tooltips = {}
    current_racquets = {}
    for player in sorted_team_players:
        # chercher l'entrée is_playing dans l'historique (déjà chargé)
        playing_entry = None
        if getattr(player, 'racquet_history', None):
            for e in sorted(player.racquet_history, key=lambda x: x.updated_at or x.created_at or datetime.min, reverse=True):
                if e.is_playing:
                    playing_entry = e
                    break

        racquet_label = 'Non renseignee'
        if playing_entry and playing_entry.racquet:
            racquet_label = f'{playing_entry.racquet.brand} {playing_entry.racquet.name}'
        elif player.racquet:
            racquet_label = f'{player.racquet.brand} {player.racquet.name}'

        string_label = 'Non renseigne'
        if playing_entry and playing_entry.string_name:
            string_label = playing_entry.string_name

        tension_label = ''
        if playing_entry and playing_entry.string_tension is not None:
            tension_label = f' ({playing_entry.string_tension} kg)'

        racquet_tooltips[player.id] = f'Raquette: {racquet_label} | Cordage: {string_label}{tension_label}'
        current_racquets[player.id] = {
            'racquet': racquet_label,
            'string': f'{string_label}{tension_label}' if string_label != 'Non renseigne' else '—',
        }
    t3 = time.perf_counter()
    current_app.logger.debug(f"built racquet tooltips in {t3 - t2:.3f}s")

    t_render_start = time.perf_counter()
    resp = render_template('show_team.html', team=team, sorted_team_players=sorted_team_players,
                           visitor_club=visitor_club, distance=distance,
                           duration=(int(elapsed_hours), round(elapsed_minutes)),
                           joker_candidates=joker_candidates,
                           current_jokers=current_jokers,
                           last_burned=last_burned,
                           burned_ranking_id=burned_ranking_id,
                           singles_count=singles_count,
                           avail_map=avail_map,
                           racquet_tooltips=racquet_tooltips,
                           current_racquets=current_racquets)
    t_render_end = time.perf_counter()
    total = t_render_end - start_total
    current_app.logger.debug(f"render_template in {t_render_end - t_render_start:.3f}s, total show_team {total:.3f}s")
    return resp


@club_management_bp.route('/_joker_candidates')
def joker_candidates_api():
    """API JSON pour chercher des candidats jokers filtrés par nom/q et limit.
    Params: team_id (obligatoire), q (optionnel), limit (optionnel)
    """
    team_id = request.args.get('team_id')
    if not team_id:
        return jsonify({'error': 'team_id required'}), 400
    try:
        team = Team.query.get(int(team_id))
    except Exception:
        return jsonify({'error': 'invalid team_id'}), 400

    q = (request.args.get('q') or '').strip()
    limit = int(request.args.get('limit') or 50)

    # Build a single optimized SQL query applying age-category and burned filters server-side
    from sqlalchemy import func
    q_param = q
    limit = int(limit)

    # Base query with single join to License (avoid duplicate joins)
    joker_query = Player.query.join(Player.license).filter(
        Player.clubId == team.club.id,
        License.gender == team.gender,
        ~Player.id.in_({p.id for p in team.players})
    )

    # burned_ranking_id can be provided to reproduce same restriction
    burned = request.args.get('burned_ranking_id')
    if burned:
        try:
            burned_ranking_id = int(burned)
            joker_query = joker_query.filter(License.rankingId >= burned_ranking_id)
        except Exception:
            pass

    # Filter by championship age category using SQL (birthDate bounds)
    try:
        champ = team.pool.championship if team.pool else None
        if not champ:
            champ = team.championship
        if champ and champ.division and champ.division.ageCategory:
            ac = champ.division.ageCategory
            from datetime import datetime, date
            today = datetime.now().date()
            max_birth_date = date(today.year - ac.minAge, 12, 31)
            min_birth_date = date(today.year - ac.maxAge, 1, 1)
            joker_query = joker_query.filter(Player.birthDate <= max_birth_date, Player.birthDate >= min_birth_date)
    except Exception:
        # on any error, don't filter by age
        pass

    if q_param:
        joker_query = joker_query.filter(
            func.lower(License.lastName).like(f'%{q_param.lower()}%') | func.lower(License.firstName).like(f'%{q_param.lower()}%')
        )

    # obtain results from DB
    results = joker_query.order_by(License.rankingId).limit(limit).all()
    # Diagnostic logging: burned value, age category and returned ranking_ids
    try:
        current_app.logger.debug(f"_joker_candidates: team={team.id} burned={burned} ageCategory={getattr(getattr(champ, 'division', None), 'ageCategory', None)} db_count={len(results)}")
        sample_ranks = [getattr(getattr(p, 'license', None), 'rankingId', None) for p in results]
        current_app.logger.debug(f"_joker_candidates: ranking_ids(returned)={sample_ranks}")
    except Exception:
        pass
    out = []
    # Defensive filter: ensure no player better (ranking_id smaller) than burned_ranking_id is returned
    if burned:
        try:
            burned_ranking_id = int(burned)
            results = [p for p in results if (getattr(getattr(p, 'license', None), 'rankingId', None) is None) or (getattr(getattr(p, 'license', None), 'rankingId', 0) >= burned_ranking_id)]
        except Exception:
            pass

    # Log after defensive filtering
    try:
        post_sample = [getattr(getattr(p, 'license', None), 'rankingId', None) for p in results]
        current_app.logger.debug(f"_joker_candidates after defensive filter: count={len(results)} ranking_ids={post_sample}")
    except Exception:
        pass

    for p in results:
        out.append({'id': p.id, 'name': p.name, 'ranking': str(p.ranking), 'ranking_id': getattr(getattr(p, 'license', None), 'rankingId', None)})
    # If app is in debug mode, include diagnostic info in the response to help tracing in browser
    resp = {'results': out}
    try:
        if current_app.debug:
            resp['_debug'] = {
                'team_id': team.id,
                'burned_param': burned,
                'returned_count': len(out),
            }
    except Exception:
        pass
    return jsonify(resp)


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
            # Utiliser rankingId (champ de la licence) pour éviter des requêtes supplémentaires
            singles_count = team.championship.singlesCount if team.championship else 4
            # trier par rankingId (id plus grand = classement moins bon)
            sorted_players = sorted(team.players, key=lambda p: (p.license.rankingId if p.license else 0))
            if len(sorted_players) >= singles_count:
                last_burned = sorted_players[singles_count - 1]
                joker_player = Player.query.get(player_id)
                # si l'un des joueurs n'a pas de licence / ranking, refuser pour sécurité
                if joker_player and joker_player.license and last_burned.license:
                    joker_rank_id = joker_player.license.rankingId
                    burned_rank_id = last_burned.license.rankingId
                    # joker_rank_id plus petit => meilleur classement -> interdit
                    if joker_rank_id < burned_rank_id:
                        return jsonify({
                            'success': False,
                            'error': f'Le joker ({joker_player.ranking}) ne peut pas être meilleur '
                                     f'que le {singles_count}e joueur brûlé ({last_burned.name} – {last_burned.ranking}).'
                        }), 400
                else:
                    return jsonify({'success': False, 'error': 'Impossible de vérifier le classement du joker (licence manquante).'}), 400
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
                racquet_id = request.form.get('racquet_id')
                if racquet_id:
                    player.racquet_id = int(racquet_id)
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
    racquets = Racquet.query.order_by(Racquet.is_current.desc(), Racquet.brand, Racquet.name).all()
    return render_template('new_player.html', club=club, genders=genders, rankings=rankings, best_rankings=best_rankings, racquets=racquets)


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
        back_url = request.form.get('back_url') or url_for('club.show_player', id=id)
        return redirect(back_url)
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
        back_url = request.args.get('back') or request.referrer or url_for('club.index')
        return render_template('update_player.html', player=player, injuries=injuries, rankings=rankings, best_rankings=bestRankings, back_url=back_url)

@club_management_bp.route('/player/<int:id>')
def show_player(id):
    back_url = request.args.get('back') or request.referrer or url_for('club.index')
    player = Player.query.get_or_404(id)
    # Préparer listes d'historique raquettes : avec date triées puis sans date
    history = list(player.racquet_history)
    with_date = sorted([e for e in history if e.purchase_date], key=lambda e: e.purchase_date, reverse=True)
    without_date = [e for e in history if not e.purchase_date]

    # Charger (si disponibles) les données racqix pour enrichir les infobulles
    entry_tooltips_html = {}
    try:
        import json, os, unicodedata, re
        docs_dir = os.path.join(current_app.root_path, '..', 'docs')
        racq_path = os.path.join(docs_dir, 'racqix_racquets.json')
        strs_path = os.path.join(docs_dir, 'racqix_strings.json')
        racq_items = {}
        str_items = {}

        def _simple_normalize(s: str) -> str:
            if not s:
                return ''
            s = s.lower()
            s = ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')
            # replace any non-alphanumeric character with a space so separators like '/', '.', '-' become separators
            s = re.sub(r"[^a-z0-9]+", ' ', s)
            s = re.sub(r"\s+", ' ', s).strip()
            return s

        if os.path.exists(racq_path):
            with open(racq_path, 'r', encoding='utf-8') as f:
                for item in json.load(f):
                    name = (item.get('name') or '').strip()
                    brand = (item.get('brand') or '').strip()
                    slug = (item.get('slug') or '').strip()
                    # register multiple variants to improve matching robustness
                    variants = set()
                    variants.add(_simple_normalize(f"{brand} {name}"))
                    variants.add(_simple_normalize(name))
                    if slug:
                        variants.add(_simple_normalize(slug.replace('-', ' ')))
                        variants.add(_simple_normalize(f"{brand} {slug}"))
                    for v in variants:
                        if v and v not in racq_items:
                            racq_items[v] = item
        if os.path.exists(strs_path):
            with open(strs_path, 'r', encoding='utf-8') as f:
                for item in json.load(f):
                    name = (item.get('name') or '').strip()
                    brand = (item.get('brand') or '').strip()
                    slug = (item.get('slug') or '').strip()
                    variants = set()
                    variants.add(_simple_normalize(f"{brand} {name}"))
                    variants.add(_simple_normalize(name))
                    if slug:
                        variants.add(_simple_normalize(slug.replace('-', ' ')))
                        variants.add(_simple_normalize(f"{brand} {slug}"))
                    for v in variants:
                        if v and v not in str_items:
                            str_items[v] = item
    except Exception:
        racq_items = {}
        str_items = {}

    import re
    import unicodedata

    def _normalize(s: str) -> str:
        if not s:
            return ''
        s = s.lower()
        s = ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')
        s = re.sub(r"[^a-z0-9 ]+", '', s)
        s = re.sub(r"\s+", ' ', s).strip()
        return s

    def _make_html_for(entry):
        parts = []
        if entry.racquet:
            racq_label = f"{entry.racquet.brand} {entry.racquet.name}"
            key = _normalize(racq_label)
            current_app.logger.debug(f"racq tooltip: looking up racquet key='{key}' label='{racq_label}'")
            item = None
            # try direct key then normalized lookup
            item = racq_items.get(_simple_normalize(racq_label)) or racq_items.get(racq_label.lower()) or racq_items.get(key)
            parts.append(f"<div><strong>{racq_label}</strong></div>")
            current_app.logger.debug(f"racq tooltip: found item={'yes' if item else 'no'} for key='{key}'")
            if item:
                # support multiple possible key names from racqix exports
                p = item.get('scoresPower') or item.get('scores_power') or item.get('scoresPower') or item.get('rating_power') or item.get('power') or item.get('power_rating') or item.get('scoresPower')
                c = item.get('scoresControl') or item.get('scores_control') or item.get('rating_control') or item.get('control') or item.get('control_rating')
                s = item.get('scoresSpin') or item.get('scores_spin') or item.get('rating_spin') or item.get('spin') or item.get('spin_rating')
                f = item.get('rating_comfort') or item.get('comfort') or item.get('comfort_rating')
                if any(x is not None for x in (p, c, s, f)):
                    parts.append('<div style="margin-top:6px;">')
                    for lbl, v in [('Puissance', p), ('Contrôle', c), ('Spin', s), ('Confort', f)]:
                        if v is None:
                            continue
                        try:
                            vv = int(float(v))
                        except Exception:
                            vv = 0
                        parts.append(f"<div style=\"font-size:0.8em;margin-bottom:4px;\">{lbl} <div style='display:inline-block;width:140px;margin-left:6px;background:#f1f5f9;border-radius:4px;overflow:hidden;vertical-align:middle'><div style='width:{vv}%;height:8px;background:#3b82f6;'></div></div> <span style='margin-left:6px;color:#6b7280'>{vv}</span></div>")
                    parts.append('</div>')
                else:
                    score = item.get('score') or item.get('racquet_score')
                    if score:
                        parts.append(f"<div style='margin-top:6px;'>Score: {score}</div>")
                if item.get('mediaImageUrl'):
                    parts.append(f"<div style='margin-top:6px;'><img src=\"{item.get('mediaImageUrl')}\" alt=\"{racq_label}\" style=\"max-width:200px;max-height:120px;\"></div>")
        else:
            parts.append('<div><strong>Raquette: Non renseignée</strong></div>')

        if entry.string_name:
            sname = entry.string_name.strip()
            key_s = _normalize(sname)
            current_app.logger.debug(f"string tooltip: looking up string key='{key_s}' label='{sname}'")
            sitem = None
            for k, it in str_items.items():
                if _normalize(k) == key_s or _normalize(it.get('name', '')) == key_s:
                    sitem = it
                    break
            current_app.logger.debug(f"string tooltip: found sitem={'yes' if sitem else 'no'} for key='{key_s}'")
            parts.append(f"<div style='margin-top:6px;'><strong>{sname}</strong></div>")
            if sitem:
                # strings store ratings under 'ratings' or top-level keys
                ratings = sitem.get('ratings') or {}
                p = ratings.get('power') or sitem.get('rating_power') or sitem.get('power')
                c = ratings.get('control') or sitem.get('rating_control') or sitem.get('control')
                sp = ratings.get('spin') or sitem.get('rating_spin') or sitem.get('spin')
                f = ratings.get('comfort') or sitem.get('rating_comfort') or sitem.get('comfort')
                if any(x is not None for x in (p, c, sp, f)):
                    parts.append('<div style="margin-top:6px;">')
                    for lbl, v in [('Puissance', p), ('Contrôle', c), ('Spin', sp), ('Confort', f)]:
                        if v is None:
                            continue
                        try:
                            vv = int(float(v))
                        except Exception:
                            vv = 0
                        parts.append(f"<div style=\"font-size:0.8em;margin-bottom:4px;\">{lbl} <div style='display:inline-block;width:140px;margin-left:6px;background:#f1f5f9;border-radius:4px;overflow:hidden;vertical-align:middle'><div style='width:{vv}%;height:8px;background:#22c55e;'></div></div> <span style='margin-left:6px;color:#6b7280'>{vv}</span></div>")
                    parts.append('</div>')
                else:
                    sscore = sitem.get('score') or sitem.get('string_score')
                    if sscore:
                        parts.append(f"<div style='margin-top:6px;'>Score: {sscore}</div>")
                if sitem.get('image_url'):
                    parts.append(f"<div style='margin-top:6px;'><img src=\"{sitem.get('image_url')}\" alt=\"{sname}\" style=\"max-width:200px;max-height:120px;\"></div>")
            else:
                parts.append(f"<div style='margin-top:6px;'>Cordage: {sname} ({entry.string_tension or '–'} kg)</div>")

        return '<div style="max-width:320px;">' + ''.join(parts) + '</div>'

    for entry in with_date + without_date:
        entry_tooltips_html[entry.id] = _make_html_for(entry)

    return render_template('show_player.html', player=player, back_url=back_url,
                           with_date=with_date, without_date=without_date,
                           entry_tooltips_html=entry_tooltips_html)


# -- Historique raquettes joueurs ----------------------------------------------

def _parse_date_club(value):
    if not value:
        return None
    try:
        return date_type.fromisoformat(value)
    except ValueError:
        return None


def _sync_player_current_racquet(player: Player, preferred_entry: PlayerRacquet | None = None) -> None:
    """Synchronise player.racquet_id avec l'unique entrée d'historique active."""
    history = list(player.racquet_history)

    chosen_entry = None
    if preferred_entry and preferred_entry in history and preferred_entry.is_playing:
        chosen_entry = preferred_entry
    else:
        active_entries = [entry for entry in history if entry.is_playing]
        active_entries.sort(key=lambda entry: entry.updated_at or entry.created_at or datetime.min, reverse=True)
        chosen_entry = active_entries[0] if active_entries else None

    for entry in history:
        entry.is_playing = bool(chosen_entry and entry.id == chosen_entry.id)

    player.racquet_id = chosen_entry.racquet_id if chosen_entry and chosen_entry.racquet_id else None


@club_management_bp.route('/search')
def player_racquets_search():
    from sqlalchemy import func
    search_query = request.args.get('q', '').strip()
    players = []
    if search_query:
        players = (
            Player.query
            .join(License)
            .filter(func.lower(License.lastName).like(f'%{search_query.lower()}%'))
            .all()
        )
    return render_template('player_racquets_search.html', players=players, search_query=search_query)


@club_management_bp.route('/racquets/<int:player_id>')
def player_racquets(player_id):
    player = Player.query.get_or_404(player_id)
    history = (
        PlayerRacquet.query
        .filter_by(player_id=player_id)
        .order_by(PlayerRacquet.purchase_date.desc().nullslast())
        .all()
    )
    return render_template('player_racquets.html', player=player, history=history)


@club_management_bp.route('/racquets/<int:player_id>/add', methods=['GET', 'POST'])
def add_player_racquet(player_id):
    player = Player.query.get_or_404(player_id)
    racquets = Racquet.query.order_by(Racquet.brand, Racquet.name).all()

    if request.method == 'POST':
        racquet_id = request.form.get('racquet_id') or None
        if racquet_id:
            racquet_id = int(racquet_id)

        entry = PlayerRacquet(
            player_id=player_id,
            racquet_id=racquet_id,
            quantity=int(request.form.get('quantity', 1)),
            grip_size=request.form.get('grip_size') or None,
            string_name=request.form.get('string_name') or None,
            string_tension=float(request.form['string_tension']) if request.form.get('string_tension') else None,
            is_owner=bool(request.form.get('is_owner')),
            is_playing=bool(request.form.get('is_playing')),
            purchase_date=_parse_date_club(request.form.get('purchase_date')),
            notes=request.form.get('notes') or None,
        )
        db.session.add(entry)
        db.session.flush()
        has_other_active = any(history_entry.is_playing for history_entry in player.racquet_history if history_entry.id != entry.id)
        if entry.is_playing or (player.racquet_id is None and not has_other_active):
            entry.is_playing = True
        _sync_player_current_racquet(player, preferred_entry=entry if entry.is_playing else None)
        db.session.commit()
        flash(f'Raquette ajoutée pour {player.name}.', 'success')
        return redirect(url_for('club.show_player', id=player_id))

    return render_template('add_player_racquet.html', player=player, racquets=racquets)


@club_management_bp.route('/racquets/entry/<int:entry_id>/edit', methods=['GET', 'POST'])
def edit_player_racquet(entry_id):
    entry = PlayerRacquet.query.get_or_404(entry_id)
    player = Player.query.get_or_404(entry.player_id)
    racquets = Racquet.query.order_by(Racquet.brand, Racquet.name).all()

    if request.method == 'POST':
        racquet_id = request.form.get('racquet_id') or None
        entry.racquet_id = int(racquet_id) if racquet_id else None
        entry.quantity = int(request.form.get('quantity', 1))
        entry.grip_size = request.form.get('grip_size') or None
        entry.string_name = request.form.get('string_name') or None
        entry.string_tension = float(request.form['string_tension']) if request.form.get('string_tension') else None
        entry.is_owner = bool(request.form.get('is_owner'))
        entry.is_playing = bool(request.form.get('is_playing'))
        entry.purchase_date = _parse_date_club(request.form.get('purchase_date'))
        entry.notes = request.form.get('notes') or None

        _sync_player_current_racquet(player, preferred_entry=entry if entry.is_playing else None)
        db.session.commit()
        flash(f'Fiche raquette mise à jour pour {player.name}.', 'success')
        return redirect(url_for('club.show_player', id=player.id))

    return render_template('edit_player_racquet.html', entry=entry, player=player, racquets=racquets)


@club_management_bp.route('/racquets/entry/<int:entry_id>/delete', methods=['POST'])
def delete_player_racquet(entry_id):
    entry = PlayerRacquet.query.get_or_404(entry_id)
    player = Player.query.get_or_404(entry.player_id)
    player_id = entry.player_id
    back = None
    db.session.delete(entry)
    db.session.flush()
    _sync_player_current_racquet(player)
    db.session.commit()
    flash('Entrée supprimée.', 'success')
    return redirect(url_for('club.show_player', id=player_id))


@club_management_bp.route('/delete_player/<int:id>', methods=['GET'])
def delete_player(id):
    player = Player.query.get_or_404(id)
    club = Club.query.get(player.clubId)
    player_name = player.name

    # Nullifier les références dans Single/Double sans supprimer les résultats
    Single.query.filter(Single.player1Id == id).update({'player1Id': None})
    Single.query.filter(Single.player2Id == id).update({'player2Id': None})
    Double.query.filter(Double.player1Id == id).update({'player1Id': None})
    Double.query.filter(Double.player2Id == id).update({'player2Id': None})
    Double.query.filter(Double.player3Id == id).update({'player3Id': None})
    Double.query.filter(Double.player4Id == id).update({'player4Id': None})

    # Supprimer les associations
    player.teams = []
    player.injuries = []
    PlayerMatchdayAvailability.query.filter_by(player_id=id).delete()
    TeamMatchdayJoker.query.filter_by(player_id=id).delete()
    PlayerRacquet.query.filter_by(player_id=id).delete()

    # Supprimer la licence associée
    license = License.query.get(player.licenseId)
    db.session.delete(player)
    if license:
        db.session.delete(license)
    db.session.commit()

    flash(f'Joueur {player_name} supprimé avec succès.')
    return redirect(url_for('club.select_gender'))

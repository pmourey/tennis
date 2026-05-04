# Source Generated with Decompyle++
# File: views.cpython-310.pyc (Python 3.10)

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
from common import get_players_order_by_ranking, get_championships, Gender, check_license, keys_with_same_value, calculate_distance_and_duration, CatType, update_players

def check_club_cookie(func):
    
    def wrapper(*args, **kwargs):
        if 'club_id' not in request.cookies:
            return redirect(url_for('admin.select_club'))
    # WARNING: Decompyle incomplete

    wrapper = None(wrapper)
    return wrapper


def index():
    clubs = Club.query.all()
    signed_club_id = request.cookies.get('club_id')
    current_app.logger.debug(f'''index -> signed club_id: {signed_club_id}''')
# WARNING: Decompyle incomplete

index = club_management_bp.route('/')(check_club_cookie(index))

def select_gender():
    pass
# WARNING: Decompyle incomplete

select_gender = club_management_bp.route('/select_gender', [
    'GET',
    'POST'], **('methods',))(check_club_cookie(select_gender))

def select_championship_new_team():
    if request.method == 'POST':
        current_app.logger.debug(f'''gender = {request.form['gender']}''')
        gender = int(request.form['gender'])
        championship_id = request.form['championship']
        return redirect(url_for('club.new_team', championship_id, gender, **('championship_id', 'gender')))
    selected_gender = None(request.args.get('gender'))
    championships = get_championships(selected_gender, **('gender',))
    return render_template('select_championship_new_team.html', championships, selected_gender, **('championships', 'gender'))

select_championship_new_team = club_management_bp.route('/select_championship_new_team', [
    'GET',
    'POST'], **('methods',))(select_championship_new_team)

def select_gender_new_team():
    if request.method == 'POST':
        gender = int(request.form['gender'])
        return redirect(url_for('club.select_championship_new_team', gender, **('gender',)))
    return None('select_gender_new_team.html')

select_gender_new_team = club_management_bp.route('/select_gender_new_team', [
    'GET',
    'POST'], **('methods',))(select_gender_new_team)

def show_invalid_players():
    signed_club_id = request.cookies.get('club_id')
# WARNING: Decompyle incomplete

show_invalid_players = club_management_bp.route('/invalid_players')(check_club_cookie(show_invalid_players))

def show_teams():
    signed_club_id = request.cookies.get('club_id')
    current_season = AppSettings.get_season()
# WARNING: Decompyle incomplete

show_teams = club_management_bp.route('/teams')(check_club_cookie(show_teams))

def new_team():
    players_dict = { }
# WARNING: Decompyle incomplete

new_team = club_management_bp.route('/new_team/', [
    'GET',
    'POST'], **('methods',))(check_club_cookie(new_team))

def update_team(id):
    team = Team.query.get_or_404(id)
    current_app.logger.debug(f'''team in database: {(team.id, id, team.name)} - players: {team.players}''')
    players_dict = { }
    if request.method == 'POST':
        for key, value in request.form.items():
            if value and key.startswith('player_name_'):
                players_dict[key] = Player.query.get(value)
        duplicates = keys_with_same_value(players_dict)
        if not request.form['name']:
            flash('Veuillez renseigner tous les champs, svp!', 'error')
        elif duplicates:
            if len(duplicates) == 1:
                flash(f'''Le joueur {duplicates[0]} est en doublon, veuillez en sélectionner un autre!''', 'error')
            else:
                flash(f'''Les joueurs {duplicates} sont en doublons, veuillez en sélectionner d\'autres!''', 'error')
        else:
            team.name = request.form.get('name')
            captain_id = request.form.get('captain_id')
            team.captainId = int(captain_id) if captain_id else None
            team.players = []
            for player in players_dict.values():
                team.players.append(player)
                player.initialize_matchday_availability(team.championship)
            team.pool = Pool.query.get(int(request.form.get('pool_id')))
            db.session.commit()
            team.initialize_player_availability()
            flash(f'''Equipe {team.name} mise à jour avec succès!''')
            return redirect(url_for('club.show_teams'))
        age_category = None.championship.division.ageCategory
        other_age_categories = []
        if age_category.type == CatType.Senior.value:
            other_age_categories = (lambda .0: [ cat for cat in .0 if cat.maxAge <= 18 ])(AgeCategory.query.filter(AgeCategory.type == CatType.Youth.value).all())
    active_players = get_players_order_by_ranking(team.gender, team.club.id, age_category, **('gender', 'club_id', 'age_category'))
    if other_age_categories:
        for cat in other_age_categories:
            active_players += get_players_order_by_ranking(team.gender, team.club.id, cat, **('gender', 'club_id', 'age_category'))
        active_players = list(set(active_players))
    active_players.sort((lambda p: p.ranking.id), **('key',))
    sorted_team_players = sorted(team.players, (lambda p: p.ranking.id), **('key',))
    if active_players:
        max_players = min(15, len(active_players))
        return render_template('update_team.html', team, sorted_team_players, active_players, max_players, request.form, **('team', 'sorted_team_players', 'players', 'max_players', 'form'))
    club = None.query.get(team.club.id)
    flash(f'''Tâche impossible! Aucun joueur existant ou disponible dans le club {club}!''', 'error')
    return render_template('index.html')

update_team = club_management_bp.route('/update_team/<int:id>', [
    'GET',
    'POST'], **('methods',))(update_team)

def infos_club(id):
    if request.method == 'GET':
        club = Club.query.get_or_404(id)
        return render_template('infos_club.html', club, **('club',))

infos_club = club_management_bp.route('/infos_club/<int:id>', [
    'GET',
    'POST'], **('methods',))(infos_club)

def show_team(id = None):
    team = Team.query.get(id)
    sorted_team_players = sorted(team.players, (lambda p: p.ranking.id), **('key',))
    signed_club_id = request.cookies.get('club_id')
# WARNING: Decompyle incomplete

show_team = None(show_team)

def save_joker(team_id):
    """Enregistre ou supprime le joueur joker d'une équipe pour une journée donnée."""
    team = Team.query.get_or_404(team_id)
    data = request.get_json()
    matchday_id = data.get('matchday_id')
    player_id = data.get('player_id')
    plays_single = bool(data.get('plays_single', False))
    plays_double = bool(data.get('plays_double', False))
    
    try:
        existing = TeamMatchdayJoker.query.filter_by(team_id, matchday_id, **('team_id', 'matchday_id')).first()
        if player_id:
            player_id = int(player_id)
            if None((lambda .0 = None: for p in .0:
p.id == player_id)(team.players)):
                pass
            return None
        singles_count = team.championship.singlesCount if None.championship else 4
        sorted_players = sorted(team.players, (lambda p: p.ranking.id), **('key',))
        if len(sorted_players) >= singles_count:
            last_burned = sorted_players[singles_count - 1]
            joker_player = Player.query.get(player_id)
            if joker_player and joker_player.ranking.id < last_burned.ranking.id:
                pass
            return None
        if None:
            existing.player_id = player_id
            existing.plays_single = plays_single
            existing.plays_double = plays_double
        else:
            db.session.add(TeamMatchdayJoker(team_id, matchday_id, player_id, plays_single, plays_double, **('team_id', 'matchday_id', 'player_id', 'plays_single', 'plays_double')))
    if existing:
        db.session.delete(existing)

    db.session.commit()
    :
        team = Team.query.get_or_404(team_id)
        data = request.get_json()
        matchday_id = data.get('matchday_id')
        player_id = data.get('player_id')
        plays_single = bool(data.get('plays_single', False))
        plays_double = bool(data.get('plays_double', False))
        
        try:
            existing = TeamMatchdayJoker.query.filter_by(team_id, matchday_id, **('team_id', 'matchday_id')).first()
            if player_id:
                player_id = int(player_id)
                if None((lambda .0 = None: for p in .0:
p.id == player_id)(team.players)):
                    pass
                return None
            singles_count = team.championship.singlesCount if None.championship else 4
            sorted_players = sorted(team.players, (lambda p: p.ranking.id), **('key',))
            if len(sorted_players) >= singles_count:
                last_burned = sorted_players[singles_count - 1]
                joker_player = Player.query.get(player_id)
                if joker_player and joker_player.ranking.id < last_burned.ranking.id:
                    pass
                return None
            if None:
                existing.player_id = player_id
                existing.plays_single = plays_single
                existing.plays_double = plays_double
            else:
                db.session.add(TeamMatchdayJoker(team_id, matchday_id, player_id, plays_single, plays_double, **('team_id', 'matchday_id', 'player_id', 'plays_single', 'plays_double')))
        if existing:
            db.session.delete(existing)

        db.session.commit()
        
        return jsonify({
            'success': True })
    return jsonify({
        'success': True })
# WARNING: Decompyle incomplete

save_joker = club_management_bp.route('/save_joker/<int:team_id>', [
    'POST'], **('methods',))(save_joker)

def save_availability(team_id):
    data = request.get_json()
    availability = data.get('availability', [])
# WARNING: Decompyle incomplete

save_availability = club_management_bp.route('/save_availability/<int:team_id>', [
    'POST'], **('methods',))(save_availability)

def update_players_route():
    signed_club_id = request.cookies.get('club_id')
# WARNING: Decompyle incomplete

update_players_route = club_management_bp.route('/update_players', [
    'GET',
    'POST'], **('methods',))(check_club_cookie(update_players_route))

def transfer_player():
    '''Transfère un ou plusieurs joueurs en conflit vers leur nouveau club.'''
    import json
    transfers_json = request.form.get('transfers', '[]')
# WARNING: Decompyle incomplete

transfer_player = club_management_bp.route('/transfer_player', [
    'POST'], **('methods',))(check_club_cookie(transfer_player))

def new_player():
    current_app.logger.debug(f'''request.method: {request.method}''')
# WARNING: Decompyle incomplete

new_player = club_management_bp.route('/new_player/', [
    'GET',
    'POST'], **('methods',))(new_player)

def update_player(id):
    player = Player.query.get_or_404(id)
    if request.method == 'POST':
        birth_date = request.form.get('birth_date')
        current_app.logger.debug(f'''birthDate: {birth_date}''')
        player.birthDate = datetime.strptime(birth_date, '%Y-%m-%d') if birth_date else None
        player.height = request.form.get('height')
        player.weight = request.form.get('weight')
        license = License.query.get(player.licenseId)
        license.rankingId = int(request.form['ranking'])
        license.bestRankingId = int(request.form['best_ranking'])
        db.session.add(license)
        current_app.logger.debug(f'''license best ranking: {license.bestRanking}''')
        player.isActive = False if request.form.get('is_active') is None else True
        selected_injuries = request.form.getlist('injuries[]')
        current_app.logger.debug(f'''selected_injuries: {selected_injuries}''')
        player.injuries = []
        db.session.add(player)
        for injury_id in selected_injuries:
            injury = Injury.query.get(injury_id)
            if injury:
                player.injuries.append(injury)
        db.session.commit()
        flash(f'''Infos {player.name} mises à jour avec succès!''')
        return redirect(url_for('medical.index'))
    injuries = None.query.join(InjurySite).order_by(asc(InjurySite.name), asc(Injury.type), asc(Injury.name)).all()
    rankings = Ranking.query.order_by(desc(Ranking.id))
    bestRankings = BestRanking.query.order_by(desc(BestRanking.id))
    return render_template('update_player.html', player, injuries, rankings, bestRankings, **('player', 'injuries', 'rankings', 'best_rankings'))

update_player = club_management_bp.route('/update_player/<int:id>', [
    'GET',
    'POST'], **('methods',))(update_player)

def show_player(id):
    return render_template('show_player.html', Player.query.get_or_404(id), **('player',))

show_player = club_management_bp.route('/player/<int:id>')(show_player)

def delete_player(id):
    if request.method == 'GET':
        player = Player.query.get_or_404(id)
        club = Club.query.get(player.clubId)
        player_name = player.name
        Single.query.filter(Single.player1Id == id).update({
            'player1Id': None })
        Single.query.filter(Single.player2Id == id).update({
            'player2Id': None })
        Double.query.filter(Double.player1Id == id).update({
            'player1Id': None })
        Double.query.filter(Double.player2Id == id).update({
            'player2Id': None })
        Double.query.filter(Double.player3Id == id).update({
            'player3Id': None })
        Double.query.filter(Double.player4Id == id).update({
            'player4Id': None })
        Team.query.filter(Team.captainId == id).update({
            'captainId': None })
        db.session.delete(player)
        db.session.commit()
        current_app.logger.debug(f'''Joueur {player_name} supprimé (Single/Double/Captain nullifiés).''')
        flash(f'''Joueur "{player_name}" supprimé du club {club}.''', 'success')
        return redirect(url_for('club.index'))

delete_player = club_management_bp.route('/delete_player/<int:id>', [
    'GET',
    'POST'], **('methods',))(delete_player)

def delete_team(id):
    if request.method == 'GET':
        team = Team.query.get_or_404(id)
        db.session.delete(team)
        db.session.commit()
        current_app.logger.debug(f'''Equipe {team} supprimé!''')
        flash(f'''L\'équipe "{team.name}" ne fait plus partie du club {team.club}!''')
        return redirect(url_for('club.show_teams'))

delete_team = club_management_bp.route('/delete_team/<int:id>', [
    'GET',
    'POST'], **('methods',))(delete_team)

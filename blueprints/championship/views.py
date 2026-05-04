# Source Generated with Decompyle++
# File: views.cpython-310.pyc (Python 3.10)

from __future__ import annotations
import string
from datetime import datetime, timedelta
from flask import request, current_app, jsonify
from sqlalchemy import desc, and_
from flask import render_template, redirect, url_for, flash
from models import AgeCategory, Division, Championship, db, Pool, Team, Matchday, Match, PoolSimulation, TeamSimulationResult
from blueprints.championship import championship_management_bp
from common import populate_championship, calculer_classement, simulate_match_scores, create_pools_and_assign_teams, schedule_matches, form_teams, get_players_order_by_ranking, remove_text_between_parentheses

def index():
    return render_template('championship_index.html')

index = championship_management_bp.route('/')(index)

def select_age_category():
    if request.method == 'POST':
        selected_age_category_id = request.form['age_category']
        return redirect(url_for('championship.select_division', selected_age_category_id, **('selected_age_category_id',)))
    age_categories = None.query.all()
    return render_template('select_age_category.html', age_categories, **('age_categories',))

select_age_category = championship_management_bp.route('/select_age_category', [
    'GET',
    'POST'], **('methods',))(select_age_category)

def select_division():
    if request.method == 'POST':
        selected_division_id = request.form['division']
        selected_division = Division.query.get(selected_division_id)
        AppSettings = AppSettings
        import models
        current_season = AppSettings.get_season()
        championship = Championship.query.filter_by(selected_division.id, current_season, **('divisionId', 'season')).first()
        if championship:
            flash(f'''Le championnat {championship} a déjà été créé pour la saison {current_season}!''')
            return redirect(url_for('championship.select_division', selected_division.ageCategoryId, **('selected_age_category_id',)))
        AppSettings = AppSettings
        import models
        datetime = datetime
        timedelta = timedelta
        import datetime
        current_season = AppSettings.get_season()
        season_year = int(current_season.split('/')[0])
        oct_first = datetime(season_year, 10, 1)
        days_until_sunday = (6 - oct_first.weekday()) % 7
        first_sunday = oct_first + timedelta(days_until_sunday, **('days',))
        season_start = f'''{season_year}-10-01'''
        default_date = first_sunday.strftime('%Y-%m-%d')
        return render_template('new_championship.html', selected_division, season_start, default_date, **('selected_division', 'season_start', 'default_date'))
    selected_age_category_id = None.args.get('selected_age_category_id')
    divisions = Division.query.filter_by(selected_age_category_id, **('ageCategoryId',)).order_by(desc(Division.type)).all()
    AppSettings = AppSettings
    import models
    current_season = AppSettings.get_season()
    new_divisions = []
    for division in divisions:
        championship_with_division = Championship.query.filter_by(division.id, current_season, **('divisionId', 'season')).first()
        if championship_with_division:
            continue
        new_divisions.append(division)
    return render_template('select_division.html', new_divisions, **('divisions',))

select_division = championship_management_bp.route('/select_division', [
    'GET',
    'POST'], **('methods',))(select_division)

def new_pool(championship_id):
    championship = Championship.query.get(championship_id)
    if request.method == 'POST':
        club_ids = request.form.getlist('clubs[]')
        club_ids = list(filter(None, club_ids))
        if len(club_ids) != len(set(club_ids)):
            Counter = Counter
            import collections
            Club = Club
            import models
            duplicates = (lambda .0: [ club_id for club_id, count in .0 if count > 1 ])(Counter(club_ids).items())
            duplicate_names = (lambda .0 = None: [ Club.query.get(club_id).name for club_id in .0 ])(duplicates)
            flash(f'''Impossible de mettre plusieurs équipes du même club dans la même poule! Club(s) en erreur: {', '.join(duplicate_names)}''', 'error')
            available_clubs = Club.query.all()
            return render_template('new_pool.html', championship, available_clubs, club_ids, True, **('championship', 'clubs', 'selected_clubs', 'preserve_all'))
        teams = None
        current_app.logger.debug(f'''Selected club_ids: {club_ids}''')
        for club_id in club_ids:
            current_app.logger.debug(f'''Processing club_id: {club_id}''')
            existing_teams = Team.query.filter_by(club_id, **('clubId',)).filter(Team.poolId.in_((lambda .0: [ p.id for p in .0 ])(championship.pools))).all()
            current_app.logger.debug(f'''Existing teams for club {club_id}: {(lambda .0: [ t.name for t in .0 ])(existing_teams)}''')
            existing_numbers = []
            for team in existing_teams:
                parts = team.name.split(' ')
                current_app.logger.debug(f'''Team name parts: {parts}''')
                if parts and parts[-1].isdigit():
                    number = int(parts[-1])
                    existing_numbers.append(number)
                    current_app.logger.debug(f'''Found existing number: {number}''')
            current_app.logger.debug(f'''All existing numbers for club {club_id}: {existing_numbers}''')
            team_number = 1
            if team_number in existing_numbers:
                team_number += 1
                if not team_number in existing_numbers:
                    current_app.logger.debug(f'''Next team number for club {club_id}: {team_number}''')
                    Club = Club
                    import models
                    club = Club.query.get(club_id)
                    if club:
                        players = get_players_order_by_ranking(championship.division.gender, club_id, True, championship.age_category, True, **('gender', 'club_id', 'asc_param', 'age_category', 'is_active'))
                        if len(players) >= championship.singlesCount:
                            captain = max(players, (lambda p: p.best_elo), **('key',))
                            club_name = remove_text_between_parentheses(club.name)
                            team = Team(f'''{club_name} {team_number}''', captain.id, club_id, **('name', 'captainId', 'clubId'))
                            team.players = players[:15]
                            teams.append(team)
                            current_app.logger.debug(f'''Created team: {team.name} with {len(team.players)} players''')
                            continue
                        current_app.logger.debug(f'''Club {club.name} has insufficient players: {len(players)}''')
                        continue
            current_app.logger.debug(f'''Club {club_id} not found''')
        current_app.logger.debug(f'''Total teams created: {len(teams)}''')
        pools = Pool.query.filter_by(championship_id, **('championshipId',)).all()
        pool_letters = (lambda .0: [ pool.letter for pool in .0 if pool.letter ])(pools)
        letter = None(None((lambda .0 = None: [ ord(l) for l in .0 if l not in pool_letters ])(string.ascii_uppercase))) if pool_letters else 'A'
        pool = Pool(letter, championship_id, **('letter', 'championshipId'))
        db.session.add(pool)
        db.session.commit()
        db.session.add_all(teams)
        db.session.commit()
        for team in teams:
            team.poolId = pool.id
        db.session.commit()
        schedule_matches(current_app, db, pool)
        flash(f'''Poule {pool.letter} créée avec succès!''', 'success')
        return redirect(url_for('championship.show_pools', championship_id, **('id',)))
    Club = Club
    import models
    available_clubs = Club.query.all()
    return render_template('new_pool.html', championship, available_clubs, **('championship', 'clubs'))

new_pool = championship_management_bp.route('/new_pool/<int:championship_id>', [
    'GET',
    'POST'], **('methods',))(new_pool)

def configure_pools(championship_id):
    championship = Championship.query.get_or_404(championship_id)
    if request.method == 'POST':
        num_pools = int(request.form['num_pools'])
        for i in range(num_pools):
            pool = Pool(chr(ord('A') + i), championship.id, **('letter', 'championshipId'))
            db.session.add(pool)
        db.session.commit()
        flash(f'''{num_pools} poules créées avec succès!''', 'success')
        return redirect(url_for('championship.assign_teams', championship.id, **('championship_id',)))
    return None('configure_pools.html', championship, **('championship',))

configure_pools = championship_management_bp.route('/configure_pools/<int:championship_id>', [
    'GET',
    'POST'], **('methods',))(configure_pools)

def assign_teams(championship_id):
    championship = Championship.query.get_or_404(championship_id)
    if request.method == 'POST':
        for pool in championship.pools:
            team_ids = request.form.getlist(f'''pool_{pool.id}_teams[]''')
            team_ids = list(filter(None, team_ids))
            for team_id in team_ids:
                team = Team.query.get(team_id)
                if team:
                    team.poolId = pool.id
        db.session.commit()
        for pool in championship.pools:
            if pool.teams:
                schedule_matches(current_app, db, pool)
        flash('Equipes assignées et matches programmés avec succès!', 'success')
        return redirect(url_for('championship.show_pools', championship.id, **('id',)))
    available_teams = None(championship, [], **('club_ids_to_filter',))
    db.session.add_all(available_teams)
    db.session.commit()
    return render_template('assign_teams.html', championship, available_teams, **('championship', 'teams'))

assign_teams = championship_management_bp.route('/assign_teams/<int:championship_id>', [
    'GET',
    'POST'], **('methods',))(assign_teams)

def new_championship():
    pass
# WARNING: Decompyle incomplete

new_championship = championship_management_bp.route('/new_championship', [
    'GET',
    'POST'], **('methods',))(new_championship)

def delete_championship(championship_id):
    championship = Championship.query.get_or_404(championship_id)
# WARNING: Decompyle incomplete

delete_championship = championship_management_bp.route('/delete_championship/<int:championship_id>', [
    'POST'], **('methods',))(delete_championship)

def delete_pool(pool_id):
    pool = Pool.query.get_or_404(pool_id)
    championship = Championship.query.get_or_404(pool.championshipId)
# WARNING: Decompyle incomplete

delete_pool = championship_management_bp.route('/delete_pool/<int:pool_id>', [
    'POST'], **('methods',))(delete_pool)

def purge_pool(pool_id = None):
    matches = Match.query.filter(Match.poolId == pool_id).all()
    if any((lambda .0: for m in .0:
m.singles)(matches)):
        for match in matches:
            for single in match.singles:
                db.session.delete(single)
            for double in match.doubles:
                db.session.delete(double)
            match.singles.clear()
            match.doubles.clear()
        db.session.commit()
        return None


def simulate_pool_batch(pool_id):
    pool = Pool.query.get_or_404(pool_id)
    if request.method == 'POST':
        num_simulations = int(request.form.get('sim_count'))
        simulation_results = (lambda .0: pass# WARNING: Decompyle incomplete
)(pool.teams)
        simulation_match_scores = (lambda .0: pass# WARNING: Decompyle incomplete
)(pool.matches)
        for i in range(num_simulations):
            if not i % 5:
                current_app.logger.debug(f'''simulations to run: {num_simulations - i}''')
            purge_pool(pool_id)
            simulate_match_scores(current_app, db, pool)
            for match in pool.matches:
                if match.homeScore is not None:
                    simulation_match_scores[match.id].append((match.homeScore, match.visitorScore))
            for ranking, data in enumerate(calculer_classement(pool)):
                (team_id, result) = data
                points = result['points']
                simulation_results[team_id].append((ranking, points))
        average_results = { }
        for team in pool.teams:
            team_results = simulation_results[team.id]
            rankings = (lambda .0: [ result[0] for result in .0 ])(team_results)
            points = (lambda .0: [ result[1] for result in .0 ])(team_results)
            average_results[team.id] = {
                'team_name': None,
                'avg_ranking': None,
                'avg_points': None,
                'best_ranking': None,
                'worst_ranking': None,
                'rankings_distribution': (lambda .0 = None: pass# WARNING: Decompyle incomplete
)(range(1, len(pool.teams) + 1)) }
        sorted_results = dict(sorted(average_results.items(), (lambda x: x[1]['avg_ranking']), **('key',)))
        PoolSimulation = PoolSimulation
        TeamSimulationResult = TeamSimulationResult
        MatchSimulationResult = MatchSimulationResult
        import models
        simulation = PoolSimulation(pool_id, num_simulations, **('pool_id', 'num_simulations'))
        db.session.add(simulation)
        db.session.commit()
        for team_id, result in sorted_results.items():
            team_result = TeamSimulationResult(simulation.id, team_id, result['avg_ranking'], result['avg_points'], result['best_ranking'], result['worst_ranking'], **('simulation_id', 'team_id', 'avg_ranking', 'avg_points', 'best_ranking', 'worst_ranking'))
            db.session.add(team_result)
        for match in pool.matches:
            for home_score, visitor_score in simulation_match_scores[match.id]:
                match_result = MatchSimulationResult(simulation.id, match.id, home_score, visitor_score, **('simulation_id', 'match_id', 'home_score', 'visitor_score'))
                db.session.add(match_result)
        db.session.commit()
        return redirect(url_for('championship.show_simulation', simulation.id, **('sim_id',)))
    return None('simulate_pool.html', pool, **('pool',))

simulate_pool_batch = championship_management_bp.route('/simulate_pool_batch/<int:pool_id>', [
    'GET',
    'POST'], **('methods',))(simulate_pool_batch)

def show_simulations(pool_id = None):
    simulations = PoolSimulation.query.filter(PoolSimulation.pool_id == pool_id).order_by(PoolSimulation.created_at.desc()).all()
    pool = Pool.query.get_or_404(pool_id)
    return render_template('pool_simulations.html', simulations, pool, **('simulations', 'pool'))

show_simulations = None(show_simulations)

def delete_simulation(sim_id = None):
    simulation = PoolSimulation.query.get_or_404(sim_id)
    pool_id = simulation.pool_id
    db.session.delete(simulation)
    db.session.commit()
    flash(f'''Simulation #{sim_id} supprimée.''', 'success')
    return redirect(url_for('championship.show_simulations', pool_id, **('pool_id',)))

delete_simulation = None(delete_simulation)

def delete_simulations_bulk(pool_id = None):
    Pool.query.get_or_404(pool_id)
    ids = request.form.getlist('sim_ids')
    if not ids:
        flash('Aucune simulation sélectionnée.', 'error')
        return redirect(url_for('championship.show_simulations', pool_id, **('pool_id',)))
    count = None
    for sid in ids:
        sim = PoolSimulation.query.get(int(sid))
        if sim and sim.pool_id == pool_id:
            db.session.delete(sim)
            count += 1
    db.session.commit()
    flash(f'''{count} simulation(s) supprimée(s).''', 'success')
    return redirect(url_for('championship.show_simulations', pool_id, **('pool_id',)))

delete_simulations_bulk = None(delete_simulations_bulk)

def delete_all_simulations(pool_id = None):
    Pool.query.get_or_404(pool_id)
    sims = PoolSimulation.query.filter_by(pool_id, **('pool_id',)).all()
    count = len(sims)
    for sim in sims:
        db.session.delete(sim)
    db.session.commit()
    flash(f'''Toutes les simulations ({count}) supprimées.''', 'success')
    return redirect(url_for('championship.show_simulations', pool_id, **('pool_id',)))

delete_all_simulations = None(delete_all_simulations)

def show_simulation(sim_id = None):
    simulation = PoolSimulation.query.get_or_404(sim_id)
    pool = Pool.query.get_or_404(simulation.pool_id)
    simTeamResults = TeamSimulationResult.query.filter(TeamSimulationResult.simulation_id == simulation.id).all()
    Counter = Counter
    import collections
    MatchSimulationResult = MatchSimulationResult
    import models
    score_distributions = { }
    for team in pool.teams:
        results = MatchSimulationResult.query.join(Match).filter(MatchSimulationResult.simulation_id == simulation.id, db.or_(Match.homeTeamId == team.id, Match.visitorTeamId == team.id)).all()
        scores = []
        for r in results:
            if r.match.homeTeamId == team.id:
                scores.append(f'''{r.home_score}/{r.visitor_score}''')
                continue
            scores.append(f'''{r.visitor_score}/{r.home_score}''')
        counter = Counter(scores)
        total = sum(counter.values())
        distribution = (lambda .0 = None: [ (score, count, round((count / total) * 100)) for score, count in .0 if count > 0 ])(sorted(counter.items(), True, **('reverse',)))
        wins = sum((lambda .0: 
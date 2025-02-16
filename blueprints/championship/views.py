# championship/views.py
from __future__ import annotations

import string
from datetime import datetime, timedelta

from flask import request, current_app, jsonify
from sqlalchemy import desc, and_

from flask import render_template, redirect, url_for, flash

from models import AgeCategory, Division, Championship, db, Pool, Team, Matchday, Match, PoolSimulation, TeamSimulationResult
from blueprints.championship import championship_management_bp
from common import populate_championship, calculer_classement, simulate_match_scores, create_pools_and_assign_teams, schedule_matches, form_teams


# Define routes for championship management
@championship_management_bp.route('/')
def index():
    return render_template('championship_index.html')


@championship_management_bp.route('/select_age_category', methods=['GET', 'POST'])
def select_age_category():
    if request.method == 'POST':
        selected_age_category_id = request.form['age_category']
        return redirect(url_for('championship.select_division', selected_age_category_id=selected_age_category_id))
    age_categories = AgeCategory.query.all()
    return render_template('select_age_category.html', age_categories=age_categories)


@championship_management_bp.route('/select_division', methods=['GET', 'POST'])
def select_division():
    if request.method == 'POST':
        selected_division_id = request.form['division']
        selected_division = Division.query.get(selected_division_id)
        championship = Championship.query.filter_by(divisionId=selected_division.id).first()
        if championship:
            flash(f"Le championnat {championship} a déjà été créé dans l'application!")
            return redirect(url_for('championship.select_division', selected_age_category_id=selected_division.ageCategoryId))
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
    # current_app.logger.debug(f'divisions: {new_divisions}')
    return render_template('select_division.html', divisions=new_divisions)


@championship_management_bp.route('/new_pool/<int:championship_id>', methods=['GET', 'POST'])
def new_pool(championship_id):
    if request.method == 'POST':
        # Fetching the list of team IDs from the form
        team_ids = request.form.getlist('teams[]')
        team_ids = list(filter(None, team_ids))
        # current_app.logger.debug(f'team_ids: {team_ids}')
        teams = [Team.query.get(team_id) for team_id in team_ids]
        # current_app.logger.debug(f'teams: {teams}')

        # Create a new pool
        pools = Pool.query.filter_by(championshipId=championship_id).all()
        pool_letters = [pool.letter for pool in pools]
        # current_app.logger.debug(f'pool_letters: {pool_letters}')
        letter = chr(min([ord(l) for l in string.ascii_uppercase if l is not None and l not in pool_letters])) if pool_letters else None
        # current_app.logger.debug(f'letter: {letter}')
        pool = Pool(letter=letter, championshipId=championship_id)
        db.session.add(pool)
        db.session.commit()

        # Assign teams to the pool
        for team in teams:
            team.poolId = pool.id
        db.session.add_all(teams)
        db.session.commit()

        # Génération des ordonnancements de matches
        schedule_matches(current_app, db, pool)
        # current_app.logger.debug(f'COMMIT DONE = {len(pool.matches)} MATCHES scheduled for pool {pool}')

        flash(f'Poule {pool.letter} créée avec succès!', 'success')
        return redirect(url_for('championship.index'))

    # Fetch all teams
    championship = Championship.query.get(championship_id)
    enrolled_teams = [team for pool in championship.pools for team in pool.teams]
    current_app.logger.debug(f'enrolled_teams: {enrolled_teams}')
    club_ids_to_filter = [team.clubId for team in enrolled_teams]
    club_ids_to_filter = list(set(club_ids_to_filter))
    current_app.logger.debug(f'clubs_to_filter: {club_ids_to_filter}')
    new_teams = form_teams(championship, club_ids_to_filter=club_ids_to_filter)
    # eligible_teams = form_teams(championship)
    db.session.add_all(new_teams)
    db.session.commit()
    current_app.logger.debug(f'new_teams: {new_teams}')
    return render_template('new_pool.html', championship=championship, teams=new_teams)

@championship_management_bp.route('/new_championship', methods=['GET', 'POST'])
def new_championship():
    if request.method == 'POST':
        # Fetching the list of dates from the form
        date_strings = request.form.getlist('dates[]')
        date_strings = list(filter(None, date_strings))
        selected_dates = [datetime.strptime(date_str, '%Y-%m-%d') for date_str in date_strings]

        singles_count = int(request.form['singles_count'])
        doubles_count = int(request.form['doubles_count'])
        division_id = int(request.form['division'])  # Get the selected division ID

        # Validation: Ensure at least one date is provided
        if not selected_dates:
            flash('Veuillez sélectionner au moins une date pour le championnat!', 'error')
            division = Division.query.get(division_id)
            return render_template('new_championship.html', selected_division=division)

        # Optional: Additional validation (e.g., ensure no conflicts between dates)
        # Example: check if there is at least one Sunday in the selected dates
        sundays_count = sum(1 for date in selected_dates if date.weekday() == 6)
        if sundays_count == 0:
            flash('Aucune des dates sélectionnées n\'est un dimanche!', 'error')
            division = Division.query.get(division_id)
            return render_template('new_championship.html', selected_division=division)

        # Create the championship
        championship = Championship(
            singlesCount=singles_count,
            doublesCount=doubles_count,
            divisionId=division_id
        )

        # current_app.logger.debug(f'championship: {championship}')
        db.session.add(championship)

        try:
            # Create matchdays for each selected date
            for date in selected_dates:
                report_date = date + timedelta(days=6)  # report au samedi suivant
                matchday = Matchday(date=date, report_date=report_date, championshipId=championship.id)
                championship.matchdays.append(matchday)
                db.session.add(matchday)
            populate_championship(app=current_app, db=db, championship=championship)
            flash('Championnat créé avec succès!', 'success')
        except Exception as e:
            db.session.rollback()  # Rollback if an error occurs
            flash(f'Erreur: {e}\nImpossible de créer le championnat.', 'error')
            division = Division.query.get(division_id)
            return render_template('new_championship.html', selected_division=division)

        db.session.commit()
        return render_template('championship_index.html')

    # GET request: Render the form with divisions
    divisions = Division.query.all()
    return render_template('new_championship.html', divisions=divisions)


@championship_management_bp.route('/delete_championship/<int:championship_id>', methods=['POST'])
def delete_championship(championship_id):
    championship = Championship.query.get_or_404(championship_id)

    try:
        db.session.delete(championship)
        db.session.commit()
        flash('Championship deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting championship: {str(e)}', 'error')

    return redirect(url_for('championship.show_championships'))

@championship_management_bp.route('/delete_pool/<int:pool_id>', methods=['POST'])
def delete_pool(pool_id):
    pool = Pool.query.get_or_404(pool_id)
    championship = Championship.query.get_or_404(pool.championshipId)
    try:
        pool_letter: str = pool.letter
        db.session.delete(pool)
        db.session.commit()
        flash(f'Pool {pool_letter} deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting pool: {str(e)}', 'error')

    return redirect(url_for('championship.show_pools', id=championship.id))

def purge_pool(pool_id: int):
    matches = Match.query.filter(Match.poolId == pool_id).all()
    if any(m.singles for m in matches):
        for match in matches:
            # Delete individual singles matches
            for single in match.singles:
                db.session.delete(single)
            # Delete individual doubles matches
            for double in match.doubles:
                db.session.delete(double)
            # Clear the lists
            match.singles.clear()
            match.doubles.clear()
        db.session.commit()


@championship_management_bp.route('/simulate_pool_batch/<int:pool_id>', methods=['GET', 'POST'])
def simulate_pool_batch(pool_id):
    pool = Pool.query.get_or_404(pool_id)
    if request.method == 'POST':
        num_simulations = int(request.form.get('sim_count'))

        # Run simulations and collect results
        # time to run 10 simulations in development environment: 1 minute
        # time to run 10 simulations in production environment: 10 minutes
        simulation_results = {team.id: [] for team in pool.teams}
        for i in range(num_simulations):
            if not i % 5:
                current_app.logger.debug(f'simulations to run: {num_simulations - i}')
            purge_pool(pool_id)
            # Simulate matches
            simulate_match_scores(current_app, db, pool)
            # Calcul du classement de la poule
            for ranking, data in enumerate(calculer_classement(pool)):
                team_id, result = data
                points = result['points']
                simulation_results[team_id].append((ranking, points))

        # Calculate average rankings and points for each team
        average_results = {}
        for team in pool.teams:
            team_results = simulation_results[team.id]
            rankings = [result[0] for result in team_results]
            points = [result[1] for result in team_results]

            average_results[team.id] = {
                'team_name': team.name,
                'avg_ranking': sum(rankings) / num_simulations,
                'avg_points': sum(points) / num_simulations,
                'best_ranking': 1 + min(rankings),
                'worst_ranking': 1 + max(rankings),
                'rankings_distribution': {
                    pos: rankings.count(pos) for pos in range(1, len(pool.teams) + 1)
                }
            }

        # Sort teams by average ranking
        sorted_results = dict(sorted(average_results.items(), key=lambda x: x[1]['avg_ranking']))

        # Create results in PoolSimulation, TeamSimulationResult models
        simulation = PoolSimulation(pool_id=pool_id, num_simulations=num_simulations)
        db.session.add(simulation)
        db.session.commit()
        for team_id, result in sorted_results.items():
            team_result = TeamSimulationResult(
                simulation_id=simulation.id,
                team_id=team_id,
                avg_ranking=result['avg_ranking'],
                avg_points=result['avg_points'],
                best_ranking=result['best_ranking'],
                worst_ranking=result['worst_ranking']
            )
            db.session.add(team_result)
            db.session.commit()

        return redirect(url_for('championship.show_simulation', sim_id=simulation.id))

    return render_template('simulate_pool.html', pool=pool)

@championship_management_bp.route('/show_simulations/<int:pool_id>')
def show_simulations(pool_id: int):
    simulations = PoolSimulation.query.filter(PoolSimulation.pool_id == pool_id).all()
    pool = Pool.query.get_or_404(pool_id)
    return render_template('pool_simulations.html', simulations=simulations, pool=pool)

@championship_management_bp.route('/show_simulation/<int:sim_id>')
def show_simulation(sim_id: int):
    simulation = PoolSimulation.query.get_or_404(sim_id)
    pool = Pool.query.get_or_404(simulation.pool_id)
    simTeamResults = TeamSimulationResult.query.filter(TeamSimulationResult.simulation_id == simulation.id).all()
    return render_template('pool_simulation_result.html', results=simTeamResults, simulation=simulation, pool=pool)

@championship_management_bp.route('/simulate_pool/<int:pool_id>', methods=['POST'])
def simulate_pool(pool_id):
    pool = Pool.query.get(pool_id)
    try:
        matches = Match.query.filter(Match.poolId == pool_id).all()
        if any(m.singles for m in matches):
            for match in matches:
                # Delete individual singles matches
                for single in match.singles:
                    db.session.delete(single)
                # Delete individual doubles matches
                for double in match.doubles:
                    db.session.delete(double)
                # Clear the lists
                match.singles.clear()
                match.doubles.clear()
            db.session.commit()
        # current_app.logger.debug(f'TRACE 1')
        simulate_match_scores(current_app, db, pool)
        # current_app.logger.debug(f'COMMIT DONE = {len(pool.matches)} MATCHES for pool {pool}')
        flash(f'{pool.championship} - Poule {pool.letter }: simulation completed!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error simulating pool: {str(e)}', 'error')

    return redirect(url_for('championship.show_pools', id=pool.championship.id))

@championship_management_bp.route('/simulate_championship/<int:championship_id>', methods=['POST'])
def simulate_championship(championship_id):
    championship = Championship.query.get_or_404(championship_id)
    # teams = Team.query.filter(Team.championshipId == championship_id).all()
    teams = Team.query.join(Pool).filter(Pool.championshipId == championship_id).all()
    try:

        # pools = Pool.query.filter(Pool.championshipId == championship.id).all()
        # current_app.logger.debug(f'COMMIT DONE = {len(pools) - int(len(exempted_teams) > 0)} POOLS of {num_teams_per_pool} teams for {championship}')
        # Section II: Génération des ordonnancements de matches
        for pool in championship.pools:
            db.session.delete(pool)
        # for matchday in championship.matchdays:
        #     db.session.delete(matchday)
        db.session.commit()
        # Section I: Génération des poules et planning de rencontres
        num_teams_per_pool, exempted_teams = create_pools_and_assign_teams(current_app, db, championship, teams)
        # Pool.query.filter(Pool.championship_id == championship.id).delete(synchronize_session=False)
        # Matchday.query.filter(Matchday.championship_id == championship.id).delete(synchronize_session=False)
        # db.session.delete_all(championship.matchdays)
        # db.session.commit()
        for pool in championship.pools:
            if pool.letter is None:
                continue
            schedule_matches(current_app, db, pool)
            # current_app.logger.debug(f'COMMIT DONE = {len(pool.matches)} MATCHES scheduled for pool {pool}')
            # Section III: Génération des feuilles de matches
            # current_app.logger.debug(f'TRACE 1')
            simulate_match_scores(current_app, db, pool)
            # current_app.logger.debug(f'COMMIT DONE = {len(pool.matches)} MATCHES for pool {pool}')
        flash(f'{championship} simulation completed!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error simulating championship: {str(e)}', 'error')

    return redirect(url_for('championship.show_championships'))

@championship_management_bp.route('/loading')
def loading():
    # Renvoyer la page de chargement
    return render_template('loading.html')

@championship_management_bp.route('/championships')
def show_championships():
    championships = Championship.query.all()
    # current_app.logger.debug(f'championships: {championships}')
    return render_template('championships.html', championships=championships)


@championship_management_bp.route('/pools/<int:id>')
def show_pools(id: int):
    # pools = Pool.query.filter_by(championshipId=championship_id).order_by(desc(Pool.name)).all()
    # pools appartenant au championship id et n'ayant pas poolId à None
    # Ascending order (A to Z)
    pools = Pool.query.filter(and_(Pool.championshipId == id, Pool.letter != None)).order_by(Pool.letter.asc()).all()
    championship = Championship.query.get(id)
    exempted_pool = Pool.query.filter(and_(Pool.championshipId == id, Pool.letter == None)).first()
    # current_app.logger.debug(f'championship: {championship} - pools: {pools} - exempted_teams: {exempted_teams}')
    return render_template('pools.html', pools=pools, championship=championship, exempted_pool=exempted_pool)


@championship_management_bp.route('/show_pool/<int:id>')
def show_pool(id: int):
    pool = Pool.query.get(id)
    # Calcul du classement de la poule
    resultat_classement = calculer_classement(pool)
    matchdays = Matchday.query.filter_by(championshipId=pool.championship.id).all() # pool.matchdays
    # current_app.logger.debug(f'matches: {pool.matches}')
    return render_template('show_pool.html', classement=resultat_classement, pool=pool, matches=pool.matches, matchdays=matchdays)

@championship_management_bp.route('/update_schedule/<int:pool_id>', methods=['POST'])
def update_schedule(pool_id: int):
    data = request.get_json()
    schedule = data.get('schedule', [])
    # current_app.logger.debug(f'schedule: {schedule}')
    try:
        for item in schedule:
            home = item['home']
            match_id = int(item['match_id'])
            team_id = int(item['team_id'])
            match = Match.query.get(match_id)
            if home:
                match.homeTeamId = team_id
            else:
                match.visitorTeamId = team_id
        # current_app.logger.debug(f'finished')

        # Check issues before commit
        pool = Pool.query.get(pool_id)
        if not pool.is_valid_schedule:
            db.session.rollback()
            # current_app.logger.debug(f'schedule: {schedule} - INCORRECT')
            return jsonify({
                'success': False,
                'error': 'incorrect schedule',
                'details': 'all teams must play against each other once'
            }), 400

        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@championship_management_bp.route('/show_match/<int:id>')
def show_match(id: int):
    match_sheet = Match.query.get(id)
    match = Match.query.get(id)
    # current_app.logger.debug(f'match: {match}')
    return render_template('show_match.html', match=match)
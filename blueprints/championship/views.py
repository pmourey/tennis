# championship/views.py
from __future__ import annotations

import string
from datetime import datetime, timedelta

from flask import request, current_app, jsonify
from sqlalchemy import desc, and_

from flask import render_template, redirect, url_for, flash

from models import AgeCategory, Division, Championship, db, Pool, Team, Matchday, Match, PoolSimulation, TeamSimulationResult
from blueprints.championship import championship_management_bp
from common import populate_championship, calculer_classement, simulate_match_scores, create_pools_and_assign_teams, schedule_matches, form_teams, get_players_order_by_ranking, remove_text_between_parentheses


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
        from models import AppSettings
        current_season = AppSettings.get_season()
        championship = Championship.query.filter_by(
            divisionId=selected_division.id, 
            season=current_season
        ).first()
        if championship:
            flash(f"Le championnat {championship} a déjà été créé pour la saison {current_season}!")
            return redirect(url_for('championship.select_division', selected_age_category_id=selected_division.ageCategoryId))
        else:
            return render_template('new_championship.html', selected_division=selected_division)
    # Retrieve the selected age category ID from the URL parameters
    selected_age_category_id = request.args.get('selected_age_category_id')
    divisions = Division.query.filter_by(ageCategoryId=selected_age_category_id).order_by(desc(Division.type)).all()
    from models import AppSettings
    current_season = AppSettings.get_season()
    
    new_divisions = []
    for division in divisions:
        championship_with_division = Championship.query.filter_by(
            divisionId=division.id, 
            season=current_season
        ).first()
        if championship_with_division:
            continue
        new_divisions.append(division)
    # current_app.logger.debug(f'divisions: {new_divisions}')
    return render_template('select_division.html', divisions=new_divisions)


@championship_management_bp.route('/new_pool/<int:championship_id>', methods=['GET', 'POST'])
def new_pool(championship_id):
    championship = Championship.query.get(championship_id)
    
    if request.method == 'POST':
        # Get selected clubs
        club_ids = request.form.getlist('clubs[]')
        club_ids = list(filter(None, club_ids))
        
        # Check for same club teams in same pool
        if len(club_ids) != len(set(club_ids)):
            from collections import Counter
            from models import Club
            duplicates = [club_id for club_id, count in Counter(club_ids).items() if count > 1]
            duplicate_names = [Club.query.get(club_id).name for club_id in duplicates]
            flash(f'Impossible de mettre plusieurs équipes du même club dans la même poule! Club(s) en erreur: {", ".join(duplicate_names)}', 'error')
            
            available_clubs = Club.query.all()
            return render_template('new_pool.html', championship=championship, clubs=available_clubs, selected_clubs=club_ids, preserve_all=True)
        
        # Create teams for selected clubs
        teams = []
        current_app.logger.debug(f'Selected club_ids: {club_ids}')
        
        for club_id in club_ids:
            current_app.logger.debug(f'Processing club_id: {club_id}')
            
            # Get existing teams for this club in championship using simple query
            existing_teams = Team.query.filter_by(clubId=club_id).filter(
                Team.poolId.in_([p.id for p in championship.pools])
            ).all()
            current_app.logger.debug(f'Existing teams for club {club_id}: {[t.name for t in existing_teams]}')
            
            # Extract existing numbers
            existing_numbers = []
            for team in existing_teams:
                parts = team.name.split(' ')
                current_app.logger.debug(f'Team name parts: {parts}')
                if parts and parts[-1].isdigit():
                    number = int(parts[-1])
                    existing_numbers.append(number)
                    current_app.logger.debug(f'Found existing number: {number}')
            
            current_app.logger.debug(f'All existing numbers for club {club_id}: {existing_numbers}')
            
            # Find next available number
            team_number = 1
            while team_number in existing_numbers:
                team_number += 1
            current_app.logger.debug(f'Next team number for club {club_id}: {team_number}')
            
            # Get club and create team directly
            from models import Club
            club = Club.query.get(club_id)
            if club:
                # Get eligible players for this club
                players = get_players_order_by_ranking(
                    gender=championship.division.gender,
                    club_id=club_id,
                    asc_param=True,
                    age_category=championship.age_category,
                    is_active=True
                )
                
                if len(players) >= championship.singlesCount:
                    captain = max(players, key=lambda p: p.best_elo)
                    club_name = remove_text_between_parentheses(club.name)
                    
                    team = Team(name=f'{club_name} {team_number}', captainId=captain.id, clubId=club_id)
                    team.players = players[:15]
                    teams.append(team)
                    current_app.logger.debug(f'Created team: {team.name} with {len(team.players)} players')
                else:
                    current_app.logger.debug(f'Club {club.name} has insufficient players: {len(players)}')
            else:
                current_app.logger.debug(f'Club {club_id} not found')
        
        current_app.logger.debug(f'Total teams created: {len(teams)}')
        
        # Create pool and assign teams
        pools = Pool.query.filter_by(championshipId=championship_id).all()
        pool_letters = [pool.letter for pool in pools if pool.letter]
        letter = chr(min([ord(l) for l in string.ascii_uppercase if l not in pool_letters])) if pool_letters else 'A'
        
        pool = Pool(letter=letter, championshipId=championship_id)
        db.session.add(pool)
        db.session.commit()
        
        # Add and commit teams first
        db.session.add_all(teams)
        db.session.commit()
        
        # Then assign to pool
        for team in teams:
            team.poolId = pool.id
        db.session.commit()
        
        schedule_matches(current_app, db, pool)
        flash(f'Poule {pool.letter} créée avec succès!', 'success')
        return redirect(url_for('championship.show_pools', id=championship_id))
    
    # Get available clubs (not teams)
    from models import Club
    available_clubs = Club.query.all()
    
    return render_template('new_pool.html', championship=championship, clubs=available_clubs)

@championship_management_bp.route('/configure_pools/<int:championship_id>', methods=['GET', 'POST'])
def configure_pools(championship_id):
    championship = Championship.query.get_or_404(championship_id)
    
    if request.method == 'POST':
        num_pools = int(request.form['num_pools'])
        
        # Create pools
        for i in range(num_pools):
            pool = Pool(letter=chr(ord('A') + i), championshipId=championship.id)
            db.session.add(pool)
        
        db.session.commit()
        flash(f'{num_pools} poules créées avec succès!', 'success')
        return redirect(url_for('championship.assign_teams', championship_id=championship.id))
    
    return render_template('configure_pools.html', championship=championship)

@championship_management_bp.route('/assign_teams/<int:championship_id>', methods=['GET', 'POST'])
def assign_teams(championship_id):
    championship = Championship.query.get_or_404(championship_id)
    
    if request.method == 'POST':
        # Process team assignments
        for pool in championship.pools:
            team_ids = request.form.getlist(f'pool_{pool.id}_teams[]')
            team_ids = list(filter(None, team_ids))
            
            for team_id in team_ids:
                team = Team.query.get(team_id)
                if team:
                    team.poolId = pool.id
        
        db.session.commit()
        
        # Schedule matches for all pools
        for pool in championship.pools:
            if pool.teams:
                schedule_matches(current_app, db, pool)
        
        flash('Equipes assignées et matches programmés avec succès!', 'success')
        return redirect(url_for('championship.show_pools', id=championship.id))
    
    # Get available teams
    available_teams = form_teams(championship, club_ids_to_filter=[])
    db.session.add_all(available_teams)
    db.session.commit()
    
    return render_template('assign_teams.html', championship=championship, teams=available_teams)

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
        from models import AppSettings
        championship = Championship(
            singlesCount=singles_count,
            doublesCount=doubles_count,
            divisionId=division_id,
            season=AppSettings.get_season()
        )

        # current_app.logger.debug(f'championship: {championship}')
        db.session.add(championship)

        try:
            db.session.commit()  # Commit championship first to get ID
            
            # Create matchdays for each selected date
            for date in selected_dates:
                report_date = date + timedelta(days=6)  # report au samedi suivant
                matchday = Matchday(date=date, report_date=report_date, championshipId=championship.id)
                championship.matchdays.append(matchday)
                db.session.add(matchday)
            
            db.session.commit()
            flash('Championnat créé avec succès!', 'success')
            return redirect(url_for('championship.configure_pools', championship_id=championship.id))
        except Exception as e:
            db.session.rollback()  # Rollback if an error occurs
            flash(f'Erreur: {e}\nImpossible de créer le championnat.', 'error')
            division = Division.query.get(division_id)
            return render_template('new_championship.html', selected_division=division)
        return render_template('championship_index.html')

    # GET request: Render the form with divisions
    divisions = Division.query.all()
    return render_template('new_championship.html', divisions=divisions)


@championship_management_bp.route('/delete_championship/<int:championship_id>', methods=['POST'])
def delete_championship(championship_id):
    championship = Championship.query.get_or_404(championship_id)

    try:
        # Get all team IDs for this championship
        team_ids = [team.id for pool in championship.pools for team in pool.teams]
        
        # Manually delete from association table
        if team_ids:
            placeholders = ','.join([f':id{i}' for i in range(len(team_ids))])
            params = {f'id{i}': team_id for i, team_id in enumerate(team_ids)}
            db.session.execute(
                db.text(f"DELETE FROM player_team_association WHERE team_id IN ({placeholders})"),
                params
            )
        
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
    teams = Team.query.join(Pool).filter(Pool.championshipId == championship_id).all()
    
    try:
        # Delete existing pools
        for pool in championship.pools:
            db.session.delete(pool)
        db.session.commit()
        
        # Create pools and assign teams
        create_pools_and_assign_teams(current_app, db, championship, teams)
        
        # Schedule and simulate matches for each pool
        for pool in championship.pools:
            if pool.letter is not None:
                schedule_matches(current_app, db, pool)
                simulate_match_scores(current_app, db, pool)
                
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
    from models import AppSettings
    current_season = AppSettings.get_season()
    
    # Get season filter from query parameter
    selected_seasons = request.args.getlist('seasons')
    if not selected_seasons:
        selected_seasons = [current_season]
    
    # Get all available seasons
    available_seasons = db.session.query(Championship.season).filter(
        Championship.season.isnot(None)
    ).distinct().order_by(Championship.season.desc()).all()
    available_seasons = [season[0] for season in available_seasons if season[0]]
    
    # Filter championships by selected seasons
    if 'all' in selected_seasons:
        championships = Championship.query.filter(Championship.season.isnot(None)).all()
        display_title = "Toutes les saisons"
    else:
        championships = Championship.query.filter(Championship.season.in_(selected_seasons)).all()
        display_title = ", ".join(selected_seasons)
    
    return render_template('championships.html', 
                         championships=championships, 
                         available_seasons=available_seasons,
                         selected_seasons=selected_seasons,
                         display_title=display_title,
                         current_season=current_season)


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
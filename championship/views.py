# championship/views.py
from __future__ import annotations

from datetime import datetime

from flask import request, current_app
from sqlalchemy import desc, and_

from flask import render_template, redirect, url_for, flash

from TennisModel import AgeCategory, Division, Championship, db, Pool, Team, Player, Matchday, Match
from championship import championship_management_bp
from common import populate_championship, calculer_classement, count_sundays_between_dates, simulate_match_scores


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
    current_app.logger.debug(f'divisions: {new_divisions}')
    return render_template('select_division.html', divisions=new_divisions)


@championship_management_bp.route('/new_championship', methods=['GET', 'POST'])
def new_championship():
    if request.method == 'POST':
        # Fetching the list of dates from the form
        date_strings = request.form.getlist('dates[]')
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

        current_app.logger.debug(f'championship: {championship}')
        db.session.add(championship)

        try:
            # Create matchdays for each selected date
            for date in selected_dates:
                matchday = Matchday(date=date, championshipId=championship.id)
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

@championship_management_bp.route('/simulate_championship/<int:championship_id>', methods=['POST'])
def simulate_championship(championship_id):
    championship = Championship.query.get_or_404(championship_id)

    try:
        # Section II: Génération des feuilles de matches
        for pool in championship.pools:
            if pool.letter is None:
                continue
            # matchdays = Matchday.query.filter_by(championshipId=pool.championship.id).all()
            # if any(matchday.matches for matchday in matchdays):
            #     for matchday in matchdays:
            #         db.session.delete(matchday.matches)
            #     db.session.commit()
            simulate_match_scores(current_app, db, pool)
            current_app.logger.debug(f'COMMIT DONE = {len(pool.matches)} MATCHES for pool {pool}')
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
    current_app.logger.debug(f'championships: {championships}')
    return render_template('championships.html', championships=championships)


@championship_management_bp.route('/pools/<int:id>')
def show_pools(id: int):
    # pools = Pool.query.filter_by(championshipId=championship_id).order_by(desc(Pool.name)).all()
    # pools appartenant au championship id et n'ayant pas poolId à None
    pools = Pool.query.filter(and_(Pool.championshipId == id, Pool.letter != None)).all()
    championship = Championship.query.get(id)
    exempted_pool = Pool.query.filter(and_(Pool.championshipId == id, Pool.letter == None)).first()
    # current_app.logger.debug(f'championship: {championship} - pools: {pools} - exempted_teams: {exempted_teams}')
    return render_template('pools.html', pools=pools, championship=championship, exempted_teams=exempted_pool.teams)


@championship_management_bp.route('/show_pool/<int:id>')
def show_pool(id: int):
    pool = Pool.query.get(id)
    # Calcul du classement de la poule
    resultat_classement = calculer_classement(pool)
    matchdays = Matchday.query.filter_by(championshipId=pool.championship.id).all() # pool.matchdays
    current_app.logger.debug(f'matches: {pool.matches}')
    return render_template('show_pool.html', classement=resultat_classement, pool=pool, matches=pool.matches, matchdays=matchdays)

@championship_management_bp.route('/show_match/<int:id>')
def show_match(id: int):
    match_sheet = Match.query.get(id)
    match = Match.query.get(id)
    current_app.logger.debug(f'match: {match}')
    return render_template('show_match.html', match=match)
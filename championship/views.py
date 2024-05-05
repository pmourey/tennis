# championship/views.py
from __future__ import annotations

from datetime import datetime

from flask import request, current_app
from sqlalchemy import desc, and_

from flask import render_template, redirect, url_for, flash

from TennisModel import AgeCategory, Division, Championship, db, Pool, Team, Player, Matchday
from championship import championship_management_bp
from common import populate_championship


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
        start_date = datetime.strptime(request.form['start_date'], '%Y-%m-%d')
        end_date = datetime.strptime(request.form['end_date'], '%Y-%m-%d')
        singles_count = int(request.form['singles_count'])
        doubles_count = int(request.form['doubles_count'])
        division_id = int(request.form['division'])  # Récupérer l'identifiant de la division sélectionnée
        championship = Championship(startDate=start_date, endDate=end_date, singlesCount=singles_count, doublesCount=doubles_count, divisionId=division_id)
        current_app.logger.debug(f'championship: {championship}')
        db.session.add(championship)
        db.session.commit()
        # Création des journées de championnat pour la saison en cours
        for date in championship.match_dates:
            matchday = Matchday(date=date, championshipId=championship.id)
            championship.matchdays.append(matchday)
            db.session.add(championship)
            db.session.add(matchday)
            db.session.commit()
        populate_championship(app=current_app, db=db, championship=championship)
        flash('Championnat créé avec succès!', 'success')
        return render_template('championship_index.html')
    divisions = AgeCategory.query.all()
    return render_template('new_championship.html', divisions=divisions)


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
    teams = Team.query.filter_by(poolId=id).all()
    pool = Pool.query.get(id)
    return render_template('pools.html', teams=teams, pool=pool)

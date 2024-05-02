# championship/views.py
from __future__ import annotations

from datetime import datetime

from flask import request, current_app
from sqlalchemy import desc

from flask import render_template, redirect, url_for, flash

from TennisModel import AgeCategory, Division, Championship, db
from championship import championship_management_bp


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

        championship = Championship(startDate=start_date, endDate=end_date, singlesCount=singles_count, doublesCount=doubles_count,
                                    divisionId=division_id)
        db.session.add(championship)
        db.session.commit()

        flash('Championnat créé avec succès!', 'success')
        return render_template('championship_index.html')
    divisions = AgeCategory.query.all()
    return render_template('new_championship.html', divisions=divisions)


@championship_management_bp.route('/list_championships')
def list_championships():
    championships = Championship.query.all()
    current_app.logger.debug(f'championships: {championships}')
    return render_template('list_championships.html', championships=championships)

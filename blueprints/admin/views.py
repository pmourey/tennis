# admin/views.py
from __future__ import annotations

import os

import pandas as pd
from flask import request, render_template, redirect, url_for, flash, make_response, current_app

from models import *
from blueprints.admin import admin_bp

from common import import_all_data, import_players
from tools.import_csv import extract


# Define routes for championship management
@admin_bp.route('/')
def index():
    return render_template('admin_index.html')


@admin_bp.route('/new_club', methods=['GET', 'POST'])
def new_club():
    if request.method == 'POST':
        club_id = request.form.get('club_id')
        club_info = [d for d in current_app.config['CLUBS'] if d['id'] == club_id][0]
        # récupération autres infos dans fichier csv du club
        BASE_PATH = os.path.dirname(__file__)
        csv_file = os.path.join(BASE_PATH, f'../../static/data/clubs.csv')
        df = pd.read_csv(csv_file)
        colonnes_a_recuperer = ['name', 'city', 'tennis_courts', 'padel_courts', 'beach_courts', 'latitude', 'longitude']
        club_tenup = extract(df=df, field_criteria='id', field_value=club_info['id'], columns=colonnes_a_recuperer)
        current_app.logger.debug(f'club_tenup: {club_tenup}')
        if club_tenup is None:
            current_app.logger.debug(f'club_tenup is None - see {club_info}')
            club = Club(id=club_info['id'], name=club_info['name'], city=club_info['city'])
        else:
            club = Club(id=club_info['id'], name=club_tenup['name'], city=club_tenup['city'], tennis_courts=club_tenup['tennis_courts'],
                        padel_courts=club_tenup['padel_courts'], beach_courts=club_tenup['beach_courts'], latitude=club_tenup['latitude'], longitude=club_tenup['longitude'])
        db.session.add(club)
        db.session.commit()
        current_app.logger.debug(f'nouveau club créé: {club}')
        message = f'Club {club} créé avec succès!\n'
        # Chargement des joueurs du club
        for gender, gender_label in enumerate(['men', 'women']):
            players_csvfile = f"static/data/players/{club_info['csvfile']}_{gender_label}.csv"
            file_path = os.path.join(current_app.config['BASE_PATH'], players_csvfile)
            current_app.logger.debug(f'players_csvfile: {file_path}')
            if not os.path.exists(file_path):
                message += f'Fichier {file_path} non trouvé!\n'
                flash(message, 'error')
                continue
            import_players(app=current_app, gender=gender, csvfile=file_path, club=club, db=db)
            # players_count = Player.query.filter(Player.clubId == club.id).count()
            players_count = Player.query.join(Player.license).filter(Player.clubId == club.id, License.gender == gender).count()
            # db.session.flush()
            message += f"{players_count} {'joueuses' if gender else 'joueurs'} ajoutés au club {club.name}!\n"
        flash(message, 'warning')
        return render_template('admin_index.html')
    clubs = Club.query.all()
    existing_clubs = [club.id for club in clubs]
    new_clubs: List[dict] = [club_info for club_info in current_app.config['CLUBS'] if club_info['id'] not in existing_clubs]
    return render_template('new_club.html', clubs=new_clubs)

@admin_bp.route('/select_club', methods=['GET', 'POST'])
def select_club():
    if request.method == 'POST':
        club_id = request.form.get('club_id')
        # Signer le club_id
        signed_club_id = current_app.serializer.dumps(club_id)
        # Stocker le club_id signé dans un cookie
        response = make_response(redirect(url_for('club.index')))
        response.set_cookie('club_id', signed_club_id)
        current_app.logger.debug(f'signed club_id: {signed_club_id}')
        return response
    # Récupérer les clubs depuis la base de données
    clubs = Club.query.all()
    if not clubs:
        # Aucune donnée en base, lancer le chargement
        message = import_all_data(current_app, db)
        flash(message, 'error')
        # return render_template('club_index.html')
        return redirect(url_for('club.index'))
    signed_club_id = request.cookies.get('club_id')
    selected_club = None
    if signed_club_id:
        try:
            club_id = current_app.serializer.loads(signed_club_id)
            selected_club = Club.query.get(club_id)
            if selected_club:
                return render_template('select_club.html', selected_club=selected_club, clubs=clubs)
        except Exception as e:
            pass
    current_app.logger.debug(f'{len(clubs)} club(s) in database!')
    return render_template('select_club.html', selected_club=selected_club, clubs=clubs)

@admin_bp.route('/delete_club', methods=['GET', 'POST'])
def delete_club():
    if request.method == 'POST':
        club_id = request.form.get('club_id')
        club = Club.query.get(club_id)
        db.session.delete(club)
        db.session.commit()
        current_app.logger.debug(f'Club {club} supprimé!')
        flash(f"Club \"{club.name}\" ne fait plus partie de l'application!")
        return redirect(url_for('admin.index'))
    clubs = Club.query.all()
    return render_template('delete_club.html', clubs=clubs)

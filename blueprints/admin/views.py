# Source Generated with Decompyle++
# File: views.cpython-310.pyc (Python 3.10)

from __future__ import annotations
import os
import pandas as pd
from flask import request, render_template, redirect, url_for, flash, make_response, current_app
from models import db, AppSettings, Club
from models import *
from blueprints.admin import admin_bp
from common import import_all_data, import_players
from tools.import_csv import extract

def index():
    return render_template('admin_index.html')

index = admin_bp.route('/')(index)

def new_club():
    if request.method == 'POST':
        club_id = request.form.get('club_id')
        club_info = (lambda .0 = None: [ d for d in .0 if d['id'] == club_id ])(current_app.config['CLUBS'])[0]
        BASE_PATH = os.path.dirname(__file__)
        csv_file = os.path.join(BASE_PATH, '../../static/data/clubs.csv')
        df = pd.read_csv(csv_file)
        colonnes_a_recuperer = [
            'name',
            'city',
            'tennis_courts',
            'padel_courts',
            'beach_courts',
            'latitude',
            'longitude']
        club_tenup = extract(df, 'id', club_info['id'], colonnes_a_recuperer, **('df', 'field_criteria', 'field_value', 'columns'))
        current_app.logger.debug(f'''club_tenup: {club_tenup}''')
        if club_tenup is None:
            current_app.logger.debug(f'''club_tenup is None - see {club_info}''')
            club = Club(club_info['id'], club_info['name'], club_info['city'], **('id', 'name', 'city'))
        else:
            club = Club(club_info['id'], club_tenup['name'], club_tenup['city'], club_tenup['tennis_courts'], club_tenup['padel_courts'], club_tenup['beach_courts'], club_tenup['latitude'], club_tenup['longitude'], **('id', 'name', 'city', 'tennis_courts', 'padel_courts', 'beach_courts', 'latitude', 'longitude'))
        db.session.add(club)
        db.session.commit()
        current_app.logger.debug(f'''nouveau club créé: {club}''')
        message = f'''Club {club} créé avec succès!\n'''
        all_conflicts = []
        for gender, gender_label in enumerate([
            'men',
            'women']):
            players_csvfile = f'''static/data/players/{club_info['csvfile']}_{gender_label}.csv'''
            file_path = os.path.join(current_app.config['BASE_PATH'], players_csvfile)
            current_app.logger.debug(f'''players_csvfile: {file_path}''')
            if not os.path.exists(file_path):
                message += f'''Fichier {file_path} non trouvé!\n'''
                flash(message, 'error')
                continue
            (success, conflicts, players_count) = import_players(current_app, gender, file_path, club, db, **('app', 'gender', 'csvfile', 'club', 'db'))
            if success and conflicts:
                all_conflicts.extend(conflicts)
                message += f'''ERREUR: {len(conflicts)} conflit(s) détecté(s) pour les {'joueuses' if gender else 'joueurs'}!\n'''
                continue
            message += f'''{players_count} {'joueuses' if gender else 'joueurs'} ajoutés au club {club.name}!\n'''
        if all_conflicts:
            db.session.delete(club)
            db.session.commit()
            flash(f'''Importation annulée : {len(all_conflicts)} joueur(s) déjà enregistré(s) dans un autre club!''', 'error')
            return render_template('import_conflicts.html', all_conflicts, club.name, **('conflicts', 'club_name'))
        None(message, 'success')
        return render_template('admin_index.html')
    clubs = None.query.all()
    existing_clubs = (lambda .0: [ club.id for club in .0 ])(clubs)
    new_clubs = (lambda .0 = None: [ club_info for club_info in .0 if club_info['id'] not in existing_clubs ])(current_app.config['CLUBS'])
    return render_template('new_club.html', new_clubs, **('clubs',))

new_club = admin_bp.route('/new_club', [
    'GET',
    'POST'], **('methods',))(new_club)

def select_club():
    if request.method == 'POST':
        club_id = request.form.get('club_id')
        signed_club_id = current_app.serializer.dumps(club_id)
        response = make_response(redirect(url_for('club.index')))
        response.set_cookie('club_id', signed_club_id)
        current_app.logger.debug(f'''signed club_id: {signed_club_id}''')
        return response
    clubs = None.query.all()
    if not clubs:
        message = import_all_data(current_app, db)
        flash(message, 'error')
        return redirect(url_for('club.index'))
    signed_club_id = None.cookies.get('club_id')
    selected_club = None
# WARNING: Decompyle incomplete

select_club = admin_bp.route('/select_club', [
    'GET',
    'POST'], **('methods',))(select_club)

def delete_club():
    if request.method == 'POST':
        club_id = request.form.get('club_id')
        club = Club.query.get(club_id)
        if club:
            players_count = len(club.players)
            club_name = club.name
            db.session.delete(club)
            db.session.commit()
            current_app.logger.debug(f'''Club {club_name} et {players_count} joueur(s) supprimés!''')
            flash(f'''Club "{club_name}" supprimé avec succès! ({players_count} joueur(s) supprimé(s) également)''', 'success')
        else:
            flash('Club non trouvé!', 'error')
        return redirect(url_for('admin.index'))
    clubs = None.query.all()
    return render_template('delete_club.html', clubs, **('clubs',))

delete_club = admin_bp.route('/delete_club', [
    'GET',
    'POST'], **('methods',))(delete_club)

def settings():
    if request.method == 'POST':
        season = request.form['season']
        AppSettings.set_season(season)
        flash(f'''Année sportive mise à jour: {season}''', 'success')
        return redirect(url_for('admin.settings'))
    current_season = None.get_season()
    
    try:
        setting = AppSettings.query.filter_by('current_season', **('key',)).first()
        if not setting:
            AppSettings.set_season(current_season)
    finally:
        pass
    existing_seasons = db.session.query(Championship.season).filter(Championship.season.isnot(None)).distinct().order_by(Championship.season.desc()).all()
    existing_seasons = (lambda .0: [ season[0] for season in .0 if season[0] ])(existing_seasons)
    return render_template('settings.html', current_season, existing_seasons, **('current_season', 'existing_seasons'))


settings = admin_bp.route('/settings', [
    'GET',
    'POST'], **('methods',))(settings)

def create_season():
    new_season = request.form['new_season']
    import re
    if not re.match('^\\d{4}/\\d{4}$', new_season):
        flash('Format de saison invalide. Utilisez YYYY/YYYY', 'error')
        return redirect(url_for('admin.settings'))
    existing_seasons = None.session.query(Championship.season).filter(Championship.season.isnot(None)).distinct().all()
    existing_seasons = (lambda .0: [ season[0] for season in .0 if season[0] ])(existing_seasons)
    if new_season in existing_seasons:
        flash(f'''La saison {new_season} existe déjà!''', 'error')
        return redirect(url_for('admin.settings'))
    None.set_season(new_season)
    flash(f'''Nouvelle saison {new_season} créée et activée!''', 'success')
    return redirect(url_for('admin.settings'))

create_season = admin_bp.route('/create_season', [
    'POST'], **('methods',))(create_season)

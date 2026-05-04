# Source Generated with Decompyle++
# File: views.cpython-310.pyc (Python 3.10)

"""
Vues du module Tournoi Interne.
Routes disponibles :
  /tournament/                           liste des tournois
  /tournament/create                     créer un tournoi
  /tournament/<id>                       détail du tournoi
  /tournament/<id>/edit                  modifier le tournoi
  /tournament/<id>/categories            gérer les catégories
  /tournament/<id>/courts                gérer les terrains
  /tournament/<id>/registrations/<cat_id>  inscriptions d'une catégorie
  /tournament/<id>/generate-draw/<cat_id>  générer le tableau
  /tournament/<id>/draw/<draw_id>          afficher le tableau
  /tournament/<id>/match/<mid>/score       saisir un résultat
  /tournament/<id>/schedule/<draw_id>      planifier les matchs
  /tournament/<id>/export-pdf/<draw_id>    exporter en PDF
"""
from __future__ import annotations
import io
import random
from datetime import date, datetime, timedelta
from flask import abort, flash, jsonify, redirect, render_template, request, send_file, url_for
from blueprints.tournament import tournament_bp
from extensions import db
from models import AgeCategory, Club, Player, Ranking, Tournament, TournamentAvailability, TournamentCategory, TournamentCourt, TournamentDraw, TournamentMatch, TournamentRegistration

def _get_tournament_or_404(tid = None):
    t = Tournament.query.get(tid)
    if not t:
        abort(404)
    return t


def index():
    tournaments = Tournament.query.order_by(Tournament.start_date.desc()).all()
    clubs = Club.query.order_by(Club.name).all()
    return render_template('tournament/index.html', tournaments, clubs, **('tournaments', 'clubs'))

index = tournament_bp.route('/')(index)

def create():
    clubs = Club.query.order_by(Club.name).all()
    age_categories = AgeCategory.query.order_by(AgeCategory.type, AgeCategory.minAge).all()
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        club_id = request.form.get('club_id')
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        is_open = request.form.get('is_open') == '1'
        surface = request.form.get('surface', 'TB')
        notes = request.form.get('notes', '')
        if not all([
            name,
            club_id,
            start_date,
            end_date]):
            flash('Tous les champs obligatoires doivent être remplis.', 'danger')
            return render_template('tournament/create.html', clubs, age_categories, **('clubs', 'age_categories'))
        tournament = None(name, club_id, datetime.strptime(start_date, '%Y-%m-%d').date(), datetime.strptime(end_date, '%Y-%m-%d').date(), is_open, surface, 'DRAFT', notes, **('name', 'club_id', 'start_date', 'end_date', 'is_open', 'surface', 'status', 'notes'))
        db.session.add(tournament)
        db.session.flush()
        court_names = request.form.getlist('court_name[]')
        court_surfaces = request.form.getlist('court_surface[]')
        for i, cname in enumerate(court_names):
            cname = cname.strip()
            if cname:
                court = TournamentCourt(tournament.id, cname, court_surfaces[i] if i < len(court_surfaces) else surface, **('tournament_id', 'name', 'surface'))
                db.session.add(court)
        db.session.commit()
        flash(f'''Tournoi « {name} » créé avec succès.''', 'success')
        return redirect(url_for('tournament.detail', tournament.id, **('tid',)))
    return None('tournament/create.html', clubs, age_categories, **('clubs', 'age_categories'))

create = tournament_bp.route('/create', [
    'GET',
    'POST'], **('methods',))(create)

def _draw_generation_type(category = None):
    """Déduit le type de génération du tableau d'une catégorie depuis sa structure.
    Retourne 'classique', 'cascade' ou 'sections'.
    """
    draws = category.draws
    qual_draws = (lambda .0: [ d for d in .0 if d.draw_type == 'QUALIFYING' ])(draws)
    if not qual_draws:
        return 'classique'
    main_draw = None((lambda .0: 
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

from flask import (abort, flash, jsonify, redirect, render_template, request,
                   send_file, url_for)

from blueprints.tournament import tournament_bp
from extensions import db
from models import (AgeCategory, Club, Player, Ranking, Tournament,
                    TournamentAvailability, TournamentCategory,
                    TournamentCourt, TournamentDraw, TournamentMatch,
                    TournamentRegistration)

# ─── Helpers ──────────────────────────────────────────────────────────────────

def _get_tournament_or_404(tid: int) -> Tournament:
    t = Tournament.query.get(tid)
    if not t:
        abort(404)
    return t


# ─── Liste des tournois ────────────────────────────────────────────────────────

@tournament_bp.route('/')
def index():
    tournaments = Tournament.query.order_by(Tournament.start_date.desc()).all()
    clubs = Club.query.order_by(Club.name).all()
    return render_template('tournament/index.html', tournaments=tournaments, clubs=clubs)


# ─── Création d'un tournoi ────────────────────────────────────────────────────

@tournament_bp.route('/create', methods=['GET', 'POST'])
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

        if not all([name, club_id, start_date, end_date]):
            flash('Tous les champs obligatoires doivent être remplis.', 'danger')
            return render_template('tournament/create.html', clubs=clubs, age_categories=age_categories)

        tournament = Tournament(
            name=name,
            club_id=club_id,
            start_date=datetime.strptime(start_date, '%Y-%m-%d').date(),
            end_date=datetime.strptime(end_date, '%Y-%m-%d').date(),
            is_open=is_open,
            surface=surface,
            status='DRAFT',
            notes=notes
        )
        db.session.add(tournament)
        db.session.flush()

        # Terrains saisis
        court_names = request.form.getlist('court_name[]')
        court_surfaces = request.form.getlist('court_surface[]')
        for i, cname in enumerate(court_names):
            cname = cname.strip()
            if cname:
                court = TournamentCourt(
                    tournament_id=tournament.id,
                    name=cname,
                    surface=court_surfaces[i] if i < len(court_surfaces) else surface
                )
                db.session.add(court)

        db.session.commit()
        flash(f'Tournoi « {name} » créé avec succès.', 'success')
        return redirect(url_for('tournament.detail', tid=tournament.id))

    return render_template('tournament/create.html', clubs=clubs, age_categories=age_categories)


# ─── Détail d'un tournoi ───────────────────────────────────────────────────────

def _draw_generation_type(category) -> str:
    """Déduit le type de génération du tableau d'une catégorie depuis sa structure.
    Retourne 'classique', 'cascade' ou 'sections'.
    """
    draws = category.draws
    qual_draws = [d for d in draws if d.draw_type == 'QUALIFYING']
    if not qual_draws:
        return 'classique'

    main_draw = next((d for d in draws if d.draw_type == 'MAIN'), None)
    if not main_draw:
        return 'classique'

    main_match_ids = {m.id for m in main_draw.matches}
    # Si un tableau qualificatif pointe vers un match qui n'est PAS dans le tableau final
    # → il pointe vers un autre tableau qualificatif → c'est de la cascade
    for qd in qual_draws:
        if qd.main_draw_match_id and qd.main_draw_match_id not in main_match_ids:
            return 'cascade'
    return 'sections'


@tournament_bp.route('/<int:tid>')
def detail(tid: int):
    tournament = _get_tournament_or_404(tid)
    age_categories = AgeCategory.query.order_by(AgeCategory.type, AgeCategory.minAge).all()
    rankings = Ranking.query.order_by(Ranking.id).all()
    draw_types = {cat.id: _draw_generation_type(cat) for cat in tournament.categories}
    return render_template('tournament/detail.html', tournament=tournament,
                           age_categories=age_categories, rankings=rankings,
                           draw_types=draw_types)


# ─── Modifier le statut ────────────────────────────────────────────────────────

@tournament_bp.route('/<int:tid>/status/<new_status>', methods=['POST'])
def set_status(tid: int, new_status: str):
    tournament = _get_tournament_or_404(tid)
    valid = ['DRAFT', 'OPEN', 'IN_PROGRESS', 'CLOSED']
    if new_status in valid:
        tournament.status = new_status
        db.session.commit()
        flash(f'Statut mis à jour : {tournament.status_label}', 'success')
    return redirect(url_for('tournament.detail', tid=tid))


# ─── Ajouter une catégorie ─────────────────────────────────────────────────────

@tournament_bp.route('/<int:tid>/add-category', methods=['POST'])
def add_category(tid: int):
    tournament = _get_tournament_or_404(tid)
    age_cat_id = request.form.get('age_category_id') or None
    gender = int(request.form.get('gender', 0))
    game_format = int(request.form.get('game_format', 1))
    min_ranking_id = request.form.get('min_ranking_id') or None
    max_ranking_id = request.form.get('max_ranking_id') or None
    allowed_series_list = request.form.getlist('allowed_series[]')
    allowed_series = ','.join(allowed_series_list) if allowed_series_list else None
    surfaces_list = request.form.getlist('surfaces[]')
    surfaces = ','.join(surfaces_list) if surfaces_list else 'TB'

    cat = TournamentCategory(
        tournament_id=tid,
        age_category_id=age_cat_id,
        gender=gender,
        game_format=game_format,
        min_ranking_id=min_ranking_id,
        max_ranking_id=max_ranking_id,
        allowed_series=allowed_series,
        surfaces=surfaces
    )
    db.session.add(cat)
    db.session.commit()
    flash('Catégorie ajoutée.', 'success')
    return redirect(url_for('tournament.detail', tid=tid))


@tournament_bp.route('/<int:tid>/delete-category/<int:cid>', methods=['POST'])
def delete_category(tid: int, cid: int):
    cat = TournamentCategory.query.get_or_404(cid)
    db.session.delete(cat)
    db.session.commit()
    flash('Catégorie supprimée.', 'success')
    return redirect(url_for('tournament.detail', tid=tid))


# ─── Gérer les terrains ────────────────────────────────────────────────────────

@tournament_bp.route('/<int:tid>/add-court', methods=['POST'])
def add_court(tid: int):
    _get_tournament_or_404(tid)
    name = request.form.get('name', '').strip()
    surface = request.form.get('surface', '')
    if name:
        court = TournamentCourt(tournament_id=tid, name=name, surface=surface)
        db.session.add(court)
        db.session.commit()
        flash('Terrain ajouté.', 'success')
    return redirect(url_for('tournament.detail', tid=tid))


@tournament_bp.route('/<int:tid>/delete-court/<int:coid>', methods=['POST'])
def delete_court(tid: int, coid: int):
    court = TournamentCourt.query.get_or_404(coid)
    db.session.delete(court)
    db.session.commit()
    flash('Terrain supprimé.', 'success')
    return redirect(url_for('tournament.detail', tid=tid))


# ─── Inscriptions d'une catégorie ─────────────────────────────────────────────

@tournament_bp.route('/<int:tid>/registrations/<int:cid>')
def registrations(tid: int, cid: int):
    tournament = _get_tournament_or_404(tid)
    category = TournamentCategory.query.get_or_404(cid)

    # Joueurs éligibles (du club pour interne, tous pour open)
    gender_filter = category.gender if category.gender != 2 else None
    players_query = Player.query.join(Player.license)

    if not tournament.is_open:
        players_query = players_query.filter(Player.clubId == tournament.club_id)
    if gender_filter is not None:
        from models import License
        players_query = players_query.filter(License.gender == gender_filter)

    all_players = players_query.all()

    # Filtrer par catégorie d'âge
    if category.age_category:
        eligible = [p for p in all_players if p.has_valid_age(category.age_category)]
    else:
        eligible = all_players

    # Filtrer par classement minimum (plancher)
    if category.min_ranking_id:
        eligible = [p for p in eligible if p.ranking.id <= category.min_ranking_id]
    # Filtrer par classement maximum (plafond)
    if category.max_ranking_id:
        eligible = [p for p in eligible if p.ranking.id >= category.max_ranking_id]
    # Filtrer par séries autorisées
    allowed_series = category.allowed_series_list
    if allowed_series:
        eligible = [p for p in eligible if p.ranking.series in allowed_series]

    registered_ids = {r.player_id for r in category.registrations if r.status != 'WITHDRAWN'}
    return render_template('tournament/registrations.html',
                           tournament=tournament, category=category,
                           eligible_players=eligible, registered_ids=registered_ids)


@tournament_bp.route('/<int:tid>/register/<int:cid>', methods=['POST'])
def register_player(tid: int, cid: int):
    category = TournamentCategory.query.get_or_404(cid)
    player_id = int(request.form.get('player_id'))

    # Vérifier les restrictions de classement et de série
    player = Player.query.get_or_404(player_id)
    if category.min_ranking_id and player.ranking.id > category.min_ranking_id:
        flash(
            f'Inscription refusée : {player.name} ({player.ranking.value}) '
            f'ne satisfait pas le classement minimum autorisé '
            f'({category.min_ranking.value}).', 'danger'
        )
        return redirect(url_for('tournament.registrations', tid=tid, cid=cid))
    if category.max_ranking_id and player.ranking.id < category.max_ranking_id:
        flash(
            f'Inscription refusée : {player.name} ({player.ranking.value}) '
            f'est trop bien classé(e) pour cette catégorie '
            f'(plafond : {category.max_ranking.value}).', 'danger'
        )
        return redirect(url_for('tournament.registrations', tid=tid, cid=cid))
    allowed_series = category.allowed_series_list
    if allowed_series and player.ranking.series not in allowed_series:
        series_labels = {1: '1ère série', 2: '2ème série', 3: '3ème série', 4: '4ème série'}
        allowed_str = ', '.join(series_labels.get(s, str(s)) for s in allowed_series)
        flash(
            f'Inscription refusée : {player.name} ({player.ranking.value}) '
            f'n\'appartient pas aux séries autorisées ({allowed_str}).', 'danger'
        )
        return redirect(url_for('tournament.registrations', tid=tid, cid=cid))

    existing = TournamentRegistration.query.filter_by(
        category_id=cid, player_id=player_id
    ).first()

    if existing:
        if existing.status == 'WITHDRAWN':
            existing.status = 'REGISTERED'
            db.session.commit()
            flash('Joueur réinscrit.', 'success')
        else:
            flash('Joueur déjà inscrit.', 'warning')
    else:
        reg = TournamentRegistration(
            tournament_id=tid,
            category_id=cid,
            player_id=player_id,
            status='REGISTERED'
        )
        db.session.add(reg)

        # Générer des disponibilités aléatoires pour démo
        for day_type in ['weekday', 'weekend']:
            avail = TournamentAvailability(
                registration_id=None,  # sera rempli après flush
                day_type=day_type,
                time_start='09:00',
                time_end='21:00'
            )
            reg.availabilities.append(avail)

        db.session.commit()
        flash('Joueur inscrit avec succès.', 'success')

    return redirect(url_for('tournament.registrations', tid=tid, cid=cid))


@tournament_bp.route('/<int:tid>/withdraw/<int:rid>', methods=['POST'])
def withdraw_player(tid: int, rid: int):
    reg = TournamentRegistration.query.get_or_404(rid)
    cid = reg.category_id
    reg.status = 'WITHDRAWN'
    db.session.commit()
    flash('Joueur désinscrit.', 'info')
    return redirect(url_for('tournament.registrations', tid=tid, cid=cid))


@tournament_bp.route('/<int:tid>/withdraw-draw/<int:rid>', methods=['POST'])
def withdraw_with_draw(tid: int, rid: int):
    """Désinscrire un joueur et gérer son forfait dans les tableaux (Art. 52, hors TMC)."""
    reg = TournamentRegistration.query.get_or_404(rid)
    cid = reg.category_id

    from blueprints.tournament.draw_generator import (can_player_be_withdrawn,
                                                      forfeit_player_in_draw)
    can_w, msg = can_player_be_withdrawn(reg.player_id, cid)
    if not can_w:
        flash(msg, 'danger')
        return redirect(url_for('tournament.registrations', tid=tid, cid=cid))

    affected = forfeit_player_in_draw(reg.player_id, cid)
    reg.status = 'WITHDRAWN'
    db.session.commit()
    if affected:
        flash(f'{reg.player.name} retiré(e) du tournoi — {len(affected)} match(s) traité(s) en WO.', 'success')
    else:
        flash(f'{reg.player.name} retiré(e) du tournoi.', 'success')
    return redirect(url_for('tournament.registrations', tid=tid, cid=cid))


@tournament_bp.route('/<int:tid>/bulk-withdraw/<int:cid>', methods=['POST'])
def bulk_withdraw(tid: int, cid: int):
    """Désinscrire plusieurs joueurs en une seule opération."""
    reg_ids = request.form.getlist('reg_ids[]')
    if not reg_ids:
        flash('Aucun joueur sélectionné.', 'warning')
        return redirect(url_for('tournament.registrations', tid=tid, cid=cid))
    count = 0
    for rid in reg_ids:
        reg = TournamentRegistration.query.get(int(rid))
        if reg and reg.category_id == cid and reg.status == 'REGISTERED':
            reg.status = 'WITHDRAWN'
            count += 1
    db.session.commit()
    flash(f'{count} joueur(s) désinscrit(s).', 'success')
    return redirect(url_for('tournament.registrations', tid=tid, cid=cid))


@tournament_bp.route('/<int:tid>/waitlist/<int:cid>', methods=['POST'])
def add_to_waitlist(tid: int, cid: int):
    """Ajouter un joueur en liste d'attente (après génération des tableaux)."""
    player_id = int(request.form.get('player_id'))
    existing = TournamentRegistration.query.filter_by(category_id=cid, player_id=player_id).first()
    if existing:
        if existing.status in ('WITHDRAWN',):
            existing.status = 'WAITLISTED'
            db.session.commit()
            flash('Joueur mis en liste d\'attente.', 'success')
        else:
            flash('Joueur déjà inscrit ou en liste d\'attente.', 'warning')
    else:
        reg = TournamentRegistration(
            tournament_id=tid, category_id=cid, player_id=player_id, status='WAITLISTED'
        )
        db.session.add(reg)
        db.session.commit()
        flash('Joueur ajouté en liste d\'attente.', 'success')
    return redirect(url_for('tournament.registrations', tid=tid, cid=cid))


@tournament_bp.route('/<int:tid>/promote-waitlist/<int:rid>/<int:mid>', methods=['POST'])
def promote_waitlist(tid: int, rid: int, mid: int):
    """Promouvoir un joueur de la liste d'attente pour remplacer un forfait dans un match."""
    reg = TournamentRegistration.query.get_or_404(rid)
    match = TournamentMatch.query.get_or_404(mid)
    slot = request.form.get('slot', 'p1')

    reg.status = 'REGISTERED'
    if slot == 'p1':
        match.player1_id = reg.player_id
    else:
        match.player2_id = reg.player_id

    if match.player1_id and match.player2_id:
        match.status = 'PENDING'
        match.score_text = None
        match.winner_id = None

    db.session.commit()
    flash(f'{reg.player.name} promu(e) depuis la liste d\'attente.', 'success')
    return redirect(url_for('tournament.show_draw', tid=tid, draw_id=match.draw_id))


@tournament_bp.route('/<int:tid>/match/<int:mid>/requalify', methods=['GET', 'POST'])
def requalify(tid: int, mid: int):
    """Requalification d'un joueur forfait (Art. 52.2, hors TMC)."""
    tournament = _get_tournament_or_404(tid)
    match = TournamentMatch.query.get_or_404(mid)

    from blueprints.tournament.draw_generator import \
        find_requalification_candidate
    from models import Player
    candidate_id, source_match = find_requalification_candidate(match)
    candidate = Player.query.get(candidate_id) if candidate_id else None

    if request.method == 'POST':
        if not candidate_id:
            flash('Aucun candidat à la requalification trouvé pour ce match.', 'danger')
            return redirect(url_for('tournament.show_draw', tid=tid, draw_id=match.draw_id))

        # Identifier le joueur WO à remplacer
        if match.winner_id == match.player1_id:
            wo_player_id = match.player2_id
        elif match.winner_id == match.player2_id:
            wo_player_id = match.player1_id
        else:
            flash('Match invalide pour requalification.', 'danger')
            return redirect(url_for('tournament.show_draw', tid=tid, draw_id=match.draw_id))

        draw = match.draw
        # Remplacer wo_player par candidate dans tous les matchs futurs PENDING
        future_matches = TournamentMatch.query.filter_by(draw_id=draw.id).filter(
            TournamentMatch.status.in_(['PENDING', 'SCHEDULED'])
        ).all()
        replaced = 0
        for nm in future_matches:
            if nm.player1_id == wo_player_id:
                nm.player1_id = candidate_id
                replaced += 1
            if nm.player2_id == wo_player_id:
                nm.player2_id = candidate_id
                replaced += 1

        db.session.commit()
        flash(f'Requalification effectuée : {candidate.name} remplace le joueur forfait dans {replaced} match(s).', 'success')
        return redirect(url_for('tournament.show_draw', tid=tid, draw_id=match.draw_id))

    return render_template('tournament/requalify.html',
                           tournament=tournament, match=match,
                           candidate=candidate, source_match=source_match)


@tournament_bp.route('/<int:tid>/convocations')
def convocations(tid: int):
    """Page de consultation des convocations et alertes de saisie (J/A)."""
    tournament = _get_tournament_or_404(tid)
    now = datetime.utcnow()
    deadline_48h = now - timedelta(hours=48)

    scheduled = []   # matchs planifiés à venir
    overdue = []     # matchs dont le résultat devrait être saisi (>48h)

    for cat in tournament.categories:
        for draw in cat.draws:
            for m in draw.matches:
                if m.status == 'BYE':
                    continue
                if m.status in ('SCHEDULED', 'PENDING') and m.player1 and m.player2:
                    scheduled.append(m)
                if (m.status == 'SCHEDULED' and m.scheduled_at
                        and m.scheduled_at < deadline_48h):
                    overdue.append(m)

    scheduled.sort(key=lambda m: (m.scheduled_at or datetime(9999, 1, 1)))
    overdue.sort(key=lambda m: m.scheduled_at)

    return render_template('tournament/convocations.html',
                           tournament=tournament,
                           scheduled=scheduled,
                           overdue=overdue,
                           now=now)


@tournament_bp.route('/<int:tid>/seed/<int:rid>', methods=['POST'])
def toggle_seed(tid: int, rid: int):
    reg = TournamentRegistration.query.get_or_404(rid)
    reg.is_seeded = not reg.is_seeded
    if not reg.is_seeded:
        reg.seed_number = None
    else:
        # Calculer le numéro de tête de série
        seeds = TournamentRegistration.query.filter_by(
            category_id=reg.category_id, is_seeded=True
        ).count()
        reg.seed_number = seeds
    db.session.commit()
    return redirect(url_for('tournament.registrations', tid=tid, cid=reg.category_id))


@tournament_bp.route('/<int:tid>/edit-availability/<int:rid>', methods=['POST'])
def edit_availability(tid: int, rid: int):
    reg = TournamentRegistration.query.get_or_404(rid)
    # Supprimer et recréer les disponibilités
    for a in reg.availabilities:
        db.session.delete(a)

    day_types = request.form.getlist('day_type[]')
    time_starts = request.form.getlist('time_start[]')
    time_ends = request.form.getlist('time_end[]')
    for i, dt in enumerate(day_types):
        if dt:
            avail = TournamentAvailability(
                registration_id=rid,
                day_type=dt,
                time_start=time_starts[i] if i < len(time_starts) else '09:00',
                time_end=time_ends[i] if i < len(time_ends) else '21:00'
            )
            db.session.add(avail)

    db.session.commit()
    flash('Disponibilités mises à jour.', 'success')
    return redirect(url_for('tournament.registrations', tid=tid, cid=reg.category_id))


# ─── Génération du tableau ────────────────────────────────────────────────────

def _check_can_generate(category, redirect_target):
    """Vérifie que la génération est autorisée selon le statut du tournoi.
    Retourne None si OK, sinon une réponse redirect avec flash d'erreur."""
    from blueprints.tournament.draw_generator import can_generate_draw
    ok, msg = can_generate_draw(category)
    if not ok:
        flash(msg, 'danger')
        return redirect_target
    return None


@tournament_bp.route('/<int:tid>/generate-draw/<int:cid>', methods=['POST'])
def generate_draw(tid: int, cid: int):
    """Tableau classique à départ en ligne (Art. 47 FFT) — BYEs adjacents aux TdS."""
    from blueprints.tournament.draw_generator import generate_draws
    category = TournamentCategory.query.get_or_404(cid)
    guard = _check_can_generate(
        category,
        redirect(url_for('tournament.registrations', tid=tid, cid=cid))
    )
    if guard:
        return guard
    draws = generate_draws(category)
    if draws:
        flash(f'Tableau classique généré pour {category.name} ({len(draws)} tableau(x)).', 'success')
        main_draw = next((d for d in draws if d.draw_type == 'MAIN'), draws[0])
        return redirect(url_for('tournament.show_draw', tid=tid, draw_id=main_draw.id))
    else:
        flash('Pas assez de joueurs inscrits (minimum 2).', 'warning')
        return redirect(url_for('tournament.registrations', tid=tid, cid=cid))


@tournament_bp.route('/<int:tid>/generate-draw-tranche/<int:cid>', methods=['POST'])
def generate_draw_tranche(tid: int, cid: int):
    """Tableau en cascade : qualificatifs chaînés par tranche de classement + tableau final."""
    import logging

    from blueprints.tournament.draw_generator import generate_draws_by_tranche
    logger = logging.getLogger(__name__)
    category = TournamentCategory.query.get_or_404(cid)
    guard = _check_can_generate(
        category,
        redirect(url_for('tournament.registrations', tid=tid, cid=cid))
    )
    if guard:
        return guard
    draws = generate_draws_by_tranche(category)
    if draws:
        nb_qualif = sum(1 for d in draws if d.draw_type == 'QUALIFYING')
        nb_main = sum(1 for d in draws if d.draw_type == 'MAIN')
        logger.info(f'[DRAW GEN] Tableaux générés: {nb_qualif} qualif + {nb_main} final pour catégorie {cid}')
        for d in draws:
            logger.info(f'  → Draw id={d.id} type={d.draw_type} name={d.name} matches={len(d.matches)}')
        flash(f'Tableau en cascade : {nb_qualif} qualificatif(s) + {nb_main} tableau final.', 'success')
        main_draw = next((d for d in draws if d.draw_type == 'MAIN'), draws[-1])
        return redirect(url_for('tournament.show_draw', tid=tid, draw_id=main_draw.id))
    else:
        flash('Pas assez de joueurs inscrits (minimum 2).', 'warning')
        return redirect(url_for('tournament.registrations', tid=tid, cid=cid))


@tournament_bp.route('/<int:tid>/generate-section-draw/<int:cid>', methods=['POST'])
def generate_section_draw(tid: int, cid: int):
    """
    Génération d'un tableau à sections (Art. 49 FFT).

    Chaque section est un tableau classique indépendant qualifiant 1 joueur
    pour le tableau final. Chaque section a exactement 1 tête de série,
    placée en bas de section (Art. 46-1-e-ii). Les joueurs d'un même
    classement sont regroupés dans les mêmes sections (Art. 45-3-e).
    """
    from blueprints.tournament.draw_generator import \
        generate_section_draw as _gen_sections
    category = TournamentCategory.query.get_or_404(cid)
    guard = _check_can_generate(
        category,
        redirect(url_for('tournament.registrations', tid=tid, cid=cid))
    )
    if guard:
        return guard
    num_sections = request.form.get('num_sections', type=int)
    draws = _gen_sections(category, num_sections=num_sections)
    if draws:
        nb_sections = sum(1 for d in draws if d.draw_type == 'QUALIFYING')
        flash(
            f'Tableau à sections généré : {nb_sections} section(s) qualificative(s) '
            f'+ 1 tableau final (Art. 49 FFT).',
            'success'
        )
        main_draw = next((d for d in draws if d.draw_type == 'MAIN'), draws[-1])
        return redirect(url_for('tournament.show_draw', tid=tid, draw_id=main_draw.id))
    else:
        flash('Pas assez de joueurs inscrits (minimum 2).', 'warning')
        return redirect(url_for('tournament.registrations', tid=tid, cid=cid))


# ─── Suppression d'un tableau ─────────────────────────────────────────────────

@tournament_bp.route('/<int:tid>/delete-draw/<int:draw_id>', methods=['POST'])
def delete_draw(tid: int, draw_id: int):
    """
    Supprime un tableau et toutes ses données (matchs, planification).
    Bloqué si le tournoi est CLOSED ou si des matchs COMPLETED/WALKOVER existent.
    """
    draw = TournamentDraw.query.get_or_404(draw_id)
    category = draw.category
    tournament = category.tournament

    if tournament.status == 'CLOSED':
        flash('Impossible de supprimer un tableau d\'un tournoi terminé.', 'danger')
        return redirect(url_for('tournament.detail', tid=tid))

    # Vérifier s'il y a des matchs joués
    played = sum(1 for m in draw.matches if m.status in ('COMPLETED', 'WALKOVER'))
    if played > 0 and tournament.status == 'IN_PROGRESS':
        flash(
            f'Ce tableau contient {played} match(s) déjà joué(s). '
            'Suppression impossible une fois le tournoi commencé (Art. 50-3 FFT).',
            'danger'
        )
        return redirect(url_for('tournament.show_draw', tid=tid, draw_id=draw_id))

    draw_name = draw.display_name
    db.session.delete(draw)
    db.session.commit()
    flash(f'Tableau « {draw_name} » supprimé avec toutes ses données de planification.', 'success')
    return redirect(url_for('tournament.detail', tid=tid))


# ─── Suppression d'un tournoi ─────────────────────────────────────────────────

@tournament_bp.route('/<int:tid>/delete', methods=['POST'])
def delete_tournament(tid: int):
    """
    Supprime un tournoi et toutes ses données (catégories, tableaux, matchs,
    inscriptions, disponibilités, terrains).
    Requiert que le tournoi soit en statut DRAFT ou OPEN.
    Les tournois IN_PROGRESS ou CLOSED ne peuvent être supprimés que si
    le J/A confirme explicitement via le paramètre 'force'.
    """
    tournament = _get_tournament_or_404(tid)
    force = request.form.get('force') == '1'

    if tournament.status in ('IN_PROGRESS', 'CLOSED') and not force:
        flash(
            f'Le tournoi « {tournament.name} » est en statut « {tournament.status_label} ». '
            'Confirmez la suppression depuis la page de détail.',
            'warning'
        )
        return redirect(url_for('tournament.detail', tid=tid))

    name = tournament.name
    db.session.delete(tournament)
    db.session.commit()
    flash(f'Tournoi « {name} » supprimé définitivement.', 'success')
    return redirect(url_for('tournament.index'))


# ─── Affichage du tableau ──────────────────────────────────────────────────────

@tournament_bp.route('/<int:tid>/draw/<int:draw_id>')
def show_draw(tid: int, draw_id: int):
    tournament = _get_tournament_or_404(tid)
    draw = TournamentDraw.query.get_or_404(draw_id)

    # Organiser les matchs par round
    from collections import defaultdict
    matches_by_round = defaultdict(list)
    for m in sorted(draw.matches, key=lambda x: x.position):
        matches_by_round[m.round_number].append(m)

    total_rounds = max(matches_by_round.keys()) if matches_by_round else 0

    # Navigation : tous les tableaux de la catégorie, qualifs d'abord puis final
    all_draws = sorted(
        draw.category.draws,
        key=lambda d: (0 if d.draw_type == 'QUALIFYING' else 1, d.id)
    )
    current_idx = next((i for i, d in enumerate(all_draws) if d.id == draw_id), 0)
    prev_draw = all_draws[current_idx - 1] if current_idx > 0 else None
    next_draw = all_draws[current_idx + 1] if current_idx < len(all_draws) - 1 else None

    # Stats de progression par tableau
    draw_stats = {}
    for d in all_draws:
        total_m = len([m for m in d.matches if m.status != 'BYE'])
        done_m  = len([m for m in d.matches if m.status in ('COMPLETED', 'WALKOVER')])
        draw_stats[d.id] = {'total': total_m, 'done': done_m}

    # ── Réparer silencieusement les propagations BYE manquantes ─────────────
    # Certains tableaux générés ont pu rater la propagation (session flush tardif).
    _matches_map = {(m.round_number, m.position): m for m in draw.matches}
    _repaired = False
    for _m in sorted(draw.matches, key=lambda x: (x.round_number, x.position)):
        if _m.status == 'BYE' and _m.winner_id:
            _nr = _m.round_number + 1
            _np = (_m.position + 1) // 2   # équivalent à math.ceil(position/2)
            _nm = _matches_map.get((_nr, _np))
            if _nm:
                if _m.position % 2 == 1 and _nm.player1_id is None:
                    _nm.player1_id = _m.winner_id
                    _repaired = True
                elif _m.position % 2 == 0 and _nm.player2_id is None:
                    _nm.player2_id = _m.winner_id
                    _repaired = True
    if _repaired:
        db.session.commit()

    # Source match map : nested [next_round][next_position][slot] → source match
    # Permet d'afficher le bouton "Saisir score" dans le match suivant
    source_match_map = {}
    for m in draw.matches:
        nr = m.round_number + 1
        np = (m.position + 1) // 2
        sl = 'p1' if m.position % 2 == 1 else 'p2'
        source_match_map.setdefault(nr, {}).setdefault(np, {})[sl] = m

    # Qualifying finals map using explicit links on TournamentDraw
    # qualif_finals_map: "matchid_slot" → qualifying final match
    # qualif_info_map: "matchid_slot" → { 'qnum': int, 'draw': TournamentDraw, 'final_match': TournamentMatch }
    qualif_finals_map = {}
    qualif_info_map = {}
    if draw.draw_type == 'MAIN':
        qual_draws = TournamentDraw.query.filter_by(
            category_id=draw.category_id, draw_type='QUALIFYING'
        ).order_by(TournamentDraw.id).all()
        for qd in qual_draws:
            if qd.main_draw_match_id and qd.main_draw_slot:
                key = f'{qd.main_draw_match_id}_{qd.main_draw_slot}'
                max_r = max((qm.round_number for qm in qd.matches), default=0)
                finals = [qm for qm in qd.matches if qm.round_number == max_r]
                final_m = finals[0] if finals else None
                if final_m:
                    qualif_finals_map[key] = final_m
                qualif_info_map[key] = {
                    'qnum': qd.qualif_number if qd.qualif_number is not None else '?',
                    'draw': qd,
                    'final_match': final_m,
                }

    # Alertes J/A
    overdue_count = sum(
        1 for m in draw.matches
        if m.status == 'SCHEDULED' and m.scheduled_at
        and m.scheduled_at < datetime.utcnow() - timedelta(hours=48)
    )

    return render_template('tournament/draw.html',
                           tournament=tournament, draw=draw,
                           matches_by_round=dict(matches_by_round),
                           total_rounds=total_rounds,
                           all_draws=all_draws, prev_draw=prev_draw,
                           next_draw=next_draw, draw_stats=draw_stats,
                           source_match_map=source_match_map,
                           qualif_finals_map=qualif_finals_map,
                           qualif_info_map=qualif_info_map,
                           overdue_count=overdue_count)


# ─── Saisie du résultat ────────────────────────────────────────────────────────

@tournament_bp.route('/<int:tid>/match/<int:mid>/score', methods=['GET', 'POST'])
def enter_score(tid: int, mid: int):
    tournament = _get_tournament_or_404(tid)
    match = TournamentMatch.query.get_or_404(mid)

    if request.method == 'POST':
        score_text = request.form.get('score_text', '').strip()
        winner_id = request.form.get('winner_id')
        is_wo = request.form.get('is_wo') == '1'
        next_dates = request.form.get('next_match_date_options', '').strip()

        if not winner_id:
            flash('Vainqueur requis.', 'danger')
        elif not is_wo and not score_text:
            flash('Score requis (ou cocher WO).', 'danger')
        else:
            if is_wo:
                score_text = 'WO'
                match.status = 'WALKOVER'
            else:
                match.status = 'COMPLETED'
            match.score_text = score_text
            match.winner_id = int(winner_id)
            match.next_match_date_options = next_dates if next_dates else None
            db.session.commit()

            from blueprints.tournament.draw_generator import propagate_winner
            propagate_winner(match)
            flash('Résultat enregistré.', 'success')

        return redirect(url_for('tournament.show_draw', tid=tid, draw_id=match.draw_id))

    # GET : page de saisie dédiée (accessible aussi directement)
    return render_template('tournament/score.html', tournament=tournament, match=match)


# ─── Planification automatique ─────────────────────────────────────────────────

@tournament_bp.route('/<int:tid>/schedule/<int:draw_id>', methods=['POST'])
def schedule(tid: int, draw_id: int):
    from blueprints.tournament.scheduler import schedule_matches
    tournament = _get_tournament_or_404(tid)
    draw = TournamentDraw.query.get_or_404(draw_id)
    count = schedule_matches(tournament, draw)
    flash(f'{count} match(s) planifié(s) automatiquement.', 'success')
    return redirect(url_for('tournament.show_draw', tid=tid, draw_id=draw_id))


# ─── Vue impression (remplace WeasyPrint — trop gourmand en mémoire/CPU) ───────

@tournament_bp.route('/<int:tid>/print/<int:draw_id>')
def print_draw(tid: int, draw_id: int):
    """Page standalone prête à imprimer / exporter en PDF via window.print()."""
    tournament = _get_tournament_or_404(tid)
    draw = TournamentDraw.query.get_or_404(draw_id)

    from collections import defaultdict
    matches_by_round = defaultdict(list)
    for m in sorted(draw.matches, key=lambda x: x.position):
        matches_by_round[m.round_number].append(m)
    total_rounds = max(matches_by_round.keys()) if matches_by_round else 0

    return render_template(
        'tournament/draw_print.html',
        tournament=tournament,
        draw=draw,
        matches_by_round=dict(matches_by_round),
        total_rounds=total_rounds,
    )


# Rétro-compatibilité : ancienne URL /export-pdf/ → redirection vers /print/
@tournament_bp.route('/<int:tid>/export-pdf/<int:draw_id>')
def export_pdf(tid: int, draw_id: int):
    from flask import redirect, url_for
    return redirect(url_for('tournament.print_draw', tid=tid, draw_id=draw_id))


# ─── Génération aléatoire des joueurs (démo) ───────────────────────────────────

@tournament_bp.route('/<int:tid>/generate-random/<int:cid>', methods=['POST'])
def generate_random_players(tid: int, cid: int):
    """Inscrit aléatoirement N joueurs éligibles (pour démo)."""
    tournament = _get_tournament_or_404(tid)
    category = TournamentCategory.query.get_or_404(cid)
    n = int(request.form.get('nb_players', 8))

    gender_filter = category.gender if category.gender != 2 else None
    players_query = Player.query.join(Player.license)
    if not tournament.is_open:
        players_query = players_query.filter(Player.clubId == tournament.club_id)
    if gender_filter is not None:
        from models import License
        players_query = players_query.filter(License.gender == gender_filter)
    if category.age_category:
        all_p = [p for p in players_query.all() if p.has_valid_age(category.age_category)]
    else:
        all_p = players_query.all()

    registered_ids = {r.player_id for r in category.registrations if r.status != 'WITHDRAWN'}
    eligible = [p for p in all_p if p.id not in registered_ids]

    # Respecter les restrictions de classement et de série
    if category.min_ranking_id:
        eligible = [p for p in eligible if p.ranking.id <= category.min_ranking_id]
    if category.max_ranking_id:
        eligible = [p for p in eligible if p.ranking.id >= category.max_ranking_id]
    series_filter = category.allowed_series_list
    if series_filter:
        eligible = [p for p in eligible if p.ranking.series in series_filter]

    # ── Échantillon représentatif par niveau de classement ──────────────────
    from collections import defaultdict
    by_ranking: dict[int, list] = defaultdict(list)
    for p in eligible:
        by_ranking[p.ranking.id].append(p)

    selected = []
    ranking_keys = sorted(by_ranking.keys())
    nb_groups = len(ranking_keys)
    if nb_groups == 0:
        flash('Aucun joueur éligible disponible.', 'warning')
        return redirect(url_for('tournament.registrations', tid=tid, cid=cid))

    per_group = max(1, n // nb_groups)
    for rk in ranking_keys:
        if len(selected) >= n:
            break
        group = by_ranking[rk]
        take = min(per_group, len(group), n - len(selected))
        selected.extend(random.sample(group, take))

    # Compléter si besoin avec des joueurs restants
    if len(selected) < n:
        taken_ids = {p.id for p in selected}
        remaining = [p for p in eligible if p.id not in taken_ids]
        extra = random.sample(remaining, min(n - len(selected), len(remaining)))
        selected.extend(extra)

    selected = selected[:n]

    for p in selected:
        reg = TournamentRegistration(
            tournament_id=tid,
            category_id=cid,
            player_id=p.id,
            status='REGISTERED'
        )
        db.session.add(reg)
        db.session.flush()
        for day_type, ts, te in [
            ('weekday', random.choice(['08:00', '09:00', '10:00']), random.choice(['18:00', '19:00', '20:00'])),
            ('weekend', '09:00', '20:00')
        ]:
            db.session.add(TournamentAvailability(
                registration_id=reg.id,
                day_type=day_type,
                time_start=ts,
                time_end=te
            ))

    db.session.commit()
    flash(f'{len(selected)} joueur(s) inscrit(s) aléatoirement.', 'success')
    return redirect(url_for('tournament.registrations', tid=tid, cid=cid))















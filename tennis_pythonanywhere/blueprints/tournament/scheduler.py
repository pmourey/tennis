"""Planificateur automatique des matchs de tournoi.
Contraintes :
- 1 match maximum par joueur et par jour
- Au moins 1 jour de repos entre deux matchs du même joueur
- Tous les matchs doivent tenir dans la période start_date → end_date
"""
from __future__ import annotations
from datetime import datetime, timedelta, date, time

from extensions import db
from models import TournamentMatch, TournamentDraw


def schedule_matches(tournament, draw) -> int:
    courts = [c for c in tournament.courts if c.is_available]
    if not courts:
        return 0

    category = draw.category
    match_duration = timedelta(minutes=category.match_duration_minutes)
    start_d: date = tournament.start_date
    end_d: date = tournament.end_date
    nb_days = (end_d - start_d).days + 1

    # Calcul du nombre de rounds et de l'espacement idéal
    matches = sorted(
        [m for m in draw.matches if m.status in ['PENDING', 'SCHEDULED']
         and m.player1_id and m.player2_id],
        key=lambda m: (m.round_number, m.position)
    )
    if not matches:
        return 0

    max_round = max(m.round_number for m in matches)

    # Répartir les rounds sur toute la durée du tournoi
    # Chaque round a son propre "bloc" de jours
    days_per_round = max(2, nb_days // max_round)  # au moins 2 jours par round

    # player_last_date : date du dernier match planifié par joueur
    player_last_date: dict[int, date] = {}
    # court_day_count : nb de matchs déjà planifiés par (date, court_id) — tous tableaux confondus
    court_day_count: dict[tuple, int] = {}
    MAX_MATCHES_PER_COURT_PER_DAY = max(1, (8 * 60) // category.match_duration_minutes)

    # Pré-charger les matchs déjà planifiés sur tous les tableaux du tournoi
    # (pour éviter les conflits inter-catégories sur le même terrain/créneau)
    all_existing = TournamentMatch.query.join(
        TournamentMatch.draw
    ).filter(
        TournamentMatch.court_id.isnot(None),
        TournamentMatch.scheduled_at.isnot(None),
        TournamentMatch.status == 'SCHEDULED'
    ).all()
    # On importe TournamentDraw pour le filtre tournament_id (déjà importé en tête de module)
    existing_in_tournament = [
        m for m in all_existing
        if m.draw and m.draw.category and m.draw.category.tournament_id == tournament.id
    ]
    for em in existing_in_tournament:
        key = (em.scheduled_at.date(), em.court_id)
        court_day_count[key] = court_day_count.get(key, 0) + 1
        p1d = em.scheduled_at.date()
        if em.player1_id:
            existing_p1 = player_last_date.get(em.player1_id)
            if existing_p1 is None or p1d > existing_p1:
                player_last_date[em.player1_id] = p1d
        if em.player2_id:
            existing_p2 = player_last_date.get(em.player2_id)
            if existing_p2 is None or p1d > existing_p2:
                player_last_date[em.player2_id] = p1d

    scheduled = 0

    for match in matches:
        p1_id = match.player1_id
        p2_id = match.player2_id

        # Date de début du bloc pour ce round
        round_start = start_d + timedelta(days=(match.round_number - 1) * days_per_round)
        round_end = min(end_d, round_start + timedelta(days=days_per_round - 1))

        # Date la plus tôt possible pour chaque joueur (1 jour de repos min)
        earliest_p1 = player_last_date.get(p1_id)
        earliest_p2 = player_last_date.get(p2_id)
        earliest = round_start
        if earliest_p1:
            earliest = max(earliest, earliest_p1 + timedelta(days=2))
        if earliest_p2:
            earliest = max(earliest, earliest_p2 + timedelta(days=2))

        # Chercher un créneau disponible dans le bloc du round
        slot_date = None
        slot_court = None

        check_date = max(earliest, round_start)
        while check_date <= end_d:
            for court in courts:
                key = (check_date, court.id)
                if court_day_count.get(key, 0) < MAX_MATCHES_PER_COURT_PER_DAY:
                    slot_date = check_date
                    slot_court = court
                    break
            if slot_date:
                break
            check_date += timedelta(days=1)

        if slot_date:
            # Heure de début (10h + nb_matchs_du_jour × durée)
            nb_today = court_day_count.get((slot_date, slot_court.id), 0)
            start_hour = 10 + (nb_today * category.match_duration_minutes) // 60
            start_min = (nb_today * category.match_duration_minutes) % 60
            match_time = datetime.combine(slot_date, time(hour=min(start_hour, 20), minute=start_min))

            match.court_id = slot_court.id
            match.scheduled_at = match_time
            match.status = 'SCHEDULED'

            court_day_count[(slot_date, slot_court.id)] = nb_today + 1
            player_last_date[p1_id] = slot_date
            player_last_date[p2_id] = slot_date
            scheduled += 1

    db.session.commit()
    return scheduled

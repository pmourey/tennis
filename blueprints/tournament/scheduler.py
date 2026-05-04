# Source Generated with Decompyle++
# File: scheduler.cpython-310.pyc (Python 3.10)

'''Planificateur automatique des matchs de tournoi.
Contraintes :
- 1 match maximum par joueur et par jour
- Au moins 1 jour de repos entre deux matchs du même joueur
- Tous les matchs doivent tenir dans la période start_date → end_date
'''
from __future__ import annotations
from datetime import datetime, timedelta, date, time
from extensions import db
from models import TournamentMatch, TournamentDraw

def schedule_matches(tournament = None, draw = None):
    courts = (lambda .0: [ c for c in .0 if c.is_available ])(tournament.courts)
    if not courts:
        return 0
    category = None.category
    match_duration = timedelta(category.match_duration_minutes, **('minutes',))
    start_d = tournament.start_date
    end_d = tournament.end_date
    nb_days = (end_d - start_d).days + 1
    matches = sorted((lambda .0: [ m for m in .0 if m.player2_id ])(draw.matches), (lambda m: (m.round_number, m.position)), **('key',))
    if not matches:
        return 0
    max_round = None((lambda .0: for m in .0:
m.round_number)(matches))
    days_per_round = max(2, nb_days // max_round)
    player_last_date = { }
    court_day_count = { }
    MAX_MATCHES_PER_COURT_PER_DAY = max(1, 480 // category.match_duration_minutes)
    all_existing = TournamentMatch.query.join(TournamentMatch.draw).filter(TournamentMatch.court_id.isnot(None), TournamentMatch.scheduled_at.isnot(None), TournamentMatch.status == 'SCHEDULED').all()
    existing_in_tournament = (lambda .0 = None: [ m for m in .0 if m.draw.category.tournament_id == tournament.id ])(all_existing)
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
        round_start = start_d + timedelta((match.round_number - 1) * days_per_round, **('days',))
        round_end = min(end_d, round_start + timedelta(days_per_round - 1, **('days',)))
        earliest_p1 = player_last_date.get(p1_id)
        earliest_p2 = player_last_date.get(p2_id)
        earliest = round_start
        if earliest_p1:
            earliest = max(earliest, earliest_p1 + timedelta(2, **('days',)))
        if earliest_p2:
            earliest = max(earliest, earliest_p2 + timedelta(2, **('days',)))
        slot_date = None
        slot_court = None
        check_date = max(earliest, round_start)
        if check_date <= end_d:
            for court in courts:
                key = (check_date, court.id)
                if court_day_count.get(key, 0) < MAX_MATCHES_PER_COURT_PER_DAY:
                    slot_date = check_date
                    slot_court = court
                
                if slot_date:
                    pass
                else:
                    check_date += timedelta(1, **('days',))
                    if check_date <= end_d or slot_date:
                        nb_today = court_day_count.get((slot_date, slot_court.id), 0)
                        start_hour = 10 + nb_today * category.match_duration_minutes // 60
                        start_min = nb_today * category.match_duration_minutes % 60
                        match_time = datetime.combine(slot_date, time(min(start_hour, 20), start_min, **('hour', 'minute')))
                        match.court_id = slot_court.id
                        match.scheduled_at = match_time
                        match.status = 'SCHEDULED'
                        court_day_count[(slot_date, slot_court.id)] = nb_today + 1
                        player_last_date[p1_id] = slot_date
                        player_last_date[p2_id] = slot_date
                        scheduled += 1
    db.session.commit()
    return scheduled


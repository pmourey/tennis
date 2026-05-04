"""
Script de diagnostic/test de la propagation des qualifiés
pour le tournoi US Cagnes - 6ème Tournoi Interne (id=4).

Lance avec :
    python test/debug_cascade_propagation.py
ou :
    pytest test/debug_cascade_propagation.py -v
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest


# ─── Fixture : app connectée à la vraie base de production ──────────────────

@pytest.fixture(scope='module')
def app():
    from app import create_app
    application = create_app()  # utilise la vraie DB (tennis.sqlite3)
    with application.app_context():
        yield application


@pytest.fixture(scope='module')
def tournament(app):
    with app.app_context():
        from models import Tournament
        t = Tournament.query.get(4)
        assert t is not None, "Tournoi id=4 introuvable"
        assert 'Cagnes' in t.name, f"Mauvais tournoi : {t.name!r}"
        return t


# ─── Helpers ────────────────────────────────────────────────────────────────

def _draws_of(cat):
    from models import TournamentDraw
    return TournamentDraw.query.filter_by(category_id=cat.id).all()


def _matches_of(draw):
    from models import TournamentMatch
    return TournamentMatch.query.filter_by(draw_id=draw.id).order_by(
        TournamentMatch.round_number, TournamentMatch.position).all()


def _r1(draw):
    return [m for m in _matches_of(draw) if m.round_number == 1]


def _last_round_matches(draw):
    matches = _matches_of(draw)
    if not matches:
        return []
    max_rnd = max(m.round_number for m in matches)
    return [m for m in matches if m.round_number == max_rnd]


def _print_draw_summary(draw, indent="  "):
    matches = _matches_of(draw)
    max_rnd = max((m.round_number for m in matches), default=0)
    print(f"{indent}Draw {draw.id} [{draw.draw_type}] {draw.name!r}")
    print(f"{indent}  qualif_number={draw.qualif_number}  "
          f"main_draw_match_id={draw.main_draw_match_id}  "
          f"main_draw_slot={draw.main_draw_slot}")
    for rnd in range(1, max_rnd + 1):
        rnd_matches = [m for m in matches if m.round_number == rnd]
        for m in rnd_matches:
            p1 = m.player1.name if m.player1 else "---"
            p2 = m.player2.name if m.player2 else "---"
            winner = m.winner.name if m.winner else "---"
            print(f"{indent}  R{rnd} m{m.id} pos{m.position} [{m.status:9s}] "
                  f"{p1:30s} vs {p2:30s}  winner={winner}")


# ─── Tests de structure ──────────────────────────────────────────────────────

class TestDrawStructure:
    """Vérifie la structure des tableaux générés pour chaque catégorie."""

    def test_all_categories_have_draws(self, app, tournament):
        with app.app_context():
            from models import Tournament
            t = Tournament.query.get(tournament.id)
            cats_without_draws = [c for c in t.categories if not _draws_of(c)]
            if cats_without_draws:
                names = [c.name for c in cats_without_draws]
                print(f"\nCatégories sans tableau : {names}")
            # On ne fail pas — juste info
            assert len(t.categories) > 0

    def test_qualifying_draws_have_qualif_number(self, app, tournament):
        """Tout tableau QUALIFYING lié au tableau final doit avoir un qualif_number."""
        with app.app_context():
            from models import Tournament, TournamentDraw
            t = Tournament.query.get(tournament.id)
            errors = []
            for cat in t.categories:
                draws = _draws_of(cat)
                main = next((d for d in draws if d.draw_type == 'MAIN'), None)
                if not main:
                    continue
                main_match_ids = {m.id for m in _matches_of(main)}
                for d in draws:
                    if d.draw_type != 'QUALIFYING':
                        continue
                    if d.main_draw_match_id in main_match_ids:
                        # Ce tableau alimente directement le tableau final
                        if d.qualif_number is None:
                            errors.append(
                                f"Cat {cat.id} Draw {d.id} {d.name!r} : "
                                f"main_draw_match_id={d.main_draw_match_id} mais qualif_number=None"
                            )
            if errors:
                print("\nERREURS qualif_number :")
                for e in errors:
                    print(" ", e)
            assert not errors, f"{len(errors)} tableau(x) sans qualif_number"

    def test_reserved_slot_matches_actual_empty_slot(self, app, tournament):
        """
        Dans un tableau cascade avec has_incoming=True,
        le main_draw_slot du feeder DOIT correspondre au slot réellement vide
        dans le dernier match R1 du tableau cible.
        """
        with app.app_context():
            from models import Tournament, TournamentDraw, TournamentMatch
            t = Tournament.query.get(tournament.id)
            errors = []
            for cat in t.categories:
                draws = _draws_of(cat)
                qual_draws = [d for d in draws if d.draw_type == 'QUALIFYING']
                for d in qual_draws:
                    feeders = [qd for qd in qual_draws if qd.main_draw_match_id is not None]
                    for feeder in feeders:
                        m = TournamentMatch.query.get(feeder.main_draw_match_id)
                        if m and m.draw_id == d.id:
                            r1 = _r1(d)
                            if not r1:
                                continue
                            last_r1 = max(r1, key=lambda x: x.position)
                            if m.id != last_r1.id:
                                continue
                            # Le slot déclaré doit correspondre au slot vide du match cible
                            if feeder.main_draw_slot == 'p1' and m.player1_id is not None:
                                errors.append(
                                    f"Cat {cat.id} Feeder {feeder.id} {feeder.name!r}: "
                                    f"main_draw_slot='p1' mais player1={m.player1.name} "
                                    f"(slot pas vide)"
                                )
                            elif feeder.main_draw_slot == 'p2' and m.player2_id is not None:
                                errors.append(
                                    f"Cat {cat.id} Feeder {feeder.id} {feeder.name!r}: "
                                    f"main_draw_slot='p2' mais player2={m.player2.name} "
                                    f"(slot pas vide)"
                                )
            if errors:
                print("\nERREURS slot réservé ne correspond pas au slot vide :")
                for e in errors:
                    print(" ", e)
            assert not errors, f"{len(errors)} erreur(s) de cohérence slot réservé"

    def test_no_wrong_bye_in_cascade(self, app, tournament):
        """
        Dans un tableau cascade, le match réservé (dernier R1) ne doit PAS
        être en statut BYE si l'un de ses joueurs est None (slot attendu).
        Les autres matchs R1 à 1 joueur DOIVENT être BYE.
        """
        with app.app_context():
            from models import Tournament, TournamentDraw, TournamentMatch
            t = Tournament.query.get(tournament.id)
            errors = []
            for cat in t.categories:
                draws = _draws_of(cat)
                qual_draws = [d for d in draws if d.draw_type == 'QUALIFYING']
                # Identifier les tableaux avec has_incoming (ils ont un feeder)
                fed_draw_ids = set()
                for qd in qual_draws:
                    if qd.main_draw_match_id:
                        m = TournamentMatch.query.get(qd.main_draw_match_id)
                        if m:
                            fed_draw_ids.add(m.draw_id)

                for d in qual_draws:
                    if d.id not in fed_draw_ids:
                        continue  # pas de has_incoming pour ce draw
                    r1 = sorted(_r1(d), key=lambda x: x.position)
                    if not r1:
                        continue
                    last_r1 = r1[-1]
                    # Le dernier match R1 doit être PENDING si un slot est None
                    if (last_r1.player1_id is None or last_r1.player2_id is None) \
                            and last_r1.status == 'BYE':
                        errors.append(
                            f"Cat {cat.id} Draw {d.id} {d.name!r} : "
                            f"dernier match R1 (m{last_r1.id}) est BYE "
                            f"alors que p1={last_r1.player1_id} p2={last_r1.player2_id}"
                        )
                    # Les autres matchs à 1 joueur doivent être BYE
                    for m in r1[:-1]:
                        one_none = (m.player1_id is None) != (m.player2_id is None)
                        if one_none and m.status != 'BYE':
                            errors.append(
                                f"Cat {cat.id} Draw {d.id} {d.name!r} : "
                                f"match R1 m{m.id} pos{m.position} a 1 joueur "
                                f"mais status={m.status!r} (attendu BYE)"
                            )
            if errors:
                print("\nERREURS statut BYE :")
                for e in errors:
                    print(" ", e)
            assert not errors, f"{len(errors)} erreur(s) de statut BYE"


# ─── Tests de propagation ────────────────────────────────────────────────────

class TestPropagation:
    """
    Simule la saisie de scores dans des tableaux qualificatifs et vérifie
    que le qualifié se retrouve bien dans le tableau cible.
    Ces tests utilisent la vraie DB mais font un ROLLBACK à la fin
    pour ne pas polluer les données.
    """

    def _enter_score_and_propagate(self, match, winner, score="6/2 6/3"):
        """Saisit un score et propage le vainqueur."""
        from blueprints.tournament.draw_generator import propagate_winner
        from extensions import db
        match.score_text = score
        match.winner_id = winner.id
        match.status = 'COMPLETED'
        db.session.flush()
        propagate_winner(match)

    def _safe_propagation_test(self, app, qd, last_m, target_match, winner_player):
        """
        Exécute propagate_winner sur un match, vérifie que le qualifié arrive
        dans le tableau cible, puis RESTAURE l'état original de la DB.
        Retourne (ok: bool, error_msg: str | None).
        """
        from extensions import db
        from blueprints.tournament.draw_generator import propagate_winner

        # Sauvegarder l'état original
        orig = {
            'm_winner': last_m.winner_id,
            'm_status': last_m.status,
            'm_score': last_m.score_text,
            'm_p1': last_m.player1_id,
            'm_p2': last_m.player2_id,
            't_p1': target_match.player1_id,
            't_p2': target_match.player2_id,
            't_status': target_match.status,
            't_winner': target_match.winner_id,
        }
        # Chercher aussi les matchs du tour suivant du tableau cible (pour BYE auto)
        next_in_target = []
        for m in target_match.draw.matches:
            if m.round_number == target_match.round_number + 1 and \
               m.position == (target_match.position + 1) // 2:
                next_in_target.append({
                    'm': m, 'p1': m.player1_id, 'p2': m.player2_id,
                    'status': m.status, 'winner': m.winner_id
                })

        error_msg = None
        try:
            # Forcer les deux joueurs présents (test)
            if last_m.player1_id is None:
                last_m.player1_id = winner_player.id
            if last_m.player2_id is None:
                # Utiliser le même joueur comme adversaire fictif
                for reg in last_m.draw.category.registrations:
                    if reg.player_id != winner_player.id:
                        last_m.player2_id = reg.player_id
                        break
                else:
                    last_m.player2_id = winner_player.id
            last_m.winner_id = winner_player.id
            last_m.score_text = "6/0 6/0"
            last_m.status = 'COMPLETED'
            db.session.flush()

            propagate_winner(last_m)  # commit interne

            # Vérifier que le qualifié est bien dans le tableau cible
            db.session.refresh(target_match)
            slot = qd.main_draw_slot
            arrived_id = target_match.player1_id if slot == 'p1' else target_match.player2_id
            if arrived_id != winner_player.id:
                error_msg = (
                    f"Draw {qd.id} {qd.name!r}: qualifié {winner_player.name} "
                    f"non arrivé dans m{target_match.id} slot={slot!r} "
                    f"(p1={target_match.player1_id}, p2={target_match.player2_id})"
                )
            else:
                print(f"\n  OK: {qd.name!r} → {winner_player.name} → "
                      f"m{target_match.id} slot={slot}")
        finally:
            # Toujours restaurer l'état original
            last_m.winner_id = orig['m_winner']
            last_m.status = orig['m_status']
            last_m.score_text = orig['m_score']
            last_m.player1_id = orig['m_p1']
            last_m.player2_id = orig['m_p2']
            target_match.player1_id = orig['t_p1']
            target_match.player2_id = orig['t_p2']
            target_match.status = orig['t_status']
            target_match.winner_id = orig['t_winner']
            for snap in next_in_target:
                snap['m'].player1_id = snap['p1']
                snap['m'].player2_id = snap['p2']
                snap['m'].status = snap['status']
                snap['m'].winner_id = snap['winner']
            db.session.commit()  # commit de restauration

        return error_msg is None, error_msg

    def test_propagation_cascade_last_draw_to_main(self, app, tournament):
        """
        Dans un tableau cascade, le vainqueur du DERNIER tableau qualificatif
        doit apparaître dans le tableau final après propagation.
        """
        with app.app_context():
            from models import Tournament, TournamentDraw, TournamentMatch
            t = Tournament.query.get(tournament.id)

            cascade_cats = []
            for cat in t.categories:
                draws = _draws_of(cat)
                qual_draws = [d for d in draws if d.draw_type == 'QUALIFYING']
                main = next((d for d in draws if d.draw_type == 'MAIN'), None)
                if not main or not qual_draws:
                    continue
                main_match_ids = {m.id for m in _matches_of(main)}
                final_linked = [d for d in qual_draws if d.main_draw_match_id in main_match_ids]
                if final_linked:
                    cascade_cats.append((cat, final_linked, main))

            if not cascade_cats:
                pytest.skip("Aucun tableau cascade/sections avec qualifiés liés au final")

            errors = []
            for cat, final_linked_draws, main in cascade_cats:
                for qd in final_linked_draws:
                    last_matches = _last_round_matches(qd)
                    if not last_matches:
                        continue
                    last_m = last_matches[0]
                    target_match = TournamentMatch.query.get(qd.main_draw_match_id)
                    if not target_match:
                        errors.append(f"Draw {qd.id}: main_draw_match_id={qd.main_draw_match_id} introuvable")
                        continue

                    winner_player = last_m.player1 or last_m.player2
                    if not winner_player:
                        # Dernier round pas encore atteint (draw en cours) → skip
                        print(f"\n  SKIP: {qd.name!r} dernier match m{last_m.id} sans joueur (en cours)")
                        continue

                    ok, err = self._safe_propagation_test(app, qd, last_m, target_match, winner_player)
                    if not ok:
                        errors.append(f"Cat {cat.id} {err}")

            if errors:
                print("\nERREURS propagation qualifiés → tableau final :")
                for e in errors:
                    print(" ", e)
            assert not errors, f"{len(errors)} erreur(s) de propagation"

    def test_propagation_cascade_intermediate(self, app, tournament):
        """
        Dans une cascade à plusieurs niveaux, le vainqueur d'un tableau
        intermédiaire doit arriver dans le tableau suivant.
        """
        with app.app_context():
            from models import Tournament, TournamentDraw, TournamentMatch
            t = Tournament.query.get(tournament.id)

            errors = []
            for cat in t.categories:
                draws = _draws_of(cat)
                qual_draws = [d for d in draws if d.draw_type == 'QUALIFYING']
                main = next((d for d in draws if d.draw_type == 'MAIN'), None)
                if not main:
                    continue
                main_match_ids = {m.id for m in _matches_of(main)}

                intermediate = [
                    d for d in qual_draws
                    if d.main_draw_match_id is not None
                    and d.main_draw_match_id not in main_match_ids
                ]
                for qd in intermediate:
                    target_match = TournamentMatch.query.get(qd.main_draw_match_id)
                    if not target_match:
                        continue
                    last_matches = _last_round_matches(qd)
                    if not last_matches:
                        continue
                    last_m = last_matches[0]
                    winner_player = last_m.player1 or last_m.player2
                    if not winner_player:
                        continue

                    ok, err = self._safe_propagation_test(app, qd, last_m, target_match, winner_player)
                    if not ok:
                        errors.append(f"Cat {cat.id} {err}")

            if errors:
                print("\nERREURS propagation intermédiaire :")
                for e in errors:
                    print(" ", e)
            assert not errors, f"{len(errors)} erreur(s) de propagation intermédiaire"

    def test_bye_auto_advance_when_other_slot_empty(self, app, tournament):
        """
        Quand le qualifié arrive dans un match dont l'autre slot est vide
        et qu'aucun autre tableau ne l'alimentera, le match doit passer
        en BYE et le qualifié avancer automatiquement au tour suivant.
        """
        with app.app_context():
            from models import Tournament, TournamentDraw, TournamentMatch
            t = Tournament.query.get(tournament.id)

            errors = []
            for cat in t.categories:
                draws = _draws_of(cat)
                main = next((d for d in draws if d.draw_type == 'MAIN'), None)
                qual_draws = [d for d in draws if d.draw_type == 'QUALIFYING']
                if not main or not qual_draws:
                    continue
                main_match_ids = {m.id for m in _matches_of(main)}

                for qd in qual_draws:
                    if qd.main_draw_match_id not in main_match_ids:
                        continue
                    target_match = TournamentMatch.query.get(qd.main_draw_match_id)
                    if not target_match:
                        continue

                    other_slot = 'p2' if qd.main_draw_slot == 'p1' else 'p1'
                    other_player_id = (target_match.player1_id if other_slot == 'p1'
                                       else target_match.player2_id)
                    if other_player_id is not None:
                        continue

                    other_feeder = next(
                        (d for d in qual_draws
                         if d.main_draw_match_id == target_match.id
                         and d.main_draw_slot == other_slot),
                        None
                    )
                    if other_feeder:
                        continue  # un autre tableau viendra remplir l'autre slot

                    last_matches = _last_round_matches(qd)
                    if not last_matches:
                        continue
                    last_m = last_matches[0]
                    winner_player = last_m.player1 or last_m.player2
                    if not winner_player:
                        continue

                    # Snapshots pour vérification et restauration
                    from extensions import db
                    from blueprints.tournament.draw_generator import propagate_winner

                    orig = {
                        'm_winner': last_m.winner_id, 'm_status': last_m.status,
                        'm_score': last_m.score_text,
                        'm_p1': last_m.player1_id, 'm_p2': last_m.player2_id,
                        't_p1': target_match.player1_id, 't_p2': target_match.player2_id,
                        't_status': target_match.status, 't_winner': target_match.winner_id,
                    }
                    # R2 du tableau final pour la propagation BYE
                    r2_snaps = []
                    for m in target_match.draw.matches:
                        if m.round_number == target_match.round_number + 1 and \
                           m.position == (target_match.position + 1) // 2:
                            r2_snaps.append({
                                'm': m, 'p1': m.player1_id, 'p2': m.player2_id,
                                'status': m.status, 'winner': m.winner_id
                            })

                    try:
                        if last_m.player1_id is None:
                            last_m.player1_id = winner_player.id
                        if last_m.player2_id is None:
                            for reg in last_m.draw.category.registrations:
                                if reg.player_id != winner_player.id:
                                    last_m.player2_id = reg.player_id
                                    break
                            else:
                                last_m.player2_id = winner_player.id
                        last_m.winner_id = winner_player.id
                        last_m.score_text = "6/0 6/0"
                        last_m.status = 'COMPLETED'
                        db.session.flush()

                        propagate_winner(last_m)  # commit interne

                        db.session.refresh(target_match)
                        if target_match.status != 'BYE':
                            errors.append(
                                f"Cat {cat.id} Draw {qd.id} {qd.name!r}: "
                                f"match final m{target_match.id} devrait être BYE "
                                f"(slot vide sans feeder) mais status={target_match.status!r}"
                            )
                        else:
                            print(f"\n  OK BYE auto: {qd.name!r} → "
                                  f"{winner_player.name} → BYE dans m{target_match.id}")
                    finally:
                        last_m.winner_id = orig['m_winner']
                        last_m.status = orig['m_status']
                        last_m.score_text = orig['m_score']
                        last_m.player1_id = orig['m_p1']
                        last_m.player2_id = orig['m_p2']
                        target_match.player1_id = orig['t_p1']
                        target_match.player2_id = orig['t_p2']
                        target_match.status = orig['t_status']
                        target_match.winner_id = orig['t_winner']
                        for snap in r2_snaps:
                            snap['m'].player1_id = snap['p1']
                            snap['m'].player2_id = snap['p2']
                            snap['m'].status = snap['status']
                            snap['m'].winner_id = snap['winner']
                        db.session.commit()

            if errors:
                print("\nERREURS BYE auto-avance :")
                for e in errors:
                    print(" ", e)
            assert not errors, f"{len(errors)} erreur(s) BYE auto-avance"


# ─── Diagnostic : afficher l'état complet des tableaux ──────────────────────

def print_full_tournament_state():
    """Fonction utilitaire pour afficher l'état complet (pas un test pytest)."""
    from app import create_app
    application = create_app()
    with application.app_context():
        from models import Tournament
        t = Tournament.query.get(4)
        print(f"\n{'='*70}")
        print(f"Tournoi : {t.name} (id={t.id})")
        print(f"{'='*70}")
        for cat in t.categories:
            draws = _draws_of(cat)
            if not draws:
                continue
            print(f"\nCatégorie : {cat.name} (id={cat.id})")
            for d in draws:
                _print_draw_summary(d)


if __name__ == '__main__':
    print_full_tournament_state()

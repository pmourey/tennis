"""
Tests unitaires du générateur de tableaux de tournoi.

Couvre :
  1. seed_positions()          – placement des TdS (Art. 46-1-e-i)
  2. _build_draw()             – placement BYE adjacents aux TdS (Art. 47-4)
  3. generate_draws()          – tableau classique à départ en ligne (Art. 47)
  4. generate_draws_by_tranche()  – tableau en cascade (qualif. enchaînés)
  5. generate_section_draw()   – tableau à sections (Art. 49)
  6. Cohérence statut tournoi  – fonctions utilitaires de garde

Les tests 3-5 utilisent une base SQLite en mémoire via Flask-SQLAlchemy.
"""
from __future__ import annotations

import math
import os
import random
import sys

import pytest

# ── Ajouter la racine du projet au path ────────────────────────────────────
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


# ══════════════════════════════════════════════════════════════════════════════
#  Tests purs (pas de DB) — seed_positions, next_power_of_2
# ══════════════════════════════════════════════════════════════════════════════

from blueprints.tournament.draw_generator import (next_power_of_2,
                                                  seed_positions)


class TestNextPowerOf2:
    def test_small(self):
        assert next_power_of_2(2) == 4
        assert next_power_of_2(3) == 4
        assert next_power_of_2(4) == 4

    def test_medium(self):
        assert next_power_of_2(5) == 8
        assert next_power_of_2(8) == 8
        assert next_power_of_2(9) == 16

    def test_large(self):
        assert next_power_of_2(17) == 32
        assert next_power_of_2(32) == 32
        assert next_power_of_2(33) == 64


class TestSeedPositions:
    """Art. 46-1-e-i : TdS en haut des fractions du demi-tableau haut
    et en bas des fractions du demi-tableau bas."""

    def _valid_top(self, draw_size: int, n_fractions: int) -> set[int]:
        """Positions valides pour le demi-tableau haut (haut de fraction)."""
        step = draw_size // n_fractions
        return {i * step for i in range(n_fractions // 2)}

    def _valid_bot(self, draw_size: int, n_fractions: int) -> set[int]:
        """Positions valides pour le demi-tableau bas (bas de fraction)."""
        step = draw_size // n_fractions
        return {(i + 1) * step - 1 for i in range(n_fractions // 2, n_fractions)}

    def test_seed1_always_top(self):
        """TdS 1 toujours en position 0 (haut du tableau)."""
        random.seed(0)
        for draw_size in (4, 8, 16, 32, 64):
            pos = seed_positions(draw_size, 2)
            assert pos[0] == 0, f"TdS1 doit être en pos 0 pour D={draw_size}"

    def test_seed2_always_bottom(self):
        """TdS 2 toujours en bas du tableau (draw_size - 1)."""
        random.seed(0)
        for draw_size in (4, 8, 16, 32, 64):
            pos = seed_positions(draw_size, 2)
            assert pos[1] == draw_size - 1, f"TdS2 doit être en pos {draw_size - 1}"

    def test_d8_n4_positions_valid(self):
        """D=8 N=4 : fractions de 2, positions valides = {0,2,5,7}."""
        valid = {0, 2, 5, 7}
        for seed_val in range(20):
            random.seed(seed_val)
            pos = seed_positions(8, 4)
            assert len(pos) == 4
            assert all(p in valid for p in pos), f"Positions invalides pour D=8 N=4 : {pos}"
            assert len(set(pos)) == 4, f"Doublons détectés : {pos}"

    def test_d16_n8_positions_valid(self):
        """D=16 N=8 : fractions de 2, positions valides = {0,2,4,6,9,11,13,15}."""
        valid = {0, 2, 4, 6, 9, 11, 13, 15}
        for seed_val in range(20):
            random.seed(seed_val)
            pos = seed_positions(16, 8)
            assert len(pos) == 8
            assert all(p in valid for p in pos), f"Positions invalides D=16 N=8 : {pos}"
            assert len(set(pos)) == 8

    def test_d32_n8_positions_in_correct_halves(self):
        """D=32 N=8 : fractions de 4, top={0,4,8,12}, bot={19,23,27,31}."""
        valid_top = {0, 4, 8, 12}
        valid_bot = {19, 23, 27, 31}
        valid_all = valid_top | valid_bot
        for seed_val in range(20):
            random.seed(seed_val)
            pos = seed_positions(32, 8)
            assert len(pos) == 8
            assert all(p in valid_all for p in pos), f"Position hors-fraction D=32 N=8 : {pos}"
            assert len(set(pos)) == 8
            # TdS1 & 2 fixes
            assert pos[0] == 0
            assert pos[1] == 31

    def test_no_duplicate_positions(self):
        """Aucun doublon quelle que soit la configuration."""
        for d in (4, 8, 16, 32):
            for n in (1, 2, 4, 8):
                if n > d:
                    continue
                random.seed(42)
                pos = seed_positions(d, n)
                assert len(pos) == len(set(pos)), f"Doublons D={d} N={n} : {pos}"

    def test_n0_returns_empty(self):
        assert seed_positions(8, 0) == []

    def test_n1_returns_position0(self):
        assert seed_positions(8, 1) == [0]


# ══════════════════════════════════════════════════════════════════════════════
#  Helpers pour les tests avec base de données en mémoire
# ══════════════════════════════════════════════════════════════════════════════

@pytest.fixture(scope='module')
def app():
    """Crée une application Flask de test avec SQLite en mémoire."""
    from app import create_app
    application = create_app({'TESTING': True,
                               'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
                               'SQLALCHEMY_TRACK_MODIFICATIONS': False,
                               'SECRET_KEY': 'test-secret'})
    with application.app_context():
        from extensions import db as _db
        _db.create_all()
        yield application
        _db.drop_all()


@pytest.fixture(scope='module')
def db(app):
    from extensions import db as _db
    return _db


def _make_tournament_category(db, n_players: int,
                               min_rk_id: int | None = None):
    """
    Crée un tournoi + catégorie + n_players inscrits (classements distincts).
    Retourne (tournament, category).
    """
    from datetime import date, datetime

    from models import (Club, License, Player, Ranking, Tournament,
                        TournamentCategory, TournamentRegistration)

    # Club (string PK)
    club = db.session.get(Club, 'TST01')
    if club is None:
        club = Club(id='TST01', name='Club Test', city='Testville')
        db.session.add(club)
        db.session.flush()

    # Classements (id faible = meilleur classement)
    rankings = []
    for i in range(1, n_players + 2):
        rk = db.session.get(Ranking, i)
        if rk is None:
            rk = Ranking(id=i, value=f'{i}/6', series=4 if i > 10 else 3)
            db.session.add(rk)
        rankings.append(rk)
    db.session.flush()

    # Tournoi
    t = Tournament(name=f'Test-{n_players}j', club_id='TST01',
                   start_date=date(2026, 6, 1), end_date=date(2026, 6, 15),
                   is_open=False, surface='TB', status='DRAFT')
    db.session.add(t)
    db.session.flush()

    cat = TournamentCategory(tournament_id=t.id, gender=0, game_format=1,
                              min_ranking_id=min_rk_id)
    db.session.add(cat)
    db.session.flush()

    for i in range(n_players):
        # License : id auto-incrémenté, rankingId = FK vers Ranking
        lic = License(firstName='Joueur', lastName=f'{i:03d}',
                      letter='A', year=2026, gender=0,
                      rankingId=rankings[i].id)
        db.session.add(lic)
        db.session.flush()
        # Player : licenseId = FK vers license.id (entier), birthDate requis
        p = Player(licenseId=lic.id, clubId='TST01',
                   birthDate=datetime(2000, 1, 1))
        db.session.add(p)
        db.session.flush()
        reg = TournamentRegistration(tournament_id=t.id, category_id=cat.id,
                                     player_id=p.id, status='REGISTERED')
        db.session.add(reg)

    db.session.commit()
    return t, cat


def _count_matches_at_round(draw, round_number: int) -> int:
    return sum(1 for m in draw.matches if m.round_number == round_number)


def _count_byes(draw) -> int:
    return sum(1 for m in draw.matches if m.status == 'BYE')


def _count_seeds(category) -> int:
    return sum(1 for r in category.registrations if r.is_seeded)


# ══════════════════════════════════════════════════════════════════════════════
#  Tests tableau classique (Art. 47) — generate_draws
# ══════════════════════════════════════════════════════════════════════════════

class TestClassicDraw:

    def test_draw_size_power_of_2(self, app, db):
        """La dimension du tableau = puissance de 2 ≥ effectif (Art. 47-2)."""
        with app.app_context():
            from blueprints.tournament.draw_generator import generate_draws
            for n in (5, 7, 9, 12, 14):
                _, cat = _make_tournament_category(db, n)
                draws = generate_draws(cat)
                main = next(d for d in draws if d.draw_type == 'MAIN')
                expected_size = next_power_of_2(n)
                r1 = _count_matches_at_round(main, 1)
                assert r1 == expected_size // 2, \
                    f"n={n}: attendu {expected_size // 2} matchs R1, obtenu {r1}"

    def test_bye_count_equals_draw_minus_n(self, app, db):
        """Nombre de BYEs = draw_size - n (Art. 47-3)."""
        with app.app_context():
            from blueprints.tournament.draw_generator import generate_draws
            for n in (5, 6, 7, 10, 12):
                _, cat = _make_tournament_category(db, n)
                draws = generate_draws(cat)
                main = next(d for d in draws if d.draw_type == 'MAIN')
                expected_size = next_power_of_2(n)
                expected_byes = expected_size - n
                actual_byes = _count_byes(main)
                assert actual_byes == expected_byes, \
                    f"n={n}: attendu {expected_byes} BYEs, obtenu {actual_byes}"

    def test_byes_adjacent_to_seeds_art47_4a(self, app, db):
        """
        Art. 47-4-a : les nb_byes premières TdS (si nb_byes < nb_seeds)
        ont leur partenaire de 1er tour = BYE.
        """
        with app.app_context():
            from blueprints.tournament.draw_generator import generate_draws
            from models import TournamentMatch
            n = 7   # draw_size=8, byes=1 → TdS1 doit être exempte
            _, cat = _make_tournament_category(db, n)
            draws = generate_draws(cat)
            main = next(d for d in draws if d.draw_type == 'MAIN')
            seed_reg = min((r for r in cat.registrations if r.is_seeded),
                           key=lambda r: r.seed_number or 999)
            # Trouver le match R1 contenant TdS1
            r1_matches = [m for m in main.matches if m.round_number == 1]
            seed1_match = next(
                (m for m in r1_matches
                 if m.player1_id == seed_reg.player_id
                 or m.player2_id == seed_reg.player_id),
                None
            )
            assert seed1_match is not None, "Match R1 de TdS1 introuvable"
            assert seed1_match.status == 'BYE', \
                f"TdS1 devrait être exemptée (BYE), statut: {seed1_match.status}"

    def test_all_seeds_placed_at_r1(self, app, db):
        """Toutes les TdS doivent figurer dans un match de round 1."""
        with app.app_context():
            from blueprints.tournament.draw_generator import generate_draws
            n = 16
            _, cat = _make_tournament_category(db, n)
            draws = generate_draws(cat)
            main = next(d for d in draws if d.draw_type == 'MAIN')
            r1_player_ids = set()
            for m in main.matches:
                if m.round_number == 1:
                    if m.player1_id:
                        r1_player_ids.add(m.player1_id)
                    if m.player2_id:
                        r1_player_ids.add(m.player2_id)
            seed_ids = {r.player_id for r in cat.registrations if r.is_seeded}
            assert seed_ids.issubset(r1_player_ids), \
                f"TdS non placées en R1 : {seed_ids - r1_player_ids}"

    def test_no_two_seeds_same_half_d8(self, app, db):
        """
        Art. 46-1-e-i : TdS1 en demi-tableau haut, TdS2 en demi-tableau bas.
        Pour D=8 : positions {0,1,2,3} = demi-haut, {4,5,6,7} = demi-bas.
        """
        with app.app_context():
            from blueprints.tournament.draw_generator import generate_draws
            from models import TournamentMatch
            n = 8
            random.seed(7)
            _, cat = _make_tournament_category(db, n)
            draws = generate_draws(cat)
            main = next(d for d in draws if d.draw_type == 'MAIN')
            seed_regs = sorted(
                [r for r in cat.registrations if r.is_seeded],
                key=lambda r: r.seed_number
            )
            if len(seed_regs) < 2:
                pytest.skip("Pas assez de TdS pour ce test")

            r1 = sorted([m for m in main.matches if m.round_number == 1],
                        key=lambda m: m.position)
            half = len(r1) // 2   # 2 pour D=8

            def find_r1_pos(player_id):
                for i, m in enumerate(r1):
                    if m.player1_id == player_id or m.player2_id == player_id:
                        return i
                return -1

            p1 = find_r1_pos(seed_regs[0].player_id)
            p2 = find_r1_pos(seed_regs[1].player_id)
            assert p1 >= 0 and p2 >= 0, "TdS1 ou TdS2 introuvable en R1"
            assert (p1 < half) != (p2 < half), \
                f"TdS1 et TdS2 dans le même demi-tableau (positions R1 : {p1}, {p2})"

    def test_two_players_returns_single_draw(self, app, db):
        """Cas limite : 2 joueurs → 1 seul tableau de dimension 4 avec 2 BYEs."""
        with app.app_context():
            from blueprints.tournament.draw_generator import generate_draws
            _, cat = _make_tournament_category(db, 2)
            draws = generate_draws(cat)
            assert len(draws) == 1
            main = draws[0]
            assert main.draw_type == 'MAIN'
            assert _count_byes(main) == 2

    def test_zero_players_returns_empty(self, app, db):
        """Moins de 2 joueurs → aucun tableau généré."""
        with app.app_context():
            from blueprints.tournament.draw_generator import generate_draws
            _, cat = _make_tournament_category(db, 1)
            draws = generate_draws(cat)
            assert draws == []


# ══════════════════════════════════════════════════════════════════════════════
#  Tests tableau en cascade (generate_draws_by_tranche)
# ══════════════════════════════════════════════════════════════════════════════

class TestCascadeDraw:

    def test_produces_main_and_qualifying(self, app, db):
        """La cascade produit au moins 1 qualifying + 1 MAIN."""
        with app.app_context():
            from blueprints.tournament.draw_generator import \
                generate_draws_by_tranche
            _, cat = _make_tournament_category(db, 12)
            draws = generate_draws_by_tranche(cat)
            types = [d.draw_type for d in draws]
            assert 'MAIN' in types
            assert 'QUALIFYING' in types

    def test_main_draw_receives_all_seeds(self, app, db):
        """Le tableau final contient toutes les TdS en R1."""
        with app.app_context():
            from blueprints.tournament.draw_generator import \
                generate_draws_by_tranche
            n = 14
            _, cat = _make_tournament_category(db, n)
            draws = generate_draws_by_tranche(cat)
            main = next(d for d in draws if d.draw_type == 'MAIN')
            r1_ids = set()
            for m in main.matches:
                if m.round_number == 1:
                    if m.player1_id:
                        r1_ids.add(m.player1_id)
                    if m.player2_id:
                        r1_ids.add(m.player2_id)
            seed_ids = {r.player_id for r in cat.registrations if r.is_seeded}
            assert seed_ids.issubset(r1_ids), \
                f"TdS absentes du tableau final : {seed_ids - r1_ids}"

    def test_qualifying_draws_linked_to_main(self, app, db):
        """Chaque draw QUALIFYING doit être lié au tableau final (main_draw_match_id)."""
        with app.app_context():
            from blueprints.tournament.draw_generator import \
                generate_draws_by_tranche
            _, cat = _make_tournament_category(db, 16)
            draws = generate_draws_by_tranche(cat)
            qual_draws = [d for d in draws if d.draw_type == 'QUALIFYING']
            unlinked = [d for d in qual_draws if d.main_draw_match_id is None]
            assert unlinked == [], \
                f"{len(unlinked)} qualifying non liés au tableau final"

    def test_no_two_qualifiers_face_each_other_r1(self, app, db):
        """
        Art. 45-3-c : deux qualifiés de tableaux différents ne se rencontrent
        pas dès le 1er tour du tableau final.
        Vérification : dans chaque match R1 du final, au plus 1 slot qualifié.
        """
        with app.app_context():
            from blueprints.tournament.draw_generator import \
                generate_draws_by_tranche
            _, cat = _make_tournament_category(db, 18)
            draws = generate_draws_by_tranche(cat)
            main = next(d for d in draws if d.draw_type == 'MAIN')
            qual_draws = [d for d in draws if d.draw_type == 'QUALIFYING']
            qualif_match_ids = {d.main_draw_match_id for d in qual_draws
                                if d.main_draw_match_id}
            r1 = [m for m in main.matches if m.round_number == 1]
            for m in r1:
                if m.id not in qualif_match_ids:
                    continue
                qualifs_in_match = sum(
                    1 for d in qual_draws if d.main_draw_match_id == m.id
                )
                assert qualifs_in_match <= 1, \
                    (f"Match R1 id={m.id} reçoit {qualifs_in_match} qualifiés "
                     f"(Art. 45-3-c violé)")


# ══════════════════════════════════════════════════════════════════════════════
#  Tests tableau à sections (Art. 49) — generate_section_draw
# ══════════════════════════════════════════════════════════════════════════════

class TestSectionDraw:

    def test_produces_n_sections_plus_main(self, app, db):
        """Nombre de draws = num_sections sections + 1 tableau final."""
        with app.app_context():
            from blueprints.tournament.draw_generator import \
                generate_section_draw
            n = 12
            _, cat = _make_tournament_category(db, n)
            draws = generate_section_draw(cat, num_sections=3)
            sections = [d for d in draws if d.draw_type == 'QUALIFYING']
            mains = [d for d in draws if d.draw_type == 'MAIN']
            assert len(sections) == 3, f"Attendu 3 sections, obtenu {len(sections)}"
            assert len(mains) == 1, "Un seul tableau final attendu"

    def test_each_section_has_exactly_one_seed(self, app, db):
        """Art. 49-2-d : 1 tête de série par section."""
        with app.app_context():
            from blueprints.tournament.draw_generator import \
                generate_section_draw
            from models import TournamentMatch
            n = 9
            _, cat = _make_tournament_category(db, n)
            draws = generate_section_draw(cat, num_sections=3)
            sections = [d for d in draws if d.draw_type == 'QUALIFYING']
            assert len(sections) == 3

            seed_ids = {r.player_id for r in cat.registrations if r.is_seeded}
            for sec in sections:
                r1_ids = set()
                for m in sec.matches:
                    if m.round_number == 1:
                        if m.player1_id:
                            r1_ids.add(m.player1_id)
                        if m.player2_id:
                            r1_ids.add(m.player2_id)
                seeds_in_section = r1_ids & seed_ids
                assert len(seeds_in_section) == 1, \
                    f"Section {sec.display_name} : {len(seeds_in_section)} TdS (attendu 1)"

    def test_seed_placed_at_bottom_of_section(self, app, db):
        """
        Art. 46-1-e-ii : la TdS est placée en bas de la section.
        En pratique : dans le match R1 de position la plus haute, la TdS
        est présente (partenaire = BYE ou joueur).
        """
        with app.app_context():
            from blueprints.tournament.draw_generator import \
                generate_section_draw
            from models import TournamentMatch
            n = 6
            _, cat = _make_tournament_category(db, n)
            draws = generate_section_draw(cat, num_sections=2)
            sections = [d for d in draws if d.draw_type == 'QUALIFYING']
            seed_ids = {r.player_id for r in cat.registrations if r.is_seeded}

            for sec in sections:
                r1 = sorted([m for m in sec.matches if m.round_number == 1],
                            key=lambda m: m.position)
                last_match = r1[-1]   # match au bas de la section
                bottom_players = {last_match.player1_id, last_match.player2_id} - {None}
                assert bottom_players & seed_ids, \
                    f"Section {sec.display_name} : TdS absente du bas de section (position {last_match.position})"

    def test_sections_linked_to_main(self, app, db):
        """Chaque section doit être liée au tableau final (Art. 45-3-c)."""
        with app.app_context():
            from blueprints.tournament.draw_generator import \
                generate_section_draw
            n = 8
            _, cat = _make_tournament_category(db, n)
            draws = generate_section_draw(cat, num_sections=4)
            sections = [d for d in draws if d.draw_type == 'QUALIFYING']
            unlinked = [d for d in sections if d.main_draw_match_id is None]
            assert unlinked == [], \
                f"{len(unlinked)} section(s) non liée(s) au tableau final"

    def test_no_two_section_winners_face_each_other_r1(self, app, db):
        """
        Art. 45-3-c : au plus 1 qualifié de section par match R1 du final.
        Satisfiable uniquement quand num_sections ≤ r1_matches (= draw_size / 2).
        Cas de test : 2 sections → final de 4, r1_matches=2 → 1 qualifié par match.
        """
        with app.app_context():
            from blueprints.tournament.draw_generator import \
                generate_section_draw

            # n=8, num_sections=2 : 2 sections pour 1 qualifié chacune →
            # final_draw_size=4, 2 matchs R1 → chaque match reçoit exactement 1 qualifié
            n = 8
            _, cat = _make_tournament_category(db, n)
            draws = generate_section_draw(cat, num_sections=2)
            main = next(d for d in draws if d.draw_type == 'MAIN')
            sections = [d for d in draws if d.draw_type == 'QUALIFYING']
            r1 = [m for m in main.matches if m.round_number == 1]
            for m in r1:
                qualifs = sum(1 for s in sections if s.main_draw_match_id == m.id)
                assert qualifs <= 1, \
                    f"Match R1 id={m.id} reçoit {qualifs} qualifiés de sections (Art. 45-3-c violé)"

    @pytest.mark.parametrize("num_sections", [3, 4, 5, 6, 8])
    def test_no_two_section_winners_same_r1_match_multi(self, app, db, num_sections):
        """
        Art. 45-3-c : pour tout num_sections ≥ 3, aucun match R1 du final
        ne doit recevoir 2 vainqueurs de sections différentes.
        BUG CONFIRMÉ avec num_sections ≥ 3 quand le final est trop petit.
        """
        with app.app_context():
            from blueprints.tournament.draw_generator import \
                generate_section_draw
            n = num_sections * 4   # assez de joueurs
            _, cat = _make_tournament_category(db, n)
            draws = generate_section_draw(cat, num_sections=num_sections)
            main = next(d for d in draws if d.draw_type == 'MAIN')
            sections = [d for d in draws if d.draw_type == 'QUALIFYING']
            r1 = [m for m in main.matches if m.round_number == 1]
            violations = []
            for m in r1:
                qualifs = sum(1 for s in sections if s.main_draw_match_id == m.id)
                if qualifs > 1:
                    violations.append((m.id, qualifs))
            assert not violations, \
                (f"num_sections={num_sections}: {len(violations)} match(s) R1 du final "
                 f"reçoivent >1 qualifié: {violations} — Art. 45-3-c violé")

    def test_section_final_size_accommodates_all_sections(self, app, db):
        """
        Le tableau final doit avoir assez de matchs R1 pour accueillir
        tous les vainqueurs de sections (1 par match).
        Condition : final_draw_size / 2 >= num_sections.
        """
        with app.app_context():
            from blueprints.tournament.draw_generator import \
                generate_section_draw
            for num_sections in (2, 3, 4, 5, 8):
                n = num_sections * 4
                _, cat = _make_tournament_category(db, n)
                draws = generate_section_draw(cat, num_sections=num_sections)
                main = next(d for d in draws if d.draw_type == 'MAIN')
                r1_count = sum(1 for m in main.matches if m.round_number == 1)
                assert r1_count >= num_sections, \
                    (f"num_sections={num_sections}: final a {r1_count} matchs R1 "
                     f"mais {num_sections} sections → pas assez de slots")

    def test_same_ranking_players_in_same_sections(self, app, db):
        """
        Art. 45-3-e : tous les joueurs d'un même classement dans le(s) même(s)
        section(s). Vérifié : joueurs de même ranking.id ne doivent pas être
        répartis dans plus de sections que la règle le permet.
        """
        with app.app_context():
            from blueprints.tournament.draw_generator import \
                generate_section_draw
            n = 9
            _, cat = _make_tournament_category(db, n)
            # Forcer 3 joueurs avec le même classement (ranking.id=5)
            # ranking_id est une propriété read-only sur Player ; modifier via la licence
            for reg in list(cat.registrations)[3:6]:
                reg.player.license.rankingId = 5
            from extensions import db as _db
            _db.session.commit()
            draws = generate_section_draw(cat, num_sections=3)
            # Si 3 joueurs de même classement, ils doivent se trouver dans
            # exactement 1 section chacun (distribution équilibrée) — pas
            # tous dans la même section sauf si 1 seule section
            # Ici on vérifie qu'aucune section n'a > 2 joueurs de ranking_id=5
            sections = [d for d in draws if d.draw_type == 'QUALIFYING']
            for sec in sections:
                r1_ids = {m.player1_id for m in sec.matches if m.round_number == 1 and m.player1_id}
                r1_ids |= {m.player2_id for m in sec.matches if m.round_number == 1 and m.player2_id}
                same_rk = sum(
                    1 for r in cat.registrations
                    if r.player_id in r1_ids and r.player.ranking_id == 5
                )
                assert same_rk <= 2, \
                    f"Section {sec.display_name} a {same_rk} joueurs de même classement (trop concentrés)"

    def test_auto_num_sections_calculation(self, app, db):
        """Sans num_sections fourni, le calcul automatique produit des sections non vides."""
        with app.app_context():
            from blueprints.tournament.draw_generator import \
                generate_section_draw
            for n in (6, 9, 12, 16):
                _, cat = _make_tournament_category(db, n)
                draws = generate_section_draw(cat)
                sections = [d for d in draws if d.draw_type == 'QUALIFYING']
                for sec in sections:
                    r1_count = sum(1 for m in sec.matches if m.round_number == 1)
                    assert r1_count >= 1, \
                        f"Section vide pour n={n}"


# ══════════════════════════════════════════════════════════════════════════════
#  Tests logique de statut tournoi
# ══════════════════════════════════════════════════════════════════════════════

class TestTournamentStatusGuards:
    """
    Vérifie que les fonctions utilitaires de garde retournent les bonnes
    valeurs selon le statut du tournoi.
    """

    def test_can_generate_draw_draft(self, app, db):
        """Statut DRAFT : génération autorisée."""
        from blueprints.tournament.draw_generator import can_generate_draw
        with app.app_context():
            t, cat = _make_tournament_category(db, 4)
            t.status = 'DRAFT'
            db.session.commit()
            ok, msg = can_generate_draw(cat)
            assert ok, f"Attendu OK pour DRAFT, message : {msg}"

    def test_can_generate_draw_open(self, app, db):
        """Statut OPEN : génération autorisée (inscriptions en cours)."""
        from blueprints.tournament.draw_generator import can_generate_draw
        with app.app_context():
            t, cat = _make_tournament_category(db, 4)
            t.status = 'OPEN'
            db.session.commit()
            ok, msg = can_generate_draw(cat)
            assert ok, f"Attendu OK pour OPEN, message : {msg}"

    def test_cannot_generate_draw_in_progress_with_played_matches(self, app, db):
        """
        Statut IN_PROGRESS avec des matchs joués : génération INTERDITE.
        """
        from blueprints.tournament.draw_generator import (can_generate_draw,
                                                          generate_draws)
        from models import TournamentMatch
        with app.app_context():
            t, cat = _make_tournament_category(db, 4)
            t.status = 'IN_PROGRESS'
            db.session.commit()
            draws = generate_draws(cat)
            # Simuler un match joué
            match = draws[0].matches[0]
            match.status = 'COMPLETED'
            match.winner_id = match.player1_id
            db.session.commit()
            ok, msg = can_generate_draw(cat)
            assert not ok, "Génération devrait être bloquée si match joué"

    def test_can_regenerate_in_progress_no_played_matches(self, app, db):
        """
        Statut IN_PROGRESS sans match joué : régénération autorisée
        (Art. 50-3 : tableau peut être refait si aucune partie commencée).
        """
        from blueprints.tournament.draw_generator import (can_generate_draw,
                                                          generate_draws)
        with app.app_context():
            t, cat = _make_tournament_category(db, 4)
            t.status = 'IN_PROGRESS'
            db.session.commit()
            generate_draws(cat)   # génère sans jouer de match
            ok, msg = can_generate_draw(cat)
            assert ok, f"Attendu OK si aucun match joué, message : {msg}"

    def test_cannot_generate_draw_closed(self, app, db):
        """Statut CLOSED : génération toujours INTERDITE."""
        from blueprints.tournament.draw_generator import can_generate_draw
        with app.app_context():
            t, cat = _make_tournament_category(db, 4)
            t.status = 'CLOSED'
            db.session.commit()
            ok, msg = can_generate_draw(cat)
            assert not ok, "Génération devrait être bloquée si tournoi terminé"


# ══════════════════════════════════════════════════════════════════════════════
#  Tests suppression d'un tableau (cascade planning)
# ══════════════════════════════════════════════════════════════════════════════

class TestDrawDeletion:

    def test_delete_draw_removes_all_matches(self, app, db):
        """La suppression d'un TournamentDraw supprime tous ses matchs."""
        with app.app_context():
            from blueprints.tournament.draw_generator import generate_draws
            from models import TournamentDraw, TournamentMatch
            _, cat = _make_tournament_category(db, 8)
            draws = generate_draws(cat)
            main = next(d for d in draws if d.draw_type == 'MAIN')
            draw_id = main.id
            match_count_before = TournamentMatch.query.filter_by(draw_id=draw_id).count()
            assert match_count_before > 0

            db.session.delete(main)
            db.session.commit()

            remaining = TournamentMatch.query.filter_by(draw_id=draw_id).count()
            assert remaining == 0, \
                f"Des matchs persistent après suppression du tableau ({remaining})"

    def test_delete_draw_removes_scheduling_data(self, app, db):
        """La suppression d'un tableau efface les données de planification."""
        with app.app_context():
            from datetime import datetime

            from blueprints.tournament.draw_generator import generate_draws
            from models import TournamentDraw, TournamentMatch
            _, cat = _make_tournament_category(db, 4)
            draws = generate_draws(cat)
            main = draws[0]
            # Simuler une planification sur un match
            m = main.matches[0]
            m.scheduled_at = datetime(2026, 6, 5, 10, 0)
            m.status = 'SCHEDULED'
            db.session.commit()
            draw_id = main.id

            db.session.delete(main)
            db.session.commit()

            remaining = TournamentMatch.query.filter_by(draw_id=draw_id).count()
            assert remaining == 0, "Données de planification non supprimées"

    def test_delete_tournament_cascades_all(self, app, db):
        """La suppression d'un tournoi supprime catégories, tableaux et matchs."""
        with app.app_context():
            from blueprints.tournament.draw_generator import generate_draws
            from models import (Tournament, TournamentCategory, TournamentDraw,
                                TournamentMatch, TournamentRegistration)
            t, cat = _make_tournament_category(db, 6)
            generate_draws(cat)
            tid = t.id

            db.session.delete(t)
            db.session.commit()

            assert TournamentCategory.query.filter_by(tournament_id=tid).count() == 0
            assert TournamentDraw.query.join(
                TournamentDraw.category
            ).filter_by(tournament_id=tid).count() == 0
            assert TournamentRegistration.query.filter_by(tournament_id=tid).count() == 0


# ══════════════════════════════════════════════════════════════════════════════
#  Tests generate_draws pour n > MAX_MAIN_DRAW (Art. 47-5)
#  Régression : bugs détectés sur l'Open d'été 2026 (128 joueurs)
#    Bug 1 : n_direct = MAX_MAIN_DRAW - qualif_spots → négatif pour n > 2×MAX
#    Bug 2 : tableau de qualification sans rounds suivants (1 seul round)
#    Bug 3 : main_draw_match_id jamais défini → qualifiés hors tableau final
# ══════════════════════════════════════════════════════════════════════════════

class TestLargeDrawQualifying:
    """
    Vérifie la génération correcte pour n > MAX_MAIN_DRAW (Art. 47-5 FFT).
    Chaque tableau de qualification doit :
    - être un vrai tableau à élimination directe (plusieurs rounds),
    - être lié au tableau final (main_draw_match_id non None),
    - respecter Art. 45-3-c (au plus 1 qualifié par match R1 du final).
    """

    def test_qualifying_draws_linked_to_main(self, app, db):
        """Pour n > MAX_MAIN_DRAW, tous les qualifying draws doivent être liés au final."""
        with app.app_context():
            from blueprints.tournament.draw_generator import (MAX_MAIN_DRAW,
                                                              generate_draws)
            _, cat = _make_tournament_category(db, MAX_MAIN_DRAW + 10)
            draws = generate_draws(cat)
            main = next(d for d in draws if d.draw_type == 'MAIN')
            qual_draws = [d for d in draws if d.draw_type == 'QUALIFYING']
            assert len(qual_draws) > 0, "Aucun tableau de qualification généré"
            unlinked = [d for d in qual_draws if d.main_draw_match_id is None]
            assert unlinked == [], \
                f"{len(unlinked)} qualifying draw(s) non liés au tableau final (bug main_draw_match_id)"

    def test_qualifying_linked_match_belongs_to_main(self, app, db):
        """main_draw_match_id doit pointer vers un match appartenant au tableau final."""
        with app.app_context():
            from blueprints.tournament.draw_generator import (MAX_MAIN_DRAW,
                                                              generate_draws)
            from models import TournamentMatch
            _, cat = _make_tournament_category(db, MAX_MAIN_DRAW + 8)
            draws = generate_draws(cat)
            main = next(d for d in draws if d.draw_type == 'MAIN')
            main_match_ids = {m.id for m in main.matches}
            qual_draws = [d for d in draws if d.draw_type == 'QUALIFYING']
            for qd in qual_draws:
                assert qd.main_draw_match_id in main_match_ids, \
                    (f"Qualifying '{qd.name}' pointe vers match id={qd.main_draw_match_id} "
                     f"qui n'appartient pas au tableau final")

    def test_qualifying_draw_has_multiple_rounds(self, app, db):
        """Le tableau de qualification doit avoir plusieurs rounds (Art. 47 : élimination directe)."""
        with app.app_context():
            from blueprints.tournament.draw_generator import (MAX_MAIN_DRAW,
                                                              generate_draws)
            _, cat = _make_tournament_category(db, MAX_MAIN_DRAW + 10)
            draws = generate_draws(cat)
            qual_draws = [d for d in draws if d.draw_type == 'QUALIFYING']
            for qd in qual_draws:
                rounds = {m.round_number for m in qd.matches}
                assert max(rounds) > 1, \
                    f"Qualifying '{qd.name}' n'a qu'un seul round (tableau incomplet)"

    def test_all_players_appear_in_a_draw(self, app, db):
        """Tous les joueurs inscrits doivent figurer dans au moins un tableau (R1)."""
        with app.app_context():
            from blueprints.tournament.draw_generator import (MAX_MAIN_DRAW,
                                                              generate_draws)
            n = MAX_MAIN_DRAW + 16
            _, cat = _make_tournament_category(db, n)
            draws = generate_draws(cat)
            present_ids = set()
            for d in draws:
                for m in d.matches:
                    if m.round_number == 1:
                        if m.player1_id:
                            present_ids.add(m.player1_id)
                        if m.player2_id:
                            present_ids.add(m.player2_id)
            registered_ids = {r.player_id for r in cat.registrations
                               if r.status == 'REGISTERED'}
            missing = registered_ids - present_ids
            assert missing == set(), \
                f"{len(missing)} joueur(s) absent(s) des tableaux (perdu dans la répartition)"

    def test_final_draw_has_correct_r1_count(self, app, db):
        """Le tableau final doit toujours avoir MAX_MAIN_DRAW // 2 matchs au R1."""
        with app.app_context():
            from blueprints.tournament.draw_generator import (MAX_MAIN_DRAW,
                                                              generate_draws)
            for n in (MAX_MAIN_DRAW + 1, MAX_MAIN_DRAW * 2, MAX_MAIN_DRAW * 4):
                _, cat = _make_tournament_category(db, n)
                draws = generate_draws(cat)
                main = next(d for d in draws if d.draw_type == 'MAIN')
                r1 = [m for m in main.matches if m.round_number == 1]
                assert len(r1) == MAX_MAIN_DRAW // 2, \
                    (f"n={n}: tableau final doit avoir {MAX_MAIN_DRAW // 2} matchs R1, "
                     f"obtenu {len(r1)}")

    def test_no_two_qualifiers_same_r1_match_large_n(self, app, db):
        """Art. 45-3-c : au plus 1 tableau qualificatif lié par match R1 du final."""
        with app.app_context():
            from blueprints.tournament.draw_generator import (MAX_MAIN_DRAW,
                                                              generate_draws)
            _, cat = _make_tournament_category(db, MAX_MAIN_DRAW * 2)
            draws = generate_draws(cat)
            main = next(d for d in draws if d.draw_type == 'MAIN')
            qual_draws = [d for d in draws if d.draw_type == 'QUALIFYING']
            r1 = [m for m in main.matches if m.round_number == 1]
            for m in r1:
                q_count = sum(1 for qd in qual_draws if qd.main_draw_match_id == m.id)
                assert q_count <= 1, \
                    f"Match R1 id={m.id} reçoit {q_count} qualifiés (Art. 45-3-c violé)"

    def test_128_players_open_ete_coherence(self, app, db):
        """
        Régression spécifique Open d'été 2026 : 128 joueurs.
        - 1 tableau final de MAX_MAIN_DRAW places
        - n_qualif tableaux de qualification, tous liés au final
        - Aucun qualif avec round_max == 1 (tableau incomplet)
        """
        with app.app_context():
            from blueprints.tournament.draw_generator import (MAX_MAIN_DRAW,
                                                              generate_draws)
            n = 128
            _, cat = _make_tournament_category(db, n)
            draws = generate_draws(cat)
            main_draws = [d for d in draws if d.draw_type == 'MAIN']
            qual_draws = [d for d in draws if d.draw_type == 'QUALIFYING']

            assert len(main_draws) == 1, "Doit avoir exactement 1 tableau final"
            main = main_draws[0]

            # Tableau final de taille MAX_MAIN_DRAW
            r1 = [m for m in main.matches if m.round_number == 1]
            assert len(r1) == MAX_MAIN_DRAW // 2, \
                f"Tableau final : attendu {MAX_MAIN_DRAW // 2} matchs R1, obtenu {len(r1)}"

            # Tous les qualifying liés
            assert len(qual_draws) > 0, "Aucun tableau de qualification généré pour 128 joueurs"
            unlinked = [d for d in qual_draws if d.main_draw_match_id is None]
            assert unlinked == [], \
                f"{len(unlinked)} qualifying non liés au tableau final"

            # Chaque qualifying a plusieurs rounds
            for qd in qual_draws:
                max_round = max(m.round_number for m in qd.matches)
                assert max_round > 1, \
                    f"Qualifying '{qd.name}' incomplet (max_round={max_round})"

            # Tous les 128 joueurs sont présents dans un tableau R1
            present_ids = set()
            for d in draws:
                for m in d.matches:
                    if m.round_number == 1:
                        if m.player1_id:
                            present_ids.add(m.player1_id)
                        if m.player2_id:
                            present_ids.add(m.player2_id)
            registered_ids = {r.player_id for r in cat.registrations
                               if r.status == 'REGISTERED'}
            assert registered_ids == present_ids, \
                f"Joueurs manquants ou en trop : diff={registered_ids.symmetric_difference(present_ids)}"

    @pytest.mark.parametrize("n", [33, 40, 50, 64, 100, 128])
    def test_parametric_n_gt_max_main_draw(self, app, db, n):
        """Vérifie les invariants pour divers effectifs n > MAX_MAIN_DRAW."""
        with app.app_context():
            from blueprints.tournament.draw_generator import (MAX_MAIN_DRAW,
                                                              generate_draws)
            _, cat = _make_tournament_category(db, n)
            draws = generate_draws(cat)
            qual_draws = [d for d in draws if d.draw_type == 'QUALIFYING']
            main_draws = [d for d in draws if d.draw_type == 'MAIN']

            assert len(main_draws) == 1, f"n={n}: doit avoir 1 tableau final"
            assert len(qual_draws) > 0, f"n={n}: doit avoir au moins 1 qualifying"

            main = main_draws[0]
            r1_main = [m for m in main.matches if m.round_number == 1]
            assert len(r1_main) == MAX_MAIN_DRAW // 2, \
                f"n={n}: tableau final incorrect ({len(r1_main)} matchs R1)"

            for qd in qual_draws:
                assert qd.main_draw_match_id is not None, \
                    f"n={n}: qualifying '{qd.name}' non lié au final"
                max_round = max(m.round_number for m in qd.matches)
                assert max_round > 1, \
                    f"n={n}: qualifying '{qd.name}' n'a qu'1 round"


# ══════════════════════════════════════════════════════════════════════════════
#  Tests propagation du vainqueur qualificatif → tableau final
# ══════════════════════════════════════════════════════════════════════════════

class TestPropagateWinner:
    """Vérifie propagate_winner pour les cas intra-draw et cross-draw."""

    def test_internal_propagation_next_round(self, app, db):
        """Après un match R1, le vainqueur arrive en R2 (même tableau)."""
        with app.app_context():
            from blueprints.tournament.draw_generator import (generate_draws,
                                                              propagate_winner)
            from models import TournamentMatch
            _, cat = _make_tournament_category(db, 4)
            draws = generate_draws(cat)
            main = next(d for d in draws if d.draw_type == 'MAIN')
            r1 = sorted([m for m in main.matches if m.round_number == 1],
                        key=lambda m: m.position)
            # Trouver le premier match avec 2 joueurs
            target = next((m for m in r1 if m.player1_id and m.player2_id), None)
            assert target is not None, "Aucun match R1 avec 2 joueurs"
            target.winner_id = target.player1_id
            target.status = 'COMPLETED'
            from extensions import db as _db
            _db.session.commit()
            propagate_winner(target)
            next_pos = (target.position + 1) // 2
            next_match = TournamentMatch.query.filter_by(
                draw_id=main.id, round_number=2, position=next_pos
            ).first()
            assert next_match is not None
            if target.position % 2 == 1:
                assert next_match.player1_id == target.player1_id, \
                    "Vainqueur R1 non propagé en R2 slot p1"
            else:
                assert next_match.player2_id == target.player1_id, \
                    "Vainqueur R1 non propagé en R2 slot p2"

    def test_qualifier_propagates_to_main_draw(self, app, db):
        """Le vainqueur de la finale qualificative apparaît dans le tableau final."""
        with app.app_context():
            from blueprints.tournament.draw_generator import (MAX_MAIN_DRAW,
                                                              generate_draws,
                                                              propagate_winner)
            from extensions import db as _db
            from models import TournamentMatch
            n = MAX_MAIN_DRAW + 4   # assez pour déclencher des qualifications
            _, cat = _make_tournament_category(db, n)
            draws = generate_draws(cat)
            qual_draws = [d for d in draws if d.draw_type == 'QUALIFYING']
            assert qual_draws, "Aucun tableau qualificatif généré"
            main = next(d for d in draws if d.draw_type == 'MAIN')

            # Jouer la finale qualificative d'un qualifying lié au final
            linked = [qd for qd in qual_draws if qd.main_draw_match_id]
            assert linked, "Aucun qualifying lié au tableau final"
            qd = linked[0]
            max_r = max(m.round_number for m in qd.matches)
            final_m = next(m for m in qd.matches if m.round_number == max_r)

            # Si le match de finale n'a pas encore de joueurs, les propager manuellement
            if not final_m.player1_id or not final_m.player2_id:
                # Trouver les meilleurs candidats dans le qualifying
                r1 = [m for m in qd.matches if m.round_number == 1
                      and m.player1_id and m.player2_id]
                if r1:
                    # Simuler les rounds précédents
                    for round_num in range(1, max_r):
                        for m in sorted(qd.matches,
                                        key=lambda x: x.position):
                            if m.round_number == round_num and m.player1_id:
                                m.winner_id = m.player1_id
                                m.status = 'COMPLETED'
                                propagate_winner(m)
                    _db.session.commit()
                    # Recharger
                    _db.session.expire_all()
                    final_m = next(m for m in qd.matches
                                   if m.round_number == max_r)

            if not (final_m.player1_id or final_m.player2_id):
                pytest.skip("Match final qualificatif sans joueurs (BYE uniquement)")

            winner_id = final_m.player1_id or final_m.player2_id
            final_m.winner_id = winner_id
            final_m.status = 'COMPLETED'
            _db.session.commit()
            propagate_winner(final_m)
            _db.session.expire_all()

            # Vérifier que le vainqueur est bien dans le match du tableau principal
            target_match = TournamentMatch.query.get(qd.main_draw_match_id)
            slot_value = (target_match.player1_id if qd.main_draw_slot == 'p1'
                          else target_match.player2_id)
            assert slot_value == winner_id, \
                (f"Qualifié non propagé dans le tableau final : "
                 f"slot {qd.main_draw_slot} du match {qd.main_draw_match_id} "
                 f"= {slot_value}, attendu {winner_id}")

    def test_propagate_does_not_overwrite_direct_player(self, app, db):
        """propagate_winner ne doit pas écraser un joueur direct dans le tableau final."""
        with app.app_context():
            from blueprints.tournament.draw_generator import (MAX_MAIN_DRAW,
                                                              generate_draws,
                                                              propagate_winner)
            from extensions import db as _db
            from models import TournamentDraw, TournamentMatch
            n = MAX_MAIN_DRAW + 4
            _, cat = _make_tournament_category(db, n)
            draws = generate_draws(cat)
            qual_draws = [d for d in draws if d.draw_type == 'QUALIFYING']
            main = next(d for d in draws if d.draw_type == 'MAIN')

            linked = [qd for qd in qual_draws if qd.main_draw_match_id]
            assert linked, "Aucun qualifying lié"
            qd = linked[0]
            target_match = TournamentMatch.query.get(qd.main_draw_match_id)

            # Placer artificiellement un joueur dans le slot cible
            slot_attr = 'player1_id' if qd.main_draw_slot == 'p1' else 'player2_id'
            original_id = getattr(target_match, slot_attr)
            if original_id is None:
                # Forcer un joueur dans ce slot
                some_pid = next(
                    r.player_id for r in cat.registrations if r.status == 'REGISTERED'
                )
                setattr(target_match, slot_attr, some_pid)
                original_id = some_pid
                _db.session.commit()

            # Simuler une finale qualificative avec un vainqueur différent
            max_r = max(m.round_number for m in qd.matches)
            final_m = next(m for m in qd.matches if m.round_number == max_r)
            fake_winner = next(
                r.player_id for r in cat.registrations
                if r.player_id != original_id
            )
            final_m.winner_id = fake_winner
            final_m.status = 'COMPLETED'
            _db.session.commit()
            propagate_winner(final_m)
            _db.session.expire_all()

            target_match = TournamentMatch.query.get(qd.main_draw_match_id)
            slot_value = getattr(target_match, slot_attr)
            assert slot_value == original_id, \
                (f"propagate_winner a écrasé le joueur direct {original_id} "
                 f"par {slot_value} dans le slot {qd.main_draw_slot}")


# ══════════════════════════════════════════════════════════════════════════════
#  Tests no-mélange de niveaux (cascade par tranches)
# ══════════════════════════════════════════════════════════════════════════════

class TestCascadeRankingIsolation:
    """
    Art. 45-3-e : les joueurs d'un même classement sont dans le même groupe.
    Pour la cascade, les joueurs NC/ND ne doivent pas affronter des joueurs
    de niveau élevé (−15, 0, 15) dès le premier tableau qualificatif.
    """

    def _get_ranking_id_for_player(self, cat, player_id: int) -> int:
        for r in cat.registrations:
            if r.player_id == player_id:
                return r.player.ranking.id
        return 9999

    def test_cascade_low_ranking_not_in_main_r1(self, app, db):
        """
        Avec 32+ joueurs disparates, les joueurs de classement faible (id élevé)
        ne doivent PAS figurer dans le tableau final R1 — ils passent par les qualifs.
        """
        with app.app_context():
            from blueprints.tournament.draw_generator import (
                TRANCHE_SIZE, generate_draws_by_tranche)
            from extensions import db as _db

            n = 40
            _, cat = _make_tournament_category(db, n)
            # Forcer les 10 derniers joueurs à avoir un ranking_id très élevé
            # (simuler des joueurs NC/ND clairement plus faibles)
            from models import Ranking
            weak_ranking = _db.session.get(Ranking, n + 10)
            if weak_ranking is None:
                weak_ranking = Ranking(id=n + 10, value='NC', series=6)
                _db.session.add(weak_ranking)
                _db.session.flush()
            sorted_regs = sorted(cat.registrations, key=lambda r: r.player.ranking.id)
            for reg in sorted_regs[-10:]:
                reg.player.license.rankingId = weak_ranking.id
            _db.session.commit()

            draws = generate_draws_by_tranche(cat)
            main = next(d for d in draws if d.draw_type == 'MAIN')
            r1_ids = set()
            for m in main.matches:
                if m.round_number == 1:
                    if m.player1_id:
                        r1_ids.add(m.player1_id)
                    if m.player2_id:
                        r1_ids.add(m.player2_id)

            for pid in r1_ids:
                rk_id = self._get_ranking_id_for_player(cat, pid)
                assert rk_id != weak_ranking.id, \
                    (f"Joueur NC (player_id={pid}, ranking_id={rk_id}) "
                     f"présent dans le tableau final R1 — "
                     f"il devrait passer par les qualifications")

    def test_cascade_tranches_do_not_mix_far_rankings(self, app, db):
        """
        Dans un tableau qualificatif de la cascade, aucun match R1 ne doit
        opposer un joueur du groupe le plus fort au joueur le plus faible
        (TRANCHE_SIZE tranches d'écart = groupes séparés).
        """
        with app.app_context():
            from blueprints.tournament.draw_generator import (
                TRANCHE_SIZE, generate_draws_by_tranche)
            from extensions import db as _db
            from models import Ranking

            n = 20
            _, cat = _make_tournament_category(db, n)
            # Créer 2 blocs bien distincts : ranking_id 1–5 (forts) et 50–54 (faibles)
            for i, reg in enumerate(sorted(cat.registrations,
                                           key=lambda r: r.player.ranking.id)):
                target_id = i + 1 if i < 10 else 50 + (i - 10)
                rk = _db.session.get(Ranking, target_id)
                if rk is None:
                    rk = Ranking(id=target_id,
                                 value='Fort' if target_id < 20 else 'Faible',
                                 series=3 if target_id < 20 else 6)
                    _db.session.add(rk)
                    _db.session.flush()
                reg.player.license.rankingId = target_id
            _db.session.commit()

            draws = generate_draws_by_tranche(cat)
            qual_draws = [d for d in draws if d.draw_type == 'QUALIFYING']

            for qd in qual_draws:
                r1_matches = [m for m in qd.matches
                              if m.round_number == 1
                              and m.player1_id and m.player2_id
                              and m.status != 'BYE']
                for m in r1_matches:
                    rk1 = self._get_ranking_id_for_player(cat, m.player1_id)
                    rk2 = self._get_ranking_id_for_player(cat, m.player2_id)
                    gap = abs(rk1 - rk2)
                    assert gap < 30, \
                        (f"Tableau '{qd.name}' R1 pos={m.position}: "
                         f"écart de classement trop grand ({gap}) — "
                         f"joueurs de niveaux trop disparates mélangés "
                         f"(ranking_ids {rk1} vs {rk2})")

    def test_cascade_all_players_placed(self, app, db):
        """Cascade : aucun joueur inscrit ne doit être oublié."""
        with app.app_context():
            from blueprints.tournament.draw_generator import \
                generate_draws_by_tranche
            n = 24
            _, cat = _make_tournament_category(db, n)
            draws = generate_draws_by_tranche(cat)
            all_r1_ids = set()
            for d in draws:
                for m in d.matches:
                    if m.round_number == 1:
                        if m.player1_id:
                            all_r1_ids.add(m.player1_id)
                        if m.player2_id:
                            all_r1_ids.add(m.player2_id)
            registered = {r.player_id for r in cat.registrations
                          if r.status == 'REGISTERED'}
            missing = registered - all_r1_ids
            assert not missing, \
                f"Cascade : {len(missing)} joueur(s) non placé(s) dans les tableaux"

    def test_cascade_no_player_in_two_draws(self, app, db):
        """
        BUG : un joueur ne doit pas apparaître dans R1 de deux draws différents.
        Le slot réservé au cascade entrant doit être VIDE à la génération.
        """
        with app.app_context():
            from collections import Counter

            from blueprints.tournament.draw_generator import \
                generate_draws_by_tranche
            n = 24
            _, cat = _make_tournament_category(db, n)
            draws = generate_draws_by_tranche(cat)
            pid_draws = Counter()
            for d in draws:
                pids_in_draw = set()
                for m in d.matches:
                    if m.round_number == 1:
                        if m.player1_id:
                            pids_in_draw.add(m.player1_id)
                        if m.player2_id:
                            pids_in_draw.add(m.player2_id)
                for pid in pids_in_draw:
                    pid_draws[pid] += 1
            duplicates = {pid: cnt for pid, cnt in pid_draws.items() if cnt > 1}
            assert not duplicates, \
                (f"Cascade : {len(duplicates)} joueur(s) présent(s) dans "
                 f">1 tableau R1 (doublons): player_ids={list(duplicates.keys())}")

    def test_cascade_reserved_slots_empty_at_generation(self, app, db):
        """
        Chaque draw QUALIFYING (sauf le 1er de chaque chaîne) doit avoir
        exactement 1 slot vide (PENDING sans p2) en R1 pour recevoir
        le cascade entrant.
        """
        with app.app_context():
            from blueprints.tournament.draw_generator import \
                generate_draws_by_tranche
            n = 24
            _, cat = _make_tournament_category(db, n)
            draws = generate_draws_by_tranche(cat)
            qual_draws = [d for d in draws if d.draw_type == 'QUALIFYING']

            for qd in qual_draws:
                # Trouver les matchs R1 avec un slot vide (non-BYE)
                r1_pending_slots = []
                for m in qd.matches:
                    if m.round_number != 1:
                        continue
                    if m.status == 'BYE':
                        continue
                    if m.player1_id is None or m.player2_id is None:
                        r1_pending_slots.append(m)
                # Le draw doit avoir au plus 1 slot réservé (pour le cascade entrant)
                # sauf s'il n'a pas d'entrant (le 1er niveau de la chaîne)
                assert len(r1_pending_slots) <= 1, \
                    (f"Draw '{qd.name}' a {len(r1_pending_slots)} slots R1 vides "
                     f"non-BYE (max attendu = 1 pour le slot de cascade)")

    def test_section_draw_same_ranking_distributed_evenly(self, app, db):
        """
        Art. 45-3-e : les joueurs d'un même classement sont répartis équitablement
        entre les sections (round-robin). Vérifié : aucune section ne concentre
        TOUS les joueurs du même classement quand leur nombre > num_sections.
        """
        with app.app_context():
            from blueprints.tournament.draw_generator import \
                generate_section_draw
            from extensions import db as _db
            from models import Ranking

            n = 12
            _, cat = _make_tournament_category(db, n)
            # 4 joueurs forts (id=1), 4 moyens (id=5), 4 NC (id=20)
            sorted_regs = sorted(cat.registrations, key=lambda r: r.player.ranking.id)
            for i, reg in enumerate(sorted_regs):
                if i < 4:
                    target_id = 1
                elif i < 8:
                    target_id = 5
                else:
                    target_id = 20
                rk = _db.session.get(Ranking, target_id)
                if rk is None:
                    rk = Ranking(id=target_id,
                                 value={1: '-15', 5: '30/1', 20: 'NC'}[target_id],
                                 series={1: 2, 5: 4, 20: 6}[target_id])
                    _db.session.add(rk)
                    _db.session.flush()
                reg.player.license.rankingId = target_id
            _db.session.commit()

            draws = generate_section_draw(cat, num_sections=4)
            sections = [d for d in draws if d.draw_type == 'QUALIFYING']

            # Vérifier qu'aucune section ne concentre TOUS les NC (qui seraient 4 pour 4 sections)
            # Avec 4 NC et 4 sections → distribution idéale = 1 NC par section
            for sec in sections:
                r1_ids = set()
                for m in sec.matches:
                    if m.round_number == 1:
                        if m.player1_id:
                            r1_ids.add(m.player1_id)
                        if m.player2_id:
                            r1_ids.add(m.player2_id)
                nc_in_sec = sum(
                    1 for reg in cat.registrations
                    if reg.player_id in r1_ids and reg.player.ranking.id == 20
                )
                assert nc_in_sec <= 2, \
                    (f"Section '{sec.name}' a {nc_in_sec} joueurs NC — "
                     f"la distribution n'est pas équilibrée (Art. 45-3-e)")


# ══════════════════════════════════════════════════════════════════════════════
#  Tests BYE automatique – Sections et Cascade MAIN
# ══════════════════════════════════════════════════════════════════════════════

class TestAutoByeFinalization:
    """
    Vérifie que les matchs du tableau final (sections et cascade) où un seul
    slot est occupé et l'autre ne sera jamais alimenté sont marqués BYE dès
    la génération, et que les vainqueurs sont propagés correctement (pas de
    match PENDING "fantôme" qui bloque le bracket).
    """

    def test_cascade_main_seeds_without_qualifier_are_bye(self, app, db):
        """
        Tableau cascade : les TdS dont le slot adverse ne recevra aucun
        qualifié doivent être en BYE (pas PENDING) dès la génération.
        Régression : avant le fix, ces matchs restaient PENDING indéfiniment.
        """
        with app.app_context():
            from blueprints.tournament.draw_generator import \
                generate_draws_by_tranche
            from models import TournamentDraw, TournamentMatch

            # 24 joueurs, 8 TdS → 1 chaîne cascade → 1 seul qualifié entre dans le MAIN
            # → 7 TdS doivent avoir status=BYE en R1
            n = 24
            _, cat = _make_tournament_category(db, n)
            draws = generate_draws_by_tranche(cat)
            main = next(d for d in draws if d.draw_type == 'MAIN')

            # Construire l'ensemble des slots alimentés par des qualifiés
            fed = {(qd.main_draw_match_id, qd.main_draw_slot)
                   for qd in draws if qd.draw_type == 'QUALIFYING'
                   and qd.main_draw_match_id and qd.main_draw_slot}

            pending_issues = []
            for m in main.matches:
                if m.round_number != 1:
                    continue
                has_p1 = m.player1_id is not None
                has_p2 = m.player2_id is not None
                p1_fed = (m.id, 'p1') in fed
                p2_fed = (m.id, 'p2') in fed
                # Slot occupé + autre slot vide et non alimenté → doit être BYE
                if has_p1 and not has_p2 and not p2_fed and m.status == 'PENDING':
                    pending_issues.append(f'm={m.id} p1_filled p2_empty_unfed PENDING')
                if not has_p1 and has_p2 and not p1_fed and m.status == 'PENDING':
                    pending_issues.append(f'm={m.id} p1_empty_unfed p2_filled PENDING')

            assert pending_issues == [], \
                'TdS sans adversaire ni qualifié restent PENDING (doivent être BYE) :\n' + \
                '\n'.join(pending_issues)

    def test_cascade_main_seeds_propagated_to_r2(self, app, db):
        """
        Les TdS passés en BYE en R1 du tableau final cascade doivent être
        propagés au R2 dès la génération.
        """
        with app.app_context():
            from blueprints.tournament.draw_generator import \
                generate_draws_by_tranche
            from models import TournamentMatch
            n = 24
            _, cat = _make_tournament_category(db, n)
            draws = generate_draws_by_tranche(cat)
            main = next(d for d in draws if d.draw_type == 'MAIN')

            # Les matchs BYE en R1 doivent avoir winner_id et le propager en R2
            r1_byes = [m for m in main.matches if m.round_number == 1 and m.status == 'BYE']
            for bye_m in r1_byes:
                assert bye_m.winner_id is not None, \
                    f'R1 BYE match {bye_m.id} sans winner_id'
                import math as _math
                r2_pos = _math.ceil(bye_m.position / 2)
                r2_match = next(
                    (m for m in main.matches if m.round_number == 2 and m.position == r2_pos),
                    None
                )
                assert r2_match is not None, f'Pas de match R2 pos={r2_pos}'
                r2_player = (r2_match.player1_id if bye_m.position % 2 == 1
                             else r2_match.player2_id)
                assert r2_player == bye_m.winner_id, \
                    (f'Vainqueur BYE R1 pos={bye_m.position} non propagé en R2 pos={r2_pos}: '
                     f'attendu {bye_m.winner_id}, trouvé {r2_player}')

    @pytest.mark.parametrize("num_sections", [3, 5, 7])
    def test_sections_final_ghost_slots_do_not_block_bracket(self, app, db, num_sections):
        """
        Tableau à sections avec N non-puissance-de-2 : le final a plus de matchs
        R1 que de sections. Un match R1 "fantôme" (sans section, sans joueur) ne
        doit pas bloquer le bracket : le vainqueur de la section adjacente doit
        recevoir un BYE récursif et avancer au round suivant.

        On ne fait avancer que les sections avec un vainqueur trivial (1 joueur).
        On vérifie ensuite qu'aucun match R2+ n'est une impasse : 1 joueur +
        autre slot non alimenté par aucune section ET son match précédent est ghost.
        """
        with app.app_context():
            import math as _math

            from blueprints.tournament.draw_generator import (
                generate_section_draw, propagate_winner)
            from extensions import db as _db
            from models import TournamentMatch

            n = num_sections * 4
            _, cat = _make_tournament_category(db, n)
            draws = generate_section_draw(cat, num_sections=num_sections)
            main = next(d for d in draws if d.draw_type == 'MAIN')
            sections = [d for d in draws if d.draw_type == 'QUALIFYING']
            all_main_matches = {(m.round_number, m.position): m for m in main.matches}

            # Propager uniquement les sections dont le match final a déjà un joueur
            # (sections à 1 joueur → winner déjà déterminé par BYE à la génération)
            for sec in sections:
                final_match = max(sec.matches, key=lambda m: m.round_number)
                winner_id = final_match.player1_id or final_match.player2_id
                if winner_id is None:
                    continue
                if final_match.status not in ('BYE', 'WALKOVER', 'COMPLETED'):
                    final_match.winner_id = winner_id
                    final_match.status = 'WALKOVER'
                    _db.session.flush()
                propagate_winner(final_match)

            # Construire les slots alimentés par des sections
            fed_slots = {  # (match_id, slot)
                (s.main_draw_match_id, s.main_draw_slot)
                for s in sections
                if s.main_draw_match_id and s.main_draw_slot
            }
            fed_r1_ids = {s.main_draw_match_id for s in sections if s.main_draw_match_id}

            def feeder_is_ghost(match, empty_slot: str) -> bool:
                """Retourne True si l'alimenteur du slot vide est un match fantôme."""
                if empty_slot == 'p1':
                    feeder_pos = match.position * 2 - 1
                else:
                    feeder_pos = match.position * 2
                feeder = all_main_matches.get((match.round_number - 1, feeder_pos))
                if feeder is None:
                    return True
                if feeder.player1_id or feeder.player2_id or feeder.winner_id:
                    return False  # Un joueur a été placé → pas fantôme
                if feeder.id in fed_r1_ids:
                    return False  # Une section alimente ce match → pas fantôme (en attente)
                return True       # Vraiment vide et sans section → fantôme

            dead_ends = []
            for m in main.matches:
                if m.round_number < 2 or m.status != 'PENDING':
                    continue
                has_p1 = m.player1_id is not None
                has_p2 = m.player2_id is not None
                if has_p1 == has_p2:
                    continue
                empty_slot = 'p2' if has_p1 else 'p1'
                if feeder_is_ghost(m, empty_slot):
                    dead_ends.append(
                        f'R{m.round_number} pos={m.position} m={m.id}: '
                        f'p1={m.player1_id} p2={m.player2_id} — slot {empty_slot} fantôme non résolu'
                    )

            assert dead_ends == [], \
                (f'num_sections={num_sections}: impasses fantômes non résolues :\n'
                 + '\n'.join(dead_ends))

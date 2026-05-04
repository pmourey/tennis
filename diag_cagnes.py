#!/usr/bin/env python3
"""
Diagnostic de cohérence complet du tournoi US Cagnes (id=4).
Vérifie les 3 types de tableaux : classique, cascade, sections.
"""
from app import create_app

PASS = "✅"
FAIL = "❌"
WARN = "⚠️ "

app = create_app()
with app.app_context():
    from collections import Counter, defaultdict

    from models import Tournament, TournamentDraw, TournamentMatch

    t = Tournament.query.get(4)
    print(f'=== Diagnostic : {t.name} (statut={t.status}) ===\n')

    all_ok = True

    for cat in sorted(t.categories, key=lambda c: c.id):
        regs = [r for r in cat.registrations if r.status == 'REGISTERED']
        seeds = [r for r in regs if r.is_seeded]
        draw_type_label = {21: 'CASCADE', 22: 'SECTIONS', 23: 'CLASSIQUE'}.get(cat.id, '?')
        print(f'══ Catégorie {cat.id} [{draw_type_label}] — {len(regs)} inscrits, {len(seeds)} TdS ══')

        all_draws = sorted(cat.draws, key=lambda x: x.id)
        qual_draws = [d for d in all_draws if d.draw_type == 'QUALIFYING']
        main_draws = [d for d in all_draws if d.draw_type == 'MAIN']

        # ── Résumé par draw ────────────────────────────────────────────────
        for d in all_draws:
            rounds = defaultdict(list)
            for m in d.matches:
                rounds[m.round_number].append(m)
            round_summary = " | ".join(
                f"R{rn}:{len(ms)}" for rn, ms in sorted(rounds.items())
            )
            print(f'  Draw {d.id} [{d.draw_type}] {d.name!r}  link={d.main_draw_match_id}/{d.main_draw_slot}  [{round_summary}]')

        ok_local = True
        errors = []
        warnings = []

        # ── CHECK 1 : au moins 1 tableau MAIN ─────────────────────────────
        if not main_draws:
            errors.append('Aucun tableau MAIN')
            ok_local = False
        else:
            main = main_draws[0]
            if len(main_draws) > 1:
                warnings.append(f'{len(main_draws)} tableaux MAIN (attendu 1)')

            # ── CHECK 2 : liens qualifying → draw suivant / main ──────────
            # Construire la carte des slots de propagation attendus
            # (draw_id, match_id, slot) → upstream_draw_id
            expected_prop_slots = {}
            for d in qual_draws:
                if d.main_draw_match_id:
                    t2 = TournamentMatch.query.get(d.main_draw_match_id)
                    if t2:
                        expected_prop_slots[(t2.draw_id, t2.id, d.main_draw_slot)] = d.id

            for d in qual_draws:
                if not d.main_draw_match_id:
                    errors.append(f'Draw {d.id} "{d.name}" : main_draw_match_id absent')
                    ok_local = False
                    continue
                target = TournamentMatch.query.get(d.main_draw_match_id)
                if target is None:
                    errors.append(f'Draw {d.id}: match cible {d.main_draw_match_id} introuvable')
                    ok_local = False
                    continue
                target_draw = TournamentDraw.query.get(target.draw_id)
                slot_val = target.player1_id if d.main_draw_slot == 'p1' else target.player2_id

                if draw_type_label == 'CASCADE':
                    # Pour cascade, la cible peut être un autre qualifying OU le main
                    if target.round_number != 1:
                        errors.append(f'Draw {d.id}: pointe vers R{target.round_number} (attendu R1)')
                        ok_local = False
                    elif slot_val is not None:
                        # Vérifier si le slot contient bien le vainqueur de ce draw
                        upstream_final = sorted(d.matches, key=lambda m: -m.round_number)[0]
                        if upstream_final.winner_id != slot_val:
                            errors.append(
                                f'Draw {d.id} "{d.name}": slot cascade contient player_id={slot_val} '
                                f'≠ vainqueur du draw (id={upstream_final.winner_id}) — conflit'
                            )
                            ok_local = False
                        # else: slot contient le bon vainqueur propagé → OK
                else:
                    # Pour sections, la cible doit être dans le tableau MAIN
                    if target.draw_id != main.id:
                        errors.append(
                            f'Draw {d.id}: pointe vers draw {target.draw_id} '
                            f'au lieu du main {main.id}'
                        )
                        ok_local = False
                    elif target.round_number != 1:
                        errors.append(f'Draw {d.id}: pointe vers R{target.round_number} (attendu R1)')
                        ok_local = False

            # ── CHECK 3 : pas 2 qualifying dans le même match R1 du main ──
            if draw_type_label != 'CASCADE':
                match_counter = Counter(d.main_draw_match_id for d in qual_draws if d.main_draw_match_id)
                doubles = {mid: cnt for mid, cnt in match_counter.items() if cnt > 1}
                if doubles:
                    errors.append(
                        f'Art. 45-3-c: {len(doubles)} match(s) R1 du final avec >1 qualifié: '
                        + ', '.join(f'match {mid}={cnt}Q' for mid, cnt in doubles.items())
                    )
                    ok_local = False

            # ── CHECK 4 : tous les joueurs inscrits placés en R1 ──────────
            placed_ids = set()
            for d in all_draws:
                for m in d.matches:
                    if m.round_number == 1:
                        if m.player1_id:
                            placed_ids.add(m.player1_id)
                        if m.player2_id:
                            placed_ids.add(m.player2_id)
            reg_ids = {r.player_id for r in regs}
            missing = reg_ids - placed_ids
            extra = placed_ids - reg_ids
            if missing:
                errors.append(f'{len(missing)} joueur(s) inscrit(s) non placé(s) en R1: {sorted(missing)}')
                ok_local = False
            if extra:
                warnings.append(f'{len(extra)} joueur(s) dans les draws mais non inscrit(s): {sorted(extra)}')

            # ── CHECK 5 : aucun joueur dans 2 draws simultanément ─────────
            # Exception attendue : vainqueur propagé dans le slot de la cascade/section
            # On reconstruit la carte des slots de propagation (draw_id, match_id, slot)
            pid_is_propagated_in = defaultdict(set)  # pid → set de draw_id où il est propagé
            for d in qual_draws:
                if d.main_draw_match_id:
                    prop_match = TournamentMatch.query.get(d.main_draw_match_id)
                    if prop_match:
                        prop_pid = (prop_match.player1_id if d.main_draw_slot == 'p1'
                                    else prop_match.player2_id)
                        if prop_pid:
                            pid_is_propagated_in[prop_pid].add(prop_match.draw_id)

            pid_to_draws = defaultdict(list)
            for d in all_draws:
                pids_in_draw = set()
                for m in d.matches:
                    if m.round_number == 1:
                        if m.player1_id:
                            pids_in_draw.add(m.player1_id)
                        if m.player2_id:
                            pids_in_draw.add(m.player2_id)
                for pid in pids_in_draw:
                    pid_to_draws[pid].append(d.id)
            dup_players = {}
            for pid, dids in pid_to_draws.items():
                if len(dids) > 1:
                    # Retirer les draws où le joueur est un vainqueur propagé (attendu)
                    non_propagated = [did for did in dids if did not in pid_is_propagated_in[pid]]
                    if len(non_propagated) > 1:
                        dup_players[pid] = dids
            if dup_players:
                from models import License, Player
                for pid, dids in dup_players.items():
                    p = Player.query.get(pid)
                    name = p.license.lastName if p and p.license else str(pid)
                    errors.append(f'Joueur {name} (id={pid}) dans {len(dids)} draws: {dids}')
                ok_local = False

            # ── CHECK 6 : doublons de joueurs dans main R1 ────────────────
            main_r1 = [m for m in main.matches if m.round_number == 1]
            pid_slots = []
            for m in main_r1:
                if m.player1_id:
                    pid_slots.append(m.player1_id)
                if m.player2_id:
                    pid_slots.append(m.player2_id)
            dup_main = {pid: cnt for pid, cnt in Counter(pid_slots).items() if cnt > 1}
            if dup_main:
                errors.append(f'Doublons dans main R1: {dup_main}')
                ok_local = False

            # ── CHECK 7 (classique) : BYE adjacents aux TdS ──────────────
            if draw_type_label == 'CLASSIQUE' and seeds:
                seed_ids = {r.player_id for r in seeds}
                r1 = sorted([m for m in main.matches if m.round_number == 1],
                            key=lambda m: m.position)
                byes_not_adj_to_seed = 0
                for m in r1:
                    if m.status == 'BYE':
                        # Vérifier qu'un des 2 joueurs est une TdS
                        if m.player1_id not in seed_ids and m.player2_id not in seed_ids:
                            byes_not_adj_to_seed += 1
                if byes_not_adj_to_seed:
                    warnings.append(
                        f'{byes_not_adj_to_seed} BYE(s) R1 non adjacents à une TdS '
                        f'(Art. 47-4)'
                    )

        # ── Affichage résultats ────────────────────────────────────────────
        if ok_local and not warnings:
            print(f'  {PASS} Toutes les vérifications passent')
        else:
            all_ok = False
        for e in errors:
            print(f'  {FAIL} {e}')
        for w in warnings:
            print(f'  {WARN} {w}')
        print()

    print('═' * 60)
    if all_ok:
        print(f'{PASS} Tournoi entièrement cohérent')
    else:
        print(f'{FAIL} Des problèmes ont été détectés — voir détails ci-dessus')


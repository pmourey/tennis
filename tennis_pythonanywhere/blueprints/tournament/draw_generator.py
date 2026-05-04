"""
Générateur de tableaux de tournoi conforme aux règles FFT (Articles 45-50).
- Art. 47 : tableau à départ en ligne → draw_size = next_power_of_2(n), BYES = draw_size - n
- Art. 46 : têtes de série dans moitiés/quarts opposés
- Qualifying par tranche de TRANCHE_SIZE niveaux de classement
- Têtes de série directement en tableau final
"""
from __future__ import annotations

import logging
import math
import random
from datetime import datetime

from extensions import db
from models import TournamentDraw, TournamentMatch

logger = logging.getLogger(__name__)

MAX_MAIN_DRAW = 32
TRANCHE_SIZE = 3    # nombre de niveaux de classement par tranche de qualification
MAX_SECTION_SIZE = 8  # nombre maximum de joueurs par section qualificative


# ─── Utilitaires ──────────────────────────────────────────────────────────────

def next_power_of_2(n: int) -> int:
    if n <= 4:
        return 4
    return 2 ** math.ceil(math.log2(n))


def can_generate_draw(category) -> tuple[bool, str]:
    """
    Vérifie si la génération (ou régénération) d'un tableau est autorisée
    selon le statut du tournoi (Art. 50-3 FFT).

    Règles :
    - DRAFT / OPEN       : toujours autorisé.
    - IN_PROGRESS        : autorisé UNIQUEMENT si aucun match n'est dans
      l'état COMPLETED ou WALKOVER (Art. 50-3 : le tableau peut être refait
      tant qu'aucune partie n'a commencé).
    - CLOSED             : toujours interdit.

    Retourne (ok: bool, message: str).
    """
    tournament = category.tournament
    status = tournament.status

    if status == 'CLOSED':
        return False, "Le tournoi est terminé (CLOSED) — modification du tableau interdite."

    if status == 'IN_PROGRESS':
        played = TournamentMatch.query.join(TournamentMatch.draw).filter(
            TournamentDraw.category_id == category.id,
            TournamentMatch.status.in_(['COMPLETED', 'WALKOVER'])
        ).count()
        if played > 0:
            return False, (
                f"Le tournoi est en cours et {played} match(s) ont déjà été joués — "
                "régénération interdite (Art. 50-3 FFT)."
            )
        return True, "Aucun match joué : régénération autorisée (Art. 50-3)."

    return True, "OK"


def nb_seeds_for_draw(draw_size: int, n: int) -> int:
    return min(n // 2, max(2, draw_size // 4))


def seed_positions(draw_size: int, nb_seeds: int) -> list[int]:
    """
    Positions (0-indexed) pour les têtes de série selon Art. 46-1-e-i FFT.

    Règle :
    - Demi-tableau haut : TdS en haut (1ère position) de chaque fraction.
    - Demi-tableau bas  : TdS en bas (dernière position) de chaque fraction.
    - TdS 1 → position 0 (fixe), TdS 2 → draw_size-1 (fixe).
    - TdS 3 & 4 tirées au sort dans les positions intérieures centrales, etc.
    """
    if nb_seeds == 0:
        return []
    if nb_seeds == 1 or draw_size < 2:
        return [0]

    # Arrondir nb_seeds à la puissance de 2 ≤ nb_seeds
    n = 1
    while n * 2 <= nb_seeds:
        n *= 2
    if n < 2:
        n = 2

    fraction_size = max(1, draw_size // n)
    half = draw_size // 2

    # Positions légales (Art. 46-1-e-i) :
    # • Demi-tableau haut : haut (première position) de chaque fraction
    # • Demi-tableau bas  : bas (dernière position) de chaque fraction
    top_positions = [i * fraction_size for i in range(n // 2)]
    bot_positions = [half + (j + 1) * fraction_size - 1 for j in range(n // 2)]

    # Ordre d'attribution :
    # TdS 1 → top_positions[0] = 0
    # TdS 2 → bot_positions[-1] = draw_size - 1
    # TdS 3 & 4 → {top_positions[-1], bot_positions[0]} tirage au sort
    # TdS 5–8 → paires suivantes tirées au sort depuis le centre
    result: list[int] = [top_positions[0], bot_positions[-1]]
    inner_top = list(reversed(top_positions[1:]))   # centre → extérieur (haut)
    inner_bot = list(bot_positions[:-1])             # centre → extérieur (bas)

    while len(result) < nb_seeds and (inner_top or inner_bot):
        pair: list[int] = []
        if inner_top:
            pair.append(inner_top.pop(0))
        if inner_bot:
            pair.append(inner_bot.pop(0))
        random.shuffle(pair)
        for p in pair:
            if len(result) < nb_seeds:
                result.append(p)

    return result[:nb_seeds]


# ─── Génération standard (sans tranches) ──────────────────────────────────────

def generate_draws(category) -> list[TournamentDraw]:
    """
    Génération standard : tableau(x) principal(aux) avec BYES.
    Si n ≤ MAX_MAIN_DRAW : un seul tableau principal.
    Si n > MAX_MAIN_DRAW : qualifying + principal.
    """
    for old_draw in list(category.draws):
        db.session.delete(old_draw)
    db.session.flush()

    registrations = [r for r in category.registrations if r.status == 'REGISTERED']
    # Filtrer selon le classement plancher (min) et plafond (max)
    if getattr(category, 'min_ranking_id', None):
        registrations = [r for r in registrations
                         if r.player.ranking.id <= category.min_ranking_id]
    if getattr(category, 'max_ranking_id', None):
        registrations = [r for r in registrations
                         if r.player.ranking.id >= category.max_ranking_id]
    _series = getattr(category, 'allowed_series_list', [])
    if _series:
        registrations = [r for r in registrations if r.player.ranking.series in _series]
    n = len(registrations)
    if n < 2:
        return []

    sorted_regs = sorted(registrations, key=lambda r: r.player.ranking.id)
    created: list[TournamentDraw] = []

    if n <= MAX_MAIN_DRAW:
        draw_size = next_power_of_2(n)
        seeds, unseeded = _prepare_seeds(sorted_regs, draw_size)
        main_draw = _create_draw(category, 'MAIN', 'Tableau Final')
        _build_draw(main_draw, seeds, unseeded, draw_size)
        created.append(main_draw)
    else:
        # Art. 47-5 : réserver des places pour les qualifiés dans le tableau final.
        # Bug corrigé : n_direct = MAX_MAIN_DRAW - qualif_spots pouvait être négatif.
        # Nouvelle logique : n_qualif slots pour qualifiés (≤ moitié du final),
        # n_direct = MAX_MAIN_DRAW - n_qualif joueurs directs.
        n_qualif = MAX_MAIN_DRAW // 2
        # Garantir ≥ 2 joueurs par mini-tableau de qualification
        while n_qualif > 1 and (n - (MAX_MAIN_DRAW - n_qualif)) < n_qualif * 2:
            n_qualif //= 2
        n_direct = MAX_MAIN_DRAW - n_qualif

        direct_regs = sorted_regs[:n_direct]
        qualif_regs = sorted_regs[n_direct:]

        # Créer n_qualif vrais tableaux de qualification à élimination directe
        ppq = max(2, len(qualif_regs) // n_qualif)  # joueurs par mini-tableau
        qual_draws = []
        for i in range(n_qualif):
            start = i * ppq
            end = start + ppq if i < n_qualif - 1 else len(qualif_regs)
            players = qualif_regs[start:end]
            if len(players) < 2:
                break
            q_size = next_power_of_2(len(players))
            q_seeds, q_unseeded = _prepare_seeds_tranche(players, q_size)
            qd = _create_draw(category, 'QUALIFYING', f'Qualifications {i + 1}')
            _build_draw(qd, q_seeds, q_unseeded, q_size)
            qual_draws.append(qd)
            created.append(qd)

        # Tableau final : joueurs directs + slots PENDING pour les qualifiés (Art. 47-5)
        seeds, unseeded = _prepare_seeds(direct_regs, MAX_MAIN_DRAW)
        main_draw = _create_draw(category, 'MAIN', 'Tableau Final')
        _build_draw_final_with_seeds(main_draw, seeds, len(qual_draws), MAX_MAIN_DRAW,
                                     direct_unseeded=unseeded)
        created.append(main_draw)

        # Lier les tableaux qualificatifs aux slots du tableau final (Art. 45-3-c)
        _link_sections_to_final(qual_draws, main_draw)

    db.session.commit()
    return created


# ─── Génération par tranches de classement (cascade en chaînes) ──────────────

def generate_draws_by_tranche(category) -> list[TournamentDraw]:
    """
    Génération en cascade par groupes de classement et chaînes parallèles.

    Architecture (Art. 45–49 FFT) :
    - Les non-têtes de série sont regroupés par tranche de TRANCHE_SIZE niveaux
      de classement consécutifs (pire → meilleur) : [G1, G2, ..., GN].
    - N_CHAINS chaînes parallèles traversent tous les niveaux.
    - À chaque niveau Gi, on crée N_CHAINS sections (tableaux classiques).
      Chaque section reçoit les joueurs de Gi affectés à sa chaîne
      + le qualifié de la section de même chaîne du niveau précédent (si existe).
      Chaque section qualifie 1 joueur (son vainqueur).
    - Le vainqueur de la dernière section de chaque chaîne entre dans le Tableau Final.
    - Art. 45.3.c : les chaînes distinctes occupent des slots distincts du tour 1 du final.
    - Art. 45.3.e : tous les joueurs d'un même classement sont dans le(s) même(s) section(s).

    N_CHAINS est calculé ainsi :
      n_chains_raw = len(non_seeds) // (2 * max(1, n_niveaux))
      n_chains = plus grande puissance de 2 ≤ n_chains_raw, min 1
    Contrôle : chaque section doit avoir ≥ 2 joueurs de son propre niveau.
    """
    for old_draw in list(category.draws):
        db.session.delete(old_draw)
    db.session.flush()

    registrations = [r for r in category.registrations if r.status == 'REGISTERED']
    if getattr(category, 'min_ranking_id', None):
        registrations = [r for r in registrations
                         if r.player.ranking.id <= category.min_ranking_id]
    if getattr(category, 'max_ranking_id', None):
        registrations = [r for r in registrations
                         if r.player.ranking.id >= category.max_ranking_id]
    _series = getattr(category, 'allowed_series_list', [])
    if _series:
        registrations = [r for r in registrations if r.player.ranking.series in _series]
    n = len(registrations)
    if n < 2:
        return []

    sorted_regs = sorted(registrations, key=lambda r: r.player.ranking.id)
    created: list[TournamentDraw] = []

    # ── Têtes de série ────────────────────────────────────────────────────────
    estimated_draw_size = next_power_of_2(n)
    seeds, non_seeds = _prepare_seeds(sorted_regs, estimated_draw_size)
    logger.info(f'[CASCADE] n={n}, seeds={len(seeds)}, non_seeds={len(non_seeds)}')
    print(f'[DRAW_GEN] n={n}, seeds={len(seeds)}, non_seeds={len(non_seeds)}')

    if not non_seeds:
        final_draw_size = next_power_of_2(len(seeds))
        final_draw = _create_draw(category, 'MAIN', 'Tableau Final')
        _build_draw(final_draw, seeds, [], final_draw_size)
        db.session.commit()
        return [final_draw]

    # ── Groupes par tranche de classement (pire → meilleur) ──────────────────
    groups = _group_by_tranche(non_seeds, TRANCHE_SIZE)
    n_levels = max(1, len(groups))
    logger.info(f'[CASCADE] {len(non_seeds)} non-seeds → {n_levels} niveaux')
    print(f'[DRAW_GEN] {len(non_seeds)} non-seeds → {n_levels} niveaux')

    # ── Calcul du nombre de chaînes parallèles ────────────────────────────────
    # Cible : ~2*n_levels joueurs par section par niveau
    n_chains_raw = max(1, len(non_seeds) // (2 * n_levels))
    # Arrondir à la puissance de 2 inférieure ou égale
    n_chains = 1
    while n_chains * 2 <= n_chains_raw:
        n_chains *= 2
    # Vérification : chaque chaîne doit avoir ≥ 2 joueurs du niveau le plus petit
    min_group_size = min(len(g) for g in groups)
    while n_chains > 1 and min_group_size // n_chains < 2:
        n_chains //= 2

    logger.info(f'[CASCADE] n_chains={n_chains} (n_chains_raw={n_chains_raw}, min_group={min_group_size})')
    print(f'[DRAW_GEN] n_chains={n_chains} (raw={n_chains_raw}, min_group={min_group_size})')

    # ── Cascade niveau par niveau ─────────────────────────────────────────────
    # prev_chain_draws[i] = dernier draw de la chaîne i (niveau précédent)
    prev_chain_draws: list[TournamentDraw | None] = [None] * n_chains

    for level_idx, group in enumerate(groups):
        # groups est trié pire→meilleur ; group[0]=meilleur, group[-1]=pire dans le groupe
        best_val  = group[0].player.ranking.value
        worst_val = group[-1].player.ranking.value
        label_base = (f'Qualifications ({worst_val}–{best_val})'
                      if best_val != worst_val
                      else f'Qualifications ({best_val})')

        # Distribuer les joueurs du groupe entre les chaînes (pire en premier → équilibré)
        group_worst_first = sorted(group, key=lambda r: r.player.ranking.id, reverse=True)
        chain_players: list[list] = [[] for _ in range(n_chains)]
        for i, reg in enumerate(group_worst_first):
            chain_players[i % n_chains].append(reg)

        curr_chain_draws: list[TournamentDraw | None] = [None] * n_chains

        for chain_idx in range(n_chains):
            players = chain_players[chain_idx]
            has_incoming = (prev_chain_draws[chain_idx] is not None)
            n_in_section = len(players) + (1 if has_incoming else 0)

            if n_in_section < 2:
                print(f'[DRAW_GEN] Niveau {level_idx+1} chaîne {chain_idx+1}: SKIP '
                      f'({len(players)} joueurs, incoming={has_incoming})')
                continue

            label = f'{label_base} – {chain_idx + 1}' if n_chains > 1 else label_base
            q_size = next_power_of_2(n_in_section)
            qd = _create_draw(category, 'QUALIFYING', label)

            # Construire le tableau avec slot réservé si qualifié entrant
            _build_draw_cascade(qd, players, q_size, has_incoming=has_incoming)

            # Lier le qualifié entrant (chaîne précédente) à ce tableau
            if has_incoming:
                _link_to_first_empty_slot(prev_chain_draws[chain_idx], qd)

            curr_chain_draws[chain_idx] = qd
            created.append(qd)
            print(f'[DRAW_GEN] Niveau {level_idx+1} ({label_base}) chaîne {chain_idx+1}: '
                  f'{len(players)} joueurs + incoming={has_incoming}, draw_size={q_size}')

        prev_chain_draws = curr_chain_draws

    # ── Tableau final : têtes de série + qualifiés des dernières chaînes ──────
    n_qualifiers = sum(1 for d in prev_chain_draws if d is not None)
    final_draw_size = next_power_of_2(len(seeds) + n_qualifiers)

    final_draw = _create_draw(category, 'MAIN', 'Tableau Final')
    _build_draw_final_with_seeds(final_draw, seeds,
                                  final_draw_size - len(seeds), final_draw_size)
    created.append(final_draw)

    # Lier les derniers draws de chaque chaîne au tableau final
    _link_chain_last_draws_to_main(prev_chain_draws, final_draw)
    n_linked = sum(1 for d in prev_chain_draws
                   if d is not None and d.main_draw_match_id is not None)
    print(f'[DRAW_GEN] Final: draw_size={final_draw_size}, {len(seeds)} TdS, '
          f'{n_qualifiers} qualifiés, {n_linked} liés')
    logger.info(f'  → Final: draw_size={final_draw_size}, {len(seeds)} TdS, '
                f'{n_qualifiers} qualifiés')

    # Marquer BYE les TdS sans adversaire ni qualifié entrant
    _finalize_main_draw_byes(final_draw)

    db.session.commit()
    return created


def _distribute_into_qualif_groups(non_seeds: list, qualif_spots: int) -> list[list]:
    """
    Divise les joueurs qualifiants en groupes homogènes (au moins 2 joueurs chacun).
    Distribution séquentielle du pire vers le meilleur classement :
    les joueurs de même niveau se retrouvent dans le même groupe.
    Retourne les groupes triés meilleur → pire (pour l'affichage des tableaux).
    """
    if not non_seeds:
        return []

    # Trier du pire (id max) vers le meilleur (id min)
    sorted_worst = sorted(non_seeds, key=lambda r: r.player.ranking.id, reverse=True)
    n = len(sorted_worst)

    # On ne peut pas avoir plus de n//2 groupes (sinon groupes de 1 joueur)
    actual_spots = min(qualif_spots, max(1, n // 2))

    base = n // actual_spots
    rem = n % actual_spots
    groups = []
    idx = 0
    for i in range(actual_spots):
        size = base + (1 if i < rem else 0)
        group = sorted_worst[idx:idx + size]
        group.sort(key=lambda r: r.player.ranking.id)  # meilleur → pire dans le groupe
        if group:
            groups.append(group)
        idx += size

    return groups


def _group_by_tranche(registrations: list, tranche_size: int) -> list[list]:
    """
    Groupe les inscriptions par tranches de tranche_size niveaux de classement consécutifs.
    Trie du pire classement (NC, id max) vers le meilleur (id min).
    Retourne les tranches dans cet ordre (pire → meilleur).
    """
    if not registrations:
        return []

    # Trier du pire (NC, id max) vers le meilleur
    sorted_worst_first = sorted(registrations, key=lambda r: r.player.ranking.id, reverse=True)
    ranking_ids = [r.player.ranking.id for r in sorted_worst_first]
    max_id = ranking_ids[0]
    min_id = ranking_ids[-1]

    tranches = []
    boundary = max_id
    while boundary >= min_id:
        lower = boundary - tranche_size
        tranche = [r for r in sorted_worst_first
                   if lower < r.player.ranking.id <= boundary]
        if tranche:
            # Re-trier la tranche du meilleur vers le pire pour le draw
            tranche.sort(key=lambda r: r.player.ranking.id)
            tranches.append(tranche)
        boundary -= tranche_size

    return tranches


# ─── Fonctions internes ────────────────────────────────────────────────────────

def _create_draw(category, draw_type: str, name: str = None) -> TournamentDraw:
    draw = TournamentDraw(
        category_id=category.id,
        draw_type=draw_type,
        name=name,
        generated_at=datetime.utcnow()
    )
    db.session.add(draw)
    db.session.flush()
    return draw


def _prepare_seeds(sorted_regs: list, draw_size: int):
    """Prépare les têtes de série (auto si aucune manuelle)."""
    manual_seeds = sorted([r for r in sorted_regs if r.is_seeded],
                          key=lambda r: r.seed_number or 999)
    unseeded = [r for r in sorted_regs if not r.is_seeded]
    if not manual_seeds:
        nb = nb_seeds_for_draw(draw_size, len(sorted_regs))
        manual_seeds = sorted_regs[:nb]
        unseeded = sorted_regs[nb:]
        for i, s in enumerate(manual_seeds):
            s.is_seeded = True
            s.seed_number = i + 1
    random.shuffle(unseeded)
    return manual_seeds, unseeded


def _prepare_seeds_tranche(tranche: list, draw_size: int):
    """Pour un tableau qualificatif, la meilleure tête de série est la TdS 1."""
    if len(tranche) <= 2:
        return [], list(tranche)
    nb = min(2, len(tranche) // 2)
    seeds = tranche[:nb]
    unseeded = list(tranche[nb:])
    random.shuffle(unseeded)
    return seeds, unseeded


def _build_draw(draw: TournamentDraw, seeds: list, unseeded: list, draw_size: int):
    """
    Construit le tableau avec :
    - Art. 46-1-e-i : placement des TdS (haut des fractions / bas des fractions)
    - Art. 47-4    : placement des BYEs (exempts) adjacents aux premières TdS
        a. n_byes < n_seeds → les n_byes premières TdS sont exemptes
        b. n_byes ≥ n_seeds → toutes TdS exemptes + surplus comme TdS virtuelles
        c. sans TdS → BYEs répartis comme des TdS virtuelles
    """
    n_byes = draw_size - len(seeds) - len(unseeded)
    slots = [None] * draw_size
    bye_reserved = [False] * draw_size

    positions = seed_positions(draw_size, len(seeds))
    for idx, reg in enumerate(seeds):
        if idx < len(positions):
            slots[positions[idx]] = reg

    # ── Réserver les positions BYE selon Art. 47-4 ───────────────────────────
    if n_byes > 0:
        if seeds:
            # BYEs adjacents aux n_seed_byes premières TdS (position partenaire = pos ^ 1)
            n_seed_byes = min(n_byes, len(seeds))
            placed = 0
            for k in range(n_seed_byes):
                if k < len(positions):
                    bp = positions[k] ^ 1   # partenaire au 1er tour (XOR 1)
                    if 0 <= bp < draw_size and slots[bp] is None and not bye_reserved[bp]:
                        bye_reserved[bp] = True
                        placed += 1
            # Art. 47-4-b : BYEs supplémentaires répartis comme TdS virtuelles
            extra = n_byes - placed
            if extra > 0:
                virtual_pos = seed_positions(draw_size, len(seeds) + extra)
                for vp in virtual_pos[len(seeds):]:
                    if extra <= 0:
                        break
                    bp = vp ^ 1
                    if 0 <= bp < draw_size and slots[bp] is None and not bye_reserved[bp]:
                        bye_reserved[bp] = True
                        extra -= 1
        else:
            # Art. 47-4-c : sans TdS, BYEs répartis comme des TdS virtuelles
            virtual_pos = seed_positions(draw_size, n_byes)
            placed = 0
            for vp in virtual_pos:
                if placed >= n_byes:
                    break
                bp = vp ^ 1
                if 0 <= bp < draw_size and slots[bp] is None and not bye_reserved[bp]:
                    bye_reserved[bp] = True
                    placed += 1

    # ── Remplir les slots libres non réservés avec les non-TdS ───────────────
    unseed_iter = iter(unseeded)
    for i in range(draw_size):
        if slots[i] is None and not bye_reserved[i]:
            try:
                slots[i] = next(unseed_iter)
            except StopIteration:
                bye_reserved[i] = True  # BYE supplémentaire

    # ── Éviter les matches « BYE vs BYE » (Art. 47-3 : 1 exempt par slot) ───
    # Si deux positions consécutives forment un match entièrement vide,
    # on récupère un joueur depuis un match à 2 joueurs non-TdS.
    seed_pos_set = set(positions)
    for match_idx in range(draw_size // 2):
        p1i, p2i = match_idx * 2, match_idx * 2 + 1
        if slots[p1i] is None and slots[p2i] is None:
            for donor in range(draw_size // 2):
                if donor == match_idx:
                    continue
                d1i, d2i = donor * 2, donor * 2 + 1
                if slots[d1i] is not None and slots[d2i] is not None:
                    # Déplacer le slot non-TdS du match donneur dans ce match vide
                    for di in (d2i, d1i):
                        if di not in seed_pos_set:
                            slots[p2i] = slots[di]
                            slots[di] = None
                            break
                    else:
                        continue
                    break

    total_rounds = int(math.log2(draw_size))
    for i in range(draw_size // 2):
        s1, s2 = slots[i * 2], slots[i * 2 + 1]
        p1 = s1.player if s1 else None
        p2 = s2.player if s2 else None
        status = 'BYE' if (p1 is None or p2 is None) else 'PENDING'
        m = TournamentMatch(
            draw_id=draw.id, round_number=1, position=i + 1,
            player1_id=p1.id if p1 else None,
            player2_id=p2.id if p2 else None,
            status=status
        )
        if status == 'BYE':
            winner = p1 or p2
            if winner:
                m.winner_id = winner.id
        db.session.add(m)

    for r in range(2, total_rounds + 1):
        for i in range(draw_size // (2 ** r)):
            db.session.add(TournamentMatch(
                draw_id=draw.id, round_number=r, position=i + 1, status='PENDING'
            ))
    db.session.flush()

    # Propager les BYEs automatiquement
    for m in TournamentMatch.query.filter_by(draw_id=draw.id, round_number=1).all():
        if m.status == 'BYE' and m.winner_id:
            _propagate_bye(m)


def _build_draw_final_with_seeds(draw: TournamentDraw, seeds: list,
                                  qualif_winner_count: int, draw_size: int,
                                  direct_unseeded=None):
    """
    Tableau final : les têtes de série sont placées selon Art. 46.
    Les non-TdS directs (direct_unseeded) occupent les slots libres suivants.
    Les slots restants sont des qualifiés à venir (status=PENDING, player=None).
    Aucun BYE n'est créé : les slots vides attendent un qualifié (Art. 47-5).
    """
    slots = [None] * draw_size
    positions = seed_positions(draw_size, len(seeds))
    for idx, reg in enumerate(seeds):
        if idx < len(positions):
            slots[positions[idx]] = reg

    # Placer les non-TdS directs dans les slots libres — au maximum 1 par match
    # pour laisser systématiquement une place au qualifié (Art. 47-5).
    # Les TdS affrontent un qualifié (slot vide) ; les matchs sans TdS reçoivent
    # 1 non-TdS en p2, laissant p1 vide pour le qualifié.
    if direct_unseeded:
        random.shuffle(direct_unseeded)
        unseeded_iter = iter(direct_unseeded)
        try:
            # Uniquement les matchs entièrement vides (sans TdS) : 1 non-TdS en p2
            for mi in range(draw_size // 2):
                s1, s2 = mi * 2, mi * 2 + 1
                if slots[s1] is None and slots[s2] is None:
                    slots[s2] = next(unseeded_iter)
        except StopIteration:
            pass

    # Créer les matchs (status=PENDING même si player=None : slot pour un qualifié)
    total_rounds = int(math.log2(draw_size))
    for i in range(draw_size // 2):
        s1, s2 = slots[i * 2], slots[i * 2 + 1]
        p1 = s1.player if s1 else None
        p2 = s2.player if s2 else None

        m = TournamentMatch(
            draw_id=draw.id, round_number=1, position=i + 1,
            player1_id=p1.id if p1 else None,
            player2_id=p2.id if p2 else None,
            status='PENDING'
        )
        db.session.add(m)

    for r in range(2, total_rounds + 1):
        for i in range(draw_size // (2 ** r)):
            db.session.add(TournamentMatch(
                draw_id=draw.id, round_number=r, position=i + 1, status='PENDING'
            ))
    db.session.flush()


def _propagate_bye(match: TournamentMatch):
    next_pos = math.ceil(match.position / 2)
    next_match = TournamentMatch.query.filter_by(
        draw_id=match.draw_id, round_number=match.round_number + 1, position=next_pos
    ).first()
    if not next_match:
        return

    if match.position % 2 == 1:
        next_match.player1_id = match.winner_id
        other_empty = next_match.player2_id is None
        other_slot = 'p2'
        feeder_pos = next_pos * 2          # match pair → alimente player2
    else:
        next_match.player2_id = match.winner_id
        other_empty = next_match.player1_id is None
        other_slot = 'p1'
        feeder_pos = next_pos * 2 - 1     # match impair → alimente player1

    # BYE récursif : si l'autre slot est vide et que le match du tour précédent
    # qui l'alimenterait est un "ghost" (aucun joueur, aucun qualifié) → avancer.
    if other_empty and next_match.status == 'PENDING':
        other_feed = TournamentDraw.query.filter_by(
            main_draw_match_id=next_match.id,
            main_draw_slot=other_slot
        ).first()
        if not other_feed:
            feeder = TournamentMatch.query.filter_by(
                draw_id=next_match.draw_id,
                round_number=next_match.round_number - 1,
                position=feeder_pos
            ).first()
            is_ghost = (
                feeder is None or (
                    feeder.player1_id is None
                    and feeder.player2_id is None
                    and feeder.winner_id is None
                    and not TournamentDraw.query.filter_by(
                        main_draw_match_id=feeder.id
                    ).count()
                )
            )
            if is_ghost:
                next_match.status = 'BYE'
                next_match.winner_id = match.winner_id
                db.session.flush()
                _propagate_bye(next_match)


def _finalize_main_draw_byes(draw: TournamentDraw):
    """
    Après génération et liaison des qualifiés, marque BYE tous les matchs R1
    où un seul slot est occupé par un joueur direct et l'autre n'est alimenté
    par aucun tableau qualificatif. Propage les vainqueurs au round suivant.
    Couvre les cas : tableau final cascade (TdS vs slot vide sans qualifié)
    et tableau final sections (match ghost totalement vide).
    """
    fed_slots: set = set()
    qual_draws = TournamentDraw.query.filter_by(
        category_id=draw.category_id, draw_type='QUALIFYING'
    ).all()
    for qd in qual_draws:
        if qd.main_draw_match_id and qd.main_draw_slot:
            fed_slots.add((qd.main_draw_match_id, qd.main_draw_slot))

    r1_matches = TournamentMatch.query.filter_by(
        draw_id=draw.id, round_number=1
    ).order_by(TournamentMatch.position).all()

    for m in r1_matches:
        if m.status != 'PENDING':
            continue
        p1_empty = m.player1_id is None
        p2_empty = m.player2_id is None
        p1_fed = (m.id, 'p1') in fed_slots
        p2_fed = (m.id, 'p2') in fed_slots

        if not p1_empty and p2_empty and not p2_fed:
            # Joueur direct en p1, p2 jamais alimenté → BYE
            m.status = 'BYE'
            m.winner_id = m.player1_id
            db.session.flush()
            _propagate_bye(m)
        elif p1_empty and not p2_empty and not p1_fed:
            # Joueur direct en p2, p1 jamais alimenté → BYE
            m.status = 'BYE'
            m.winner_id = m.player2_id
            db.session.flush()
            _propagate_bye(m)


# ─── Tableau à sections (Art. 49 FFT) ────────────────────────────────────────

def generate_section_draw(category, num_sections: int = None) -> list[TournamentDraw]:
    """
    Génère un tableau à sections selon Art. 49 FFT.

    Un tableau à sections qualifie ``num_sections`` joueurs (nombre ≠ puissance de 2
    si possible). Il est constitué de ``num_sections`` sections parallèles, chacune
    étant un tableau classique à départ en ligne (Art. 47) qualifiant 1 joueur.

    Règles appliquées :
    - Art. 49-2-d  : chaque section comporte exactement 1 tête de série.
    - Art. 46-1-e-ii : la TdS k est placée en bas de la section k (Art. 49 § section
      inférieure = section 1, TdS 1 en bas, TdS 2 en bas de la section 2, etc.).
    - Art. 45-3-e  : tous les joueurs d'un même classement sont dans le même groupe ;
      distribution équilibrée entre les sections par tirage au sort.
    - Art. 45-3-c  : deux qualifiés de sections différentes ne se rencontrent pas
      dès le 1er tour du tableau final.
    """
    for old in list(category.draws):
        db.session.delete(old)
    db.session.flush()

    registrations = [r for r in category.registrations if r.status == 'REGISTERED']
    if getattr(category, 'min_ranking_id', None):
        registrations = [r for r in registrations
                         if r.player.ranking.id <= category.min_ranking_id]
    if getattr(category, 'max_ranking_id', None):
        registrations = [r for r in registrations
                         if r.player.ranking.id >= category.max_ranking_id]
    _series = getattr(category, 'allowed_series_list', [])
    if _series:
        registrations = [r for r in registrations if r.player.ranking.series in _series]
    n = len(registrations)
    if n < 2:
        return []

    sorted_regs = sorted(registrations, key=lambda r: r.player.ranking.id)

    # ── Calculer num_sections si non fourni ───────────────────────────────────
    if num_sections is None:
        section_size = next_power_of_2(max(2, n // 3))
        section_size = min(section_size, MAX_SECTION_SIZE)
        num_sections = max(1, n // section_size)

    # Garantir au moins 2 joueurs par section
    if n < num_sections * 2:
        num_sections = max(1, n // 2)

    created: list[TournamentDraw] = []

    # ── Têtes de série (1 par section) ────────────────────────────────────────
    # Les num_sections meilleurs joueurs sont TdS ; TdS k → section k.
    seeds = sorted_regs[:num_sections]
    non_seeds = sorted_regs[num_sections:]
    for i, reg in enumerate(seeds):
        reg.is_seeded = True
        reg.seed_number = i + 1

    # ── Distribution des non-TdS (Art. 45-3-e) ───────────────────────────────
    # Grouper par niveau de classement, puis distribuer équitablement
    # entre les sections par tirage au sort au sein de chaque groupe.
    sections_players: list[list] = [[] for _ in range(num_sections)]
    from itertools import groupby as _groupby
    non_seeds_sorted = sorted(non_seeds, key=lambda r: r.player.ranking.id)
    for _rk_id, group_iter in _groupby(non_seeds_sorted,
                                        key=lambda r: r.player.ranking.id):
        group = list(group_iter)
        random.shuffle(group)
        for i, reg in enumerate(group):
            sections_players[i % num_sections].append(reg)

    # ── Génération de chaque section ──────────────────────────────────────────
    # Art. 46-1-e-ii : TdS k placée en bas de la section k.
    for k, seed_reg in enumerate(seeds):
        section_players = sections_players[k]
        n_in_section = 1 + len(section_players)
        section_size = next_power_of_2(n_in_section)
        label = f'Section {k + 1}'
        section_draw = _create_draw(category, 'QUALIFYING', label)
        _build_section(section_draw, seed_reg, section_players, section_size)
        created.append(section_draw)
        logger.info(f'[SECTION] Section {k + 1}: {n_in_section} joueurs, size={section_size}')
        print(f'[SECTION_DRAW] Section {k + 1}: {n_in_section} joueurs, size={section_size}')

    # ── Tableau final ─────────────────────────────────────────────────────────
    # Art. 45-3-c : chaque match R1 du final reçoit au plus 1 qualifié de section.
    # Il faut donc au moins num_sections matchs R1, soit final_draw_size >= 2*num_sections.
    final_draw_size = next_power_of_2(2 * num_sections)
    final_draw = _create_draw(category, 'MAIN', 'Tableau Final')
    _build_empty_final(final_draw, final_draw_size)
    created.append(final_draw)

    # Lier chaque section au tableau final (Art. 45-3-c)
    _link_sections_to_final(created[:-1], final_draw)
    logger.info(f'[SECTION] Final: draw_size={final_draw_size}, {num_sections} sections')
    print(f'[SECTION_DRAW] Final: draw_size={final_draw_size}, {num_sections} sections')

    # Marquer les matchs R1 fantômes (aucun section qualifié) comme BYE
    _finalize_main_draw_byes(final_draw)

    db.session.commit()
    return created


def _build_section(draw: TournamentDraw, seed, unseeded: list, section_size: int):
    """
    Construit une section selon Art. 49 FFT.

    - La tête de série est placée EN BAS de la section (position section_size - 1),
      conformément à Art. 46-1-e-ii.
    - Art. 47-4 : le BYE adjacent à la TdS lui garantit l'exemption si nécessaire ;
      les BYEs supplémentaires sont distribués vers le haut de la section.
    - Les non-TdS sont placés par tirage au sort dans les positions restantes.
    """
    n_players = 1 + len(unseeded)
    n_byes = section_size - n_players
    slots = [None] * section_size
    bye_reserved = [False] * section_size

    # TdS en bas de la section (Art. 46-1-e-ii)
    slots[section_size - 1] = seed

    # BYE adjacent à la TdS (position partenaire = (section_size-1) ^ 1 = section_size-2)
    if n_byes > 0:
        bp = (section_size - 1) ^ 1
        if slots[bp] is None and not bye_reserved[bp]:
            bye_reserved[bp] = True

        # BYEs supplémentaires distribués vers le haut de la section
        extra = n_byes - sum(bye_reserved)
        for vp in range(0, section_size - 2, 2):   # positions paires en haut
            if extra <= 0:
                break
            bp2 = vp ^ 1
            if (slots[vp] is None and not bye_reserved[vp]
                    and slots[bp2] is None and not bye_reserved[bp2]):
                bye_reserved[bp2] = True
                extra -= 1

    # Remplir les slots libres avec les non-TdS (tirage au sort)
    random.shuffle(unseeded)
    unseed_iter = iter(unseeded)
    for i in range(section_size):
        if slots[i] is None and not bye_reserved[i]:
            try:
                slots[i] = next(unseed_iter)
            except StopIteration:
                bye_reserved[i] = True

    # Créer les matchs du 1er tour
    total_rounds = int(math.log2(section_size))
    for i in range(section_size // 2):
        s1, s2 = slots[i * 2], slots[i * 2 + 1]
        p1 = s1.player if s1 else None
        p2 = s2.player if s2 else None
        status = 'BYE' if (p1 is None or p2 is None) else 'PENDING'
        m = TournamentMatch(
            draw_id=draw.id, round_number=1, position=i + 1,
            player1_id=p1.id if p1 else None,
            player2_id=p2.id if p2 else None,
            status=status
        )
        if status == 'BYE':
            winner = p1 or p2
            if winner:
                m.winner_id = winner.id
        db.session.add(m)

    for r in range(2, total_rounds + 1):
        for i in range(section_size // (2 ** r)):
            db.session.add(TournamentMatch(
                draw_id=draw.id, round_number=r, position=i + 1, status='PENDING'
            ))
    db.session.flush()

    for m in TournamentMatch.query.filter_by(draw_id=draw.id, round_number=1).all():
        if m.status == 'BYE' and m.winner_id:
            _propagate_bye(m)


def _build_empty_final(draw: TournamentDraw, draw_size: int):
    """
    Crée un tableau final vide (tous les slots seront remplis par les
    vainqueurs de sections via _link_sections_to_final).
    """
    total_rounds = int(math.log2(draw_size))
    for r in range(1, total_rounds + 1):
        for i in range(draw_size // (2 ** r)):
            db.session.add(TournamentMatch(
                draw_id=draw.id, round_number=r, position=i + 1, status='PENDING'
            ))
    db.session.flush()


def _link_sections_to_final(section_draws: list, final_draw: TournamentDraw):
    """
    Lie le vainqueur de chaque section à un slot du tableau final.

    Art. 45-3-c : deux qualifiés de sections différentes ne se rencontrent
    pas dès le 1er tour → répartition pass1 (p1 de chaque match) avant
    pass2 (p2 de chaque match).
    Art. 47-6  : un qualifié est préférentiellement placé en non-exempt
    (on préfère un slot dont l'adversaire est connu ; si tous vides, peu
    importe).
    """
    main_r1 = TournamentMatch.query.filter_by(
        draw_id=final_draw.id, round_number=1
    ).order_by(TournamentMatch.position).all()

    # N'utiliser que les slots réellement vides (player_id is None)
    # pass1 = premier slot vide par match, pass2 = second slot vide par match
    # → garantit ≤ 1 qualifié par match et n'écrase pas les joueurs directs
    pass1 = []
    pass2 = []
    for m in main_r1:
        p1_empty = m.player1_id is None and m.status != 'BYE'
        p2_empty = m.player2_id is None and m.status != 'BYE'
        if p1_empty and p2_empty:
            pass1.append((m.id, 'p1'))
            pass2.append((m.id, 'p2'))
        elif p1_empty:
            pass1.append((m.id, 'p1'))
        elif p2_empty:
            pass1.append((m.id, 'p2'))
    empty_slots = pass1 + pass2

    for i, sec_draw in enumerate(section_draws):
        if i < len(empty_slots):
            mid, slot = empty_slots[i]
            sec_draw.main_draw_match_id = mid
            sec_draw.main_draw_slot = slot
            sec_draw.qualif_number = i + 1


# ─── Lien tableaux qualificatifs → tableau principal ─────────────────────────

def _link_qualif_draws_to_main(category_id: int, main_draw: TournamentDraw):
    """
    Après génération, lie chaque tableau qualificatif à son slot (match + p1/p2)
    dans le tableau final.
    Art. 45.3.c : deux qualifiés issus de tableaux différents ne doivent pas
    se rencontrer dès le premier tour → on répartit un qualifié par match en
    première passe, puis les éventuels surplus en deuxième passe.
    """
    qual_draws = TournamentDraw.query.filter_by(
        category_id=category_id, draw_type='QUALIFYING'
    ).order_by(TournamentDraw.id).all()

    main_r1 = TournamentMatch.query.filter_by(
        draw_id=main_draw.id, round_number=1
    ).order_by(TournamentMatch.position).all()

    # Première passe : un seul slot par match (p1 ou p2)
    pass1 = []
    pass2 = []
    for m in main_r1:
        p1_empty = m.player1_id is None and m.status != 'BYE'
        p2_empty = m.player2_id is None and m.status != 'BYE'
        if p1_empty and p2_empty:
            pass1.append((m.id, 'p1'))
            pass2.append((m.id, 'p2'))
        elif p1_empty:
            pass1.append((m.id, 'p1'))
        elif p2_empty:
            pass1.append((m.id, 'p2'))

    # Répartir : pass1 d'abord (chaque match reçoit au plus 1 qualifié)
    # puis pass2 si plus de qualifiés que de matchs
    empty_slots = pass1 + pass2

    for i, qd in enumerate(qual_draws):
        if i < len(empty_slots):
            mid, slot = empty_slots[i]
            qd.main_draw_match_id = mid
            qd.main_draw_slot = slot
            qd.qualif_number = i + 1


def _build_draw_cascade(draw: TournamentDraw, players: list,
                        draw_size: int, has_incoming: bool = False):
    """
    Construit un tableau qualificatif de la cascade.
    Si has_incoming=True, laisse un slot vide en position draw_size-1 (dernier slot
    du 1er tour) pour le qualifié entrant depuis le niveau précédent.
    Les joueurs fournis sont placés selon Art. 46 (têtes de série en demi-tableaux).
    """
    slots = [None] * draw_size

    # Préparer les têtes de série pour ce tableau
    q_seeds, q_unseeded = _prepare_seeds_tranche(players, draw_size) if len(players) >= 2 else ([], list(players))

    # Placer les têtes de série
    n_seeds_to_place = len(q_seeds)
    positions = seed_positions(draw_size, n_seeds_to_place)
    for idx, reg in enumerate(q_seeds):
        if idx < len(positions):
            slots[positions[idx]] = reg

    # Le dernier slot (draw_size-1 = player2 du dernier match R1) est réservé au qualifié entrant
    reserved_slot = draw_size - 1 if has_incoming else None
    # Index (0-based) du match contenant ce slot réservé
    reserved_match_idx = (draw_size // 2 - 1) if has_incoming else -1

    unseed_iter = iter(q_unseeded)
    for i in range(draw_size):
        if i == reserved_slot:
            continue   # ce slot sera rempli par le qualifié de la chaîne précédente
        if slots[i] is None:
            try:
                slots[i] = next(unseed_iter)
            except StopIteration:
                pass   # BYE

    total_rounds = int(math.log2(draw_size))
    for i in range(draw_size // 2):
        s1, s2 = slots[i * 2], slots[i * 2 + 1]
        p1 = s1.player if s1 else None
        p2 = s2.player if s2 else None

        # Seul le DERNIER match (i == reserved_match_idx) contient le slot qualifié entrant.
        # Les autres matchs avec un joueur vs personne sont des BYEs normaux.
        is_reserved_match = (i == reserved_match_idx)
        both_none = (p1 is None and p2 is None)
        one_none = (p1 is None) != (p2 is None)

        if both_none:
            # Les deux slots vides : BYE implicite (p1) + qualifié entrant (p2) → PENDING
            status = 'PENDING'
        elif one_none:
            if is_reserved_match:
                # Joueur réel + qualifié entrant attendu → PENDING
                status = 'PENDING'
            else:
                # Joueur réel vs personne, pas de qualifié attendu → BYE normal
                status = 'BYE'
        else:
            status = 'PENDING'

        m = TournamentMatch(
            draw_id=draw.id, round_number=1, position=i + 1,
            player1_id=p1.id if p1 else None,
            player2_id=p2.id if p2 else None,
            status=status
        )
        if status == 'BYE':
            winner = p1 or p2
            if winner:
                m.winner_id = winner.id
        db.session.add(m)

    for r in range(2, total_rounds + 1):
        for i in range(draw_size // (2 ** r)):
            db.session.add(TournamentMatch(
                draw_id=draw.id, round_number=r, position=i + 1, status='PENDING'
            ))
    db.session.flush()

    # Propager les BYEs
    for m in TournamentMatch.query.filter_by(draw_id=draw.id, round_number=1).all():
        if m.status == 'BYE' and m.winner_id:
            _propagate_bye(m)


def _link_to_first_empty_slot(prev_draw: TournamentDraw, next_draw: TournamentDraw):
    """
    Lie le vainqueur de prev_draw au slot réservé du 1er tour de next_draw.
    Le slot réservé est TOUJOURS draw_size-1 = player2 du DERNIER match de round 1
    (construit avec has_incoming=True).
    On cherche en partant du dernier match (DESC position).
    """
    r1_matches = TournamentMatch.query.filter_by(
        draw_id=next_draw.id, round_number=1
    ).order_by(TournamentMatch.position.desc()).all()  # cherche en partant de la fin

    for m in r1_matches:
        # Cas 1 : les deux slots vides → le slot réservé est player2 (draw_size-1)
        if m.player1_id is None and m.player2_id is None:
            prev_draw.main_draw_match_id = m.id
            prev_draw.main_draw_slot = 'p2'   # réservé = player2 du dernier match
            return
        # Cas 2 : player2 vide (slot réservé normal) et match pas encore BYE
        if m.player2_id is None and m.status != 'BYE':
            prev_draw.main_draw_match_id = m.id
            prev_draw.main_draw_slot = 'p2'
            return
        # Cas 3 : player1 vide (slot réservé inversé, rare)
        if m.player1_id is None and m.status != 'BYE':
            prev_draw.main_draw_match_id = m.id
            prev_draw.main_draw_slot = 'p1'
            return


def _link_chain_last_draws_to_main(chain_last_draw: list, final_draw: TournamentDraw):
    """
    Lie le dernier draw de chaque chaîne à un slot vide du tableau final.
    Art. 45.3.c : répartition pass1/pass2 pour éviter que deux qualifiés
    se rencontrent dès le 1er tour.
    """
    main_r1 = TournamentMatch.query.filter_by(
        draw_id=final_draw.id, round_number=1
    ).order_by(TournamentMatch.position).all()

    pass1 = []
    pass2 = []
    for m in main_r1:
        p1_empty = m.player1_id is None
        p2_empty = m.player2_id is None
        if p1_empty and p2_empty:
            pass1.append((m.id, 'p1'))
            pass2.append((m.id, 'p2'))
        elif p1_empty:
            pass1.append((m.id, 'p1'))
        elif p2_empty:
            pass1.append((m.id, 'p2'))

    empty_slots = pass1 + pass2
    slot_idx = 0
    for chain_idx, last_draw in enumerate(chain_last_draw):
        if last_draw is None:
            continue
        if slot_idx < len(empty_slots):
            mid, slot = empty_slots[slot_idx]
            last_draw.main_draw_match_id = mid
            last_draw.main_draw_slot = slot
            last_draw.qualif_number = chain_idx + 1
            slot_idx += 1


def propagate_winner(match: TournamentMatch):
    """Propage le vainqueur au match suivant dans le même tableau,
    ou vers le tableau principal si c'est le dernier tour d'un tableau qualificatif."""
    if not match.winner_id:
        return

    # ── Propagation interne (tour suivant dans le même tableau) ──────────────
    next_pos = math.ceil(match.position / 2)
    next_match = TournamentMatch.query.filter_by(
        draw_id=match.draw_id, round_number=match.round_number + 1, position=next_pos
    ).first()
    if next_match:
        if match.position % 2 == 1:
            next_match.player1_id = match.winner_id
        else:
            next_match.player2_id = match.winner_id
        db.session.commit()
        return

    # ── Fin de tableau qualificatif → propagation vers le tableau principal ──
    draw = match.draw
    if draw.draw_type != 'QUALIFYING':
        return
    if not draw.main_draw_match_id or not draw.main_draw_slot:
        return

    target_match = TournamentMatch.query.get(draw.main_draw_match_id)
    if not target_match:
        return

    if draw.main_draw_slot == 'p1':
        # Garde-fou : ne pas écraser un joueur direct déjà placé
        if target_match.player1_id is not None:
            import logging
            logging.getLogger(__name__).warning(
                f'propagate_winner: slot p1 du match {target_match.id} déjà occupé par '
                f'player {target_match.player1_id} — propagation annulée (Draw {draw.id})'
            )
            return
        target_match.player1_id = match.winner_id
        other_empty = (target_match.player2_id is None)
        other_slot = 'p2'
    else:
        # Garde-fou : ne pas écraser un joueur direct déjà placé
        if target_match.player2_id is not None:
            import logging
            logging.getLogger(__name__).warning(
                f'propagate_winner: slot p2 du match {target_match.id} déjà occupé par '
                f'player {target_match.player2_id} — propagation annulée (Draw {draw.id})'
            )
            return
        target_match.player2_id = match.winner_id
        other_empty = (target_match.player1_id is None)
        other_slot = 'p1'

    db.session.flush()

    # Si l'autre slot est vide et qu'aucun autre tableau qualificatif ne vient le remplir,
    # c'est un BYE implicite → avancer automatiquement le qualifié
    if other_empty and target_match.status == 'PENDING':
        other_feed = TournamentDraw.query.filter_by(
            main_draw_match_id=target_match.id,
            main_draw_slot=other_slot
        ).first()
        if not other_feed:
            target_match.status = 'BYE'
            target_match.winner_id = match.winner_id
            db.session.flush()
            _propagate_bye(target_match)

    db.session.commit()


def forfeit_player_in_draw(player_id: int, category_id: int) -> list:
    """
    Gère le forfait d'un joueur encore dans les tableaux.
    L'adversaire de chaque match PENDING/SCHEDULED avec ce joueur avance par walkover.
    Retourne la liste des matchs affectés.
    """
    draws = TournamentDraw.query.filter_by(category_id=category_id).all()
    affected = []
    for draw in draws:
        for match in draw.matches:
            if match.status not in ('PENDING', 'SCHEDULED'):
                continue
            if match.player1_id == player_id or match.player2_id == player_id:
                opponent_id = match.player2_id if match.player1_id == player_id else match.player1_id
                if opponent_id:
                    match.winner_id = opponent_id
                    match.status = 'WALKOVER'
                    match.score_text = 'WO'
                    db.session.flush()
                    propagate_winner(match)
                else:
                    match.status = 'BYE'
                    db.session.flush()
                affected.append(match)
    db.session.commit()
    return affected


def can_player_be_withdrawn(player_id: int, category_id: int) -> tuple:
    """
    Vérifie si un joueur peut être retiré selon Art. 52 (hors TMC).
    Retourne (bool, message).
    """
    draws = TournamentDraw.query.filter_by(category_id=category_id).all()
    for draw in draws:
        for match in draw.matches:
            if match.status == 'COMPLETED':
                if match.player1_id == player_id or match.player2_id == player_id:
                    return False, (
                        f"Ce joueur a déjà disputé au moins un match (tableau {draw.display_name}). "
                        "Le retrait n'est pas autorisé (Art. 52)."
                    )
    return True, "OK"


def find_requalification_candidate(match: TournamentMatch):
    """
    Trouve le candidat à la requalification pour un match WALKOVER (Art. 52.2).
    Le candidat est le joueur que le défaillant a battu au tour précédent.
    Retourne (candidate_player_id, source_match) ou (None, None).
    """
    # Identifier le joueur forfait (pas le winner)
    if match.winner_id == match.player1_id:
        wo_player_id = match.player2_id
    elif match.winner_id == match.player2_id:
        wo_player_id = match.player1_id
    else:
        return None, None

    if not wo_player_id or match.round_number <= 1:
        return None, None

    # Chercher le match précédent où wo_player_id a gagné
    prev_match = TournamentMatch.query.filter_by(
        draw_id=match.draw_id,
        round_number=match.round_number - 1
    ).filter(TournamentMatch.winner_id == wo_player_id).first()

    if not prev_match:
        return None, None

    # Le candidat est le perdant du match précédent
    candidate_id = (prev_match.player2_id
                    if prev_match.player1_id == wo_player_id
                    else prev_match.player1_id)
    return candidate_id, prev_match
















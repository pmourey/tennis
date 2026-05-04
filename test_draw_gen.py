"""
Test rapide du générateur de tableaux par tranche.
Simule la logique de generate_draws_by_tranche sans accès DB.
"""
import math


def next_power_of_2(n):
    if n <= 4:
        return 4
    return 2 ** math.ceil(math.log2(n))


def simulate(total_players, seeds_count, description):
    players = [{'name': f'P{i}', 'ranking_id': i, 'ranking_val': f'R{i}'} for i in range(1, total_players + 1)]
    sorted_regs = sorted(players, key=lambda r: r['ranking_id'])
    seeds = sorted_regs[:seeds_count]
    non_seeds = sorted_regs[seeds_count:]

    n_ns = len(non_seeds)
    if n_ns < 2:
        result = f"  DIRECT → tableau final sans qualif"
        n_qualifiers = 0
    else:
        n_chains_raw = max(2, n_ns // 4)
        n_chains = 1
        while n_chains < n_chains_raw:
            n_chains *= 2
        while n_chains > 2 and n_ns // n_chains < 2:
            n_chains //= 2

        all_ns_worst = sorted(non_seeds, key=lambda r: r['ranking_id'], reverse=True)
        chain_buckets = [[] for _ in range(n_chains)]
        for i, reg in enumerate(all_ns_worst):
            chain_buckets[i % n_chains].append(reg)

        draws = []
        for chain_idx, bucket in enumerate(chain_buckets):
            if len(bucket) < 2:
                continue
            q_size = next_power_of_2(len(bucket))
            draws.append(f"Section {chain_idx+1}: {len(bucket)} joueurs → draw_size={q_size} → 1 qualifié")

        n_qualifiers = len(draws)
        final_draw_size = next_power_of_2(seeds_count + n_qualifiers)
        actual_slots = final_draw_size - seeds_count

        result = "\n".join(f"  {d}" for d in draws)
        result += f"\n  Tableau Final: draw_size={final_draw_size} ({seeds_count} TdS + {actual_slots} slots qualifs)"
        result += f"\n  => {n_qualifiers} qualifies" + (" OK" if n_qualifiers >= 2 else " PROBLEME")

    print(f"\n{'='*55}")
    print(f"{description} ({total_players} joueurs, {seeds_count} TdS, {len(non_seeds)} non-seeds)")
    print(result)


simulate(8, 2, "Petit tournoi")
simulate(10, 2, "10 joueurs 2 TdS")
simulate(10, 4, "CC AIXOIS type A")
simulate(12, 4, "CC AIXOIS type B")
simulate(14, 4, "CC AIXOIS type C")
simulate(16, 4, "Grand tournoi")
simulate(6, 2, "Tres petit")
simulate(5, 2, "Minimum")
simulate(4, 2, "4 joueurs seulement")
simulate(9, 3, "9 joueurs 3 TdS")

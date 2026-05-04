"""Script de diagnostic des tableaux en base de données."""
from app import create_app

flask_app = create_app()
with flask_app.app_context():
    from models import Tournament, TournamentDraw, TournamentMatch

    # Trouver Open d'été 2026
    t = (Tournament.query.filter(Tournament.name.ilike('%t%2026%')).first()
         or Tournament.query.filter(Tournament.name.ilike('%ete%')).first()
         or Tournament.query.filter(Tournament.name.ilike('%open%')).first()
         or Tournament.query.order_by(Tournament.id.desc()).first())

    print(f"Tournoi: {t.name!r} (id={t.id}, status={t.status})")
    for cat in t.categories:
        regs = [r for r in cat.registrations if r.status == 'REGISTERED']
        print(f"\n=== Categorie: {cat.name!r} (id={cat.id}) - {len(regs)} inscrits ===")
        for draw in sorted(cat.draws, key=lambda d: d.id):
            matches = sorted(draw.matches, key=lambda m: (m.round_number, m.position))
            total_r = max((m.round_number for m in matches), default=0)
            print(f"  Draw: {draw.name!r} type={draw.draw_type} id={draw.id} "
                  f"main_match={draw.main_draw_match_id} slot={draw.main_draw_slot} "
                  f"qualif_num={draw.qualif_number}")
            for r in range(1, total_r + 1):
                ms = [m for m in matches if m.round_number == r]
                print(f"    Round {r} ({len(ms)} matchs):")
                for m in ms:
                    p1 = m.player1.name if m.player1 else "—"
                    p2 = m.player2.name if m.player2 else "—"
                    w  = m.winner.name  if m.winner  else "—"
                    print(f"      pos={m.position} [{p1}] vs [{p2}] => {m.status} winner={w}")

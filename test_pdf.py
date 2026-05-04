from app import create_app
from collections import defaultdict
app = create_app()
with app.app_context():
    from models import TournamentDraw
    from flask import render_template
    from weasyprint import HTML

    for draw_id, label in [(81, '32j'), (108, '16j'), (102, '8j')]:
        draw = TournamentDraw.query.get(draw_id)
        if not draw:
            print(f'Draw {draw_id} non trouvé')
            continue
        mbr = defaultdict(list)
        for m in sorted(draw.matches, key=lambda x: x.position):
            mbr[m.round_number].append(m)
        html = render_template('tournament/draw_pdf.html',
            tournament=draw.category.tournament,
            draw=draw,
            matches_by_round=dict(mbr),
            total_rounds=max(mbr.keys()))
        pdf = HTML(string=html, base_url='.').write_pdf()
        path = f'/tmp/test_draw_{label}.pdf'
        with open(path, 'wb') as f:
            f.write(pdf)
        print(f'✅ PDF {label} -> {path}  ({len(pdf)//1024} Ko)')

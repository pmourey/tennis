"""Export PDF des tableaux de tournoi via WeasyPrint."""
from __future__ import annotations
from flask import render_template
from weasyprint import HTML


def export_draw_pdf(tournament, draw) -> bytes:
    """Génère un PDF du tableau au format A4."""
    html_content = render_template(
        'tournament/draw_pdf.html',
        tournament=tournament,
        draw=draw
    )
    pdf = HTML(string=html_content).write_pdf(
        stylesheets=[],
        presentational_hints=True
    )
    return pdf


from __future__ import annotations

from flask import Blueprint

tournament_bp = Blueprint('tournament', __name__, template_folder='templates', static_folder='static')

from . import views


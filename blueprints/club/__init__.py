from __future__ import annotations
from flask import Blueprint
club_management_bp = Blueprint('club', __name__, template_folder='templates/club', static_folder='static')
from . import views

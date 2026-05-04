from __future__ import annotations
from flask import Blueprint
championship_management_bp = Blueprint('championship', __name__, template_folder='templates/championship')
from . import views

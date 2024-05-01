# Inside club/submodule/__init__.py
from __future__ import annotations

from flask import Blueprint

# Create a Blueprint instance for the submodule
club_management_bp = Blueprint('club', __name__, template_folder='templates/club', static_folder='static')

# Import views from the submodule to register routes
from . import views

# Inside championship/__init__.py
from __future__ import annotations

from flask import Blueprint

# Create a Blueprint instance for the submodule
championship_management_bp = Blueprint('championship', __name__, template_folder='templates/championship')

# Import views from the submodule to register routes
from . import views

# Inside medical/__init__.py
from __future__ import annotations

from flask import Blueprint

# Create a Blueprint instance for the submodule
medical_management_bp = Blueprint('medical', __name__, template_folder='templates/medical', static_folder='static')

# Import views from the submodule to register routes
from . import views

# Inside admin/__init__.py
from __future__ import annotations

from flask import Blueprint

# Create a Blueprint instance for the submodule
admin_bp = Blueprint('admin', __name__, template_folder='templates/admin')

# Import views from the submodule to register routes
from . import views

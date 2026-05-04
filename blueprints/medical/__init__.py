from __future__ import annotations
from flask import Blueprint
medical_management_bp = Blueprint('medical', __name__, template_folder='templates/medical', static_folder='static')
from . import views

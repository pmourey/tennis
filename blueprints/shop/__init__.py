from flask import Blueprint

shop_bp = Blueprint('shop', __name__, template_folder='templates', static_folder='static')

from . import views

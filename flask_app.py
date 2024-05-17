"""
Copyright © 2024 Philippe Mourey

This script provides CRUD features inside a Flask application to offer a tool for tennis clubs to help build teams and manage player availability

"""
from __future__ import annotations

import secrets
from logging import basicConfig, DEBUG
import locale

from flask import Flask, jsonify

from flask import render_template
from itsdangerous import URLSafeSerializer

from TennisModel import db, License, InjurySite
from admin import admin_bp

from club import club_management_bp
from championship import championship_management_bp
from common import InjuryType
from medical import medical_management_bp

app = Flask(__name__, static_folder='static', static_url_path='/static')

# Set the secret key to some random bytes. Keep this really secret!
# Generate a random string of bytes for the secret key and convert them to a string representation
app.secret_key = secrets.token_bytes(32).hex()

# Créer un sérialiseur avec la clé secrète de l'application
app.serializer = URLSafeSerializer(app.secret_key)

# Register blueprints
app.register_blueprint(club_management_bp, url_prefix='/club')
app.register_blueprint(championship_management_bp, url_prefix='/championship')
app.register_blueprint(medical_management_bp, url_prefix='/medical')
app.register_blueprint(admin_bp, url_prefix='/admin')

# Set the environment (development, production, etc.)
# Replace 'development' with the appropriate value for your environment
app.config.from_object('config.Config')
# app.config.from_pyfile(config_filename)

db.init_app(app)

locale.setlocale(locale.LC_TIME, 'fr_FR')
basicConfig(level=DEBUG)


@app.route('/')
def welcome():
    return render_template('index.html')


@app.before_request
def create_tables():
    db.create_all()


@app.route('/licensees-by-gender', methods=['GET'])
def licensees_by_gender():
    # Query to count licensees by gender
    result = db.session.query(License.gender, db.func.count(License.id)).group_by(License.gender).all()

    # Calculate total number of licensees
    total_licensees = sum(count for gender, count in result)

    # Convert the result to a dictionary with percentages
    gender_percentages = {}
    for gender, count in result:
        gender_name = "Male" if gender == 0 else "Female" if gender == 1 else "Mixed"
        percentage = (count / total_licensees) * 100
        gender_percentages[gender_name] = f'{round(percentage, 2)} %'

    return jsonify(gender_percentages)


# Define a custom filter function
def sort_players_by_elo(players):
    return sorted(players, key=lambda p: p.refined_elo, reverse=True)

def sort_players_by(players, sort_criteria):
    if not sort_criteria:
        return players
    return sorted(players, key=lambda p: getattr(p, sort_criteria), reverse=True)

def none_to_zero(value):
    return value if value != 'None' else ''

# Add the filter to the Jinja environment
app.jinja_env.filters['sort_players_by_elo'] = sort_players_by_elo
app.jinja_env.filters['sort_players_by'] = sort_players_by
app.jinja_env.filters['none_to_zero'] = none_to_zero

# app.run()
# toolbar.init_app(app)
# app.run(debug=True, use_debugger=True, use_reloader=False)

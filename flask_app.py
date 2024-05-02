"""
Copyright © 2024 Philippe Mourey

This script provides CRUD features inside a Flask application to offer a tool for tennis clubs to help build teams and manage player availability

"""
from __future__ import annotations

import secrets
from logging import basicConfig, DEBUG
import locale

from flask import Flask

from flask import render_template
from itsdangerous import URLSafeSerializer

from TennisModel import db
from admin import admin_bp

from club import club_management_bp
from championship import championship_management_bp

app = Flask(__name__, static_folder='static', static_url_path='/static')

# Set the secret key to some random bytes. Keep this really secret!
# Generate a random string of bytes for the secret key and convert them to a string representation
app.secret_key = secrets.token_bytes(32).hex()

# Créer un sérialiseur avec la clé secrète de l'application
app.serializer = URLSafeSerializer(app.secret_key)

# Register blueprints
app.register_blueprint(club_management_bp, url_prefix='/club')
app.register_blueprint(championship_management_bp, url_prefix='/championship')
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

# app.run()
# toolbar.init_app(app)
# app.run(debug=True, use_debugger=True, use_reloader=False)

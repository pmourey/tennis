"""
Copyright © 2024 Philippe Mourey

This script provides CRUD features inside a Flask application to offer a tool for tennis clubs to help build teams and manage player availability

"""
from __future__ import annotations

from flask import Flask, render_template, jsonify
from extensions import db, migrate
import secrets
from itsdangerous import URLSafeSerializer
from logging import basicConfig, DEBUG
import locale

from models import License


def create_app():
	app = Flask(__name__, static_folder='static', static_url_path='/static')

	# Set the secret key
	app.secret_key = secrets.token_bytes(32).hex()

	# Create serializer
	app.serializer = URLSafeSerializer(app.secret_key)

	# Config
	app.config.from_object('config.Config')

	# Initialize extensions
	db.init_app(app)
	migrate.init_app(app, db)

	# Register blueprints
	from blueprints.admin import admin_bp
	from blueprints.club import club_management_bp
	from blueprints.championship import championship_management_bp
	from blueprints.medical import medical_management_bp

	app.register_blueprint(club_management_bp, url_prefix='/club')
	app.register_blueprint(championship_management_bp, url_prefix='/championship')
	app.register_blueprint(medical_management_bp, url_prefix='/medical')
	app.register_blueprint(admin_bp, url_prefix='/admin')

	# Locale settings
	locale.setlocale(locale.LC_TIME, 'fr_FR')
	basicConfig(level=DEBUG)

	# Add the filter to the Jinja environment
	app.jinja_env.filters['sort_players_by_elo'] = sort_players_by_elo
	app.jinja_env.filters['sort_players_by'] = sort_players_by
	app.jinja_env.filters['none_to_zero'] = none_to_zero

	@app.route('/')
	def welcome():
		return render_template('index.html')

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

	return app


# @app.before_request
# def create_tables(app):
#     with app.app_context():
#         db.create_all()


# Define a custom filter function
def sort_players_by_elo(players):
	return sorted(players, key=lambda p: p.refined_elo, reverse=True)


def sort_players_by(players, sort_criteria):
	if not sort_criteria:
		return players
	return sorted(players, key=lambda p: getattr(p, sort_criteria), reverse=True)


def none_to_zero(value):
	return value if value != 'None' else ''

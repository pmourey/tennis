# Source Generated with Decompyle++
# File: app.cpython-310.pyc (Python 3.10)

'''
Copyright © 2024 Philippe Mourey

This script provides CRUD features inside a Flask application to offer a tool for tennis clubs to help build teams and manage player availability

'''
from __future__ import annotations
import locale
import secrets
from logging import DEBUG, basicConfig
from flask import Flask, jsonify, render_template
from itsdangerous import URLSafeSerializer
from extensions import db, migrate
from models import License

def create_app(test_config = (None,)):
    app = Flask(__name__, 'static', '/static', **('static_folder', 'static_url_path'))
    app.secret_key = secrets.token_bytes(32).hex()
    app.serializer = URLSafeSerializer(app.secret_key)
    app.config.from_object('config.Config')
    if test_config:
        app.config.update(test_config)
    db.init_app(app)
    migrate.init_app(app, db)
    admin_bp = admin_bp
    import blueprints.admin
    championship_management_bp = championship_management_bp
    import blueprints.championship
    club_management_bp = club_management_bp
    import blueprints.club
    medical_management_bp = medical_management_bp
    import blueprints.medical
    tournament_bp = tournament_bp
    import blueprints.tournament
    shop_bp = shop_bp
    import blueprints.shop
    app.register_blueprint(club_management_bp, '/club', **('url_prefix',))
    app.register_blueprint(championship_management_bp, '/championship', **('url_prefix',))
    app.register_blueprint(medical_management_bp, '/medical', **('url_prefix',))
    app.register_blueprint(admin_bp, '/admin', **('url_prefix',))
    app.register_blueprint(tournament_bp, '/tournament', **('url_prefix',))
    app.register_blueprint(shop_bp, '/shop', **('url_prefix',))
    locale.setlocale(locale.LC_TIME, 'fr_FR')
    basicConfig(DEBUG, **('level',))
    app.jinja_env.filters['sort_players_by_elo'] = sort_players_by_elo
    app.jinja_env.filters['sort_players_by'] = sort_players_by
    app.jinja_env.filters['none_to_zero'] = none_to_zero
    with app.app_context():
        db.create_all()
        _run_column_migrations(app, db)
        None(None, None, None)
    with None:
        if not None:
            pass
    
    def run_migration_endpoint():
        '''Endpoint pour forcer la migration des colonnes manquantes.'''
        pass
    # WARNING: Decompyle incomplete

    run_migration_endpoint = None(run_migration_endpoint)
    
    def welcome():
        return render_template('index.html')

    welcome = app.route('/')(welcome)
    
    def licensees_by_gender():
        result = db.session.query(License.gender, db.func.count(License.id)).group_by(License.gender).all()
        total_licensees = sum((lambda .0: for gender, count in .0:
count)(result))
        gender_percentages = { }
        for gender, count in result:
            if gender == 0:
                pass
            elif gender == 1:
                pass
            
            gender_name = 'Mixed'
            percentage = (count / total_licensees) * 100
            gender_percentages[gender_name] = f'''{round(percentage, 2)} %'''
        return jsonify(gender_percentages)

    licensees_by_gender = app.route('/licensees-by-gender', [
        'GET'], **('methods',))(licensees_by_gender)
    return app


def _run_column_migrations(app, db):
    """Ajoute les colonnes manquantes sans utiliser Alembic (SQLite compatible).
\t   Appelée une seule fois au démarrage de l'app."""
    inspect = inspect
    text = text
    import sqlalchemy
    inspector = inspect(db.engine)
    tables = inspector.get_table_names()
    if 'player_matchday_availability' in tables:
        pma_cols = (lambda .0: pass# WARNING: Decompyle incomplete
)(inspector.get_columns('player_matchday_availability'))
        for col, ddl in (('plays_single', 'INTEGER NOT NULL DEFAULT 0'), ('plays_double', 'INTEGER NOT NULL DEFAULT 0'), ('is_substitute', 'INTEGER NOT NULL DEFAULT 0')):
            if col not in pma_cols:
                db.session.execute(text(f'''ALTER TABLE player_matchday_availability ADD COLUMN {col} {ddl}'''))
                app.logger.info(f'''Migration: player_matchday_availability.{col} ajouté''')
    if 'team_matchday_joker' in tables:
        tmj_cols = (lambda .0: pass# WARNING: Decompyle incomplete
)(inspector.get_columns('team_matchday_joker'))
        for col, ddl in (('plays_single', 'INTEGER NOT NULL DEFAULT 0'), ('plays_double', 'INTEGER NOT NULL DEFAULT 0')):
            if col not in tmj_cols:
                db.session.execute(text(f'''ALTER TABLE team_matchday_joker ADD COLUMN {col} {ddl}'''))
                app.logger.info(f'''Migration: team_matchday_joker.{col} ajouté''')
    if 'tournament_draw' in tables:
        td_cols = (lambda .0: pass# WARNING: Decompyle incomplete
)(inspector.get_columns('tournament_draw'))
        for col, ddl in (('name', 'VARCHAR(120)'), ('main_draw_match_id', 'INTEGER'), ('main_draw_slot', 'VARCHAR(2)'), ('qualif_number', 'INTEGER')):
            if col not in td_cols:
                db.session.execute(text(f'''ALTER TABLE tournament_draw ADD COLUMN {col} {ddl}'''))
                app.logger.info(f'''Migration: tournament_draw.{col} ajouté''')
    if 'tournament_category' in tables:
        tc_cols = (lambda .0: pass# WARNING: Decompyle incomplete
)(inspector.get_columns('tournament_category'))
        if 'surfaces' not in tc_cols:
            db.session.execute(text("ALTER TABLE tournament_category ADD COLUMN surfaces VARCHAR(60) DEFAULT 'TB'"))
            app.logger.info('Migration: tournament_category.surfaces ajouté')
    if 'racquet' not in tables:
        db.session.execute(text('\n\t\t\tCREATE TABLE IF NOT EXISTS racquet (\n\t\t\t\tid INTEGER PRIMARY KEY AUTOINCREMENT,\n\t\t\t\tname VARCHAR(100) NOT NULL,\n\t\t\t\tbrand VARCHAR(50) NOT NULL,\n\t\t\t\thead_size FLOAT, length FLOAT,\n\t\t\t\tstrung_weight FLOAT, unstrung_weight FLOAT,\n\t\t\t\tbalance FLOAT, swingweight INTEGER, stiffness INTEGER,\n\t\t\t\tbeam_width VARCHAR(20), string_pattern VARCHAR(10),\n\t\t\t\tstring_tension VARCHAR(20), price FLOAT,\n\t\t\t\turl VARCHAR(500), image_url VARCHAR(500), image_local VARCHAR(200),\n\t\t\t\tplayer_type VARCHAR(50), composition VARCHAR(100), color VARCHAR(50),\n\t\t\t\tcreated_at DATETIME DEFAULT CURRENT_TIMESTAMP\n\t\t\t)\n\t\t'))
        app.logger.info('Migration: table racquet créée')
    db.session.commit()


def sort_players_by_elo(players):
    return sorted(players, (lambda p: p.refined_elo), True, **('key', 'reverse'))


def sort_players_by(players, sort_criteria):
    if not sort_criteria:
        return players
    return None(None, (lambda p = None: getattr(p, sort_criteria)), True, **('key', 'reverse'))


def none_to_zero(value):
    if value != 'None':
        return value


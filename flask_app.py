"""
Copyright © 2023 Philippe Mourey

This script provides CRUD features inside a Flask application for job's research follow-up and contact recruiters at monthly basis using a scheduler

"""
from __future__ import annotations

from logging import basicConfig, DEBUG
import locale
from datetime import datetime, timedelta
from flask import Flask, request, flash, url_for, redirect, render_template, session, send_file
from flask_debugtoolbar import DebugToolbarExtension
from sqlalchemy import DateTime, desc

from TennisModel import Player, db

from flask import render_template, redirect, url_for, flash

app = Flask(__name__, static_folder='static', static_url_path='/static')
# Set the environment (development, production, etc.)
# Replace 'development' with the appropriate value for your environment
app.config.from_object('config.Config')
# app.config.from_pyfile(config_filename)

db.init_app(app)

toolbar = DebugToolbarExtension(app)

locale.setlocale(locale.LC_TIME, 'fr_FR')
basicConfig(level=DEBUG)

# Set the secret key to some random bytes. Keep this really secret!
app.secret_key = b'_5#y2L"F4Q8z\n\xec]/'


# app.config['SECRET_KEY'] = 'fifa2022'
# app.config['SESSION_TYPE'] = 'filesystem'


@app.route('/')
def welcome():
    return render_template('index.html')


@app.route('/players')
def show_players():
    app.logger.debug('This is a debug message.')
    # Reverse order query
    # players = Player.query.filter(Player.isActive).order_by(desc(Player.birthDate)).all()
    # players = Player.query.filter(Player.isActive).all()
    players = Player.query.all()
    app.logger.debug(f'players: {players}')
    return render_template('players.html', players=players)

@app.route('/teams')
def show_teams():
    app.logger.debug('This is a debug message.')
    pass
    # Reverse order query
    # players = Player.query.filter(Player.active).order_by(desc(Player.birthDate)).all()
    # return render_template('teams.html', players=players)

@app.route('/new_player/', methods=['GET', 'POST'])
def new_player():
    if request.method == 'POST':
        if not (request.form['name'] and request.form['birth_date']):
            flash('Please enter all the fields', 'error')
        else:
            player = Player(name=request.form['name'], birthDate=request.form['birth_date'],
                            height=request.form['height'], weight=request.form['weight'],
                            is_captain=request.form['is_captain'], is_active=True)
            # logging.warning("See this message in Flask Debug Toolbar!")
            db.session.add(player)
            db.session.commit()
            flash('Record was successfully added')
    return redirect(url_for('show_players'))


@app.route('/delete/<int:id>', methods=['GET', 'POST'])
def delete(id):
    app.logger.debug(f'Delete job #{id}')
    if request.method == 'GET':
        player = Player.query.get_or_404(id)
        app.logger.debug(f'Player debug: {player}')
        # db.session.delete(job)
        player.isActive = False
        db.session.commit()
        flash(f'Joueur \"{player.name}\" supprimé de l\'équipe  \"{player.team}\"!')
        return redirect(url_for('show_players'))


@app.route('/update/<int:id>', methods=['GET', 'POST'])
def update(id):
    player: Player = Player.query.get_or_404(id)
    if request.method == 'POST':
        player.name = request.form.get('name')
        birth_date = request.form.get('birthDate')
        app.logger.debug(f'birthDate: {birth_date}')
        player.birthDate = datetime.strptime(birth_date, '%Y-%m-%d') if birth_date else None
        player.height = request.form.get('height')
        player.weight = request.form.get('weight')
        player.is_captain = request.form.get('is_captain')
        db.session.commit()
        flash('Record was successfully updated')
        return redirect(url_for('show_all'))
    else:
        return render_template('update.html', player=player)


@app.before_request
def create_tables():
    db.create_all()

# app.run()
# toolbar.init_app(app)
# app.run(debug=True, use_debugger=True, use_reloader=False)

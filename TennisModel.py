from datetime import datetime

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship

db = SQLAlchemy()


# class TennisResults(db.Model):
#     __tablename__ = 'tennis_results'
#     id = db.Column(db.Integer, primary_key=True, autoincrement=True)
#     tournament_id = db.Column(db.Integer, ForeignKey('tournament.id'), nullable=False)
#     player_id = db.Column(db.Integer, ForeignKey('player.id'), nullable=False)
#     match_id = db.Column(db.Integer, ForeignKey('match.id'), nullable=False)
#     is_winner = db.Column(db.Boolean, default=False)
#
#     tournament = relationship('Tournament')
#     player = relationship('Player')
#     match = relationship('Match')
#
#
# class Tournament(db.Model):
#     __tablename__ = 'tournament'
#     id = db.Column(db.Integer, primary_key=True, autoincrement=True)
#     name = db.Column(db.String(20), unique=True, nullable=False)
#     city = db.Column(db.String(20), nullable=False)
#     # country = db.Column(db.String(20), nullable=False)
#     start_date = db.Column(db.DateTime, nullable=False)
#     end_date = db.Column(db.DateTime, nullable=False)
#     logo = db.Column(db.String(20), nullable=False)
#
#     location = relationship('Club')
#
#
# class Match(db.Model):
#     __tablename__ = 'match'
#     id = db.Column(db.Integer, primary_key=True, autoincrement=True)
#     match_date = db.Column(db.DateTime, nullable=False)
#     match_type = db.Column(db.String(20), nullable=False)
#     match_format = db.Column(db.String(20), nullable=False)
#     surface = db.Column(db.String(20), nullable=False)
#     tournament_id = db.Column(db.Integer, ForeignKey('tournament.id'), nullable=False)
#     player_id = db.Column(db.Integer, ForeignKey('player.id'), nullable=False)
#     opponent_id = db.Column(db.Integer, ForeignKey('player.id'), nullable=False)
#     match_score = db.Column(db.String(20), nullable=False)


class Player(db.Model):
    __tablename__ = 'player'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(20), unique=True, nullable=False)
    birthDate = db.Column(db.DateTime, nullable=False)
    height = db.Column(db.Integer, nullable=False)
    weight = db.Column(db.Integer, nullable=False)
    teamId = db.Column(db.Integer, ForeignKey('team.id'), nullable=False)  # Add ForeignKey for team
    clubId = db.Column(db.Integer, db.ForeignKey('club.id'), nullable=False)  # Add ForeignKey for club
    isCaptain = db.Column(db.Boolean, default=False)
    isActive = db.Column(db.Boolean, default=True)

    # Define the relationship with Team
    team = relationship('Team', back_populates='players')
    # Define the relationship with Club
    club = relationship('Club')

    @property
    def age(self):
        today = datetime.now()
        return today.year - self.birthDate.year - ((today.month, today.day) < (self.birthDate.month, self.birthDate.day))

    def __repr__(self):
        return f'{self.name}'


class Team(db.Model):
    __tablename__ = 'team'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(20), unique=True, nullable=False)

    # Define the relationship with Player
    players = relationship('Player', back_populates='team')

    def __repr__(self):
        return f'{self.name}'


class Club(db.Model):
    __tablename__ = 'club'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(20), unique=True, nullable=False)
    city = db.Column(db.String(20), nullable=False)
    logo = db.Column(db.String(20), nullable=False)

    # Define the relationship with Player
    players = relationship('Player', back_populates='club')

    def __repr__(self):
        return f'{self.name}'

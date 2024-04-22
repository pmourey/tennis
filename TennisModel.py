from datetime import datetime

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import ForeignKey, Table
from sqlalchemy.orm import relationship

db = SQLAlchemy()

# Table d'association entre Player et Team
player_team_association = Table(
    'player_team_association',
    db.Model.metadata,
    db.Column('player_id', db.Integer, db.ForeignKey('player.id')),
    db.Column('team_id', db.Integer, db.ForeignKey('team.id'))
)


class Player(db.Model):
    __tablename__ = 'player'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(20), unique=True, nullable=False)
    birthDate = db.Column(db.DateTime, nullable=False)
    height = db.Column(db.Integer, nullable=False)
    weight = db.Column(db.Integer, nullable=False)
    clubId = db.Column(db.Integer, db.ForeignKey('club.id'), nullable=False)
    isActive = db.Column(db.Boolean, default=True)

    # Define the relationship with Club
    club = relationship('Club')

    # Define the relationship with Team using many-to-many association
    teams = relationship('Team', secondary=player_team_association, back_populates='players')

    @property
    def age(self):
        today = datetime.now()
        return today.year - self.birthDate.year - ((today.month, today.day) < (self.birthDate.month, self.birthDate.day))

    def __repr__(self):
        return f'{self.name}'


class Club(db.Model):
    __tablename__ = 'club'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(20), unique=True, nullable=False)
    city = db.Column(db.String(20), nullable=False)

    # Define the relationship with Player
    players = relationship('Player', back_populates='club')

    def __repr__(self):
        return f'{self.name}'

class Team(db.Model):
    __tablename__ = 'team'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(20), unique=True, nullable=False)
    captainId = db.Column(db.Integer, db.ForeignKey('player.id'))

    # Define the relationship with Player using many-to-many association
    players = relationship('Player', secondary=player_team_association, back_populates='teams')

    @property
    def club(self):
        return self.players[0].club if self.players else None

    @property
    def captainName(self):
        is_captain = [p for p in self.players if p.id == self.captainId]
        return is_captain[0].name if is_captain else None

    def __repr__(self):
        return f'{self.name}'


class Championship(db.Model):
    __tablename__ = 'championship'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    startDate = db.Column(db.Date, nullable=False)
    endDate = db.Column(db.Date, nullable=False)
    ageCategory = db.Column(db.String(20), nullable=False)
    singlesCount = db.Column(db.Integer, nullable=False)
    doublesCount = db.Column(db.Integer, nullable=False)

    # Relation avec les rencontres (matchs) du championnat
    matches = relationship('Match', back_populates='championship')


class Match(db.Model):
    __tablename__ = 'match'

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)

    # Clé étrangère vers le championnat auquel appartient le match
    championship_id = db.Column(db.Integer, ForeignKey('championship.id'))
    championship = relationship('Championship', back_populates='matches')

    # Clé étrangère vers l'équipe à domicile
    homeTeamId = db.Column(db.Integer, ForeignKey('team.id'))
    homeTeam = relationship('Team', foreign_keys=[homeTeamId])

    # Clé étrangère vers l'équipe adverse
    awayTeamId = db.Column(db.Integer, ForeignKey('team.id'))
    awayTeam = relationship('Team', foreign_keys=[awayTeamId])

    # Relation avec la feuille de match
    match_sheet = relationship('MatchSheet', uselist=False, back_populates='match')


class MatchSheet(db.Model):
    __tablename__ = 'match_sheet'

    id = db.Column(db.Integer, primary_key=True)
    score = db.Column(db.String(20), nullable=False)

    # Clé étrangère vers le match auquel la feuille de match est associée
    match_id = db.Column(db.Integer, ForeignKey('match.id'))
    match = relationship('Match', back_populates='match_sheet')

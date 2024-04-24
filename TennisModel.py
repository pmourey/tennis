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
    poolId = db.Column(db.Integer, db.ForeignKey('pool.id'))

    # Define the relationship with Player using many-to-many association
    players = relationship('Player', secondary=player_team_association, back_populates='teams')  # Correction ici

    @property
    def championship_name(self):
        return self.pool.championship.name if self.pool else None

    @property
    def pool(self):
        return Pool.query.get(self.poolId) if self.poolId else None

    @property
    def club(self):
        return self.players[0].club if self.players else None

    @property
    def captainName(self):
        is_captain = [p for p in self.players if p.id == self.captainId]
        return is_captain[0].name if is_captain else None

    def __repr__(self):
        return f'{self.name}'


class AgeCategory(db.Model):
    __tablename__ = 'age_category'

    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.Integer, nullable=False)  # Champ Jeunes/Seniors/Vétérans (0 pour jeunes, 1 pour seniors, 2 pour vétérans)
    minAge = db.Column(db.Integer, nullable=False)
    maxAge = db.Column(db.Integer, nullable=False)

    @property
    def name(self) -> str:
        categories = {0: 'Jeunes', 1: 'Seniors', 2: 'Seniors Plus'}
        if self.type == 0:
            return f'U{self.minAge}'
        elif self.type == 1:
            return categories[self.type]
        else:
            return f'{categories[self.type]} {self.minAge}'

    def __repr__(self):
        return f'{self.name}'


class Division(db.Model):
    __tablename__ = 'division'

    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.Integer, nullable=False)  # Champ National/Prenational/Regional/Departmental
    number = db.Column(db.Integer, nullable=True)  # Niveau de division dans la catégorie définie dans type
    gender = db.Column(db.Integer, nullable=False)  # Champ masculin/féminin (0 pour masculin, 1 pour féminin, 2 pour mixte)

    # Référence vers AgeCategory
    ageCategoryId = db.Column(db.Integer, db.ForeignKey('age_category.id'), nullable=False)
    ageCategory = relationship('AgeCategory')

    @property
    def name(self) -> str:
        categories = {0: 'National', 1: 'Prénational', 2: 'Régional', 3: 'Départemental'}
        gender = {0: 'Masculin', 1: 'Féminin', 2: 'Mixte'}
        level = f' {self.number}' if self.number else ''
        return f'{categories[self.type]}{level} - {self.ageCategory} - {gender[self.gender]}'

    def __repr__(self):
        return f'{self.name}'


class Championship(db.Model):
    __tablename__ = 'championship'

    id = db.Column(db.Integer, primary_key=True)
    startDate = db.Column(db.Date, nullable=False)
    endDate = db.Column(db.Date, nullable=False)
    singlesCount = db.Column(db.Integer, nullable=False)
    doublesCount = db.Column(db.Integer, nullable=False)
    divisionId = db.Column(db.Integer, db.ForeignKey('division.id'))  # Ajout de la clé étrangère vers la division

    division = relationship('Division')  # Relation avec la division
    pools = relationship('Pool', back_populates='championship')  # Relation avec les poules du championnat

    @property
    def name(self):
        division = Division.query.get(self.divisionId)
        return f'{division.name}'

    def __repr__(self):
        return f'{self.name}'


class Pool(db.Model):
    __tablename__ = 'pool'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    letter = db.Column(db.String(1), nullable=True)

    # Clé étrangère vers le championnat auquel appartient la poule
    championshipId = db.Column(db.Integer, ForeignKey('championship.id'))
    championship = relationship('Championship', back_populates='pools')

    # Relation avec les matchs de la poule
    matches = relationship('Match', back_populates='pool')

    @property
    def name(self):
        pool = f'non définie' if not self.letter else self.letter
        # return f'id #{self.id} - poule {pool} - championnat: {self.championship.name}'
        return f'id #{self.id} - poule {pool}'

    def __repr__(self):
        return self.letter

class Match(db.Model):
    __tablename__ = 'match'

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)

    # Clé étrangère vers la poule auquelle appartient le match
    poolId = db.Column(db.Integer, ForeignKey('pool.id'))
    pool = relationship('Pool', back_populates='matches')

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

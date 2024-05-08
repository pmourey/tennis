import logging
import re
from datetime import datetime, timedelta, date
from typing import Optional

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import ForeignKey, Table, Integer, String
from sqlalchemy.orm import relationship, backref, DeclarativeBase, mapped_column

db = SQLAlchemy()


# db = SQLAlchemy(session_options={"autoflush": False})

class BestRanking(db.Model):
    __tablename__ = 'best_ranking'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    value = db.Column(db.String(10), nullable=False)  # Valeur du classement (par exemple, "15/4")
    series = db.Column(db.Integer, nullable=True)  # 1ère, 2ème, 3ème, 4ème série

    # Define the relationship with License
    # licenseId = db.Column(db.Integer, db.ForeignKey('license.id'), nullable=False)
    license = relationship('License', back_populates='best_rankings')

    def __eq__(self, other):
        return self.id == other.id

    def __lt__(self, other):
        return self.id < other.id

    def __gt__(self, other):
        return self.id > other.id

    def __repr__(self):
        return self.value


class Ranking(db.Model):
    __tablename__ = 'ranking'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    value = db.Column(db.String(10), nullable=False)  # Valeur du classement (par exemple, "15/4")
    series = db.Column(db.Integer, nullable=True)  # 1ère, 2ème, 3ème, 4ème série

    # Define the relationship with License
    # licenseId = db.Column(db.Integer, db.ForeignKey('license.id'), nullable=False)
    # license = relationship('License', back_populates='rankings')

    license = relationship('License', back_populates='rankings')

    # license = relationship('License', primaryjoin='Ranking.licenseId == License.id', back_populates='rankings')

    def __eq__(self, other):
        return self.id == other.id

    def __lt__(self, other):
        return self.id < other.id

    def __gt__(self, other):
        return self.id > other.id

    def __repr__(self):
        return self.value


class Club(db.Model):
    __tablename__ = 'club'
    id = db.Column(db.String(8), primary_key=True)
    name = db.Column(db.String(20), unique=True, nullable=False)
    city = db.Column(db.String(20), nullable=False)
    tennis_courts = db.Column(db.Integer, nullable=True)
    padel_courts = db.Column(db.Integer, nullable=True)
    beach_courts = db.Column(db.Integer, nullable=True)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)

    # Define the relationship with Player
    players = relationship('Player', back_populates='club', cascade="all, delete-orphan")

    def __repr__(self):
        return f'{self.name}'

    @property
    def info(self) -> str:
        formatted_id = f"{self.id[:2]:s} {self.id[2:4]:s} {self.id[4:]:s}"
        courts = f'Tennis : {self.tennis_courts} terrains'
        if self.padel_courts:
            courts += f', Padel : {self.padel_courts}'
        if self.beach_courts:
            courts += f', Beach Tennis : {self.beach_courts}'
        return f'{self.name} ({formatted_id}) - {courts}'  # - lat/lng: ({self.latitude},{self.longitude})'

class License(db.Model):
    __tablename__ = 'license'
    id = db.Column(db.Integer, primary_key=True)
    firstName = db.Column(db.String(20), nullable=False)
    lastName = db.Column(db.String(20), nullable=False)
    letter = db.Column(db.String(1), nullable=False)
    year = db.Column(db.Integer, nullable=False)  # Année de la licence
    gender = db.Column(db.Integer, nullable=False)  # Champ masculin/féminin (0 pour masculin, 1 pour féminin, 2 pour mixte)

    # Define the relationship with Ranking using rankingId
    rankingId = db.Column(db.Integer, ForeignKey('ranking.id'), nullable=False)
    ranking = relationship('Ranking', foreign_keys=[rankingId], back_populates='license')

    # Define the relationship with Ranking using bestRankingId
    bestRankingId = db.Column(Integer, ForeignKey('best_ranking.id'), nullable=True)
    bestRanking = relationship('BestRanking', foreign_keys=[bestRankingId], back_populates='license')

    # # Define the back reference to rankings
    rankings = relationship('Ranking', back_populates='license', foreign_keys=[rankingId], overlaps="ranking")
    best_rankings = relationship('BestRanking', back_populates='license', foreign_keys=[bestRankingId], overlaps="bestRanking")

    # Define the relationship with Player
    players = relationship('Player', back_populates='license')

    @property
    def name(self):
        return f'{self.firstName} {self.lastName}'

    def __repr__(self):
        return f'{self.id} - {self.name}'


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
    birthDate = db.Column(db.DateTime, nullable=False)
    weight = db.Column(db.Integer, nullable=True)
    height = db.Column(db.Integer, nullable=True)
    isActive = db.Column(db.Boolean, default=True)

    # Define the foreign key relationship with Club
    clubId = db.Column(db.Integer, db.ForeignKey('club.id', ondelete='CASCADE'), nullable=False)  # Add this line
    club = relationship('Club', back_populates='players')  # Add this line

    # Define the relationship with License
    licenseId = db.Column(db.Integer, db.ForeignKey('license.id', ondelete='CASCADE'), nullable=False)
    license = relationship('License', back_populates='players', single_parent=True, cascade="all, delete-orphan")  # Add cascade option here

    # Define the relationship with Team using many-to-many association
    teams = relationship('Team', secondary=player_team_association, back_populates='players', single_parent=True, cascade="all, delete-orphan")

    @property
    def gender(self):
        return self.license.gender

    @property
    def ranking_id(self):
        license = License.query.get(self.licenseId)
        ranking = Ranking.query.get(license.rankingId)
        return ranking.id

    @property
    def ranking(self):
        license = License.query.get(self.licenseId)
        return Ranking.query.get(license.rankingId)

    @property
    def last_name(self):
        license = License.query.get(self.licenseId)
        return license.lastName

    @property
    def name(self):
        return f'{self.license.firstName} {self.license.lastName[0]}.'

    # Add a property to calculate the age of the player
    @property
    def age(self) -> int:
        today = datetime.now()
        return today.year - self.birthDate.year - ((today.month, today.day) < (self.birthDate.month, self.birthDate.day))

    def has_valid_age(self, age_category) -> bool:
        # logger = logging.getLogger(__name__)
        # logger.info(f'prout - age_category: {age_category}')
        return age_category.minAge <= self.age <= age_category.maxAge

    # Add a property to format the birth date (based on license info)
    @property
    def formatted_birth_date(self):
        return self.birthDate.replace(month=1, day=1).strftime('%Y-%m-%d')

    def __repr__(self):
        return f'{self.name}'


class Team(db.Model):
    __tablename__ = 'team'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(20), unique=False, nullable=False)
    captainId = db.Column(db.Integer, db.ForeignKey('player.id'))
    poolId = db.Column(db.Integer, db.ForeignKey('pool.id'), nullable=True)

    # Define the foreign key relationship with Pool
    pool = relationship('Pool', back_populates='teams')

    # Define the relationship with Player using many-to-many association
    players = relationship('Player', secondary=player_team_association, back_populates='teams')  # Correction ici

    def weight(self, championship) -> int:
        return (Ranking.query.count() * championship.singlesCount) - sum([p.license.rankingId for i, p in enumerate(self.players) if i < championship.singlesCount])

    @property
    def gender(self) -> int:
        if all(p.gender == 0 for p in self.players):
            return 0
        elif all(p.gender == 1 for p in self.players):
            return 1
        else:
            return 2

    @property
    def championship(self):
        return self.pool.championship if self.pool else None

    @property
    def championship_name(self):
        return self.pool.championship.name if self.pool else None

    @property
    def match_days(self):
        return self.championship.matchdays

    @property
    def club(self):
        return self.players[0].club if self.players else None

    @property
    def captainName(self):
        captain = Player.query.get(self.captainId)
        return captain.name if captain else None

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
            return f'U{self.maxAge}'
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

    # Define the one-to-many relationship with Matchday
    matchdays = relationship('Matchday', back_populates='championship')

    pools = relationship('Pool', back_populates='championship')  # Relation avec les poules du championnat

    @property
    def exempted_teams(self):
        return Team.query.join(Pool).filter(Pool.championshipId == self.id).all()

    @property
    def num_matches(self):
        return self.singlesCount + self.doublesCount

    @property
    def name(self):
        division = Division.query.get(self.divisionId)
        return f'{division.name}' if division else None

    @property
    def age_category(self):
        # division = Division.query.get(self.divisionId)
        return self.division.ageCategory

    @property
    def teams(self):
        teams = []
        for pool in self.pools:
            teams.extend(Pool.query.get(pool.id).teams)
        return teams

    @property
    def match_dates(self):
        sundays = []
        current_date = self.startDate
        while current_date <= self.endDate:
            if current_date.weekday() == 6:  # Sunday has index 6
                sundays.append(current_date)
            current_date += timedelta(days=1)
        return sundays

    @property
    def match_dates_new(self):
        division = Division.query.get(self.divisionId)
        if division.type == 0:  # National
            # dimanches 27 avril, 4, 11, 18 et 25 mai 2025
            return [date(2025, 4, 27), date(2025, 5, 4), date(2025, 5, 11), date(2025, 5, 18), date(2025, 5, 25)]
        elif division.ageCategory.type == 1:  # Senior
            if division.ageCategory.minAge in [35, 45, 55]:
                # Dimanches 1, 8, 15, 22 octobre 2023
                # Dimanche 12 novembre 2023
                return [date(2023, 10, 1), date(2023, 10, 8), date(2023, 10, 15), date(2023, 10, 22), date(2023, 11, 12)]
            elif division.ageCategory.minAge in [65, 75]:
                # Mardis 3, 10, 17, 24 octobre 2023
                # Mardi 7 novembre 2023
                return [date(2023, 10, 3), date(2023, 10, 10), date(2023, 10, 17), date(2023, 10, 24), date(2023, 11, 7)]

    def __repr__(self):
        return f'{self.name}'


class Pool(db.Model):
    __tablename__ = 'pool'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    letter = db.Column(db.String(1), nullable=True)

    # Clé étrangère vers le championnat auquel appartient la poule
    championshipId = db.Column(db.Integer, ForeignKey('championship.id'))
    championship = relationship('Championship', back_populates='pools')

    teams = relationship('Team', back_populates='pool')

    # Relation avec les matchs de la poule
    matches = relationship('Match', back_populates='pool')

    @property
    def is_exempted(self) -> bool:
        return self.letter is None

    def get_team_by_id(self, team_id: int) -> Optional[Team]:
        return Team.query.get(team_id) if team_id else None

    @property
    def best_team(self) -> Optional[Team]:
        return max(self.teams, key=lambda team: team.weight(self.championship)) if self.teams else None

    @property
    def worst_team(self) -> Optional[Team]:
        return min(self.teams, key=lambda team: team.weight(self.championship)) if self.teams else None

    @property
    def name(self):
        pool = f'non définie' if not self.letter else self.letter
        # return f'id #{self.id} - poule {pool} - championnat: {self.championship.name}'
        return f'id #{self.id} - pool: {pool} - championship: {self.championship}'

    def __repr__(self):
        return self.letter


class Matchday(db.Model):
    __tablename__ = 'matchday'

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)

    # Define the many-to-one relationship with Pool
    championshipId = db.Column(db.Integer, db.ForeignKey('championship.id'), nullable=True)
    championship = relationship('Championship', back_populates='matchdays')

    # Define the one-to-many relationship with Match
    matches = relationship('Match', back_populates='matchday')

    def __repr__(self):
        return f'Journée #{self.id}'

# matchday_match_association = Table(
#     'matchday_match_association',
#     Base.metadata,
#     db.Column('matchday_id', db.Integer, db.ForeignKey('matchday.id')),
#     db.Column('match_id', db.Integer, db.ForeignKey('match.id'))
# )


class Match(db.Model):
    __tablename__ = 'match'

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)

    # Clé étrangère vers la journée de match
    matchdayId = db.Column(db.Integer, db.ForeignKey('matchday.id'))
    matchday = relationship('Matchday', back_populates='matches')

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

    def __repr__(self):
        # match_day = Matchday.query.get(self.matchdayId)
        # pool = Pool.query.get(self.poolId)
        match_sheet = MatchSheet.query.filter_by(id=self.matchdayId).first()
        return f'{match_sheet}'


class MatchSheet(db.Model):
    __tablename__ = 'match_sheet'

    id = db.Column(db.Integer, primary_key=True)
    score = db.Column(db.String(20), nullable=False)

    winnerId = db.Column(db.Integer, ForeignKey('team.id'))
    winner = relationship('Team', foreign_keys=[winnerId])

    # Clé étrangère vers le match auquel la feuille de match est associée
    matchId = db.Column(db.Integer, ForeignKey('match.id', ondelete='CASCADE'))
    match = relationship('Match', back_populates='match_sheet', single_parent=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f'{self.score}'

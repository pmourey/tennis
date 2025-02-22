from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta, date
from typing import Optional, List, Iterable

from sqlalchemy import ForeignKey, Table, Integer, String, Float, Boolean, and_
from sqlalchemy.orm import relationship, backref, DeclarativeBase, mapped_column

from extensions import db


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


class Distance(db.Model):
    __tablename__ = 'distance'
    id = db.Column(db.Integer, primary_key=True)
    from_club_id = db.Column(db.String(8), ForeignKey('club.id'), nullable=False)
    to_club_id = db.Column(db.String(8), ForeignKey('club.id'), nullable=False)
    distance = db.Column(db.Float, nullable=True)
    duration = db.Column(db.Float, nullable=True)

    from_club = relationship('Club', foreign_keys=[from_club_id])
    to_club = relationship('Club', foreign_keys=[to_club_id])


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

    # # Define the relationship with Team
    # teams = relationship('Team', back_populates='club', cascade="all, delete-orphan")

    def __repr__(self):
        return f'{self.name}'

    def __eq__(self, other):
        return self.id == other.id

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



player_injury_association = Table(
    'player_injury_association',
    db.Model.metadata,
    db.Column('player_id', db.Integer, db.ForeignKey('player.id')),
    db.Column('injury_id', db.Integer, db.ForeignKey('injury.id'))
)


class InjurySite(db.Model):
    __tablename__ = 'injury_site'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)

    # Relations avec les blessures
    injuries = db.relationship('Injury', back_populates='site')

    def __repr__(self):
        return self.name

    @property
    def acute_injuries(self) -> List[str]:
        injuries = Injury.query.filter_by(siteId=self.id).all()
        logging.info(injuries)
        return [injury.name for injury in injuries if injury.type == 0]

    @property
    def overuse_injuries(self) -> List[str]:
        injuries = Injury.query.filter_by(siteId=self.id).all()
        logging.info(injuries)
        return [injury.name for injury in injuries if injury.type == 1]


class Injury(db.Model):
    __tablename__ = 'injury'

    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(Integer)
    name = db.Column(db.String)
    # description = db.Column(db.String)
    # temporary = db.Column(db.Boolean, nullable=True)
    # invalidity_rate = db.Column(db.Float, nullable=True)
    # recovery_duration = db.Column(db.Integer, nullable=True)

    siteId = db.Column(db.Integer, db.ForeignKey('injury_site.id'))
    site = db.relationship('InjurySite', back_populates='injuries')

    # Ajout de la relation avec les joueurs
    players = relationship('Player', secondary=player_injury_association, back_populates='injuries', single_parent=True)  # , cascade="all, delete-orphan")

    @property
    def site_name(self) -> str:
        site = InjurySite.query.get(self.siteId)
        return site.name

    def __repr__(self):
        return self.name


class PlayerMatchdayAvailability(db.Model):
    __tablename__ = 'player_matchday_availability'

    player_id = db.Column(db.Integer, db.ForeignKey('player.id', ondelete='CASCADE'), primary_key=True)
    matchday_id = db.Column(db.Integer, db.ForeignKey('matchday.id', ondelete='CASCADE'), primary_key=True)
    is_available = db.Column(db.Boolean, default=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    player = relationship('Player', back_populates='matchday_availabilities')
    matchday = relationship('Matchday', back_populates='player_availabilities')

class Player(db.Model):
    __tablename__ = 'player'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    birthDate = db.Column(db.DateTime, nullable=False)
    weight = db.Column(db.Integer, nullable=True, default=0)
    height = db.Column(db.Integer, nullable=True, default=0)
    isActive = db.Column(db.Boolean, default=True)

    # Replace the secondary relationship with direct relationship to the association model
    matchday_availabilities = relationship(
        'PlayerMatchdayAvailability',
        back_populates='player',
        cascade="all, delete-orphan"
    )

    # Define the relationship with Team using many-to-many association
    injuries = relationship('Injury', secondary=player_injury_association, back_populates='players', single_parent=True)  # , cascade="all, delete-orphan")

    # Define the foreign key relationship with Club
    clubId = db.Column(db.Integer, db.ForeignKey('club.id', ondelete='CASCADE'), nullable=False)  # Add this line
    club = relationship('Club', back_populates='players')  # Add this line

    # Define the relationship with License
    licenseId = db.Column(db.Integer, db.ForeignKey('license.id', ondelete='CASCADE'), nullable=False)
    license = relationship('License', back_populates='players', single_parent=True, cascade="all, delete-orphan")  # Add cascade option here

    # Define the relationship with Team using many-to-many association
    teams = relationship('Team', secondary=player_team_association, back_populates='players', single_parent=True, cascade="all, delete-orphan")

    def is_available(self, matchday) -> bool:
        """Check if player is available for a specific matchday"""
        availability = PlayerMatchdayAvailability.query.filter_by(
            player_id=self.id,
            matchday_id=matchday.id
        ).first()
        return availability.is_available if availability else False

    def initialize_matchday_availability(self, championship):
        """Initialize availability for all matchdays in a championship for this player"""
        # Get all matchdays for the championship
        matchdays = Matchday.query.filter_by(championshipId=championship.id).all()

        # Create availability records for each matchday
        for matchday in matchdays:
            # Check if availability record already exists
            existing = PlayerMatchdayAvailability.query.filter_by(
                player_id=self.id,
                matchday_id=matchday.id
            ).first()

            if not existing:
                availability = PlayerMatchdayAvailability(
                    player_id=self.id,
                    matchday_id=matchday.id,
                    is_available=True,
                    updated_at=datetime.utcnow()
                )
                db.session.add(availability)

        db.session.commit()
    @property
    def gender(self):
        return self.license.gender

    @property
    def double_rating(self):
        zero_ranking = Ranking.query.filter_by(value="0").first()
        return self.ranking.id - zero_ranking.id

    @property
    def double_info(self):
        return f'{self.name} ({self.double_rating})'

    @property
    def ranking_id(self):
        license = License.query.get(self.licenseId)
        ranking = Ranking.query.get(license.rankingId)
        return ranking.id

    @property
    def best_ranking_id(self):
        license = License.query.get(self.licenseId)
        ranking = BestRanking.query.get(license.rankingId)
        return ranking.id

    @best_ranking_id.setter
    def best_ranking_id(self, value):
        license = License.query.get(self.licenseId)
        if license:
            logging.info(f"Setting best_ranking_id to {value} - old license value = {license.bestRanking.value}")
            license.bestRankingId = value
        else:
            raise AttributeError("Player does not have a license")

    @property
    def ranking(self):
        license = License.query.get(self.licenseId)
        return Ranking.query.get(license.rankingId)

    @property
    def best_ranking(self):
        license = License.query.get(self.licenseId)
        return BestRanking.query.get(license.bestRankingId) if license.bestRankingId else None

    @property
    def last_name(self):
        license = License.query.get(self.licenseId)
        return license.lastName

    @property
    def name(self):
        return f'{self.license.firstName} {self.license.lastName[0]}'

    @property
    def info(self):
        return f'{self.name} ({self.ranking}) {(self.current_elo, self.refined_elo, self.best_elo)}'  # (elo: {self.current_elo})'

    @property
    def elo_tuple(self):
        return self.current_elo, self.refined_elo, self.best_elo

    @property
    def full_info(self):
        nd_ranking = Ranking.query.filter_by(value="ND").first()
        if self.best_ranking.id == nd_ranking.id:
            best_ranking = ', ex. ???'
        else:
            best_ranking = f', ex. {self.best_ranking}' if self.best_ranking.id < self.ranking.id else ''
        age_and_ranking = f'({self.age} ans{best_ranking})'
        return f'{self.name} {self.ranking} {age_and_ranking}'

    # Add a property to calculate the age of the player
    @property
    def age(self) -> int:
        today = datetime.now()
        return today.year - self.birthDate.year - ((today.month, today.day) < (self.birthDate.month, self.birthDate.day))

    def has_valid_age(self, age_category) -> bool:
        return age_category.minAge - 1 <= self.age < age_category.maxAge

    # Add a property to format the birth date (based on license info)
    @property
    def formatted_birth_date(self):
        return self.birthDate.replace(month=1, day=1).strftime('%Y-%m-%d')

    @property
    def current_elo(self) -> int:
        """
            Classement ELO du joueur
        """
        elo_weight = 15  # to better fit with ELO rating system (10 is better)
        nc_ranking = Ranking.query.filter_by(value="NC").first()
        second_series_threshold = Ranking.query.filter_by(value="-15").first()
        if self.ranking.id < second_series_threshold.id:
            ranking_delta = (second_series_threshold.id - self.ranking.id) // 10 + nc_ranking.id - second_series_threshold.id
        else:
            ranking_delta = nc_ranking.id - self.ranking.id
        return ranking_delta * elo_weight # Classement ELO actuel du joueur

    @property
    def best_elo(self) -> int:
        """
            Classement ELO du joueur
        """
        elo_weight = 15  # to better fit with ELO rating system (10 is better)
        nc_ranking = Ranking.query.filter_by(value="NC").first()
        second_series_threshold = Ranking.query.filter_by(value="-15").first()
        if self.best_ranking:
            if self.ranking.id < second_series_threshold.id:
                ranking_delta = (second_series_threshold.id - self.best_ranking.id) // 10 + nc_ranking.id - second_series_threshold.id
            else:
                ranking_delta = nc_ranking.id - self.best_ranking.id
            return ranking_delta * elo_weight if ranking_delta != -1 else self.current_elo # Meilleur classement ELO du joueur
        else:
            return self.current_elo

    @property
    def refined_elo(self) -> int:
        """
            Classement affiné par rapport au meilleur ancien classement du joueur et âge passé/actuel
        """
        # Détermination du classement affiné
        age_decay_rate: float = 0.007
        # best_rank_age, age = self.license.bestRanking.age, self.age   # not in player.csv :-( (only displayed on tenup) assume optimal ranking age is 25
        best_rank_age = 25
        if self.best_elo <= self.current_elo:
            return self.current_elo
        age_factor = 1 - abs(self.age - best_rank_age) * age_decay_rate
        # Coefficient de pondération en fonction du nombre de blessures
        injuries_weight = (1 - len(self.injuries) / 15)
        # injuries_weight = 1
        return max(self.current_elo, round(self.best_elo * injuries_weight * age_factor))
        # value = max(self.current_elo, round(self.best_elo * injuries_weight * age_factor))
        # return int((self.current_elo + value) / 2)

    def has_injury(self, injury: Injury) -> bool:
        return any(i.id == injury.id for i in self.injuries)

    def __repr__(self):
        return f'{self.name}'


class Team(db.Model):
    __tablename__ = 'team'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(20), unique=False, nullable=False)
    captainId = db.Column(db.Integer, db.ForeignKey('player.id'))
    poolId = db.Column(db.Integer, db.ForeignKey('pool.id'), nullable=True)
    ranking = db.Column(db.Integer, nullable=True)
    clubId = db.Column(db.String(8), db.ForeignKey('club.id', ondelete='CASCADE'), nullable=False)

    # Define the foreign key relationship with Pool
    pool = relationship('Pool', back_populates='teams')

    # # Define the foreign key relationship with Club
    # club = relationship('Club', back_populates='teams')  # Add this line

    # Define the relationship with Player using many-to-many association
    players = relationship('Player', secondary=player_team_association, back_populates='teams')  # Correction ici

    @property
    def avg_age(self) -> int:
        return round(sum([p.age for p in self.players]) / len(self.players))

    def get_available_players(self, matchday):
        """Get list of available players for a specific matchday"""
        return Player.query.join(
            PlayerMatchdayAvailability
        ).filter(
            PlayerMatchdayAvailability.matchday_id == matchday.id,
            PlayerMatchdayAvailability.is_available == True,
            Player.id.in_([p.id for p in self.players])
        ).all()

    def initialize_player_availability(self):
        """Initialize availability for all players in the team"""
        matchdays = Matchday.query.filter_by(championshipId=self.championship.id).all()

        availabilities = []
        for player in self.players:
            for matchday in matchdays:
                existing = PlayerMatchdayAvailability.query.filter_by(
                    player_id=player.id,
                    matchday_id=matchday.id
                ).first()

                if not existing:
                    availability = PlayerMatchdayAvailability(
                        player_id=player.id,
                        matchday_id=matchday.id,
                        is_available=True,
                        updated_at=datetime.utcnow()
                    )
                    availabilities.append(availability)

        if availabilities:
            db.session.add_all(availabilities)
            db.session.commit()

    def matches_played(self) -> int:
        return len(self.pool.teams) - 1

    @property
    def matches_won(self) -> int:
        matches = Match.query.filter(Match.homeTeamId == self.id).all() + Match.query.filter(
            Match.visitorTeamId == self.id).all()
        return sum(1 for m in matches if m.homeScore > m.visitorScore)

    @property
    def matches_lost(self) -> int:
        matches = Match.query.filter(Match.homeTeamId == self.id).all() + Match.query.filter(
            Match.visitorTeamId == self.id).all()
        return sum(1 for m in matches if m.homeScore < m.visitorScore)

    def is_visitor(self, match: Match) -> bool:
        visitor_team = Team.query.get(match.visitorTeamId)
        return visitor_team.id == self.id

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
        return [matchday for matchday in self.championship.matchdays
                if any(match.homeTeamId == self.id or match.visitorTeamId == self.id
                       for match in matchday.matches)]

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
    # startDate = db.Column(db.Date, nullable=False)
    # endDate = db.Column(db.Date, nullable=False)
    singlesCount = db.Column(db.Integer, nullable=False)
    doublesCount = db.Column(db.Integer, nullable=False)

    # dates = relationship('ChampionshipDate', backref='championship', lazy='dynamic')

    divisionId = db.Column(db.Integer, db.ForeignKey('division.id'))  # Ajout de la clé étrangère vers la division
    division = relationship('Division')  # Relation avec la division

    # Define the one-to-many relationship with Matchday
    # matchdays = relationship('Matchday', back_populates='championship')
    matchdays = relationship('Matchday', back_populates='championship', cascade="all, delete-orphan")

    # pools = relationship('Pool', back_populates='championship')  # Relation avec les poules du championnat
    pools = relationship('Pool', back_populates='championship', cascade="all, delete-orphan")  # Relation avec les poules du championnat

    @property
    def start_date(self):
        return self.matchdays[0].date if self.matchdays else None

    @property
    def end_date(self):
        return self.matchdays[-1].date if self.matchdays else None

    @property
    def exempted_teams(self):
        return Team.query.join(Pool).filter(and_(Pool.championshipId == self.id, Pool.letter == None)).all()

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

    # @property
    # def match_dates_new(self):
    #     division = Division.query.get(self.divisionId)
    #     if division.type == 0:  # National
    #         # dimanches 27 avril, 4, 11, 18 et 25 mai 2025
    #         return [date(2025, 4, 27), date(2025, 5, 4), date(2025, 5, 11), date(2025, 5, 18), date(2025, 5, 25)]
    #     elif division.ageCategory.type == 1:  # Senior
    #         if division.ageCategory.minAge in [35, 45, 55]:
    #             # Dimanches 1, 8, 15, 22 octobre 2023
    #             # Dimanche 12 novembre 2023
    #             return [date(2023, 10, 1), date(2023, 10, 8), date(2023, 10, 15), date(2023, 10, 22), date(2023, 11, 12)]
    #         elif division.ageCategory.minAge in [65, 75]:
    #             # Mardis 3, 10, 17, 24 octobre 2023
    #             # Mardi 7 novembre 2023
    #             return [date(2023, 10, 3), date(2023, 10, 10), date(2023, 10, 17), date(2023, 10, 24), date(2023, 11, 7)]

    def __repr__(self):
        return f'{self.name}'


class PoolSimulation(db.Model):
    __tablename__ = 'pool_simulation'

    id = db.Column(db.Integer, primary_key=True)
    pool_id = db.Column(db.Integer, ForeignKey('pool.id'), nullable=False)
    num_simulations = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    pool = relationship('Pool', back_populates='simulations')
    team_results = relationship('TeamSimulationResult', back_populates='simulation', cascade="all, delete-orphan")


class TeamSimulationResult(db.Model):
    __tablename__ = 'team_simulation_result'

    id = db.Column(db.Integer, primary_key=True)
    simulation_id = db.Column(db.Integer, ForeignKey('pool_simulation.id'), nullable=False)
    team_id = db.Column(db.Integer, ForeignKey('team.id'), nullable=False)
    avg_ranking = db.Column(db.Float, nullable=False)
    avg_points = db.Column(db.Float, nullable=False)
    best_ranking = db.Column(db.Integer, nullable=False)
    worst_ranking = db.Column(db.Integer, nullable=False)

    # Relationships
    simulation = relationship('PoolSimulation', back_populates='team_results')
    team = relationship('Team')

class Pool(db.Model):
    __tablename__ = 'pool'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    letter = db.Column(db.String(1), nullable=True)

    # Clé étrangère vers le championnat auquel appartient la poule
    championshipId = db.Column(db.Integer, ForeignKey('championship.id'))
    championship = relationship('Championship', back_populates='pools')

    teams = relationship('Team', back_populates='pool', cascade="all, delete-orphan")

    # Relation avec les matchs de la poule
    matches = relationship('Match', back_populates='pool', cascade="all, delete-orphan")

    simulations = relationship('PoolSimulation', back_populates='pool', cascade="all, delete-orphan")

    @property
    def is_valid_schedule(self) -> bool:
        encounters = {team.id: [] for team in self.teams}
        for match in self.matches:
            encounters[match.homeTeamId].append(match.visitorTeamId)
            encounters[match.visitorTeamId].append(match.homeTeamId)
        for team_id in encounters:
            if len(encounters[team_id]) != len(self.teams) - 1:
                return False
        return True

    @property
    def is_started(self) -> bool:
        return any(m.is_started for m in self.matches)

    @property
    def is_exempted(self) -> bool:
        return self.letter is None

    def get_team_by_id(self, team_id: int) -> Optional[Team]:
        return Team.query.get(team_id) if team_id else None

    @property
    def best_team(self) -> Optional[Team]:
        # return max(self.teams, key=lambda team: team.weight(self.championship)) if self.teams else None
        teams: Iterable[Team] = self.teams
        if teams:
            return max(teams, key=lambda team: team.weight(self.championship))
        else:
            return None

    @property
    def worst_team(self) -> Optional[Team]:
        # return min(self.teams, key=lambda team: team.weight(self.championship)) if self.teams else None
        teams: Iterable[Team] = self.teams
        if teams:
            return min(teams, key=lambda team: team.weight(self.championship))
        else:
            return None

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
    report_date = db.Column(db.Date, nullable=True)
    # tournament_round = db.Column(db.Integer, nullable=True)  # Champ pour le tour du tournoi (Null si phase de poule)

    # Replace the secondary relationship with direct relationship to the association model
    player_availabilities = relationship(
        'PlayerMatchdayAvailability',
        back_populates='matchday',
        cascade="all, delete-orphan"
    )

    # Define the many-to-one relationship with Pool
    championshipId = db.Column(db.Integer, db.ForeignKey('championship.id'), nullable=True)
    championship = relationship('Championship', back_populates='matchdays')

    # Define the one-to-many relationship with Match
    # matches = relationship('Match', back_populates='matchday')
    matches = relationship('Match', back_populates='matchday', cascade="all, delete-orphan")

    @property
    def singles_count(self):
        return Championship.query.get(self.championshipId).singlesCount

    @property
    def is_completed(self):
        return all(len(match.singles) == self.championship.singlesCount and
                   len(match.doubles) == self.championship.doublesCount
                   for match in self.matches)

    def available_players(self) -> list[Player]:
        # Get all available players for a matchday
        available_players = PlayerMatchdayAvailability.query.filter_by(
            matchday_id=self.id,
            is_available=True
        ).all()

        return [p.player for p in available_players]

    def __repr__(self):
        return f'Journée #{self.id}'


# class FinalTable(db.Model):
#     __tablename__ = 'final_table'
#
#     id = db.Column(db.Integer, primary_key=True)
#     championshipId = db.Column(db.Integer, ForeignKey('championship.id'), nullable=False)
#     teamId = db.Column(db.Integer, ForeignKey('team.id'), nullable=False)
#     position = db.Column(db.Integer, nullable=False)
#
#     championship = relationship('Championship', back_populates='final_table')
#     team = relationship('Team')
#
#     def __repr__(self):
#         return f'Final Table Entry: Championship ID - {self.championshipId}, Team ID - {self.teamId}, Position - {self.position}'


class Match(db.Model):
    __tablename__ = 'match'

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    homeScore = db.Column(db.Integer, nullable=True)
    visitorScore = db.Column(db.Integer, nullable=True)

    # Clé étrangère vers la journée de match
    matchdayId = db.Column(db.Integer, db.ForeignKey('matchday.id'))
    matchday = relationship('Matchday', back_populates='matches')

    # Clé étrangère vers la poule à laquelle appartient le match
    poolId = db.Column(db.Integer, ForeignKey('pool.id'))
    pool = relationship('Pool', back_populates='matches')

    # # Clé étrangère vers l'équipe à domicile
    homeTeamId = db.Column(db.Integer, ForeignKey('team.id'))
    homeTeam = relationship('Team', foreign_keys=[homeTeamId])

    # # Clé étrangère vers l'équipe adverse
    visitorTeamId = db.Column(db.Integer, ForeignKey('team.id'))
    visitorTeam = relationship('Team', foreign_keys=[visitorTeamId])

    singles = relationship('Single', back_populates='match', cascade="all, delete-orphan")
    doubles = relationship('Double', back_populates='match', cascade="all, delete-orphan")


    @property
    def is_started(self) -> bool:
        return self.singles or self.doubles

    @property
    def sets_count(self) -> tuple[int, int]:
        home_sets = visitor_sets = 0
        for match in self.singles + self.doubles:
            p1_sets, p2_sets = match.score.sets_count
            home_sets += p1_sets
            visitor_sets += p2_sets
        # logging.info((home_sets, visitor_sets))
        return home_sets, visitor_sets

    @property
    def games_count(self) -> tuple[int, int]:
        home_games = visitor_games = 0
        for match in self.singles + self.doubles:
            p1_games, p2_games = match.score.games_count
            home_games += p1_games
            visitor_games += p2_games
        return home_games, visitor_games

    @property
    def score(self) -> str:
        return f'{self.homeScore}-{self.visitorScore}' if self.homeScore is not None and self.visitorScore is not None else ''

    def __repr__(self):
        return f'#{self.id} le {self.date} -> {self.homeTeam} vs {self.visitorTeam}: {self.score}'

    def winner(self) -> Optional[Team]:
        if self.homeScore > self.visitorScore:
            return self.homeTeam
        elif self.homeScore < self.visitorScore:
            return self.visitorTeam
        else:
            return None


class Single(db.Model):
    __tablename__ = 'singles'
    id = db.Column(db.Integer, primary_key=True)
    scoreId = db.Column(db.Integer, ForeignKey('score.id'))
    matchId = db.Column(db.Integer, ForeignKey('match.id'))
    player1Id = db.Column(db.Integer, ForeignKey('player.id'))
    player2Id = db.Column(db.Integer, ForeignKey('player.id'))

    match = relationship('Match', back_populates='singles')
    score = relationship('Score', back_populates='singles')

    # Define the many-to-one relationship with Player
    player1 = relationship('Player', foreign_keys=[player1Id])
    player2 = relationship('Player', foreign_keys=[player2Id])


class Double(db.Model):
    __tablename__ = 'doubles'
    id = db.Column(db.Integer, primary_key=True)
    scoreId = db.Column(db.Integer, ForeignKey('score.id'))
    matchId = db.Column(db.Integer, ForeignKey('match.id'))
    player1Id = db.Column(db.Integer, ForeignKey('player.id'))
    player2Id = db.Column(db.Integer, ForeignKey('player.id'))
    player3Id = db.Column(db.Integer, ForeignKey('player.id'))
    player4Id = db.Column(db.Integer, ForeignKey('player.id'))

    match = relationship('Match', back_populates='doubles')
    score = relationship('Score', back_populates='doubles')

    # Define the many-to-one relationship with Player
    player1 = relationship('Player', foreign_keys=[player1Id])
    player2 = relationship('Player', foreign_keys=[player2Id])
    player3 = relationship('Player', foreign_keys=[player3Id])
    player4 = relationship('Player', foreign_keys=[player4Id])

    @property
    def home_weight(self):
        player1, player2 = Player.query.get(self.player1Id), Player.query.get(self.player2Id)
        return player1.weight + player2.weight

    @property
    def visitor_weight(self):
        player3, player4 = Player.query.get(self.player3Id), Player.query.get(self.player4Id)
        return player3.weight + player4.weight


class Score(db.Model):
    __tablename__ = 'score'

    id = db.Column(db.Integer, primary_key=True)
    firstSetP1 = db.Column(db.Integer, nullable=False)
    firstSetP2 = db.Column(db.Integer, nullable=False)
    firstTieBreak = db.Column(db.Integer, nullable=True)
    secondSetP1 = db.Column(db.Integer, nullable=False)
    secondSetP2 = db.Column(db.Integer, nullable=False)
    secondTieBreak = db.Column(db.Integer, nullable=True)
    thirdSetP1 = db.Column(db.Integer, nullable=True)
    thirdSetP2 = db.Column(db.Integer, nullable=True)
    superTieBreak = db.Column(db.Integer, nullable=True)

    singles = relationship('Single', back_populates='score', cascade="all, delete-orphan")
    doubles = relationship('Double', back_populates='score', cascade="all, delete-orphan")

    # Relationship with Match
    # game_id = db.Column(db.Integer, ForeignKey('game.id'))
    # game = relationship("Game", back_populates="score")

    # # Define the relationship with License
    # matchSheetId = db.Column(db.Integer, db.ForeignKey('match_sheet.id', ondelete='CASCADE'), nullable=False)
    # matchSheet = relationship('MatchSheet', back_populates='scores', cascade="all, delete-orphan")  # Add cascade option here

    @property
    def games_count(self) -> tuple[int, int]:
        team1_games = self.firstSetP1 + self.secondSetP1
        team1_games += int(self.thirdSetP1) if self.thirdSetP1 else 0
        team2_games = self.firstSetP2 + self.secondSetP2
        team2_games += int(self.thirdSetP2) if self.thirdSetP2 else 0
        return team1_games, team2_games

    @property
    def sets_count(self) -> tuple[int, int]:
        team1_sets = int(self.firstSetP1 > self.firstSetP2) + int(self.secondSetP1 > self.secondSetP2)
        team1_sets += int(self.thirdSetP1) if self.thirdSetP1 else 0
        team2_sets = int(self.firstSetP2 > self.firstSetP1) + int(self.secondSetP2 > self.secondSetP1)
        team2_sets += int(self.thirdSetP2) if self.thirdSetP2 else 0
        return team1_sets, team2_sets

    def __repr__(self):
        firstTieBreak = f' ({self.firstTieBreak})' if self.firstTieBreak else ''
        first_set = f'{self.firstSetP1}/{self.firstSetP2}{firstTieBreak}'
        secondTieBreak = f' ({self.secondTieBreak})' if self.secondTieBreak else ''
        second_set = f'{self.secondSetP1}/{self.secondSetP2}{secondTieBreak}'
        super_tie_break = None
        if self.superTieBreak:
            winner_score, loser_score = max(10, self.superTieBreak + 2), self.superTieBreak
            super_tie_break = f'{winner_score}/{loser_score}' if self.thirdSetP1 > self.thirdSetP2 else f'{loser_score}/{winner_score}'
        sets = [first_set, second_set, super_tie_break]
        return ' - '.join(filter(None, sets))

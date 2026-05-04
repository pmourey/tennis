# Source Generated with Decompyle++
# File: models.cpython-310.pyc (Python 3.10)

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
    id = db.Column(db.Integer, True, True, **('primary_key', 'autoincrement'))
    value = db.Column(db.String(10), False, **('nullable',))
    series = db.Column(db.Integer, True, **('nullable',))
    license = relationship('License', 'best_rankings', **('back_populates',))
    
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
    id = db.Column(db.Integer, True, True, **('primary_key', 'autoincrement'))
    value = db.Column(db.String(10), False, **('nullable',))
    series = db.Column(db.Integer, True, **('nullable',))
    license = relationship('License', 'rankings', **('back_populates',))
    
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
    id = db.Column(db.Integer, True, **('primary_key',))
    from_club_id = db.Column(db.String(8), ForeignKey('club.id'), False, **('nullable',))
    to_club_id = db.Column(db.String(8), ForeignKey('club.id'), False, **('nullable',))
    distance = db.Column(db.Float, True, **('nullable',))
    duration = db.Column(db.Float, True, **('nullable',))
    from_club = relationship('Club', [
        from_club_id], **('foreign_keys',))
    to_club = relationship('Club', [
        to_club_id], **('foreign_keys',))


class Club(db.Model):
    __tablename__ = 'club'
    id = db.Column(db.String(8), True, **('primary_key',))
    name = db.Column(db.String(20), True, False, **('unique', 'nullable'))
    city = db.Column(db.String(20), False, **('nullable',))
    tennis_courts = db.Column(db.Integer, True, **('nullable',))
    padel_courts = db.Column(db.Integer, True, **('nullable',))
    beach_courts = db.Column(db.Integer, True, **('nullable',))
    latitude = db.Column(db.Float, True, **('nullable',))
    longitude = db.Column(db.Float, True, **('nullable',))
    players = relationship('Player', 'club', 'all, delete-orphan', **('back_populates', 'cascade'))
    
    def __repr__(self):
        return f'''{self.name}'''

    
    def __eq__(self, other):
        return self.id == other.id

    
    def info(self = None):
        formatted_id = f'''{self.id[:2]:s} {self.id[2:4]:s} {self.id[4:]:s}'''
        courts = f'''Tennis : {self.tennis_courts} terrains'''
        if self.padel_courts:
            courts += f''', Padel : {self.padel_courts}'''
        if self.beach_courts:
            courts += f''', Beach Tennis : {self.beach_courts}'''
        return f'''{self.name} ({formatted_id}) - {courts}'''

    info = None(info)


class License(db.Model):
    __tablename__ = 'license'
    id = db.Column(db.Integer, True, **('primary_key',))
    firstName = db.Column(db.String(20), False, **('nullable',))
    lastName = db.Column(db.String(20), False, **('nullable',))
    letter = db.Column(db.String(1), False, **('nullable',))
    year = db.Column(db.Integer, False, **('nullable',))
    gender = db.Column(db.Integer, False, **('nullable',))
    rankingId = db.Column(db.Integer, ForeignKey('ranking.id'), False, **('nullable',))
    ranking = relationship('Ranking', [
        rankingId], 'license', **('foreign_keys', 'back_populates'))
    bestRankingId = db.Column(Integer, ForeignKey('best_ranking.id'), True, **('nullable',))
    bestRanking = relationship('BestRanking', [
        bestRankingId], 'license', **('foreign_keys', 'back_populates'))
    rankings = relationship('Ranking', 'license', [
        rankingId], 'ranking', **('back_populates', 'foreign_keys', 'overlaps'))
    best_rankings = relationship('BestRanking', 'license', [
        bestRankingId], 'bestRanking', **('back_populates', 'foreign_keys', 'overlaps'))
    players = relationship('Player', 'license', **('back_populates',))
    
    def name(self):
        return f'''{self.firstName} {self.lastName}'''

    name = property(name)
    
    def __repr__(self):
        return f'''{self.id} - {self.name}'''


player_team_association = Table('player_team_association', db.Model.metadata, db.Column('player_id', db.Integer, db.ForeignKey('player.id', 'CASCADE', **('ondelete',))), db.Column('team_id', db.Integer, db.ForeignKey('team.id', 'CASCADE', **('ondelete',))))
player_injury_association = Table('player_injury_association', db.Model.metadata, db.Column('player_id', db.Integer, db.ForeignKey('player.id', 'CASCADE', **('ondelete',))), db.Column('injury_id', db.Integer, db.ForeignKey('injury.id', 'CASCADE', **('ondelete',))))

class InjurySite(db.Model):
    __tablename__ = 'injury_site'
    id = db.Column(db.Integer, True, **('primary_key',))
    name = db.Column(db.String)
    injuries = db.relationship('Injury', 'site', **('back_populates',))
    
    def __repr__(self):
        return self.name

    
    def acute_injuries(self = None):
        injuries = Injury.query.filter_by(self.id, **('siteId',)).all()
        logging.info(injuries)
        return (lambda .0: [ injury.name for injury in .0 if injury.type == 0 ])(injuries)

    acute_injuries = None(acute_injuries)
    
    def overuse_injuries(self = None):
        injuries = Injury.query.filter_by(self.id, **('siteId',)).all()
        logging.info(injuries)
        return (lambda .0: [ injury.name for injury in .0 if injury.type == 1 ])(injuries)

    overuse_injuries = None(overuse_injuries)


class Injury(db.Model):
    __tablename__ = 'injury'
    id = db.Column(db.Integer, True, **('primary_key',))
    type = db.Column(Integer)
    name = db.Column(db.String)
    siteId = db.Column(db.Integer, db.ForeignKey('injury_site.id'))
    site = db.relationship('InjurySite', 'injuries', **('back_populates',))
    players = relationship('Player', player_injury_association, 'injuries', True, **('secondary', 'back_populates', 'single_parent'))
    
    def site_name(self = None):
        site = InjurySite.query.get(self.siteId)
        return site.name

    site_name = None(site_name)
    
    def __repr__(self):
        return self.name



class PlayerMatchdayAvailability(db.Model):
    __tablename__ = 'player_matchday_availability'
    player_id = db.Column(db.Integer, db.ForeignKey('player.id', 'CASCADE', **('ondelete',)), True, **('primary_key',))
    matchday_id = db.Column(db.Integer, db.ForeignKey('matchday.id', 'CASCADE', **('ondelete',)), True, **('primary_key',))
    is_available = db.Column(db.Boolean, True, **('default',))
    plays_single = db.Column(db.Boolean, False, False, '0', **('default', 'nullable', 'server_default'))
    plays_double = db.Column(db.Boolean, False, False, '0', **('default', 'nullable', 'server_default'))
    is_substitute = db.Column(db.Boolean, False, False, '0', **('default', 'nullable', 'server_default'))
    updated_at = db.Column(db.DateTime, datetime.utcnow, datetime.utcnow, **('default', 'onupdate'))
    player = relationship('Player', 'matchday_availabilities', **('back_populates',))
    matchday = relationship('Matchday', 'player_availabilities', **('back_populates',))


class TeamMatchdayJoker(db.Model):
    '''Joueur joker : 1 seul par équipe par journée, hors liste nominative des 15.'''
    __tablename__ = 'team_matchday_joker'
    id = db.Column(db.Integer, True, True, **('primary_key', 'autoincrement'))
    team_id = db.Column(db.Integer, db.ForeignKey('team.id', 'CASCADE', **('ondelete',)), False, **('nullable',))
    matchday_id = db.Column(db.Integer, db.ForeignKey('matchday.id', 'CASCADE', **('ondelete',)), False, **('nullable',))
    player_id = db.Column(db.Integer, db.ForeignKey('player.id', 'SET NULL', **('ondelete',)), True, **('nullable',))
    plays_single = db.Column(db.Boolean, False, False, '0', **('default', 'nullable', 'server_default'))
    plays_double = db.Column(db.Boolean, False, False, '0', **('default', 'nullable', 'server_default'))
    __table_args__ = (db.UniqueConstraint('team_id', 'matchday_id', 'uq_team_matchday_joker', **('name',)),)
    team = relationship('Team', 'jokers', **('back_populates',))
    matchday = relationship('Matchday', 'jokers', **('back_populates',))
    player = relationship('Player')
    
    def __repr__(self):
        return f'''Joker {self.player} ({self.team} - J{self.matchday_id})'''



class Player(db.Model):
    __tablename__ = 'player'
    id = db.Column(db.Integer, True, True, **('primary_key', 'autoincrement'))
    birthDate = db.Column(db.DateTime, False, **('nullable',))
    weight = db.Column(db.Integer, True, 0, **('nullable', 'default'))
    height = db.Column(db.Integer, True, 0, **('nullable', 'default'))
    isActive = db.Column(db.Boolean, True, **('default',))
    hiddenInTenup = db.Column(db.Boolean, False, False, '0', **('default', 'nullable', 'server_default'))
    matchday_availabilities = relationship('PlayerMatchdayAvailability', 'player', 'all, delete-orphan', **('back_populates', 'cascade'))
    injuries = relationship('Injury', player_injury_association, 'players', True, **('secondary', 'back_populates', 'single_parent'))
    clubId = db.Column(db.Integer, db.ForeignKey('club.id', 'CASCADE', **('ondelete',)), False, **('nullable',))
    club = relationship('Club', 'players', **('back_populates',))
    licenseId = db.Column(db.Integer, db.ForeignKey('license.id', 'CASCADE', **('ondelete',)), False, **('nullable',))
    license = relationship('License', 'players', **('back_populates',))
    teams = relationship('Team', player_team_association, 'players', True, 'all, delete-orphan', **('secondary', 'back_populates', 'single_parent', 'cascade'))
    
    def is_available(self = None, matchday = None):
        '''Check if player is available for a specific matchday'''
        availability = PlayerMatchdayAvailability.query.filter_by(self.id, matchday.id, **('player_id', 'matchday_id')).first()
        if availability:
            return availability.is_available

    
    def initialize_matchday_availability(self, championship):
        '''Initialize availability for all matchdays in a championship for this player'''
        matchdays = Matchday.query.filter_by(championship.id, **('championshipId',)).all()
        for matchday in matchdays:
            existing = PlayerMatchdayAvailability.query.filter_by(self.id, matchday.id, **('player_id', 'matchday_id')).first()
            if not existing:
                availability = PlayerMatchdayAvailability(self.id, matchday.id, True, datetime.utcnow(), **('player_id', 'matchday_id', 'is_available', 'updated_at'))
                db.session.add(availability)
        db.session.commit()

    
    def gender(self):
        return self.license.gender

    gender = property(gender)
    
    def double_rating(self):
        zero_ranking = Ranking.query.filter_by('0', **('value',)).first()
        return self.ranking.id - zero_ranking.id

    double_rating = property(double_rating)
    
    def double_info(self):
        return f'''{self.name} ({self.double_rating})'''

    double_info = property(double_info)
    
    def ranking_id(self):
        license = License.query.get(self.licenseId)
        ranking = Ranking.query.get(license.rankingId)
        return ranking.id

    ranking_id = property(ranking_id)
    
    def best_ranking_id(self):
        license = License.query.get(self.licenseId)
        ranking = BestRanking.query.get(license.rankingId)
        return ranking.id

    best_ranking_id = property(best_ranking_id)
    
    def best_ranking_id(self, value):
        license = License.query.get(self.licenseId)
        if license:
            logging.info(f'''Setting best_ranking_id to {value} - old license value = {license.bestRanking.value}''')
            license.bestRankingId = value
            return None
        raise None('Player does not have a license')

    best_ranking_id = best_ranking_id.setter(best_ranking_id)
    
    def ranking(self):
        license = License.query.get(self.licenseId)
        return Ranking.query.get(license.rankingId)

    ranking = property(ranking)
    
    def best_ranking(self):
        license = License.query.get(self.licenseId)
        if license.bestRankingId:
            return BestRanking.query.get(license.bestRankingId)

    best_ranking = property(best_ranking)
    
    def last_name(self):
        license = License.query.get(self.licenseId)
        return license.lastName

    last_name = property(last_name)
    
    def name(self):
        return f'''{self.license.firstName} {self.license.lastName}'''

    name = property(name)
    
    def info(self):
        return f'''{self.name} ({self.ranking}) {(self.current_elo, self.refined_elo, self.best_elo)}'''

    info = property(info)
    
    def elo_tuple(self):
        return (self.current_elo, self.refined_elo, self.best_elo)

    elo_tuple = property(elo_tuple)
    
    def full_info(self):
        nd_ranking = Ranking.query.filter_by('ND', **('value',)).first()
        if self.best_ranking.id == nd_ranking.id:
            best_ranking = ', ex. ???'
        elif self.best_ranking.id < self.ranking.id:
            pass
        
        best_ranking = ''
        age_and_ranking = f'''({self.age} ans{best_ranking})'''
        return f'''{self.name} {self.ranking} {age_and_ranking}'''

    full_info = property(full_info)
    
    def age(self = None):
        today = datetime.now()
        return today.year - self.birthDate.year - ((today.month, today.day) < (self.birthDate.month, self.birthDate.day))

    age = None(age)
    
    def has_valid_age(self = None, age_category = None):
        if self.age <= self.age:
            return self.age < age_category.maxAge
        self.age <= self.age
        return self.age

    
    def formatted_birth_date(self):
        return self.birthDate.replace(1, 1, **('month', 'day')).strftime('%Y-%m-%d')

    formatted_birth_date = property(formatted_birth_date)
    
    def current_elo(self = None):
        '''
            Classement ELO du joueur
        '''
        elo_weight = 15
        nc_ranking = Ranking.query.filter_by('NC', **('value',)).first()
        second_series_threshold = Ranking.query.filter_by('-15', **('value',)).first()
        if self.ranking.id < second_series_threshold.id:
            ranking_delta = (second_series_threshold.id - self.ranking.id) // 10 + nc_ranking.id - second_series_threshold.id
            return ranking_delta * elo_weight
        ranking_delta = None.id - self.ranking.id
        return ranking_delta * elo_weight

    current_elo = None(current_elo)
    
    def best_elo(self = None):
        '''
            Classement ELO du joueur
        '''
        elo_weight = 15
        nc_ranking = Ranking.query.filter_by('NC', **('value',)).first()
        second_series_threshold = Ranking.query.filter_by('-15', **('value',)).first()
        if self.best_ranking:
            if self.ranking.id < second_series_threshold.id:
                ranking_delta = (second_series_threshold.id - self.best_ranking.id) // 10 + nc_ranking.id - second_series_threshold.id
            else:
                ranking_delta = nc_ranking.id - self.best_ranking.id
            if ranking_delta != -1:
                return ranking_delta * elo_weight
            return None.current_elo
        return None.current_elo

    best_elo = None(best_elo)
    
    def refined_elo(self = None):
        '''
            Classement affiné par rapport au meilleur ancien classement du joueur et âge passé/actuel
        '''
        age_decay_rate = 0.007
        best_rank_age = 25
        if self.best_elo <= self.current_elo:
            return self.current_elo
        age_factor = None - abs(self.age - best_rank_age) * age_decay_rate
        injuries_weight = 1 - len(self.injuries) / 15
        return max(self.current_elo, round(self.best_elo * injuries_weight * age_factor))

    refined_elo = None(refined_elo)
    
    def has_injury(self = None, injury = None):
        return None((lambda .0 = None: for i in .0:
i.id == injury.id)(self.injuries))

    
    def age_category(self):
        """Retourne la catégorie d'âge principale du joueur selon les règles FFT."""
        AC = AgeCategory
        import models
        age = self.age
        youth = AC.query.filter(AC.type == 0, AC.minAge <= age, AC.maxAge >= age).order_by(AC.maxAge).first()
        if youth:
            return youth
        veteran = None.query.filter(AC.type == 2, AC.minAge <= age, AC.maxAge >= age).order_by(AC.minAge).first()
        if veteran:
            return veteran
        senior = None.query.filter(AC.type == 1).first()
        return senior

    age_category = property(age_category)
    
    def __repr__(self):
        return f'''{self.name}'''



class Team(db.Model):
    __tablename__ = 'team'
    id = db.Column(db.Integer, True, True, **('primary_key', 'autoincrement'))
    name = db.Column(db.String(20), False, False, **('unique', 'nullable'))
    captainId = db.Column(db.Integer, db.ForeignKey('player.id', 'SET NULL', **('ondelete',)), True, **('nullable',))
    poolId = db.Column(db.Integer, db.ForeignKey('pool.id'), True, **('nullable',))
    ranking = db.Column(db.Integer, True, **('nullable',))
    clubId = db.Column(db.String(8), db.ForeignKey('club.id', 'CASCADE', **('ondelete',)), False, **('nullable',))
    pool = relationship('Pool', 'teams', **('back_populates',))
    players = relationship('Player', player_team_association, 'teams', **('secondary', 'back_populates'))
    jokers = relationship('TeamMatchdayJoker', 'team', 'all, delete-orphan', **('back_populates', 'cascade'))
    
    def avg_age(self = None):
        return round(sum((lambda .0: [ p.age for p in .0 ])(self.players)) / len(self.players))

    avg_age = None(avg_age)
    
    def get_available_players(self, matchday):
        """Retourne les joueurs disponibles pour une journée donnée.
        Si aucune sélection de rôle n'a été faite → retourne tous les joueurs actifs.
        Sinon → retourne les joueurs avec is_available=True.
        """
        player_ids = (lambda .0: [ p.id for p in .0 ])(self.players)
        role_selection_count = PlayerMatchdayAvailability.query.filter(PlayerMatchdayAvailability.matchday_id == matchday.id, PlayerMatchdayAvailability.player_id.in_(player_ids), db.or_(PlayerMatchdayAvailability.plays_single == True, PlayerMatchdayAvailability.plays_double == True, PlayerMatchdayAvailability.is_substitute == True)).count()
        if role_selection_count == 0:
            available = Player.query.filter(Player.id.in_(player_ids), Player.isActive.is_(True)).all()
        else:
            available = Player.query.join(PlayerMatchdayAvailability).filter(PlayerMatchdayAvailability.matchday_id == matchday.id, PlayerMatchdayAvailability.is_available == True, Player.id.in_(player_ids)).all()
        joker = self.get_joker(matchday)
        if joker and joker not in available:
            available.append(joker)
        return available

    
    def get_players_for_simulation(self = None, matchday = None, singles_count = None, doubles_count = ('singles_count', 'int', 'doubles_count', 'int')):

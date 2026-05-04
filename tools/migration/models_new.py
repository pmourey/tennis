from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta, date
from typing import Optional, List, Iterable

from sqlalchemy import ForeignKey, Table, Integer, String, Float, Boolean, and_
from sqlalchemy.orm import relationship, backref, DeclarativeBase, mapped_column

from extensions import db

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

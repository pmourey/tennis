# Source Generated with Decompyle++
# File: common.cpython-310.pyc (Python 3.10)

from __future__ import annotations
import json
import logging
from multiprocessing import Pool
import os
import csv
import re
from datetime import datetime, timedelta
from enum import Enum
from random import shuffle, choice, random, sample, randint
from typing import List, Optional
import pandas as pd
from sqlalchemy import desc, asc, and_
from random import random
from typing import List
from models import Club, Player, AgeCategory, Division, Ranking, License, Championship, BestRanking, Team, Pool, Match, Matchday, Single, Score, Double, Injury, InjurySite
from tools.import_csv import extract
from mapbox import Directions
from geojson import Feature, Point

class CatType(Enum):
    Youth = 0
    Senior = 1
    Veteran = 2


class DivType(Enum):
    National = 0
    Prenational = 1
    Regional = 2
    Departmental = 3


class Series(Enum):
    First = 1
    Second = 2
    Third = 3
    Fourth = 4


class Gender(Enum):
    Male = 0
    Female = 1
    Mixte = 2


class BodyPart(Enum):
    Head = 0
    Body = 1
    Leg = 2
    Arm = 3
    Hand = 4
    Foot = 5
    Back = 6
    Neck = 7
    Shoulder = 8
    Chest = 9
    Waist = 10
    Hip = 11
    Knee = 12
    Ankle = 13
    Elbow = 14
    Wrist = 15
    Finger = 16
    Toe = 17
    Nose = 18
    Ear = 19
    Eye = 20
    Mouth = 21
    Face = 22
    Tongue = 23
    Throat = 24
    Lip = 25
    Chin = 26


class InjuryType(Enum):
    Acute = 0
    OverUse = 1


def count_sundays_between_dates(start_date, end_date):

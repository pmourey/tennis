import re

from sqlalchemy import Column, Integer, String, Float
from sqlalchemy.ext.declarative import declarative_base

# Définir une classe de base pour les modèles de données
Base = declarative_base()


# Définir un modèle de données pour une table 'club'
class Club(Base):
    __tablename__ = 'club'
    id = Column(String(8), primary_key=True)
    name = Column(String(20), unique=True, nullable=False)
    city = Column(String(20), nullable=False)
    tennis_courts = Column(Integer, nullable=True)
    padel_courts = Column(Integer, nullable=True)
    beach_courts = Column(Integer, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

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

    @staticmethod
    def from_json(club_json):
        regex = r"Tennis : (\d+) terrain(?:s), Padel : (\d+), Beach Tennis : (\d+)"
        matches = re.search(regex, club_json['terrainPratiqueLibelle'])
        tennis_count = padel_count = beach_count = 0
        if matches:
            tennis_count = int(matches.group(1))
            padel_count = int(matches.group(2))
            beach_count = int(matches.group(3))
        else:
            regex = r"Tennis : (\d+) terrain(?:s), Padel : (\d+)"
            matches = re.search(regex, club_json['terrainPratiqueLibelle'])
            if matches:
                tennis_count = int(matches.group(1))
                padel_count = int(matches.group(2))
            else:
                regex = r"Tennis : (\d+) terrain(?:s), Beach Tennis : (\d+)"
                matches = re.search(regex, club_json['terrainPratiqueLibelle'])
                if matches:
                    tennis_count = int(matches.group(1))
                    beach_count = int(matches.group(2))
                else:
                    regex = r"(\d+) terrain"
                    matches = re.search(regex, club_json['terrainPratiqueLibelle'])
                    if matches:
                        tennis_count = int(matches.group(1))
        club = Club(id=club_json['clubId'],
                    name=club_json['nom'],
                    city=club_json['ville'],
                    tennis_courts=tennis_count,
                    padel_courts=padel_count,
                    beach_courts=beach_count,
                    latitude=club_json['lat'],
                    longitude=club_json['lng']
        )
        return club

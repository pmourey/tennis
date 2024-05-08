import glob
import json
import os
import re

from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from TenUpModel import Club, Base
import pandas as pd


# Fonction pour supprimer les caractères spéciaux des données JSON
def remove_special_characters(json_string):
    # Remplacer les caractères spéciaux par des espaces vides
    json_string = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f\n\u0027]', '', json_string)
    return json_string


def extract_courts(club_json):
    # Expression régulière pour extraire le nombre de terrains de tennis, padel et beach
    regex = r"Tennis : (\d+) terrains, Padel : (\d+), Beach Tennis : (\d+)"
    # Rechercher les correspondances dans la chaîne 'terrainPratiqueLibelle'
    matches = re.search(regex, club_json['terrainPratiqueLibelle'])
    if matches:
        tennis_count = int(matches.group(1))
        padel_count = int(matches.group(2))
        beach_count = int(matches.group(3))
        return [tennis_count, padel_count, beach_count]
    return [0] * 3

if __name__ == '__main__':
    directory = os.path.dirname(os.path.realpath(__file__))
    engine = create_engine(f'sqlite:///{directory}/tenup.db', echo=True)
    # Créer toutes les tables dans la base de données
    Base.metadata.create_all(engine)

    Session = sessionmaker(bind=engine)
    session = Session()

    # mon code postal
    # location = '06700'
    # location = 'MONTPON'
    # location = 'BRIANCON'
    # location = 'CANNES'
    # location = 'HYERES'
    # location = 'MARSEILLE'
    location = 'RIORGES'

    pattern = f'find_clubs_{location}.html'  # Modèle de nom des fichiers que vous souhaitez rechercher
    # Utilisation d'une expression régulière pour extraire les arguments
    regexp = r"jQuery.extend\(([^,]+),\s*([^)]+)\)"
    # regexp = r"jQuery.extend\(([^)]+),\s*([^)]+)\)"

    # Parcours de tous les fichiers correspondant au motif dans le répertoire
    for filename in glob.glob(os.path.join(f"{directory}/data", pattern)):
        with open(filename, 'r') as file:
            for line in file:
                match = re.match(regexp, line)
                if match:
                    json_string = match.group(2)
                    # json_string = remove_special_characters(json_string)
                    json_string = json_string.replace('\\n', '').replace('\\u0027', "'")
                    # json_string = json_string.replace('(', '').replace(')', '')
                    # pattern = r',"tagcommander_click":"\s+tc_events_19\(this,\'clic\',{.*?}\)"'
                    # cleaned_string = re.sub(pattern, '', cleaned_string)
                    json_string = re.sub(r'}$', '})"}}', json_string)
                    print(json_string)
                    try:
                        data = json.loads(json_string)
                        clubs = data['fft_recherche_club']['resultat']
                        print(f'{len(clubs)} clubs trouvés à 30km de {location}!')
                        for club_json in clubs:
                            club = Club.from_json(club_json)
                            session.add(club)
                            session.commit()
                            print(club.info)
                        # for club in clubs:
                        #     print(club['clubId'], club['nom'], club['ville'], club['lat'], club['lng'], club['terrainPratiqueLibelle'])
                    except json.JSONDecodeError as e:
                        print(f"Erreur de chargement du fichier {filename}", e)
                        continue
                    except IntegrityError as e:
                        # Rollback the session to prevent partial insertion
                        session.rollback()
                        print(f"Error inserting club: {club}. IntegrityError: {e}")
                        # You can log the error, skip the record, or handle it as needed
                    except Exception as e:
                        session.rollback()
                        print(f"Error inserting club: {club}. Error: {e}")
                        # Handle other types of exceptions here

    session.close()

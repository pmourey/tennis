import os

import pandas as pd

def extract(df, field_criteria, field_value, columns):
    """
        Extract
    :param field_criteria:
    :param field_value:
    :param columns:
    :return: {'name': 'TC MÉDITERRANEE', 'latitude': 43.722466, 'longitude': 7.25919}
    """
    # # Filtrer les lignes avec le critère spécifié et sélectionner les colonnes spécifiées
    resultat_filtre = df.loc[df[field_criteria] == field_value, columns]
    result = resultat_filtre.to_dict('records')
    return result[0] if result else None

if __name__ == '__main__':
    BASE_PATH = os.path.dirname(__file__)
    csv_file = os.path.join(BASE_PATH, f'../static/data/clubs.csv')

    # Lire le fichier CSV dans un DataFrame
    df = pd.read_csv(csv_file)

    # Afficher les premières lignes du DataFrame pour vérifier
    # print(df.head())
    # print(df)

    # # Sélectionner les colonnes à récupérer
    colonnes_a_recuperer = ['name', 'latitude', 'longitude']

    a = extract(df=df, field_criteria='id', field_value=62060002, columns=colonnes_a_recuperer)
    print(a)

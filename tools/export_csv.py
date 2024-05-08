import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import pandas as pd


def export_to_csv(table_name: str, output_csv: str):
    # Requête SQL pour sélectionner toutes les données de la table
    sql_query = f"SELECT * FROM {table_name}"

    # Utiliser pandas pour lire les données de la table dans un DataFrame
    df = pd.read_sql_query(sql_query, engine)

    # Exporter le DataFrame vers un fichier CSV
    df.to_csv(output_csv, index=False)


if __name__ == '__main__':
    engine = create_engine('sqlite:///tenup.db', echo=True)

    Session = sessionmaker(bind=engine)
    session = Session()

    BASE_PATH = os.path.dirname(__file__)
    export_file = os.path.join(BASE_PATH, f'../static/data/clubs.csv')

    export_to_csv(table_name='club', output_csv=export_file)

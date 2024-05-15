# medical/views.py
import os

from flask import url_for, render_template, current_app
import json

from medical import medical_management_bp


@medical_management_bp.route('/')
def index():
    # Charger le fichier JSON
    # Construire le chemin absolu du fichier JSON
    static_folder = current_app.blueprints['medical'].static_folder
    file_path = os.path.join(static_folder, 'data', 'injuries_fr.json')
    with open(file_path, 'r') as file:
        data = json.load(file)

    # Passer les données au template HTML
    return render_template('medical_index.html', data=data)

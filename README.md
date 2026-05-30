# TennisManager

![Licence](https://img.shields.io/badge/licence-MIT-blue.svg)
![Python](https://img.shields.io/badge/Python-3.9+-green.svg)
![Flask](https://img.shields.io/badge/Flask-3.0+-yellow.svg)

Application web Flask pour la gestion d'un club de tennis, des championnats par equipes, des tournois individuels FFT, du suivi medical et d'un module materiel (raquettes/cordages).

## A propos

Le projet est organise en blueprints Flask:

- Admin
- Club
- Championship
- Tournament
- Medical
- Shop

La base est geree via SQLAlchemy, avec SQLite par defaut.

## Fonctionnalites implementees

### Admin

- Creation/suppression de clubs
- Selection du club actif via cookie signe
- Import initial des donnees clubs/joueurs depuis CSV
- Gestion des saisons (saison active, creation au format YYYY/YYYY)

### Club

- CRUD equipes et joueurs
- Gestion des blessures joueur
- Gestion des disponibilites par journee (simple/double/remplacant)
- Gestion des jokers avec controle de regle de classement
- Mutations/transferts de joueurs entre clubs
- Historique raquettes/cordages par joueur (entree active synchronisee)
- Calcul distance/temps de trajet entre clubs (Mapbox si cle configuree)

### Championnats par equipes

- Creation de championnats par division et saison
- Creation/configuration de poules
- Affectation des equipes aux poules
- Planification des rencontres
- Consultation des poules, matches et classements
- Simulations de poules et simulations batch avec historisation
- Filtrage multi-saisons

### Tournoi individuel (FFT Art. 44 a 52)

- Creation de tournoi interne ou ouvert
- Statuts: DRAFT, OPEN, IN_PROGRESS, CLOSED
- Categories (genre, tranche d'age, format, bornes de classement, series autorisees, surfaces)
- Inscriptions, desinscriptions, liste d'attente, promotion liste d'attente
- Tetes de serie (activation manuelle) et disponibilites joueurs
- Convocations/alertes de retard de saisie
- Saisie des resultats, WO, propagation des vainqueurs
- Requalification/remplacement selon regles metier implementees
- Suppression controlee de tableaux/tournois selon statut et matchs joues

Modes de generation des tableaux:

- Tableau classique (depart en ligne)
- Tableau en cascade (qualificatifs chaines par tranche)
- Tableau a sections (qualificatifs paralleles + final)

Planification/edition:

- Planification automatique des matchs
- Vue d'impression
- Route export PDF conservee en retro-compatibilite (redirection vers impression)

### Medical

- Referentiel blessures/sites
- Liste des joueurs blesses
- Recherche joueurs

### Shop (raquettes/cordages)

- Catalogue raquettes avec filtres avances (poids, tamis, equilibre, rigidite, swingweight, annee...)
- Detail raquette et suggestions de modeles similaires
- Import/scraping de raquettes (racquetfinder) avec fusion et mise a jour
- Outils de diagnostic scraping
- Assistant de selection raquette base profil joueur
- Catalogue cordages Racqix + API JSON de filtrage
- Import Racqix (raquettes + cordages)

## Synthese: implemente vs README precedent

### Correctifs apportes au README

- Ajout des modules Medical et Shop (absents du README precedent)
- Ajout des fonctions avancees du tournoi: liste d'attente, requalification, convocations, suppression controlee
- Precision sur l'export PDF: URL conservee mais redirection vers vue impression
- Mise a jour de la stack Flask (3.0+) et de la base par defaut (SQLite)

### Ecart principal detecte

- Le README precedent indiquait PostgreSQL en prerequis, alors que la configuration active est SQLite (SQLALCHEMY_DATABASE_URI = sqlite:///tennis.sqlite3)

## Routes principales

### Application

- /
- /licensees-by-gender

### Blueprints

- /admin
- /club
- /championship
- /tournament
- /medical
- /shop

Exemples de routes tournoi:

- GET /tournament/
- GET|POST /tournament/create
- GET /tournament/<tid>
- POST /tournament/<tid>/generate-draw/<cid>
- POST /tournament/<tid>/generate-draw-tranche/<cid>
- POST /tournament/<tid>/generate-section-draw/<cid>
- GET /tournament/<tid>/draw/<draw_id>
- GET|POST /tournament/<tid>/match/<mid>/score
- POST /tournament/<tid>/schedule/<draw_id>
- GET /tournament/<tid>/print/<draw_id>
- GET /tournament/<tid>/export-pdf/<draw_id>

## Stack technique

- Backend: Flask 3, SQLAlchemy, Flask-Migrate
- Frontend: Jinja2, HTML, CSS, JavaScript
- Donnees: SQLite par defaut (adaptable a un autre SGBD)
- Integrations: Mapbox (optionnel), pandas, scraping web, reportlab/weasyprint (selon usage)

## Installation

1. Cloner le repository

```bash
git clone https://github.com/pmourey/tennis.git
cd tennis
```

2. Creer un environnement virtuel

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows
```

3. Installer les dependances

```bash
pip install -r requirements.txt
```

4. Lancer l'application

```bash
python app.py
```

Alternative WSGI: utiliser wsgi.py.

## Prerequis

- Python 3.9+
- pip
- SQLite (inclus dans Python, par defaut)
- Optionnel: cle MAPBOX_API_KEY pour les fonctions d'itineraire

## Documentation et contribution

- Voir CONTRIBUTING.md pour contribuer
- Voir Wiki.md et docs/ pour la documentation projet

## Licence

Projet sous licence MIT. Voir LICENSE.md.






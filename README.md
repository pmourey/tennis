# tennis

https://godot70.pythonanywhere.com

### TODOS
- [x] Création Club par défaut (USC Tennis)
- [x] Création des joueurs licenciés
- [x] Création d'une équipe à partir de joueurs au statut 'disponible'
- [ ] Création du championnat par équipes pour une saison donnée (date rencontres, format championnat, feuilles de match, etc...)
  - [x] ajout formulaire de création des championnats (vs catégorie d'âge et division)
  - [x] Création d'une équipe associée au championnat à partir des joueurs du club
  - [x] Assignation de l'équipe créée à un championnat via la poule communiquée par la ligue
  - [x] Création du calendrier prévisionnel du championnat (identique presque chaque année) et journées de championnat
  - [ ] Formulaire d'ajout des équipes adverses présentes dans la poule et du planning des rencontres pour l'équipe (domicile/extérieur/exempt) (utilisé après envoi par la ligue du calendrier des rencontres)
  - [ ] Gestion des disponibilités joueurs
- [ ] Administration:
  - [ ] Ajout club
    - [x] Ajout à partir des clubs listés en dur dans config.py (et 2 fichiers joueurs/joueuses présents dans static/data)
    - [ ] Faire formulaires d'ajout club et joueurs à partir de fichiers csv
  - [x] Suppression club
  - [x] Changement club

* https://docs.sqlalchemy.org/en/20/orm/join_conditions.html#relationship-foreign-keys
* https://docs.sqlalchemy.org/en/13/orm/mapped_sql_expr.html#mapper-sql-expressions
* https://realpython.com/flask-blueprint/
* https://github.com/ryuichi-sumida/algorithm_for_round_robin_tournament
* https://docs.mapbox.com/mapbox-gl-js/example/setstyle/

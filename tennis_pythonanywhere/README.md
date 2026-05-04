# TennisManager

![Licence](https://img.shields.io/badge/licence-MIT-blue.svg)
![Python](https://img.shields.io/badge/Python-3.9+-green.svg)
![Flask](https://img.shields.io/badge/Flask-2.0+-yellow.svg)

Une application web complète pour la gestion des clubs de tennis, des championnats par équipes et le suivi des joueurs.

## 🎾 À propos

TennisManager est une solution complète pour la gestion des clubs de tennis, offrant :

- Gestion des clubs (USC Tennis comme club par défaut)
- Gestion des licences joueurs
- Création et gestion des équipes
- Organisation des championnats par saison
- Support administratif multi-clubs

## ✨ Fonctionnalités principales

### 🏢 Gestion des clubs

- Administration complète des clubs
- Gestion des droits d'accès
- Interface personnalisée par club

### 📅 Gestion des saisons sportives

- Création et gestion des saisons sportives (format YYYY/YYYY)
- Calcul automatique de l'année sportive courante (octobre à septembre)
- Historisation complète des championnats par saison
- Interface de filtrage multi-saisons
- Paramétrage de la saison active

### 👥 Gestion des joueurs

- Inscription et suivi des joueurs
- Gestion des licences
- Suivi des classements
- Gestion des mutations

### 🏆 Championnats

- Configuration des divisions par saison sportive
- Gestion des poules
- Planification des rencontres
- Saisie et suivi des résultats
- Historisation des championnats par saison
- Filtrage et consultation des saisons précédentes

### 🎾 Module Tournoi Individuel (conforme règles FFT Art. 44–52)

Ce module gère l'organisation complète d'un tournoi de tennis individuel, depuis
la création jusqu'à l'export PDF des tableaux.

#### Fonctionnalités générales

- Création de tournois internes (club) ou ouverts, avec gestion de l'état
  (`DRAFT` → `OPEN` → `IN_PROGRESS` → `CLOSED`)
- Gestion des catégories (simple / double, genre, tranche d'âge, surface,
  classement minimum autorisé)
- Gestion des terrains (nom, surface)
- Inscription des joueurs avec statut (`REGISTERED`, `WITHDRAWN`, etc.)
- Désignation manuelle des têtes de série ou attribution automatique
- Saisie des disponibilités des joueurs
- Planification automatique des matchs par terrain et par créneau horaire
- Export PDF des tableaux (bibliothèque ReportLab)

#### Génération des tableaux — conformité FFT

Trois modes de génération, tous conformes aux règles FFT :

| Mode | Route | Description |
|------|-------|-------------|
| **Tableau classique** | `POST /generate-draw/<cid>` | Tableau à départ en ligne (Art. 47) avec têtes de série et exempts (BYEs) |
| **Tableau en cascade** | `POST /generate-draw-tranche/<cid>` | Tableaux qualificatifs chaînés par tranches de classement puis tableau final |
| **Tableau à sections** | `POST /generate-section-draw/<cid>` | Tableau à sections parallèles (Art. 49) avec tirage `num_sections` optionnel |

**Tableau classique à départ en ligne (Art. 47)**

- Dimension = plus petite puissance de 2 ≥ effectif (`next_power_of_2`)
- Nombre de BYEs = dimension − effectif (Art. 47-3)
- Têtes de série placées en **haut des fractions du demi-tableau haut** et en
  **bas des fractions du demi-tableau bas** (Art. 46-1-e-i)
- BYEs placés **adjacents aux premières têtes de série** (Art. 47-4-a :
  si `nb_byes < nb_seeds`, les premières TdS sont exemptes)
- BYEs supplémentaires distribués comme des têtes de série virtuelles
  (Art. 47-4-b/c)
- Tirage au sort pour les positions des TdS 3 & 4, 5 & 6, etc.
  (paires depuis le centre, Art. 46-1-c)
- Propagation automatique des vainqueurs par forfait (BYE/WO)

**Tableau à sections (Art. 49)**

- Nombre de sections = `num_sections` (paramètre POST optionnel ; calculé
  automatiquement si absent)
- Chaque section est un **tableau classique indépendant** qualifiant
  **1 joueur** pour le tableau final
- **1 tête de série par section** (Art. 49-2-d)
- La TdS k est placée **en bas de la section k** (Art. 46-1-e-ii)
- Tous les joueurs d'un même classement sont regroupés dans les mêmes sections
  (Art. 45-3-e) ; distribution équilibrée par tirage au sort au sein de chaque
  groupe de classement
- Le tableau final reçoit les vainqueurs de sections avec au plus **1 qualifié
  par match** au 1er tour (Art. 45-3-c)

**Conformité Art. 52 — Remplacement / Requalification**

- Vérification qu'un joueur n'a pas encore disputé de match avant retrait
- Requalification disponible à partir des 1/16 de finale du tableau final,
  et en tableau intermédiaire pour les joueurs NC, 5e et 4e série
- Gestion des forfaits avec propagation WO automatique

#### Routes disponibles

```
GET  /tournament/                              Liste des tournois
POST /tournament/create                        Créer un tournoi
GET  /tournament/<id>                          Détail du tournoi
POST /tournament/<id>/status/<new_status>      Changer le statut
POST /tournament/<id>/add-category             Ajouter une catégorie
POST /tournament/<id>/delete-category/<cid>    Supprimer une catégorie
POST /tournament/<id>/add-court                Ajouter un terrain
POST /tournament/<id>/delete-court/<coid>      Supprimer un terrain
GET  /tournament/<id>/registrations/<cid>      Inscriptions d'une catégorie
POST /tournament/<id>/generate-draw/<cid>      Générer tableau classique (Art. 47)
POST /tournament/<id>/generate-draw-tranche/<cid>  Générer tableau en cascade
POST /tournament/<id>/generate-section-draw/<cid>  Générer tableau à sections (Art. 49)
GET  /tournament/<id>/draw/<draw_id>           Afficher un tableau
POST /tournament/<id>/match/<mid>/score        Saisir un résultat
GET  /tournament/<id>/schedule/<draw_id>       Planification des matchs
GET  /tournament/<id>/export-pdf/<draw_id>     Exporter le tableau en PDF
```

## 🛠 Technologies utilisées

- **Backend:** Python, Flask
- **Base de données:** SQLAlchemy ORM
- **Cartographie:** Mapbox GL JS
- **Frontend:** HTML, CSS, JavaScript
- **Hébergement:** PythonAnywhere

## 🚀 Installation

1. Cloner le repository

  ```bash
  git clone https://github.com/pmourey/tennis.git
  ```

2. Créer un environnement virtuel

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

3. Installer les dépendances

```bash
pip install -r requirements.txt
```

## 📖 Documentation

La documentation complète est disponible dans le wiki du projet, incluant :

- Guide d'utilisation détaillé
- Documentation API
- Guides d'administration
- FAQ

## 🤝 Contribution

Les contributions sont les bienvenues ! Voir `CONTRIBUTING.md` pour les lignes directrices.

## 🔑 Prérequis

- Python 3.9+
- Base de données PostgreSQL
- Compte Mapbox pour les services de cartographie

## 📝 Licence

Ce projet est sous licence MIT - voir le fichier `LICENSE.md` pour plus de détails.

## 📞 Contact

Pour toute question ou suggestion, n'hésitez pas à :

- Ouvrir une issue
- Contacter l'équipe de développement

## 🌟 Démo

Une version de démonstration est disponible sur PythonAnywhere :
http://godot70.pythonanywhere.com

Cette démo vous permet de tester les principales fonctionnalités de l'application :

- Gestion des équipes par saison sportive
- Suivi des championnats avec historique
- Gestion des joueurs et mutations
- Planification des rencontres
- Administration des saisons sportives
- Filtrage et consultation multi-saisons

Note : Les données de la démo sont réinitialisées périodiquement.

---

Développé avec ❤️ pour la communauté du tennis






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






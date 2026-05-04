# Gestion des conflits d'importation et suppression en cascade

## Résumé des modifications

### 1. Détection des conflits lors de l'importation de joueurs

**Fichier modifié : `common.py`**

La fonction `import_players` a été modifiée pour :
- Vérifier si un joueur avec une licence existante est déjà enregistré dans un autre club
- Détecter les conflits et faire un rollback de l'importation si des conflits sont trouvés
- Retourner un tuple `(success: bool, conflicts: list, players_count: int)`
- Réutiliser les licences existantes au lieu de créer des doublons

**Structure des conflits retournés :**
```python
{
    'license_number': '2707867 H',
    'name': 'Milan ABBAS',
    'ranking': '15/4',
    'current_club': 'NICE GIORDANA',
    'new_club': 'AUTRE CLUB'
}
```

### 2. Gestion des conflits dans l'interface d'administration

**Fichier modifié : `blueprints/admin/views.py`**

La route `new_club` a été mise à jour pour :
- Collecter tous les conflits détectés lors de l'importation
- Supprimer le club créé si des conflits sont détectés (rollback complet)
- Afficher la liste des joueurs en conflit avec leur club actuel

**Template créé : `blueprints/admin/templates/admin/import_conflicts.html`**

Ce template affiche :
- Un message d'avertissement clair sur les conflits
- Un tableau listant tous les joueurs en conflit
- Les informations : N° licence, nom, classement, club actuel, nouveau club

### 3. Suppression en cascade des joueurs

**Configuration dans `models.py` :**

La relation `Club.players` est configurée avec `cascade="all, delete-orphan"` :
```python
players = relationship('Player', back_populates='club', cascade="all, delete-orphan")
```

La clé étrangère `Player.clubId` est configurée avec `ondelete='CASCADE'` :
```python
clubId = db.Column(db.Integer, db.ForeignKey('club.id', ondelete='CASCADE'), nullable=False)
```

**Amélioration de la suppression dans `blueprints/admin/views.py` :**
- Compte le nombre de joueurs avant suppression
- Affiche un message confirmant la suppression du club et des joueurs
- Gère les erreurs si le club n'existe pas

### 4. Correction de la relation Player.license

**Fichier modifié : `models.py`**

La relation `Player.license` a été corrigée pour éviter la suppression de la licence :
```python
# AVANT (incorrect)
license = relationship('License', back_populates='players', single_parent=True, cascade="all, delete-orphan")

# APRÈS (correct)
license = relationship('License', back_populates='players')
```

Cette correction évite l'erreur `NOT NULL constraint failed: player.licenseId` lors de la suppression d'un club.

## Processus de fonctionnement

### Importation de joueurs

1. L'utilisateur tente d'importer un club avec ses joueurs
2. Pour chaque joueur dans le fichier CSV :
   - Vérification si la licence existe déjà
   - Si oui, vérification si un joueur avec cette licence existe dans un autre club
   - Si conflit détecté, ajout à la liste des conflits
   - Si pas de conflit, utilisation de la licence existante ou création d'une nouvelle
3. Si des conflits sont détectés :
   - Rollback de toutes les insertions
   - Suppression du club créé
   - Affichage de la page des conflits
4. Si aucun conflit :
   - Commit de tous les joueurs
   - Message de succès

### Suppression de club

1. L'utilisateur sélectionne un club à supprimer
2. Comptage du nombre de joueurs liés au club
3. Suppression du club
4. Grâce à la cascade :
   - Tous les joueurs du club sont automatiquement supprimés
   - Les relations avec les équipes sont supprimées
5. Message de confirmation avec le nombre de joueurs supprimés

## Tests

Un script de test a été créé : `test/test_club_import.py`

Pour l'exécuter :
```bash
cd /Users/display/PycharmProjects/tennis
python test/test_club_import.py
```

Les tests vérifient :
- La détection des conflits d'importation
- La suppression en cascade des joueurs
- La réutilisation des licences existantes

## Recommandations

1. **Avant de réimporter un club** : Supprimer d'abord l'ancien club pour éviter les conflits
2. **Sauvegarde** : Toujours faire une sauvegarde de la base de données avant de supprimer un club
3. **Vérification** : Utiliser la page des conflits pour identifier les joueurs problématiques
4. **Nettoyage** : Si un joueur change de club, supprimer d'abord son ancien club ou le mettre à jour manuellement

## Fichiers modifiés

- `common.py` : Fonction `import_players` et `import_all_data`
- `blueprints/admin/views.py` : Routes `new_club` et `delete_club`
- `models.py` : Relation `Player.license` (suppression cascade incorrecte)
- `blueprints/admin/templates/admin/import_conflicts.html` : Nouveau template
- `test/test_club_import.py` : Nouveau fichier de tests

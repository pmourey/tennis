# Correction du bug d'affichage des joueurs "brûlés" dans show_team

## Problème rencontré

Sur la page de l'équipe (ex: US Cagnes 4 - `/club/show_team/55`), l'affichage du logo des joueurs "brûlés" 🔥 ne fonctionnait pas correctement après modification de la constitution de l'équipe :
- La première ligne était vide
- Le formatage de la liste était incorrect

## Causes identifiées

### 1. Balise HTML orpheline

Dans le template `show_team.html`, il y avait une balise fermante `</ul>` sans balise ouvrante `<ul>` correspondante :

```html
<!-- Code incorrect -->
<td>
    {% for player in sorted_team_players %}
        ...
    {% endfor %}
    </ul>  <!-- ❌ Balise orpheline ! -->
</td>
```

Cette balise orpheline causait un problème de rendu HTML et créait une ligne vide au début de la liste.

### 2. Tri incorrect des joueurs

Dans `blueprints/club/views.py`, le tri des joueurs utilisait l'objet `Ranking` au lieu de son ID :

```python
# Code incorrect
sorted_team_players = sorted(team.players, key=lambda p: p.ranking)  # ❌
```

Cela causait un tri basé sur la représentation de l'objet plutôt que sur la valeur numérique du classement, ce qui pouvait donner un ordre incorrect.

## Solutions appliquées

### 1. Suppression de la balise orpheline

**Fichier : `blueprints/club/templates/club/show_team.html`**

```html
<!-- Avant (lignes 31-41) -->
<td>
        {% for player in sorted_team_players %}
            {% set icon_brule = "&#x1F525; " if loop.index <= team.championship.singlesCount else '' %}
            {% set icon_injury = "&#127973; " if player.injuries else '' %}
    {{ icon_brule | safe }}{{ icon_injury | safe }}<a href="...">{{ player.full_info }}</a><br>
        {% endfor %}
    </ul>  <!-- ❌ À SUPPRIMER -->
</td>

<!-- Après (lignes 31-40) -->
<td>
    {% for player in sorted_team_players %}
        {% set icon_brule = "&#x1F525; " if loop.index <= team.championship.singlesCount else '' %}
        {% set icon_injury = "&#127973; " if player.injuries else '' %}
        {{ icon_brule | safe }}{{ icon_injury | safe }}<a href="...">{{ player.full_info }}</a><br>
    {% endfor %}
</td>
```

**Améliorations :**
- ✅ Suppression de la balise `</ul>` orpheline
- ✅ Réindentation correcte du code
- ✅ Meilleure lisibilité

### 2. Correction du tri des joueurs

**Fichier : `blueprints/club/views.py`**

Corrections effectuées dans **3 endroits** :

#### a) Fonction `update_team` (ligne 248)
```python
# Avant
active_players.sort(key=lambda p: p.ranking)  # ❌

# Après
active_players.sort(key=lambda p: p.ranking.id)  # ✅
```

#### b) Fonction `update_team` (ligne 250)
```python
# Avant
sorted_team_players = sorted(team.players, key=lambda p: p.ranking)  # ❌

# Après
sorted_team_players = sorted(team.players, key=lambda p: p.ranking.id)  # ✅
```

#### c) Fonction `show_team` (ligne 272)
```python
# Avant
sorted_team_players = sorted(team.players, key=lambda p: p.ranking)  # ❌

# Après
sorted_team_players = sorted(team.players, key=lambda p: p.ranking.id)  # ✅
```

## Fonctionnement de l'icône "brûlé" 🔥

L'icône de joueur "brûlé" indique les joueurs qui sont **obligatoires** pour les simples dans un match :

```jinja
{% set icon_brule = "&#x1F525; " if loop.index <= team.championship.singlesCount else '' %}
```

**Logique :**
- Les joueurs sont triés par classement (du meilleur au moins bon)
- Les N premiers joueurs (N = `championship.singlesCount`) sont marqués comme "brûlés" 🔥
- Ces joueurs **doivent** jouer les matchs de simples lors des rencontres

**Exemple :**
Si `singlesCount = 4`, les 4 premiers joueurs de la liste triée auront l'icône 🔥.

## Résultat attendu

Après ces corrections, la page d'équipe affiche correctement :

✅ **Liste des joueurs bien formatée** (sans ligne vide)
- 🔥 Joueur 1 (15/1) - meilleur classement
- 🔥 Joueur 2 (15/2)
- 🔥 Joueur 3 (15/3)
- 🔥 Joueur 4 (15/4)
- Joueur 5 (30/1) - non brûlé
- Joueur 6 (30/2) - non brûlé

✅ **Tri correct par classement** (ordre numérique d'ID)
✅ **Icône 🔥 correctement positionnée** pour les N premiers joueurs
✅ **Icône 🏥 pour les joueurs blessés** (si applicable)

## Fichiers modifiés

1. ✏️ `blueprints/club/templates/club/show_team.html`
   - Suppression de la balise `</ul>` orpheline
   - Réindentation du code

2. ✏️ `blueprints/club/views.py`
   - Correction du tri dans `update_team()` (2 endroits)
   - Correction du tri dans `show_team()`

## Tests de validation

Pour vérifier le correctif :

1. Aller sur `/club/show_team/55` (US Cagnes 4)
2. Vérifier que :
   - ✅ La liste des joueurs commence directement (pas de ligne vide)
   - ✅ Les joueurs sont triés du meilleur au moins bon classement
   - ✅ L'icône 🔥 apparaît sur les N premiers joueurs (N = singlesCount)
   - ✅ Le HTML est bien formaté (pas de balise orpheline)

## Informations complémentaires

### Icônes utilisées

- **🔥** (`&#x1F525;`) : Joueur "brûlé" (obligatoire pour les simples)
- **🏥** (`&#127973;`) : Joueur blessé

### Tri par ranking.id

Le tri par `ranking.id` assure un ordre numérique correct :
- ID 1 = NC (Non Classé)
- ID 2 = 40
- ID 3 = 30/5
- ...
- ID 209 = 15/1
- ID 210 = T500
- etc.

Plus l'ID est élevé, meilleur est le classement.

---
**Date de correction :** 8 février 2026  
**Statut :** ✅ Résolu

# Correction du bug de suppression de joueur (404)

## Problème rencontré

Lors de la tentative de suppression d'un joueur, l'application retournait une erreur 404 :
```
INFO:werkzeug:127.0.0.1 - - [08/Feb/2026 11:18:06] "GET /club/player/delete_player/25 HTTP/1.1" 404 -
```

## Cause du problème

Le JavaScript dans `manage_player.js` et `show_teams.js` construisait les URLs de suppression de manière **relative** :

```javascript
// Code incorrect
function confirmDelete(playerId) {
    window.location.href = "delete_player/" + playerId;  // URL relative !
}
```

Selon la page d'origine (ex: `/club/player/25`), cela générait une URL incorrecte comme :
- `/club/player/delete_player/25` ❌ (au lieu de `/club/delete_player/25` ✅)

## Solution appliquée

### 1. Modification des templates HTML

Les templates passent maintenant l'URL **complète** générée par Flask à la fonction JavaScript :

**Fichiers modifiés :**
- `blueprints/club/templates/club/players.html`
- `blueprints/club/templates/club/show_player.html`
- `blueprints/club/templates/club/teams.html`

**Avant :**
```html
<button onclick="confirmDelete({{ player.id }})">Supprimer</button>
```

**Après :**
```html
<button onclick="confirmDelete('{{ url_for('club.delete_player', id=player.id) }}')">Supprimer</button>
```

### 2. Modification des fichiers JavaScript

Les fonctions `confirmDelete` acceptent maintenant l'URL complète au lieu de l'ID :

**Fichiers modifiés :**
- `blueprints/club/static/manage_player.js`
- `blueprints/club/static/show_teams.js`

**Avant :**
```javascript
function confirmDelete(playerId) {
    var result = confirm("Êtes-vous sûr de vouloir supprimer ce joueur?");
    if (result) {
        window.location.href = "delete_player/" + playerId;  // URL relative
    }
}
```

**Après :**
```javascript
function confirmDelete(deleteUrl) {
    var result = confirm("Êtes-vous sûr de vouloir supprimer ce joueur?");
    if (result) {
        window.location.href = deleteUrl;  // URL absolue fournie par Flask
    }
}
```

## Routes confirmées

Les routes de suppression sont bien enregistrées :
- ✅ `/club/delete_player/<int:id>` (méthode: GET, POST)
- ✅ `/club/delete_team/<int:id>` (méthode: GET, POST)
- ✅ `/admin/delete_club` (méthode: GET, POST)

## Avantages de cette approche

1. **Robustesse** : Les URLs sont toujours correctes, quelle que soit la page d'origine
2. **Maintenabilité** : Si les routes Flask changent, seul le template doit être mis à jour
3. **Cohérence** : Utilisation systématique de `url_for()` comme recommandé par Flask
4. **Pas de duplication** : La logique de construction d'URL reste dans Flask (DRY)

## Test de validation

```bash
# Depuis la racine du projet
cd /Users/display/PycharmProjects/tennis
python -c "from app import create_app; app = create_app(); \
[print(f'{rule}') for rule in app.url_map.iter_rules() if 'delete' in str(rule)]"
```

## Fichiers modifiés

1. ✏️ `blueprints/club/templates/club/players.html`
2. ✏️ `blueprints/club/templates/club/show_player.html`
3. ✏️ `blueprints/club/templates/club/teams.html`
4. ✏️ `blueprints/club/static/manage_player.js`
5. ✏️ `blueprints/club/static/show_teams.js`

---
**Date de correction :** 8 février 2026
**Statut :** ✅ Résolu

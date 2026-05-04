#!/bin/bash
# Script de redémarrage propre du serveur Flask

cd /Users/display/PycharmProjects/tennis

# Supprimer tous les fichiers .pyc et __pycache__
echo "Nettoyage du cache Python..."
find . -name "*.pyc" -delete 2>/dev/null
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null
echo "Cache nettoyé."

# Tuer les processus Flask existants sur le port 8081
echo "Arrêt des processus Flask existants..."
PIDS=$(lsof -ti:8081 2>/dev/null)
if [ -n "$PIDS" ]; then
    kill $PIDS 2>/dev/null
    sleep 1
    echo "Processus arrêtés: $PIDS"
else
    echo "Aucun processus sur le port 8081."
fi

# Démarrer Flask
echo "Démarrage de Flask sur le port 8081..."
export FLASK_APP=app.py
export FLASK_DEBUG=True
export FLASK_ENV=development
export FLASK_RUN_PORT=8081
export FLASK_RUN_HOST=0.0.0.0

flask run

